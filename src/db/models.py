"""SQL schema constants for the Warframe Relic Tracker database."""

SCHEMA_SQL = """
-- Relic master table
CREATE TABLE IF NOT EXISTS relics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    tier TEXT NOT NULL,
    introduced TEXT DEFAULT '',
    vaulted INTEGER NOT NULL DEFAULT 0,
    vaulted_version TEXT DEFAULT '',
    is_baro INTEGER NOT NULL DEFAULT 0,
    last_synced TEXT DEFAULT ''
);

CREATE INDEX IF NOT EXISTS idx_relics_tier ON relics(tier);
CREATE INDEX IF NOT EXISTS idx_relics_vaulted ON relics(vaulted);

-- Relic drop table (items inside each relic)
CREATE TABLE IF NOT EXISTS relic_drops (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    relic_id INTEGER NOT NULL,
    item_name TEXT NOT NULL,
    part_name TEXT NOT NULL DEFAULT '',
    rarity TEXT NOT NULL,
    item_count INTEGER NOT NULL DEFAULT 1,
    ducat_value INTEGER NOT NULL DEFAULT 0,
    FOREIGN KEY (relic_id) REFERENCES relics(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_drops_relic_id ON relic_drops(relic_id);
CREATE INDEX IF NOT EXISTS idx_drops_item_name ON relic_drops(item_name);

-- User collection tracking
CREATE TABLE IF NOT EXISTS collection (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    relic_id INTEGER NOT NULL UNIQUE,
    obtained INTEGER NOT NULL DEFAULT 0,
    quantity INTEGER NOT NULL DEFAULT 0,
    notes TEXT DEFAULT '',
    updated_at TEXT DEFAULT '',
    FOREIGN KEY (relic_id) REFERENCES relics(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_collection_obtained ON collection(obtained);

-- Warframe Market price cache
CREATE TABLE IF NOT EXISTS market_cache (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    item_url_name TEXT NOT NULL,
    item_display_name TEXT DEFAULT '',
    avg_price REAL DEFAULT 0,
    median_price REAL DEFAULT 0,
    min_price REAL DEFAULT 0,
    max_price REAL DEFAULT 0,
    volume INTEGER DEFAULT 0,
    orders_count INTEGER DEFAULT 0,
    platform TEXT NOT NULL DEFAULT 'pc',
    cached_at TEXT DEFAULT '',
    UNIQUE(item_url_name, platform)
);

CREATE INDEX IF NOT EXISTS idx_market_url_name ON market_cache(item_url_name);
CREATE INDEX IF NOT EXISTS idx_market_platform ON market_cache(platform);
"""
