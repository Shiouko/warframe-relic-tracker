# Warframe Relic Tracker — Implementation Plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** Build a local dashboard app that tracks Warframe relic collections, shows ducat values, and displays live market prices, with a standalone installer for easy distribution.

**Architecture:** FastAPI backend serves a single-page dashboard. SQLite stores user collection and cached API data. Background sync fetches relic data from WFCD drop tables and market prices from Warframe Market API. Packaged as a standalone executable via PyInstaller + Inno Setup installer.

**Tech Stack:** Python 3.11+, FastAPI, SQLite, httpx, Jinja2, 2005 Professional CSS (Verdana/Tahoma, steel blue), PyInstaller, Inno Setup

---

## Project Structure

```
warframe-relic-tracker/
├── src/
│   ├── __init__.py
│   ├── main.py                  # Entry point, FastAPI app
│   ├── config.py                # Settings, paths, constants
│   ├── db/
│   │   ├── __init__.py
│   │   ├── database.py          # SQLite connection, init, migrations
│   │   └── models.py            # SQL schemas as constants
│   ├── services/
│   │   ├── __init__.py
│   │   ├── drop_data.py         # WFCD drop data fetching/parsing
│   │   ├── market_api.py        # Warframe Market API client
│   │   ├── ducats.py            # Ducat value calculator
│   │   ├── sync.py              # Orchestrates full data sync
│   │   └── collection.py        # User collection CRUD
│   ├── api/
│   │   ├── __init__.py
│   │   ├── relics.py            # /api/relics routes
│   │   ├── overview.py          # /api/overview route
│   │   └── collection.py        # /api/collection routes
│   └── static/
│       ├── index.html           # Dashboard SPA
│       ├── css/
│       │   └── app.css          # 2005 professional theme (Verdana, steel blue, beveled)
│       └── js/
│           └── app.js           # Frontend logic (vanilla JS, fetch API)
├── tests/
│   ├── __init__.py
│   ├── test_drop_data.py
│   ├── test_market_api.py
│   ├── test_ducats.py
│   └── test_api.py
├── installer/
│   ├── warframe-relic-tracker.spec  # PyInstaller spec
│   └── setup.iss                      # Inno Setup script
├── requirements.txt
├── pyproject.toml
├── README.md
└── .gitignore
```

---

## Phase 1: Foundation (Tasks 1–5)

### Task 1: Project Scaffolding

**Objective:** Initialize project with proper Python packaging, dependencies, and git.

**Files:**
- Create: `pyproject.toml`
- Create: `requirements.txt`
- Create: `.gitignore`
- Create: `src/__init__.py`

**Steps:**

1. Create `pyproject.toml`:
```toml
[project]
name = "warframe-relic-tracker"
version = "0.1.0"
description = "Track Warframe relic collections with ducat values and market prices"
requires-python = ">=3.11"
dependencies = [
    "fastapi>=0.115.0",
    "uvicorn[standard]>=0.34.0",
    "httpx>=0.28.0",
    "jinja2>=3.1.0",
    "aiosqlite>=0.20.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0.0",
    "pytest-asyncio>=0.25.0",
    "ruff>=0.9.0",
]
build = [
    "pyinstaller>=6.0.0",
]

[project.scripts]
relic-tracker = "src.main:run"
```

2. Create `requirements.txt`:
```
fastapi>=0.115.0
uvicorn[standard]>=0.34.0
httpx>=0.28.0
jinja2>=3.1.0
aiosqlite>=0.20.0
```

3. Create `.gitignore`:
```gitignore
__pycache__/
*.pyc
*.pyo
dist/
build/
*.spec
*.db
.env
.venv/
*.egg-info/
.ruff_cache/
```

4. Create empty `src/__init__.py`

5. Git init:
```bash
git init
git add .
git commit -m "chore: project scaffolding"
```

**Verification:** `pip install -e ".[dev]"` succeeds.

---

### Task 2: Config Module

**Objective:** Centralize all paths, constants, and settings in one place.

**Files:**
- Create: `src/config.py`

**Steps:**

1. Create `src/config.py`:
```python
from pathlib import Path
import os

# Base paths
APP_DIR = Path(os.environ.get("RELIC_TRACKER_DIR", Path.home() / ".relic-tracker"))
DATA_DIR = APP_DIR / "data"
DB_PATH = DATA_DIR / "relics.db"
CACHE_DIR = DATA_DIR / "cache"

# Warframe Market API
MARKET_API_BASE = "https://api.warframe.market/v1"
MARKET_API_V2_BASE = "https://api.warframe.market/v2"

# WFCD Drop Data (raw GitHub content)
WFCD_DROP_DATA_URL = "https://raw.githubusercontent.com/WFCD/warframe-drop-data/master/data/relics.json"

# Ducat values by rarity
DUCAT_VALUES = {
    "Common": 15,
    "Uncommon": 45,
    "Rare": 100,
}

# Cross-rarity ducat overrides (item appears at different rarities in different relics)
# These are calculated dynamically; this is just for known exceptions
DUCAT_EXCEPTIONS = {
    # (item_name, computed_ducat_value) — override if wiki says different
}

# Market price cache TTL (seconds)
PRICE_CACHE_TTL = 3600  # 1 hour

# Relic tiers in display order
RELIC_TIERS = ["Lith", "Meso", "Neo", "Axi", "Requiem"]

# Server
HOST = "127.0.0.1"
PORT = 8420
```

2. Commit.

