"""User collection CRUD service.

Provides functions to query, update, and compute statistics
over the user's relic collection.
"""

from __future__ import annotations

from datetime import datetime, timezone

from src.db.database import get_db


async def get_all_relics_with_status(
    tier: str | None = None,
    vaulted: int | None = None,
    obtained: int | None = None,
) -> list[dict]:
    """Return all relics joined with their collection status.

    Args:
        tier: Filter by tier name (e.g. "Lith").
        vaulted: Filter by vaulted status (0 or 1).
        obtained: Filter by obtained status (0 or 1).

    Returns:
        A list of dicts with keys:
            id, name, tier, vaulted, is_baro, obtained, quantity,
            notes, drop_count, total_ducats
    """
    db = await get_db()

    query = """
        SELECT
            r.id,
            r.name,
            r.tier,
            r.vaulted,
            r.is_baro,
            COALESCE(c.obtained, 0) AS obtained,
            COALESCE(c.quantity, 0) AS quantity,
            COALESCE(c.notes, '') AS notes,
            (SELECT COUNT(*) FROM relic_drops rd WHERE rd.relic_id = r.id) AS drop_count,
            COALESCE(
                (SELECT MAX(rd2.ducat_value) FROM relic_drops rd2 WHERE rd2.relic_id = r.id),
                0
            ) AS total_ducats
        FROM relics r
        LEFT JOIN collection c ON c.relic_id = r.id
    """

    conditions = []
    params: list = []

    if tier is not None:
        conditions.append("r.tier = ?")
        params.append(tier)
    if vaulted is not None:
        conditions.append("r.vaulted = ?")
        params.append(vaulted)
    if obtained is not None:
        conditions.append("COALESCE(c.obtained, 0) = ?")
        params.append(obtained)

    if conditions:
        query += " WHERE " + " AND ".join(conditions)

    query += " ORDER BY r.tier, r.name"

    cursor = await db.execute(query, params)
    rows = await cursor.fetchall()

    return [dict(row) for row in rows]


async def get_relic_details(relic_id: int) -> dict | None:
    """Return full details for a single relic including its drops.

    Returns:
        A dict with keys: id, name, tier, introduced, vaulted,
        vaulted_version, is_baro, obtained, quantity, notes, drops (list).
        Returns None if the relic is not found.
    """
    db = await get_db()

    cursor = await db.execute(
        """
        SELECT
            r.id, r.name, r.tier, r.introduced, r.vaulted,
            r.vaulted_version, r.is_baro,
            COALESCE(c.obtained, 0) AS obtained,
            COALESCE(c.quantity, 0) AS quantity,
            COALESCE(c.notes, '') AS notes
        FROM relics r
        LEFT JOIN collection c ON c.relic_id = r.id
        WHERE r.id = ?
        """,
        (relic_id,),
    )
    row = await cursor.fetchone()
    if not row:
        return None

    relic = dict(row)

    # Fetch drops
    drop_cursor = await db.execute(
        """
        SELECT id, item_name, part_name, rarity, item_count, ducat_value
        FROM relic_drops
        WHERE relic_id = ?
        ORDER BY rarity, item_name
        """,
        (relic_id,),
    )
    drops = await drop_cursor.fetchall()
    relic["drops"] = [dict(d) for d in drops]

    return relic


async def toggle_obtained(relic_id: int) -> dict:
    """Toggle the obtained status of a relic (0 -> 1 or 1 -> 0).

    Returns:
        The updated collection entry as a dict with keys:
            relic_id, obtained, quantity, notes.
    """
    db = await get_db()
    now = datetime.now(timezone.utc).isoformat()

    # Get current state
    cursor = await db.execute(
        "SELECT obtained FROM collection WHERE relic_id = ?",
        (relic_id,),
    )
    row = await cursor.fetchone()
    if not row:
        # Create entry if missing
        await db.execute(
            """
            INSERT INTO collection (relic_id, obtained, quantity, notes, updated_at)
            VALUES (?, 1, 0, '', ?)
            """,
            (relic_id, now),
        )
        await db.commit()
        return {"relic_id": relic_id, "obtained": 1, "quantity": 0, "notes": ""}

    new_obtained = 0 if row["obtained"] else 1
    await db.execute(
        "UPDATE collection SET obtained = ?, updated_at = ? WHERE relic_id = ?",
        (new_obtained, now, relic_id),
    )
    await db.commit()

    return {"relic_id": relic_id, "obtained": new_obtained}


