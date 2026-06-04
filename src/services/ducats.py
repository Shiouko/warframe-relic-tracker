"""Ducat value calculator based on item rarity."""

from __future__ import annotations

from src.config import DUCAT_VALUES


def calculate_ducat_value(rarity: str) -> int:
    """Return the ducat value for a given rarity.

    - Rare      -> 100
    - Uncommon  ->  45
    - Common    ->  15
    - Unknown   ->  15 (fallback)
    """
    return DUCAT_VALUES.get(rarity, 15)


def calculate_ducats_for_drop(rarity: str, item_count: int = 1) -> int:
    """Return total ducats for a drop considering item count."""
    return calculate_ducat_value(rarity) * item_count


def best_ducat_value(item_drops: list[dict]) -> int:
    """Calculate the best possible ducat value from a list of drops.

    In Warframe, the ducat value of a relic is determined by its best drop
    considering special cross-rarity rules:

    - If the relic has both Uncommon and Rare drops, the best value is 65
      (higher than the standard Uncommon 45, lower than Rare 100).
    - If the relic has Common drops mixed with any other rarity, the best
      value is 25 (higher than Common 15).
    - Otherwise, use the standard rarity value.

    Each drop dict is expected to have keys: 'rarity', 'item_count'.
    """
    if not item_drops:
        return 0

    rarities = set()
    for drop in item_drops:
        rarities.add(drop.get("rarity", ""))

    # Special cross-rarity rules
    if "Uncommon" in rarities and "Rare" in rarities:
        return 65
    if "Common" in rarities and len(rarities) > 1:
        return 25

    # Standard: find the highest single-rarity value
    best = 0
    for drop in item_drops:
        val = calculate_ducats_for_drop(
            drop.get("rarity", ""), drop.get("item_count", 1)
        )
        if val > best:
            best = val
    return best
