"""Data synchronization service.

Orchestrates fetching drop data from WFCD and market prices from
Warframe Market, then upserts everything into the local SQLite DB.
"""

from __future__ import annotations

from datetime import datetime, timezone

from src.db.database import get_db
from src.services.drop_data import fetch_relic_data
from src.services.market_api import get_item_statistics
from src.services.ducats import calculate_ducats_for_drop


async def sync_relics() -> dict:
    """Fetch relic data from WFCD and upsert into the database.

    Steps:
        1. Fetch normalized relic data from WFCD.
        2. For each relic, upsert into the ``relics`` table.
        3. Delete old drops for that relic and insert fresh ones.
        4. Ensure a ``collection`` entry exists for every relic.

    Returns:
        A summary dict: {relics_synced: int, drops_synced: int}.
    """
    relics = fetch_relic_data()
    db = await get_db()
    now = datetime.now(timezone.utc).isoformat()

    relics_synced = 0
    drops_synced = 0

    for relic in relics:
        # Upsert relic
        await db.execute(
            """
            INSERT INTO relics (name, tier, introduced, vaulted, vaulted_version, is_baro, last_synced)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(name) DO UPDATE SET
                tier = excluded.tier,
                introduced = excluded.introduced,
                vaulted = excluded.vaulted,
                vaulted_version = excluded.vaulted_version,
                is_baro = excluded.is_baro,
                last_synced = excluded.last_synced
            """,
            (
                relic["name"],
                relic["tier"],
                relic["introduced"],
                relic["vaulted"],
                relic["vaulted_version"],
                relic["is_baro"],
                now,
            ),
        )
        relics_synced += 1

        # Get the relic id (after upsert)
        row = await db.execute(
            "SELECT id FROM relics WHERE name = ?", (relic["name"],)
        )
        relic_row = await row.fetchone()
        if not relic_row:
            continue
        relic_id = relic_row[0]

        # Replace drops: delete old, insert new
        await db.execute(
            "DELETE FROM relic_drops WHERE relic_id = ?", (relic_id,)
        )

        for drop in relic["drops"]:
            ducat_value = calculate_ducats_for_drop(
                drop["rarity"], drop.get("item_count", 1)
            )
            await db.execute(
                """
                INSERT INTO relic_drops
                    (relic_id, item_name, part_name, rarity, item_count, ducat_value)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    relic_id,
                    drop["item_name"],
                    drop.get("part_name", ""),
                    drop["rarity"],
                    drop.get("item_count", 1),
                    ducat_value,
                ),
            )
            drops_synced += 1

        # Ensure a collection entry exists for this relic
        await db.execute(
            """
            INSERT OR IGNORE INTO collection (relic_id, obtained, quantity, notes, updated_at)
            VALUES (?, 0, 0, '', ?)
            """,
            (relic_id, now),
        )

    await db.commit()
    return {"relics_synced": relics_synced, "drops_synced": drops_synced}


async def sync_market_prices(
    url_names: list[str], platform: str = "pc"
) -> int:
    """Fetch market price statistics for a list of items and upsert into cache.

    Args:
        url_names: List of Warframe Market URL-safe item names.
        platform: Target platform.

    Returns:
        Number of items successfully synced.
    """
    db = await get_db()
    synced = 0

    for url_name in url_names:
        stats = get_item_statistics(url_name, platform)
        if stats is None:
            continue

        await db.execute(
            """
            INSERT INTO market_cache
                (item_url_name, item_display_name, avg_price, median_price,
                 min_price, max_price, volume, orders_count, platform, cached_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(item_url_name, platform) DO UPDATE SET
                item_display_name = excluded.item_display_name,
                avg_price = excluded.avg_price,
                median_price = excluded.median_price,
                min_price = excluded.min_price,
                max_price = excluded.max_price,
                volume = excluded.volume,
                orders_count = excluded.orders_count,
                cached_at = excluded.cached_at
            """,
            (
                stats["url_name"],
                stats["item_display_name"],
                stats["avg_price"],
                stats["median_price"],
                stats["min_price"],
                stats["max_price"],
                stats["volume"],
                stats["orders_count"],
                stats["platform"],
                stats["cached_at"],
            ),
        )
        synced += 1

    await db.commit()
    return synced