**Verification:** `python -c "from src.config import APP_DIR; print(APP_DIR)"` prints path without error.

---

### Task 3: Database Schema & Init

**Objective:** Define SQLite schema and create the database with all tables.

**Files:**
- Create: `src/db/__init__.py`
- Create: `src/db/models.py`
- Create: `src/db/database.py`

**Steps:**

1. Create `src/db/__init__.py` (empty)

2. Create `src/db/models.py`:
```python
SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS relics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,          -- e.g. "Lith A1"
    tier TEXT NOT NULL,                  -- Lith, Meso, Neo, Axi, Requiem
    introduced TEXT,                     -- e.g. "30.5"
    vaulted INTEGER DEFAULT 0,          -- 0=active, 1=vaulted
    vaulted_version TEXT,               -- version when vaulted, if any
    is_baro INTEGER DEFAULT 0,          -- 1 if from Baro Ki'Teer
    last_synced TEXT                     -- ISO timestamp
);

CREATE TABLE IF NOT EXISTS relic_drops (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    relic_id INTEGER NOT NULL,
    item_name TEXT NOT NULL,             -- e.g. "Nova Prime"
    part_name TEXT,                      -- e.g. "Blueprint", "Neuroptics"
    rarity TEXT NOT NULL,                -- Common, Uncommon, Rare
    item_count INTEGER DEFAULT 1,        -- how many units drop
    ducat_value INTEGER NOT NULL,        -- calculated from rarity
    FOREIGN KEY (relic_id) REFERENCES relics(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS collection (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    relic_id INTEGER NOT NULL UNIQUE,
    obtained INTEGER DEFAULT 0,          -- 0=not obtained, 1=obtained
    quantity INTEGER DEFAULT 0,          -- how many the user has
    notes TEXT,
    updated_at TEXT,                     -- ISO timestamp
    FOREIGN KEY (relic_id) REFERENCES relics(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS market_cache (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    item_url_name TEXT NOT NULL,         -- warframe.market url_name
    item_display_name TEXT,              -- human-readable name
    avg_price REAL,
    median_price REAL,
    min_price REAL,
    max_price REAL,
    volume INTEGER,
    orders_count INTEGER,
    platform TEXT DEFAULT 'pc',
    cached_at TEXT,                      -- ISO timestamp
    UNIQUE(item_url_name, platform)
);

CREATE INDEX IF NOT EXISTS idx_relics_tier ON relics(tier);
CREATE INDEX IF NOT EXISTS idx_relics_vaulted ON relics(vaulted);
CREATE INDEX IF NOT EXISTS idx_relic_drops_relic_id ON relic_drops(relic_id);
CREATE INDEX IF NOT EXISTS idx_relic_drops_item ON relic_drops(item_name);
CREATE INDEX IF NOT EXISTS idx_collection_obtained ON collection(obtained);
CREATE INDEX IF NOT EXISTS idx_market_cache_item ON market_cache(item_url_name);
"""
```

3. Create `src/db/database.py`:
```python
import aiosqlite
from pathlib import Path
from src.config import DB_PATH, DATA_DIR
from src.db.models import SCHEMA_SQL


_db: aiosqlite.Connection | None = None


async def get_db() -> aiosqlite.Connection:
    """Get or create the database connection."""
    global _db
    if _db is None:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        _db = await aiosqlite.connect(str(DB_PATH))
        _db.row_factory = aiosqlite.Row
        await _db.execute("PRAGMA journal_mode=WAL")
        await _db.execute("PRAGMA foreign_keys=ON")
        await _db.executescript(SCHEMA_SQL)
        await _db.commit()
    return _db


async def close_db():
    """Close the database connection."""
    global _db
    if _db:
        await _db.close()
        _db = None
```

4. Commit.

**Verification:** Run quick script:
```python
python -c "
import asyncio
from src.db.database import get_db
async def test():
    db = await get_db()
    cursor = await db.execute('SELECT name FROM sqlite_master WHERE type=\"table\"')
    tables = [row[0] for row in await cursor.fetchall()]
    print(tables)
    assert 'relics' in tables
    assert 'relic_drops' in tables
    assert 'collection' in tables
    assert 'market_cache' in tables
    print('All tables created!')
asyncio.run(test())
"
```

---

### Task 4: Ducat Calculator

**Objective:** Calculate ducat values from rarity, handle cross-rarity exceptions.

**Files:**
- Create: `src/services/__init__.py`
- Create: `src/services/ducats.py`
- Create: `tests/test_ducats.py`

**Steps:**

1. Create `src/services/__init__.py` (empty)

2. Write failing test `tests/test_ducats.py`:
```python
from src.services.ducats import calculate_ducat_value


def test_rare_ducats():
    assert calculate_ducat_value("Rare") == 100


def test_uncommon_ducats():
    assert calculate_ducat_value("Uncommon") == 45


def test_common_ducats():
    assert calculate_ducat_value("Common") == 15


def test_unknown_rarity_defaults_to_common():
    assert calculate_ducat_value("Unknown") == 15
```

