from fastapi import APIRouter
from src.services.collection import get_overview_stats

router = APIRouter(prefix="/api", tags=["overview"])

@router.get("/overview")
async def overview():
    return await get_overview_stats()
