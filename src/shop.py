"""
wyrd — Shop / Market System for Embodied Play Mode.

Settlement shops with economy-themed inventories, buy/sell mechanics,
and creature loot generation. Wired into the embody module via
`_handle_market()` and `_generate_creature_loot()`.
"""

import random
from collections import Counter

from .render import ANSI_RESET, ANSI_BOLD, ANSI_DIM, _color
from .economy import ECONOMY_ICONS

# ── Item Tables ────────────────────────────────────────────────────────

# Items organized by settlement economy type
# Each entry: (name, base_price, category)
_SHOP_ITEMS: dict[str, list[tuple[str, int, str]]] = {
    "farming": [
        ("fresh bread", 3, "food"),
        ("wheel of cheese", 8, "food"),
        ("dried herbs", 5, "herb"),
        ("sack of grain", 4, "food"),
        ("basket of apples", 2, "food"),
        ("flask of cider", 6, "drink"),
        ("sturdy straw hat", 10, "clothing"),
        ("woven basket", 7, "tool"),
    ],
    "logging": [
        ("sturdy oak plank", 8, "material"),
        ("bag of wood shavings", 2, "material"),
        ("carved wooden bowl", 6, "craft"),
        ("pine resin jar", 5, "material"),
        ("fine ash bow", 25, "weapon"),
        ("wooden shield", 20, "armor"),
        ("whittling knife", 12, "tool"),
        ("tinderbox", 4, "tool"),
    ],
    "mining": [
        ("chunk of iron ore", 10, "material"),
        ("small ruby", 40, "gem"),
        ("sharp pickaxe", 18, "tool"),
        ("bag of salt", 5, "food"),
        ("iron dagger", 22, "weapon"),
        ("candle lantern", 9, "tool"),
        ("lump of coal", 3, "material"),
        ("silver bracelet", 35, "jewelry"),
    ],
    "fishing": [
        ("smoked fish", 5, "food"),
        ("string of pearls", 30, "gem"),
        ("fishing net", 12, "tool"),
        ("jar of fish oil", 4, "material"),
        ("dried squid", 7, "food"),
        ("coral pendant", 20, "jewelry"),
        ("seashell whistle", 3, "trinket"),
        ("anchovy paste", 6, "food"),
    ],
    "trading": [
        ("silk scarf", 30, "clothing"),
        ("incense bundle", 8, "luxury"),
        ("foreign spice jar", 15, "food"),
        ("brass compass", 40, "tool"),
        ("ornate mirror", 50, "luxury"),
        ("map of distant lands", 25, "tool"),
        ("perfume bottle", 20, "luxury"),
        ("fine leather gloves", 18, "clothing"),
    ],
    "pastoral": [
        ("sheep's wool bundle", 6, "material"),
        ("warm cloak", 15, "clothing"),
        ("goat cheese", 7, "food"),
        ("woolen blanket", 12, "tool"),
        ("leather waterskin", 5, "tool"),
        ("horn drinking cup", 4, "craft"),
        ("cured meat", 8, "food"),
        ("shepherd's crook", 3, "tool"),
    ],
}

_UNIVERSAL_ITEMS: list[tuple[str, int, str]] = [
    ("healing salve", 15, "potion"),
    ("trail rations (3 days)", 6, "food"),
    ("bandages", 4, "tool"),
]

# Creature loot tables keyed by creature type
_CREATURE_LOOT: dict[str, list[tuple[str, int, str]]] = {
    "beast": [
        ("thick fur pelt", 12, "material"),
        ("sharp fang", 8, "craft"),
        ("tough hide", 10, "material"),
        ("bone club", 6, "weapon"),
        ("claw talisman", 15, "jewelry"),
    ],
    "monster": [
        ("vial of venom", 20, "potion"),
        ("chimeric scale", 25, "material"),
        ("glowing eye", 30, "gem"),
        ("horn", 18, "craft"),
        ("strange egg", 18, "trinket"),
    ],
    "humanoid": [
        ("rusty sword", 10, "weapon"),
        ("stolen coin pouch", 20, "valuable"),
        ("crude map", 12, "tool"),
        ("tarnished ring", 15, "jewelry"),
        ("old shield", 14, "armor"),
    ],
    "dragon": [
        ("dragon scale", 100, "material"),
        ("wyrm tooth", 80, "craft"),
        ("glimmering gem", 150, "gem"),
        ("ancient scroll", 120, "tool"),
    ],
    "undead": [
        ("cold iron coin", 10, "valuable"),
        ("bone powder", 5, "material"),
        ("grave dust", 8, "potion"),
        ("chill touch ring", 35, "jewelry"),
    ],
    "elemental": [
        ("crystallized essence", 45, "material"),
        ("ember shard", 30, "gem"),
        ("void crystal", 60, "gem"),
        ("elemental core", 50, "craft"),
    ],
}

