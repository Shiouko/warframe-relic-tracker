"""Async SQLite database connection manager using aiosqlite."""

from __future__ import annotations

import aiosqlite

from src.config import DB_PATH, DATA_DIR
from src.db.models import SCHEMA_SQL

_connection: aiosqlite.Connection | None = None


async def get_db() -> aiosqlite.Connection:
    """Return the shared async SQLite connection, creating it on first call.

    - WAL journal mode for better concurrency
    - Foreign keys enforced
    - Row factory set to aiosqlite.Row so columns are accessible by name
    - Tables auto-created via SCHEMA_SQL on first connection
    """
    global _connection
    if _connection is not None:
        return _connection

    # Ensure the data directory exists
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    _connection = await aiosqlite.connect(str(DB_PATH))
    _connection.row_factory = aiosqlite.Row

    # Enable WAL mode and foreign keys
    await _connection.execute("PRAGMA journal_mode=WAL")
    await _connection.execute("PRAGMA foreign_keys=ON")

    # Create all tables if they don't exist
    await _connection.executescript(SCHEMA_SQL)
    await _connection.commit()

    return _connection


async def close_db() -> None:
    """Close the database connection if open."""
    global _connection
    if _connection is not None:
        await _connection.close()
        _connection = None