async def set_quantity(relic_id: int, quantity: int) -> dict:
    """Set the quantity of a specific relic the user owns.

    Args:
        relic_id: The relic's database ID.
        quantity: New quantity (must be >= 0).

    Returns:
        The updated collection entry as a dict.
    """
    if quantity < 0:
        quantity = 0

    db = await get_db()
    now = datetime.now(timezone.utc).isoformat()

    # Upsert collection entry
    await db.execute(
        """
        INSERT INTO collection (relic_id, obtained, quantity, notes, updated_at)
        VALUES (?, 0, ?, '', ?)
        ON CONFLICT(relic_id) DO UPDATE SET
            quantity = excluded.quantity,
            updated_at = excluded.updated_at
        """,
        (relic_id, quantity, now),
    )
    await db.commit()

    return {"relic_id": relic_id, "quantity": quantity}


async def get_overview_stats() -> dict:
    """Compute and return overview statistics for the user's collection.

    Returns:
        A dict with keys:
            total_relics, obtained_relics, vaulted_relics,
            total_ducat_value, completion_pct, by_tier
        where by_tier maps tier names to {total, obtained} dicts.
    """
    db = await get_db()

    # Total relics
    cursor = await db.execute("SELECT COUNT(*) AS cnt FROM relics")
    total = (await cursor.fetchone())["cnt"]

    # Obtained relics
    cursor = await db.execute(
        "SELECT COUNT(*) AS cnt FROM collection WHERE obtained = 1"
    )
    obtained = (await cursor.fetchone())["cnt"]

    # Vaulted relics
    cursor = await db.execute(
        "SELECT COUNT(*) AS cnt FROM relics WHERE vaulted = 1"
    )
    vaulted = (await cursor.fetchone())["cnt"]

    # Total ducat value: sum of best ducat value per obtained relic
    cursor = await db.execute(
        """
        SELECT COALESCE(SUM(sub.best_ducats), 0) AS total
        FROM collection c
        JOIN (
            SELECT relic_id, MAX(ducat_value) AS best_ducats
            FROM relic_drops
            GROUP BY relic_id
        ) sub ON sub.relic_id = c.relic_id
        WHERE c.obtained = 1
        """
    )
    total_ducats = (await cursor.fetchone())["total"]

    # Completion percentage
    completion_pct = round((obtained / total * 100), 1) if total > 0 else 0.0

    # By-tier breakdown
    cursor = await db.execute(
        """
        SELECT
            r.tier,
            COUNT(*) AS total,
            SUM(CASE WHEN COALESCE(c.obtained, 0) = 1 THEN 1 ELSE 0 END) AS obtained
        FROM relics r
        LEFT JOIN collection c ON c.relic_id = r.id
        GROUP BY r.tier
        ORDER BY
            CASE r.tier
                WHEN 'Lith' THEN 1
                WHEN 'Meso' THEN 2
                WHEN 'Neo' THEN 3
                WHEN 'Axi' THEN 4
                WHEN 'Requiem' THEN 5
                ELSE 6
            END
        """
    )
    tier_rows = await cursor.fetchall()
    by_tier = {}
    for row in tier_rows:
        by_tier[row["tier"]] = {"total": row["total"], "obtained": row["obtained"]}

    return {
        "total_relics": total,
        "obtained_relics": obtained,
        "vaulted_relics": vaulted,
        "total_ducat_value": total_ducats,
        "completion_pct": completion_pct,
        "by_tier": by_tier,
    }