_DEFAULT_LOOT: list[tuple[str, int, str]] = [
    ("odd trinket", 5, "trinket"),
    ("scrap metal", 3, "material"),
    ("small coin", 2, "valuable"),
    ("bone fragment", 1, "craft"),
]


# ── Shop Generation ────────────────────────────────────────────────────


def shop_items_for_economy(economy_type: str, rng: random.Random,
                           population: int) -> list[dict]:
    """Generate a shop's inventory based on settlement economy.

    Args:
        economy_type: The settlement's economy type
        rng: Seeded random state
        population: Settlement population (larger = more items)

    Returns:
        List of item dicts with name, price, category, stock
    """
    items = []
    economy_items = _SHOP_ITEMS.get(economy_type, _SHOP_ITEMS["trading"])

    num_items = min(len(economy_items), max(3, population // 200))
    num_items = rng.randint(max(2, num_items - 1), num_items + 1)
    chosen = rng.sample(economy_items, min(num_items, len(economy_items)))

    for name, base_price, category in chosen:
        price_variance = rng.uniform(0.8, 1.2)
        price = max(1, int(base_price * price_variance))
        items.append({
            "name": name,
            "price": price,
            "category": category,
            "stock": rng.randint(1, 5),
        })

    num_universal = rng.randint(1, 2)
    universal = rng.sample(_UNIVERSAL_ITEMS, num_universal)
    for name, base_price, category in universal:
        items.append({"name": name, "price": base_price,
                      "category": category, "stock": 3})

    return items


def creature_loot(creature_type: str, tier: int,
                  rng: random.Random) -> list[dict]:
    """Generate loot from a defeated creature.

    Args:
        creature_type: The creature's type (beast, monster, etc.)
        tier: Creature tier (1-5)
        rng: Seeded random state

    Returns:
        List of item dicts with name, price, category
    """
    loot_table = _CREATURE_LOOT.get(creature_type.lower(), _DEFAULT_LOOT)
    num_items = rng.randint(1, 1 + tier // 2)
    items = rng.sample(loot_table, min(num_items, len(loot_table)))
    return [{"name": name, "price": price * tier, "category": cat}
            for name, price, cat in items]


def estimate_item_value(item_name: str) -> int:
    """Estimate the base gold value of an item by name lookup."""
    for name, price, _ in _UNIVERSAL_ITEMS:
        if name == item_name:
            return price
    for _, items_list in _SHOP_ITEMS.items():
        for name, price, _ in items_list:
            if name == item_name:
                return price
    for _, items_list in _CREATURE_LOOT.items():
        for name, price, _ in items_list:
            if name == item_name:
                return price
    for name, price, _ in _DEFAULT_LOOT:
        if name == item_name:
            return price
    return 5


# ── Rendering ──────────────────────────────────────────────────────────


def render_shop_settlement_name(settlement_name: str, economy_type: str | None,
                                gold: int) -> str:
    """Render top of the market display."""
    economy_label = economy_type or "general"
    econ_icon = ECONOMY_ICONS.get(economy_label, "\U0001f3ea")
    return (
        f"  {ANSI_BOLD}── {settlement_name} Market ──{ANSI_RESET}\n"
        f"  {econ_icon} {economy_label.title()} Town\n"
    )


def render_item_list(item: dict, index: int) -> str:
    """Render a single item row."""
    name = item["name"]
    price = item["price"]
    stock = item.get("stock", 1)
    stock_str = f" ({stock} left)" if stock > 1 else ""
    price_str = f"{_color(220)}{price}g{ANSI_RESET}"
    return f"  {index+1}. {name}  —  {price_str}{stock_str}"


def render_sell_inventory(inventory: list[str]) -> list[str]:
    """Render player inventory for selling. Returns display lines."""
    if not inventory:
        return ["  Your inventory is empty."]

    counts = Counter(inventory)
    lines = [f"  {ANSI_BOLD}Your Items:{ANSI_RESET}"]
    for i, (item, count) in enumerate(sorted(counts.items())):
        sell_price = max(1, estimate_item_value(item) // 2)
        count_str = f" x{count}" if count > 1 else ""
        lines.append(
            f"  {i+1}. {item}{count_str} — "
            f"sell for {_color(220)}{sell_price}g{ANSI_RESET}"
        )
    lines.append("")
    lines.append(f"  {ANSI_DIM}[#] sell  [q] back to market{ANSI_RESET}")
    return lines
