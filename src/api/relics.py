from fastapi import APIRouter, Query
from src.services.collection import get_all_relics_with_status, get_relic_details

router = APIRouter(prefix="/api", tags=["relics"])

@router.get("/relics")
async def list_relics(
    tier: str | None = Query(None),
    vaulted: bool | None = Query(None),
    obtained: bool | None = Query(None),
):
    return await get_all_relics_with_status(tier=tier, vaulted=vaulted, obtained=obtained)

@router.get("/relics/{relic_id}")
async def relic_details(relic_id: int):
    details = await get_relic_details(relic_id)
    if not details:
        return {"error": "Relic not found"}
    return details
