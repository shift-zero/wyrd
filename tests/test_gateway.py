"""Tests for gateway module — Phase 22: Surface Polish."""
import pytest
from src.gateway import _resolve_world


def test_resolve_world_returns_session_world():
    """When world_in_session is set, it should be returned directly."""
    fake = object()
    result, err = _resolve_world(fake, [], 0)
    assert result is fake
    assert err is None


def test_resolve_world_no_world_no_list():
    """When no world is in session and no worlds are available, return error."""
    result, err = _resolve_world(None, [], 0)
    assert result is None
    assert err is not None
    assert "generate or select" in err


def test_resolve_world_no_session_no_worlds():
    """When no session and sorted_worlds is empty."""
    result, err = _resolve_world(None, [], 5)
    assert result is None
    assert err is not None
