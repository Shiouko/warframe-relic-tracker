"""Warframe Community Drop Tables (WFCD) data fetcher.

Fetches relic and drop data from the WFCD GitHub repository and
normalizes it into a consistent structure for the tracker.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import httpx

from src.config import CACHE_DIR, WFCD_DROP_DATA_URL
from src.services.ducats import best_ducat_value


def _extract_tier_from_name(name: str) -> str:
    """Derive the relic tier (Lith, Meso, Neo, Axi, Requiem) from its name."""
    prefix = name.split(" ")[0] if name else ""
    for tier in ("Lith", "Meso", "Neo", "Axi", "Requiem"):
        if prefix.startswith(tier):
            return tier
    return "Unknown"


def _normalize_relic(raw: dict) -> dict:
    """Convert a single raw WFCD relic entry into our normalized format."""
    name = raw.get("relic_name", raw.get("name", ""))
    tier = _extract_tier_from_name(name)

    # Parse vaulted status
    vaulted_raw = raw.get("vaulted", raw.get("is_vaulted", False))
    vaulted = 1 if vaulted_raw in (True, 1, "true", "True") else 0

    introduced = raw.get("introduced", raw.get("era", ""))
    vaulted_version = raw.get("vaulted_version", "")
    is_baro = 1 if raw.get("is_baro", False) else 0

    # Normalize drops
    raw_drops = raw.get("drops", raw.get("rewards", []))
    drops = []
    for d in raw_drops:
        item_name = d.get("item_name", d.get("name", ""))
        part_name = d.get("part_name", d.get("part", ""))
        rarity = d.get("rarity", "")
        item_count = d.get("item_count", d.get("amount", 1))
        if isinstance(item_count, str):
            try:
                item_count = int(item_count)
            except ValueError:
                item_count = 1
        drops.append({
            "item_name": item_name,
            "part_name": part_name,
            "rarity": rarity,
            "item_count": item_count,
        })

    return {
        "name": name,
        "tier": tier,
        "introduced": introduced,
        "vaulted": vaulted,
        "vaulted_version": vaulted_version,
        "is_baro": is_baro,
        "drops": drops,
    }


def fetch_relic_data() -> list[dict]:
    """Fetch and normalize relic data from WFCD GitHub.

    Returns a list of normalized relic dicts, each with:
        name, tier, introduced, vaulted, vaulted_version, is_baro, drops
    """
    response = httpx.get(WFCD_DROP_DATA_URL, timeout=30)
    response.raise_for_status()

    raw_data = response.json()

    # The WFCD data may be a list of relics directly, or wrapped in a dict
    if isinstance(raw_data, dict):
        # Could be {"relics": [...]} or keyed by relic name
        if "relics" in raw_data:
            raw_list = raw_data["relics"]
        else:
            raw_list = list(raw_data.values())
            # Filter out non-relic entries
            raw_list = [v for v in raw_list if isinstance(v, dict)]
    elif isinstance(raw_data, list):
        raw_list = raw_data
    else:
        return []

    normalized = []
    for raw_relic in raw_list:
        if not isinstance(raw_relic, dict):
            continue
        relic = _normalize_relic(raw_relic)
        if relic["name"]:
            # Compute per-drop ducat values
            for drop in relic["drops"]:
                drop["ducat_value"] = (
                    drop.get("item_count", 1)
                    * ({"Common": 15, "Uncommon": 45, "Rare": 100}.get(drop["rarity"], 15))
                )
            # Compute overall best ducat value for the relic
            relic["total_ducats"] = best_ducat_value(relic["drops"])
            normalized.append(relic)

    return normalized


def fetch_relic_data_cached(max_age_seconds: int = 3600) -> list[dict]:
    """Fetch relic data with a local file cache.

    If a cached file exists in CACHE_DIR/relics.json and is newer than
    max_age_seconds, it is used instead of making a network request.
    Otherwise, fresh data is fetched and saved to the cache.
    """
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_file = CACHE_DIR / "relics.json"

    # Try to use cache
    if cache_file.exists():
        age = time.time() - cache_file.stat().st_mtime
        if age < max_age_seconds:
            try:
                with open(cache_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, OSError):
                pass  # Cache corrupted, fetch fresh

    # Fetch fresh data
    data = fetch_relic_data()

    # Write to cache
    try:
        with open(cache_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except OSError:
        pass  # Non-fatal if cache write fails

    return data
