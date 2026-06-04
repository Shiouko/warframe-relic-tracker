from pathlib import Path
import os

# Base paths
APP_DIR = Path(os.environ.get("RELIC_TRACKER_DIR", Path.home() / ".relic-tracker"))
DATA_DIR = APP_DIR / "data"
DB_PATH = DATA_DIR / "relics.db"
CACHE_DIR = DATA_DIR / "cache"

# Warframe Market API
MARKET_API_BASE = "https://api.warframe.market/v1"

# WFCD Drop Data (raw GitHub content)
WFCD_DROP_DATA_URL = "https://raw.githubusercontent.com/WFCD/warframe-drop-data/master/data/relics.json"

# Ducat values by rarity
DUCAT_VALUES = {
    "Common": 15,
    "Uncommon": 45,
    "Rare": 100,
}

# Market price cache TTL (seconds)
PRICE_CACHE_TTL = 3600  # 1 hour

# Relic tiers in display order
RELIC_TIERS = ["Lith", "Meso", "Neo", "Axi", "Requiem"]

# Server
HOST = "127.0.0.1"
PORT = 8420