3. Run test — should fail (module doesn't exist yet)

4. Implement `src/services/ducats.py`:
```python
from src.config import DUCAT_VALUES


def calculate_ducat_value(rarity: str) -> int:
    """Calculate ducat value from drop rarity.

    Standard values:
        Rare = 100, Uncommon = 45, Common = 15
    Falls back to Common (15) for unknown rarities.
    """
    return DUCAT_VALUES.get(rarity, DUCAT_VALUES["Common"])


def calculate_ducats_for_drop(rarity: str, item_count: int = 1) -> int:
    """Calculate total ducat value for a drop, considering item count."""
    return calculate_ducat_value(rarity) * item_count


def best_ducat_value(item_drops: list[dict]) -> int:
    """Given multiple drops of the same item across different relics,
    return the best ducat value.

    Per wiki rules:
        - If appears as both Uncommon and Rare: 65 ducats
        - If appears as both Common and Uncommon: 25 ducats
        - If appears as both Common and Rare: 25 ducats
    """
    rarities = {d["rarity"] for d in item_drops}

    if "Rare" in rarities and "Uncommon" in rarities:
        return 65
    if "Common" in rarities and ("Uncommon" in rarities or "Rare" in rarities):
        return 25

    # All same rarity or single rarity — use standard value
    rarity = list(rarities)[0]
    return calculate_ducat_value(rarity)
```

5. Run tests — all should pass.

6. Commit.

---

### Task 5: Drop Data Fetcher

**Objective:** Fetch and parse relic data from WFCD drop data repository.

**Files:**
- Create: `src/services/drop_data.py`
- Create: `tests/test_drop_data.py`

**Steps:**

1. Create `src/services/drop_data.py`:
```python
import httpx
import json
from pathlib import Path
from src.config import WFCD_DROP_DATA_URL, CACHE_DIR, RELIC_TIERS


async def fetch_relic_data() -> list[dict]:
    """Fetch relic data from WFCD drop data repository.

    Returns list of normalized relic dicts:
    [
        {
            "name": "Lith A1",
            "tier": "Lith",
            "introduced": "26.0",
            "vaulted": False,
            "vaulted_version": None,
            "is_baro": False,
            "drops": [
                {"item_name": "Aklex Prime", "part_name": "Blueprint", "rarity": "Uncommon", "item_count": 1},
                ...
            ]
        },
        ...
    ]
    """
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(WFCD_DROP_DATA_URL)
        response.raise_for_status()
        raw_data = response.json()

    relics = []
    for relic in raw_data:
        normalized = {
            "name": relic.get("name", ""),
            "tier": relic.get("tier", ""),
            "introduced": relic.get("Introduced", ""),
            "vaulted": relic.get("Vaulted") is not None,
            "vaulted_version": relic.get("Vaulted"),
            "is_baro": relic.get("IsBaro", False),
            "drops": [],
        }

        for drop in relic.get("drops", []):
            item_full = drop.get("item", "")
            part = drop.get("part", "")
            # If no separate part name, the full item name is the part
            if not part:
                part = item_full

            normalized["drops"].append({
                "item_name": item_full,
                "part_name": part,
                "rarity": drop.get("rarity", "Common"),
                "item_count": drop.get("item_count", 1),
            })

        relics.append(normalized)

    return relics


def _cache_path() -> Path:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    return CACHE_DIR / "relics.json"


async def fetch_relic_data_cached(max_age_seconds: int = 86400) -> list[dict]:
    """Fetch relic data with local file cache.

    Cache is valid for max_age_seconds (default 24 hours).
    """
    cache = _cache_path()
    if cache.exists():
        import os, time
        age = time.time() - os.path.getmtime(cache)
        if age < max_age_seconds:
            return json.loads(cache.read_text())

    data = await fetch_relic_data()
    cache.write_text(json.dumps(data, indent=2))
    return data
```

2. Write test `tests/test_drop_data.py`:
```python
import pytest
from src.services.drop_data import fetch_relic_data


@pytest.mark.asyncio
async def test_fetch_relic_data_returns_list():
    data = await fetch_relic_data()
    assert isinstance(data, list)
    assert len(data) > 0


@pytest.mark.asyncio
async def test_relic_has_required_fields():
    data = await fetch_relic_data()
    relic = data[0]
    assert "name" in relic
    assert "tier" in relic
    assert "drops" in relic
    assert isinstance(relic["drops"], list)


@pytest.mark.asyncio
async def test_relic_tiers_are_valid():
    from src.config import RELIC_TIERS
    data = await fetch_relic_data()
    for relic in data:
        assert relic["tier"] in RELIC_TIERS, f"Unknown tier: {relic['tier']}"


@pytest.mark.asyncio
async def test_drop_has_ducat_relevant_fields():
    data = await fetch_relic_data()
    for relic in data:
        for drop in relic["drops"]:
            assert "rarity" in drop
            assert drop["rarity"] in ("Common", "Uncommon", "Rare")
```

3. Run tests — verify against real API.

4. Commit.

---

## Phase 2: Market Data & Sync (Tasks 6–8)

### Task 6: Warframe Market API Client

**Objective:** Fetch item prices and statistics from Warframe Market.

**Files:**
- Create: `src/services/market_api.py`
- Create: `tests/test_market_api.py`

**Steps:**

1. Create `src/services/market_api.py`:
```python
import httpx
from datetime import datetime, timezone
from src.config import MARKET_API_BASE


async def get_item_statistics(url_name: str, platform: str = "pc") -> dict | None:
    """Fetch price statistics for a single item.

    Returns dict with avg_price, median_price, min_price, max_price, volume
    or None if item not found.
    """
    headers = {
        "Platform": platform,
        "Language": "en",
    }
    async with httpx.AsyncClient(timeout=15.0) as client:
        try:
            resp = await client.get(
                f"{MARKET_API_BASE}/items/{url_name}/statistics",
                headers=headers,
            )
            resp.raise_for_status()
        except (httpx.HTTPStatusError, httpx.RequestError):
            return None

        data = resp.json()
        stats = data.get("payload", {}).get("statistics_closed", {})
        day_stats = stats.get("90days", [])

        if not day_stats:
            return None

        # Use the most recent day's data
        latest = day_stats[-1]
        return {
            "url_name": url_name,
            "avg_price": latest.get("avg_price"),
            "median_price": latest.get("median"),
            "min_price": latest.get("min_price"),
            "max_price": latest.get("max_price"),
            "volume": latest.get("volume"),
            "platform": platform,
            "cached_at": datetime.now(timezone.utc).isoformat(),
        }


async def search_item(query: str, platform: str = "pc") -> list[dict]:
    """Search for items by name. Returns list of {url_name, item_name}."""
    headers = {
        "Platform": platform,
        "Language": "en",
    }
    async with httpx.AsyncClient(timeout=15.0) as client:
        try:
            resp = await client.get(
                f"{MARKET_API_BASE}/items",
                headers=headers,
            )
            resp.raise_for_status()
        except (httpx.HTTPStatusError, httpx.RequestError):
            return []

        items = resp.json().get("payload", {}).get("items", [])
        query_lower = query.lower()
        return [
            {"url_name": item["url_name"], "item_name": item["item_name"]}
            for item in items
            if query_lower in item["item_name"].lower()
        ]
```

2. Write test `tests/test_market_api.py`:
```python
import pytest
from src.services.market_api import get_item_statistics, search_item


@pytest.mark.asyncio
async def test_search_item():
    results = await search_item("ash prime")
    assert len(results) > 0
    assert any("ash" in r["item_name"].lower() for r in results)


@pytest.mark.asyncio
async def test_get_item_statistics():
    stats = await get_item_statistics("ash_prime_set")
    assert stats is not None
    assert "avg_price" in stats
    assert "median_price" in stats
    assert stats["platform"] == "pc"


@pytest.mark.asyncio
async def test_get_item_statistics_invalid():
    stats = await get_item_statistics("this_item_does_not_exist_xyz")
    assert stats is None
```

3. Run tests.

4. Commit.

---

### Task 7: Sync Service (Data Ingestion)

**Objective:** Orchestrate fetching relic data + market prices and writing to SQLite.

**Files:**
- Create: `src/services/sync.py`

**Steps:**

1. Create `src/services/sync.py`:
```python
import asyncio
from datetime import datetime, timezone
from src.db.database import get_db
from src.services.drop_data import fetch_relic_data_cached
from src.services.market_api import get_item_statistics
from src.services.ducats import calculate_ducat_value
import logging

logger = logging.getLogger(__name__)


async def sync_relics() -> dict:
    """Sync relic drop data from WFCD into local database.

    Returns {"relics_synced": N, "drops_synced": M}.
    """
    db = await get_db()
    data = await fetch_relic_data_cached(max_age_seconds=0)  # force refresh

    relics_synced = 0
    drops_synced = 0

    for relic in data:
        cursor = await db.execute(
            """INSERT INTO relics (name, tier, introduced, vaulted, vaulted_version, is_baro, last_synced)
               VALUES (?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(name) DO UPDATE SET
                   tier=excluded.tier,
                   introduced=excluded.introduced,
                   vaulted=excluded.vaulted,
                   vaulted_version=excluded.vaulted_version,
                   is_baro=excluded.is_baro,
                   last_synced=excluded.last_synced""",
            (
                relic["name"],
                relic["tier"],
                relic["introduced"],
                1 if relic["vaulted"] else 0,
                relic["vaulted_version"],
                1 if relic["is_baro"] else 0,
                datetime.now(timezone.utc).isoformat(),
            ),
        )
        relic_id = cursor.lastrowid
        if relic_id is None:
            # Already existed, fetch its ID
            row = await db.execute("SELECT id FROM relics WHERE name=?", (relic["name"],))
            row = await row.fetchone()
            relic_id = row[0]

        # Replace drops for this relic
        await db.execute("DELETE FROM relic_drops WHERE relic_id=?", (relic_id,))

        for drop in relic["drops"]:
            ducat = calculate_ducat_value(drop["rarity"])
            await db.execute(
                """INSERT INTO relic_drops (relic_id, item_name, part_name, rarity, item_count, ducat_value)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (relic_id, drop["item_name"], drop["part_name"], drop["rarity"], drop["item_count"], ducat),
            )
            drops_synced += 1

        # Ensure collection entry exists
        await db.execute(
            "INSERT OR IGNORE INTO collection (relic_id, obtained, quantity) VALUES (?, 0, 0)",
            (relic_id,),
        )

        relics_synced += 1

    await db.commit()
    logger.info(f"Synced {relics_synced} relics with {drops_synced} drops")
    return {"relics_synced": relics_synced, "drops_synced": drops_synced}


async def sync_market_prices(url_names: list[str] | None = None, platform: str = "pc") -> int:
    """Sync market prices for given items (or all unique items if None).

    Returns count of items synced.
    """
    db = await get_db()

    if url_names is None:
        # Get all unique item names from drops, try to build url_names
        cursor = await db.execute("SELECT DISTINCT item_name FROM relic_drops")
        rows = await cursor.fetchall()
        # We'd need a mapping from display name to url_name
        # For now, we skip items we can't map
        logger.info(f"Market sync needs url_name mapping for {len(rows)} items")
        return 0

    synced = 0
    for url_name in url_names:
        stats = await get_item_statistics(url_name, platform)
        if stats:
            await db.execute(
                """INSERT INTO market_cache (item_url_name, item_display_name, avg_price, median_price,
                   min_price, max_price, volume, platform, cached_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                   ON CONFLICT(item_url_name, platform) DO UPDATE SET
                       avg_price=excluded.avg_price,
                       median_price=excluded.median_price,
                       min_price=excluded.min_price,
                       max_price=excluded.max_price,
                       volume=excluded.volume,
                       cached_at=excluded.cached_at""",
                (
                    url_name, url_name.replace("_", " ").title(),
                    stats["avg_price"], stats["median_price"],
                    stats["min_price"], stats["max_price"],
                    stats["volume"], platform, stats["cached_at"],
                ),
            )
            synced += 1
        # Small delay to be respectful to the API
        await asyncio.sleep(0.5)

    await db.commit()
    return synced
```

2. Commit.

---

### Task 8: Collection Service

**Objective:** CRUD operations for user's relic collection (toggle obtained, set quantity, get stats).

**Files:**
- Create: `src/services/collection.py`

**Steps:**

1. Create `src/services/collection.py`:
```python
from src.db.database import get_db


async def get_all_relics_with_status(tier: str | None = None, vaulted: bool | None = None, obtained: bool | None = None) -> list[dict]:
    """Get all relics with collection status, optionally filtered."""
    db = await get_db()

    query = """
        SELECT r.id, r.name, r.tier, r.vaulted, r.is_baro,
               c.obtained, c.quantity, c.notes,
               (SELECT COUNT(*) FROM relic_drops WHERE relic_id = r.id) as drop_count,
               (SELECT SUM(d.ducat_value) FROM relic_drops d WHERE relic_id = r.id) as total_ducats
        FROM relics r
        LEFT JOIN collection c ON c.relic_id = r.id
        WHERE 1=1
    """
    params = []

    if tier:
        query += " AND r.tier = ?"
        params.append(tier)
    if vaulted is not None:
        query += " AND r.vaulted = ?"
        params.append(1 if vaulted else 0)
    if obtained is not None:
        query += " AND c.obtained = ?"
        params.append(1 if obtained else 0)

    query += " ORDER BY r.tier, r.name"

    cursor = await db.execute(query, params)
    rows = await cursor.fetchall()

    return [
        {
            "id": row[0],
            "name": row[1],
            "tier": row[2],
            "vaulted": bool(row[3]),
            "is_baro": bool(row[4]),
            "obtained": bool(row[5]),
            "quantity": row[6] or 0,
            "notes": row[7],
            "drop_count": row[8],
            "total_ducats": row[9] or 0,
        }
        for row in rows
    ]


async def get_relic_details(relic_id: int) -> dict | None:
    """Get full details for a single relic including its drops."""
    db = await get_db()

    cursor = await db.execute(
        """SELECT r.id, r.name, r.tier, r.introduced, r.vaulted, r.vaulted_version,
                  r.is_baro, c.obtained, c.quantity, c.notes
           FROM relics r
           LEFT JOIN collection c ON c.relic_id = r.id
           WHERE r.id = ?""",
        (relic_id,),
    )
    row = await cursor.fetchone()
    if not row:
        return None

    # Get drops
    drops_cursor = await db.execute(
        "SELECT item_name, part_name, rarity, item_count, ducat_value FROM relic_drops WHERE relic_id = ?",
        (relic_id,),
    )
    drops = await drops_cursor.fetchall()

    return {
        "id": row[0],
        "name": row[1],
        "tier": row[2],
        "introduced": row[3],
        "vaulted": bool(row[4]),
        "vaulted_version": row[5],
        "is_baro": bool(row[6]),
        "obtained": bool(row[7]),
        "quantity": row[8] or 0,
        "notes": row[9],
        "drops": [
            {
                "item_name": d[0],
                "part_name": d[1],
                "rarity": d[2],
                "item_count": d[3],
                "ducat_value": d[4],
            }
            for d in drops
        ],
    }


async def toggle_obtained(relic_id: int) -> dict:
    """Toggle obtained status for a relic. Returns new state."""
    db = await get_db()

    cursor = await db.execute(
        "SELECT obtained FROM collection WHERE relic_id = ?", (relic_id,)
    )
    row = await cursor.fetchone()
    if not row:
        return {"error": "Relic not found in collection"}

    new_state = 0 if row[0] else 1
    await db.execute(
        "UPDATE collection SET obtained = ?, updated_at = datetime('now') WHERE relic_id = ?",
        (new_state, relic_id),
    )
    await db.commit()
    return {"relic_id": relic_id, "obtained": bool(new_state)}


async def set_quantity(relic_id: int, quantity: int) -> dict:
    """Set quantity of a relic the user has."""
    db = await get_db()
    await db.execute(
        "UPDATE collection SET quantity = ?, updated_at = datetime('now') WHERE relic_id = ?",
        (quantity, relic_id),
    )
    await db.commit()
    return {"relic_id": relic_id, "quantity": quantity}


async def get_overview_stats() -> dict:
    """Get dashboard overview statistics."""
    db = await get_db()

    total = await (await db.execute("SELECT COUNT(*) FROM relics")).fetchone()
    obtained = await (await db.execute(
        "SELECT COUNT(*) FROM collection WHERE obtained = 1"
    )).fetchone()
    vaulted = await (await db.execute(
        "SELECT COUNT(*) FROM relics WHERE vaulted = 1"
    )).fetchone()

    total_ducats = await (await db.execute("""
        SELECT SUM(d.ducat_value)
        FROM relic_drops d
        JOIN relics r ON d.relic_id = r.id
        JOIN collection c ON c.relic_id = r.id
        WHERE c.obtained = 1
    """)).fetchone()

    # Per-tier breakdown
    tier_stats = await (await db.execute("""
        SELECT r.tier,
               COUNT(*) as total,
               SUM(CASE WHEN c.obtained = 1 THEN 1 ELSE 0 END) as obtained
        FROM relics r
        LEFT JOIN collection c ON c.relic_id = r.id
        GROUP BY r.tier
        ORDER BY CASE r.tier
            WHEN 'Lith' THEN 1
            WHEN 'Meso' THEN 2
            WHEN 'Neo' THEN 3
            WHEN 'Axi' THEN 4
            WHEN 'Requiem' THEN 5
        END
    """)).fetchall()

    return {
        "total_relics": total[0] if total else 0,
        "obtained_relics": obtained[0] if obtained else 0,
        "vaulted_relics": vaulted[0] if vaulted else 0,
        "total_ducat_value": total_ducats[0] if total_ducats and total_ducats[0] else 0,
        "completion_pct": round(
            (obtained[0] / total[0] * 100) if total and total[0] > 0 else 0, 1
        ),
        "by_tier": [
            {"tier": t[0], "total": t[1], "obtained": t[2] or 0}
            for t in tier_stats
        ],
    }
```

2. Commit.

---

## Phase 3: API Layer (Tasks 9–11)

### Task 9: FastAPI App & Routes

**Objective:** Wire up FastAPI with all API routes and static file serving.

**Files:**
- Create: `src/main.py`
- Create: `src/api/__init__.py`
- Create: `src/api/relics.py`
- Create: `src/api/overview.py`
- Create: `src/api/collection.py`

**Steps:**

1. Create `src/api/__init__.py` (empty)

2. Create `src/api/overview.py`:
```python
from fastapi import APIRouter
from src.services.collection import get_overview_stats

router = APIRouter(prefix="/api", tags=["overview"])


@router.get("/overview")
async def overview():
    return await get_overview_stats()
```

3. Create `src/api/relics.py`:
```python
from fastapi import APIRouter, Query
from src.services.collection import get_all_relics_with_status, get_relic_details

router = APIRouter(prefix="/api", tags=["relics"])


@router.get("/relics")
async def list_relics(
    tier: str | None = Query(None, description="Filter by tier"),
    vaulted: bool | None = Query(None, description="Filter by vaulted status"),
    obtained: bool | None = Query(None, description="Filter by obtained status"),
):
    return await get_all_relics_with_status(tier=tier, vaulted=vaulted, obtained=obtained)


@router.get("/relics/{relic_id}")
async def relic_details(relic_id: int):
    details = await get_relic_details(relic_id)
    if not details:
        return {"error": "Relic not found"}, 404
    return details
```

4. Create `src/api/collection.py`:
```python
from fastapi import APIRouter
from src.services.collection import toggle_obtained, set_quantity

router = APIRouter(prefix="/api", tags=["collection"])


@router.post("/collection/{relic_id}/toggle")
async def toggle(relic_id: int):
    return await toggle_obtained(relic_id)


@router.post("/collection/{relic_id}/quantity")
async def quantity(relic_id: int, qty: int):
    return await set_quantity(relic_id, qty)
```

5. Create `src/main.py`:
```python
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from src.db.database import close_db
from src.api.overview import router as overview_router
from src.api.relics import router as relics_router
from src.api.collection import router as collection_router
from pathlib import Path


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: run initial sync
    from src.services.sync import sync_relics
    await sync_relics()
    yield
    # Shutdown
    await close_db()


app = FastAPI(
    title="Warframe Relic Tracker",
    version="0.1.0",
    lifespan=lifespan,
)

# API routes
app.include_router(overview_router)
app.include_router(relics_router)
app.include_router(collection_router)

# Static files
STATIC_DIR = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/")
async def index():
    return FileResponse(str(STATIC_DIR / "index.html"))


def run():
    import uvicorn
    uvicorn.run("src.main:app", host="127.0.0.1", port=8420, reload=True)


if __name__ == "__main__":
    run()
```

6. Commit.

**Verification:** Run `python -m src.main`, open http://127.0.0.1:8420/docs — FastAPI Swagger UI should show all endpoints.

---

### Task 10: Sync API Endpoint

**Objective:** Add endpoint to trigger manual data refresh.

**Files:**
- Modify: `src/main.py`

**Steps:**

1. Add sync route to `src/main.py`:
```python
from src.services.sync import sync_relics


@app.post("/api/sync")
async def sync():
    result = await sync_relics()
    return {"status": "ok", **result}
```

2. Commit.

---

### Task 11: Test API Endpoints

**Objective:** Write integration tests for all API endpoints.

**Files:**
- Create: `tests/test_api.py`

**Steps:**

1. Create `tests/test_api.py`:
```python
import pytest
from httpx import AsyncClient, ASGITransport
from src.main import app


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.mark.asyncio
async def test_overview(client):
    resp = await client.get("/api/overview")
    assert resp.status_code == 200
    data = resp.json()
    assert "total_relics" in data
    assert "obtained_relics" in data


@pytest.mark.asyncio
async def test_list_relics(client):
    resp = await client.get("/api/relics")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)


@pytest.mark.asyncio
async def test_list_relics_filter_tier(client):
    resp = await client.get("/api/relics", params={"tier": "Lith"})
    assert resp.status_code == 200
    data = resp.json()
    for relic in data:
        assert relic["tier"] == "Lith"


@pytest.mark.asyncio
async def test_toggle_collection(client):
    # First get a relic
    resp = await client.get("/api/relics")
    relics = resp.json()
    if relics:
        relic_id = relics[0]["id"]
        resp = await client.post(f"/api/collection/{relic_id}/toggle")
        assert resp.status_code == 200
```

2. Run: `pytest tests/test_api.py -v`

3. Commit.

---

## Phase 4: Frontend Dashboard (Tasks 12–16)

### Task 12: HTML Shell & 2005 Professional Styling

**Objective:** Create the SPA shell with the 2005 professional web aesthetic (Verdana/Tahoma fonts, steel blue headers, beveled borders, clean corporate look).

**Files:**
- Create: `src/static/index.html`
- Create: `src/static/css/app.css`

**Steps:**

1. Create `src/static/index.html` — Full SPA with 2005 professional theme:
   - NO TailwindCSS, NO CDN frameworks — pure hand-crafted CSS
   - Verdana/Geneva 11px body text, Tahoma/Arial headings
   - Steel blue (#336699) header, dark navy (#003366) navigation
   - Max-width 960px container, clean layout
   - Navigation: Dashboard | Relics | Collection (horizontal nav bar)
   - Table-based panels with clean borders
   - Modal for relic details (styled as a panel with border)
   - Loading states using simple text (no spinners)

2. Create `src/static/css/app.css` — Complete 2005 professional theme:
   - **Typography:** Verdana/Geneva body (11px), Tahoma headings (13-16px)
   - **Colors:** #336699 steel blue, #003366 dark navy, #E8EEF4 panel headers
   - **Borders:** 1px solid #CCCCCC, beveled effects (border-style: outset) on buttons
   - **Tables:** Alternating row colors (#FFFFFF / #F5F5F5), #B0C4DE borders
   - **Navigation:** Dark navy bar with white text, hover states
   - **Tags/Badges:** Inline-block with #E8EEF4 background, #B0C4DE border
   - **Tier colors:** Lith=#CD7F32 bronze, Meso=#C0C0C0 silver, Neo=#FFD700 gold, Axi=#E5E4E2 platinum
   - **Rarity colors:** Common=#666666 gray, Uncommon=#009900 green, Rare=#CC6600 orange
   - **Vaulted badge:** Red background with white text
   - **Buttons:** Beveled/outset borders, flat colors, NO rounded corners, NO gradients
   - **No rounded corners anywhere** (maybe 2-3px max for subtle softness)
   - **Footer:** Dark navy with light blue text

3. Commit.

**Key CSS values:**
```css
body { font-family: Verdana, Geneva, sans-serif; font-size: 11px; color: #333333; }
h1 { font-family: Tahoma, Arial, sans-serif; font-size: 16px; color: #003366; }
h2 { font-family: Tahoma, Arial, sans-serif; font-size: 14px; color: #336699; }
h3 { font-family: Tahoma, Arial, sans-serif; font-size: 12px; color: #003366; }
.header { background: #336699; color: #fff; border-bottom: 2px solid #003366; }
.nav { background: #003366; }
.nav a { color: #fff; border-right: 1px solid #004488; }
.panel { border: 1px solid #CCCCCC; background: #fff; }
.panel-header { background: #E8EEF4; border-bottom: 1px solid #CCCCCC; font-weight: bold; color: #003366; }
table th { background: #E8EEF4; border: 1px solid #B0C4DE; color: #003366; }
table td { border: 1px solid #CCCCCC; }
.tag { background: #E8EEF4; border: 1px solid #B0C4DE; padding: 2px 8px; font-size: 10px; }
button { border-style: outset; background: #E8EEF4; font-family: Verdana; font-size: 11px; }
```

---

### Task 13: Frontend JavaScript

**Objective:** Build the client-side logic for fetching data and rendering the dashboard.

**Files:**
- Create: `src/static/js/app.js`

**Steps:**

1. Create `src/static/js/app.js`:
   - Router (hash-based SPA navigation)
   - API client functions (fetch wrappers)
   - Dashboard view: overview cards, tier progress bars
   - Relics view: grid/list with filters (tier, vaulted, obtained)
   - Collection view: only obtained relics
   - Relic detail modal: drops table, ducat values, market price
   - Toggle obtained button (POST to /api/collection/{id}/toggle)
   - Sync button (POST /api/sync)
   - Loading states and error handling
   - Search/filter functionality

2. Commit.

---

### Task 14: Dashboard View

**Objective:** Implement the overview dashboard with stats panels and tier breakdown in 2005 professional style.

**Key elements:**
- Panel-based layout with #E8EEF4 panel headers
- Stats table: Total relics / Obtained / Completion % / Total ducats
- Per-tier breakdown table with alternating row colors
- Vaulted count as a tag/badge
- "Last synced" timestamp in the footer area
- Sync button with beveled/outset border style

---

### Task 15: Relic Browser View

**Objective:** Implement the relic browsing view with filters and sorting in 2005 professional style.

**Key elements:**
- Table-based relic listing (not cards) with clean borders
- Filter bar: tier links (All/Lith/Meso/Neo/Axi), vaulted checkbox, obtained checkbox
- Each row shows: name, tier tag, vaulted badge, drop count, total ducats
- Click row to open detail modal
- Toggle obtained checkbox on each row

---

### Task 16: Relic Detail Modal

**Objective:** Implement the modal that shows full relic information in 2005 professional style.

**Key elements:**
- Panel-style modal with #E8EEF4 header bar
- Relic name, tier tag, introduced version, vaulted badge
- Table of drops: item name, part, rarity tag, ducat value
- Market price (if available)
- Quantity input field (standard browser input)
- Notes textarea (standard browser textarea)
- Toggle obtained beveled button
- Close button

---

## Phase 5: Packaging & Distribution (Tasks 17–19)

### Task 17: PyInstaller Standalone Build

**Objective:** Package the app as a single executable.

**Files:**
- Create: `installer/warframe-relic-tracker.spec`

**Steps:**

1. Create PyInstaller spec file:
```python
# warframe-relic-tracker.spec
a = Analysis(
    ['../src/main.py'],
    pathex=['..'],
    binaries=[],
    datas=[
        ('../src/static', 'src/static'),
    ],
    hiddenimports=['src.db.models'],
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
```

2. Build command:
```bash
pyinstaller installer/warframe-relic-tracker.spec --onefile --name RelicTracker
```

---

### Task 18: Inno Setup Installer (Windows)

**Objective:** Create a Windows installer that wraps the PyInstaller executable.

**Files:**
- Create: `installer/setup.iss`

**Steps:**

1. Create Inno Setup script:
```iss
[Setup]
AppName=Warframe Relic Tracker
AppVersion=0.1.0
DefaultDirName={autopf}\RelicTracker
DefaultGroupName=Warframe Relic Tracker
OutputBaseFilename=RelicTracker-Setup
Compression=lzma2
SolidCompression=yes

[Files]
Source: "dist\RelicTracker.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\Relic Tracker"; Filename: "{app}\RelicTracker.exe"
Name: "{group}\Uninstall"; Filename: "{uninstallexe}"

[Run]
Filename: "{app}\RelicTracker.exe"; Description: "Launch Relic Tracker"; Flags: postinstall nowait
```

---

### Task 19: Cross-Platform Build Scripts

**Objective:** Create build scripts for all platforms.

**Files:**
- Create: `installer/build.sh` (Linux/Mac)
- Create: `installer/build.bat` (Windows)

**Steps:**

1. `installer/build.sh`:
```bash
#!/bin/bash
set -e
echo "Building Warframe Relic Tracker..."
pip install pyinstaller
pyinstaller installer/warframe-relic-tracker.spec --onefile --name RelicTracker
echo "Build complete: dist/RelicTracker"
```

2. `installer/build.bat`:
```batch
@echo off
echo Building Warframe Relic Tracker...
pip install pyinstaller
pyinstaller installer\warframe-relic-tracker.spec --onefile --name RelicTracker
echo Build complete: dist\RelicTracker.exe
```

3. Commit.

---

## Phase 6: Polish & Documentation (Tasks 20–22)

### Task 20: README

**Objective:** Write comprehensive README with screenshots description, install guide, usage.

**Files:**
- Create: `README.md`

**Content:**
- Project description
- Features list
- Screenshots (placeholder)
- Installation (pip, executable, source)
- Usage guide
- API reference (auto from FastAPI /docs)
- Development setup
- Contributing guide
- License (MIT)

---

### Task 21: Error Handling & Edge Cases

**Objective:** Add proper error handling, empty states, and offline behavior.

**Key items:**
- Graceful handling when WFCD API is down
- Graceful handling when Warframe Market is rate-limiting
- Empty state UI (no relics synced yet)
- Loading skeletons
- Network error toasts

---

### Task 22: Final Testing & QA

**Objective:** Run full test suite, manual testing, fix issues.

**Steps:**
1. Run: `pytest tests/ -v --cov=src`
2. Manual test: sync, browse, toggle, search, filter
3. Test PyInstaller build
4. Fix any issues found

---

## Estimated Effort

| Phase | Tasks | Est. Time |
|---|---|---|
| 1. Foundation | Tasks 1–5 | ~30 min |
| 2. Data & Sync | Tasks 6–8 | ~25 min |
| 3. API Layer | Tasks 9–11 | ~20 min |
| 4. Frontend | Tasks 12–16 | ~45 min |
| 5. Packaging | Tasks 17–19 | ~20 min |
| 6. Polish | Tasks 20–22 | ~20 min |
| **Total** | **22 tasks** | **~2.5–3 hours** |

---

## Key Decisions Summary

| Decision | Choice | Why |
|---|---|---|
| Language | Python | Existing libraries, faster dev, PyInstaller for distribution |
| Backend | FastAPI | Async, auto docs, lightweight |
| Database | SQLite | Zero config, portable, single file |
| Frontend | Pure CSS (2005 professional) | Verdana/Tahoma, steel blue, beveled borders, NO frameworks |
| Market prices | Warframe Market API | Free, well-documented, statistics endpoint |
| Drop data | WFCD GitHub | JSON files, actively maintained |
| Installer | PyInstaller + Inno Setup | Single exe, Windows installer |
| Package name | `relic-tracker` | Short, memorable |
| Port | 8420 | Easy to remember, unlikely to conflict |
| Theme | 2005 Professional Aesthetic | Clean corporate look, tables, no rounded corners |
