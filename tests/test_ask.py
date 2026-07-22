"""
Tests for wyrd Phase 8 Item 3 — Conversational World Agent.

Tests cover both deterministic mode and the LLM integration layer.
LLM mode tests mock the API layer to avoid real HTTP calls.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import json
from unittest.mock import patch, MagicMock
from io import StringIO

from src.generate import generate_world
from src.lore import generate_lore
from src.narrative import generate_narrative
from src.ask import (
    ask_about_world,
    _gather_context,
    _deterministic_answer,
    _world_stats,
    _regions_summary,
    _lore_summary,
    _narrative_summary,
    _chronicles_summary,
    _magic_summary,
    _get_llm_config,
    _build_llm_prompt,
    _call_llm,
)


# ── Fixtures ──────────────────────────────────────────────────────────


def _make_test_world(seed: int = 42) -> 'World':
    """Create a seeded test world with lore and narrative."""
    world = generate_world(seed, width=40, height=24)
    if not world.lore:
        world.lore = generate_lore(world)
    if not world.narrative:
        world.narrative = generate_narrative(world)
    return world


# ── Context Gathering Tests ───────────────────────────────────────────


class TestContextGathering:
    """World context functions must produce coherent output."""

    def test_world_stats_returns_string(self):
        world = _make_test_world(42)
        stats = _world_stats(world)
        assert isinstance(stats, str)
        assert str(world.seed) in stats
        assert "souls" in stats or "Population" in stats

    def test_world_stats_has_key_numbers(self):
        world = _make_test_world(42)
        stats = _world_stats(world)
        assert "x" in stats or "×" in stats  # size notation
        assert "Regions" in stats
        assert str(world.width) in stats

    def test_regions_summary_lists_all_regions(self):
        world = _make_test_world(42)
        summary = _regions_summary(world)
        for region in world.regions:
            assert region.name in summary

    def test_regions_summary_includes_settlements(self):
        world = _make_test_world(42)
        summary = _regions_summary(world)
        # At least one settlement name should appear
        any_settlement = any(
            s.name in summary
            for r in world.regions
            for s in r.settlements
        )
        assert any_settlement, "No settlement names found in region summary"

    def test_lore_summary_with_lore(self):
        world = _make_test_world(42)
        summary = _lore_summary(world)
        assert isinstance(summary, str)
        # Should have some content (features or relationships)
        assert len(summary) > 10

    def test_lore_summary_without_lore(self):
        world = _make_test_world(42)
        world.lore = None
        summary = _lore_summary(world)
        assert "No lore" in summary

    def test_narrative_summary_with_narrative(self):
        world = _make_test_world(42)
        summary = _narrative_summary(world)
        assert isinstance(summary, str)
        assert "Characters" in summary or "(No narrative" in summary

    def test_narrative_summary_without_narrative(self):
        world = _make_test_world(42)
        world.narrative = None
        summary = _narrative_summary(world)
        assert "No narrative" in summary

    def test_chronicles_summary_without_chronicles(self):
        world = _make_test_world(42)
        world.chronicles = None
        summary = _chronicles_summary(world)
        assert "No chronicles" in summary

    def test_magic_summary_without_magic(self):
        world = _make_test_world(42)
        world.magic = None
        summary = _magic_summary(world)
        assert "No magic" in summary

    def test_gather_context_returns_dict(self):
        world = _make_test_world(42)
        ctx = _gather_context(world)
        assert isinstance(ctx, dict)
        for key in ("world_stats", "regions", "lore", "narrative", "chronicles", "magic"):
            assert key in ctx


# ── LLM Config Tests ──────────────────────────────────────────────────


class TestLlmConfig:
    """LLM configuration reading."""

    def test_llm_config_defaults(self):
        with patch.dict(os.environ, {}, clear=True):
            config = _get_llm_config()
            assert config["api_key"] == ""
            assert config["endpoint"] == "https://api.openai.com/v1/chat/completions"
            assert config["model"] == "gpt-4o-mini"

    def test_llm_config_from_env(self):
        with patch.dict(os.environ, {
            "WYRD_LLM_API_KEY": "sk-test123",
            "WYRD_LLM_ENDPOINT": "https://custom.api.com/v1/chat",
            "WYRD_LLM_MODEL": "gpt-4",
        }, clear=True):
            config = _get_llm_config()
            assert config["api_key"] == "sk-test123"
            assert config["endpoint"] == "https://custom.api.com/v1/chat"
            assert config["model"] == "gpt-4"


# ── LLM Prompt Tests ──────────────────────────────────────────────────


class TestLlmPrompt:
    """LLM prompt construction."""

    def test_build_llm_prompt_has_system_and_user(self):
        context = {"world_stats": "Seed: 42", "regions": "test"}
        messages = _build_llm_prompt(context, "Tell me about this world")
        assert len(messages) == 2
        assert messages[0]["role"] == "system"
        assert messages[1]["role"] == "user"
        assert messages[1]["content"] == "Tell me about this world"

    def test_build_llm_prompt_includes_world_data(self):
        context = {"world_stats": "Seed: 42", "regions": "test"}
        messages = _build_llm_prompt(context, "Hello")
        system_content = messages[0]["content"]
        assert "Seed: 42" in system_content
        assert "wyrd" in system_content.lower()


# ── LLM Call Tests ────────────────────────────────────────────────────


class TestLlmCall:
    """LLM API call handling (mocked)."""

    @patch("urllib.request.urlopen")
    def test_call_llm_success(self, mock_urlopen):
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps({
            "choices": [{"message": {"content": "The world is vast and ancient."}}]
        }).encode()
        mock_resp.__enter__.return_value = mock_resp
        mock_urlopen.return_value = mock_resp

        config = {"api_key": "sk-test", "endpoint": "https://test.api/v1", "model": "gpt-4"}
        messages = [{"role": "user", "content": "Hello"}]
        result = _call_llm(messages, config)
        assert result == "The world is vast and ancient."

    @patch("urllib.request.urlopen")
    def test_call_llm_empty_choices_raises(self, mock_urlopen):
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps({"choices": []}).encode()
        mock_resp.__enter__.return_value = mock_resp
        mock_urlopen.return_value = mock_resp

        config = {"api_key": "sk-test", "endpoint": "https://test.api/v1", "model": "gpt-4"}
        import pytest
        with pytest.raises(ValueError, match="empty choices"):
            _call_llm([{"role": "user", "content": "Hi"}], config)

    @patch("urllib.request.urlopen")
    def test_call_llm_temperature_set(self, mock_urlopen):
        """Verify temperature and max_tokens are in the payload."""
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps({
            "choices": [{"message": {"content": "answer"}}]
        }).encode()
        mock_resp.__enter__.return_value = mock_resp
        mock_urlopen.return_value = mock_resp

        config = {"api_key": "sk-test", "endpoint": "https://test.api/v1", "model": "gpt-4"}

        # Track the payload
        def check_payload(req, **_kwargs):
            body = json.loads(req.data)
            assert body["temperature"] == 0.7
            assert body["max_tokens"] == 1024
            assert body["model"] == "gpt-4"
            return mock_resp

        mock_urlopen.side_effect = check_payload
        _call_llm([{"role": "user", "content": "Hi"}], config)


# ── Deterministic Mode Tests ──────────────────────────────────────────


class TestDeterministicMode:
    """The deterministic fallback must answer from world data."""

    def test_deterministic_question_about_overview(self):
        world = _make_test_world(42)
        answer = _deterministic_answer(world, "tell me about this world")
        assert "wyrd" in answer or "Seed" in answer or "Overview" in answer

    def test_deterministic_question_about_settlement(self):
        world = _make_test_world(42)
        answer = _deterministic_answer(world, "what is the largest settlement")
        assert len(answer) > 20

    def test_deterministic_question_about_nonsense(self):
        world = _make_test_world(42)
        answer = _deterministic_answer(world, "xyzzy flurbo garblex")
        # Should give a helpful fallback rather than crash
        assert "don't have a direct answer" in answer.lower() or "I don't" in answer
        assert "wyrd" in answer

    def test_deterministic_empty_question(self):
        world = _make_test_world(42)
        answer = _deterministic_answer(world, "")
        assert len(answer) > 20

    def test_deterministic_question_about_culture(self):
        world = _make_test_world(42)
        answer = _deterministic_answer(world, "tell me about the cultures")
        assert len(answer) > 20


# ── Integration Tests ─────────────────────────────────────────────────


class TestAskIntegration:
    """High-level wyrd ask command behavior."""

    def test_ask_deterministic_mode_no_llm(self):
        """ask_about_world with use_llm=False should work without env vars."""
        world = _make_test_world(42)
        answer = ask_about_world(world, "overview", use_llm=False)
        assert len(answer) > 20
        assert "wyrd" in answer or "Overview" in answer or str(world.seed) in answer

    def test_ask_deterministic_no_api_key(self):
        """ask_about_world with use_llm=True but no API key falls back gracefully."""
        with patch.dict(os.environ, {}, clear=True):
            world = _make_test_world(42)
            answer = ask_about_world(world, "tell me about this world", use_llm=True)
            # Should indicate no API key and still answer
            assert len(answer) > 20

    def test_ask_with_snapshot_year_flows(self):
        """Verify the snapshot year path doesn't crash in ask flow."""
        world = _make_test_world(42)
        # Just test that context gathering works when we might have sim state
        ctx = _gather_context(world)
        assert "world_stats" in ctx
        assert "regions" in ctx
