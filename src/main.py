import uvicorn
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from src.config import HOST, PORT
from src.db.database import close_db
from src.services.sync import sync_relics
from src.api.overview import router as overview_router
from src.api.relics import router as relics_router
from src.api.collection import router as collection_router

STATIC_DIR = Path(__file__).parent / "static"

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: sync relic data
    await sync_relics()
    yield
    # Shutdown: close database connections
    await close_db()

app = FastAPI(title="Warframe Relic Tracker", lifespan=lifespan)

# Include API routers
app.include_router(overview_router)
app.include_router(relics_router)
app.include_router(collection_router)

# Serve index.html at root
@app.get("/")
async def index():
    return FileResponse(str(STATIC_DIR / "index.html"))

# Mount static files
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# Manual sync endpoint
@app.post("/api/sync")
async def sync():
    await sync_relics()
    return {"status": "sync complete"}

def run():
    uvicorn.run(app, host=HOST, port=PORT)

if __name__ == "__main__":
    run()
