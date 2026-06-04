"""Warframe Market API client for fetching item prices and statistics."""

from __future__ import annotations

from datetime import datetime, timezone

import httpx

from src.config import MARKET_API_BASE


def _headers(platform: str = "pc") -> dict[str, str]:
    """Return standard headers for Warframe Market API requests."""
    return {
        "Platform": platform,
        "Language": "en",
        "Accept": "application/json",
    }


def get_item_statistics(
    url_name: str, platform: str = "pc"
) -> dict | None:
    """Fetch price statistics for a single item from Warframe Market.

    Args:
        url_name: The URL-friendly item name (e.g. "ash_prime_set").
        platform: Target platform ("pc", "ps4", "xb1", "switch").

    Returns:
        A dict with keys: url_name, item_display_name, avg_price,
        median_price, min_price, max_price, volume, orders_count,
        platform, cached_at.  Returns None on failure.
    """
    url = f"{MARKET_API_BASE}/items/{url_name}/statistics"
    try:
        resp = httpx.get(url, headers=_headers(platform), timeout=15)
        resp.raise_for_status()
        payload = resp.json()

        item_data = payload.get("payload", {}).get("item", {})
        statistics = item_data.get("statistics_closed", {})
        orders = payload.get("payload", {}).get("statistics_closed", {})

        # Extract values from the statistics structure
        # WF API returns statistics_closed with "48hours" and "90days" keys
        stats_48h = statistics.get("48hours", statistics)
        if isinstance(stats_48h, list) and stats_48h:
            # Take the most recent entry
            latest = stats_48h[-1] if stats_48h else {}
        elif isinstance(stats_48h, dict):
            latest = stats_48h
        else:
            latest = {}

        return {
            "url_name": url_name,
            "item_display_name": item_data.get("en", {}).get("item_name", url_name),
            "avg_price": float(latest.get("avg_price", 0)),
            "median_price": float(latest.get("median", 0)),
            "min_price": float(latest.get("min_price", 0)),
            "max_price": float(latest.get("max_price", 0)),
            "volume": int(latest.get("volume", 0)),
            "orders_count": int(latest.get("order_count", 0)),
            "platform": platform,
            "cached_at": datetime.now(timezone.utc).isoformat(),
        }
    except (httpx.HTTPError, ValueError, KeyError, TypeError):
        return None


def search_item(query: str, platform: str = "pc") -> list[dict]:
    """Search for items on Warframe Market by name.

    Args:
        query: Search string to match against item names.
        platform: Target platform.

    Returns:
        A list of matching item dicts with keys: url_name,
        item_name, trading_tax, tags.
    """
    url = f"{MARKET_API_BASE}/items"
    try:
        resp = httpx.get(url, headers=_headers(platform), timeout=15)
        resp.raise_for_status()
        payload = resp.json()

        items = payload.get("payload", {}).get("items", [])
        query_lower = query.lower()

        results = []
        for item in items:
            item_name = item.get("item_name", "")
            if query_lower in item_name.lower():
                results.append({
                    "url_name": item.get("url_name", ""),
                    "item_name": item_name,
                    "trading_tax": item.get("trading_tax", 0),
                    "tags": item.get("tags", []),
                })
        return results
    except (httpx.HTTPError, ValueError, KeyError):
        return []
