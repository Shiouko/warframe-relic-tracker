# Warframe Relic Tracker

A comprehensive web-based tool for tracking your Warframe Void Relic collection, ducat values, and market prices.

## Features

- 📊 **Dashboard** — Overview of collection completion, ducat totals, and vaulted relic stats
- 🔍 **Relic Browser** — Browse all relics filtered by tier (Lith/Meso/Neo/Axi/Requiem), vaulted status, and obtained status
- 💎 **Detail View** — View drop tables, ducat values per part, and live market prices
- ✅ **Collection Checklist** — Toggle relics as obtained, set quantities, track your progress
- 💰 **Auto-Calculated Ducats** — Ducat values derived automatically from drop rarity (Common=15, Uncommon=45, Rare=100)
- 📈 **Market Price Data** — Live price data from the Warframe Market API with hourly caching
- 🔄 **Sync Engine** — Automatically fetches latest relic data from WFCD Drop Data
- 🎨 **2005 Professional Theme** — Retro steel-blue UI with Verdana/Tahoma typography and beveled borders

## Tech Stack

- **Backend:** Python 3.11+ / FastAPI / Uvicorn
- **Database:** SQLite (via aiosqlite)
- **Frontend:** Vanilla JS SPA with custom 2005 Professional CSS
- **Data Sources:** [WFCD Drop Data](https://github.com/WFCD/warframe-drop-data) + [Warframe Market API](https://warframe.market/api)
- **Packaging:** PyInstaller + Inno Setup (Windows)

## Quick Start

### From Source (Development)

```bash
# Clone the repository
git clone https://github.com/Shiouko/warframe-relic-tracker.git
cd warframe-relic-tracker

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate  # Linux/macOS
# .venv\Scripts\activate   # Windows

# Install dependencies
pip install -r requirements.txt

# Run the application
python -m src.main
```

The application will be available at **http://127.0.0.1:8420**

### Standalone Executable

See [Build Instructions](#building-the-standalone-executable) below.

## Usage Guide

### Dashboard

The **Dashboard** tab shows:
- Total relics and how many you've collected
- Ducat value of your collection
- Breakdown by tier (Lith, Meso, Neo, Axi)
- Vaulted vs. unvaulted statistics

### Relics

The **Relics** tab provides a filterable list of all Void Relics:
- Filter by tier: Lith, Meso, Neo, Axi, Requiem
- Filter by status: Vaulted, Unvaulted, Obtained
- Click any relic to view detailed drop tables

### Collection

The **Collection** tab tracks what you own:
- Toggle relics as obtained/not obtained
- Set quantities for each relic
- View your collection progress and ducat totals

### Syncing Data

Click the **Sync Data** button in the toolbar to manually refresh relic data from WFCD and market prices from Warframe Market. Data is also synced automatically on application startup.

### API Endpoints

The application exposes a REST API for programmatic access:

- `GET /api/overview` — Dashboard statistics
- `GET /api/relics` — List all relics (supports `tier`, `vaulted`, `obtained` query params)
- `GET /api/relics/{id}` — Relic detail with drop table
- `GET /api/collection` — Collection state
- `POST /api/collection` — Update collection entry
- `POST /api/sync` — Trigger manual data sync

## Development Setup

### Project Structure

```
warframe-relic-tracker/
├── src/
│   ├── api/            # FastAPI route handlers
│   │   ├── collection.py
│   │   ├── overview.py
│   │   └── relics.py
│   ├── db/             # Database models and connection
│   │   ├── database.py
│   │   └── models.py
│   ├── services/       # Business logic
│   │   ├── collection.py
│   │   ├── drop_data.py
│   │   ├── ducats.py
│   │   ├── market_api.py
│   │   └── sync.py
│   ├── static/         # Frontend assets
│   │   ├── css/app.css
│   │   ├── js/app.js
│   │   └── index.html
│   ├── config.py       # Application configuration
│   └── main.py         # FastAPI application entry point
├── installer/          # Packaging scripts
│   ├── warframe-relic-tracker.spec  # PyInstaller spec
│   ├── setup.iss       # Inno Setup installer script
│   ├── build.sh        # Linux/macOS build script
│   └── build.bat       # Windows build script
├── tests/              # Test suite
├── requirements.txt    # Python dependencies
├── README.md
├── LICENSE
└── .gitignore
```

### Running Tests

```bash
pytest tests/ -v
```

### Code Style

This project uses [Ruff](https://docs.astral.sh/ruff/) for linting and formatting:

```bash
ruff check src/
ruff format src/
```

## Building the Standalone Executable

### Linux / macOS

```bash
chmod +x installer/build.sh
./installer/build.sh
# Output: dist/RelicTracker
```

### Windows

```cmd
installer\build.bat
REM Output: dist\RelicTracker.exe
```

### Creating the Windows Installer

1. Build the executable first using `build.bat`
2. Install [Inno Setup 6](https://jrsoftware.org/isdl.php)
3. Open `installer/setup.iss` in Inno Setup
4. Click Build → Compile

This produces `dist/WarfameRelicTracker_Setup_1.0.0.exe`.

## Configuration

Data is stored in `~/.relic-tracker/` by default. Override with the `RELIC_TRACKER_DIR` environment variable:

```bash
RELIC_TRACKER_DIR=/custom/path python -m src.main
```

The server runs on `127.0.0.1:8420` by default. Configure via environment:

```bash
HOST=0.0.0.0 PORT=9000 python -m src.main
```

## License

MIT License. See [LICENSE](LICENSE) for details.

Data sourced from:
- [Warframe Drop Data](https://github.com/WFCD/warframe-drop-data) by WFCD
- [Warframe Market API](https://warframe.market/api)
