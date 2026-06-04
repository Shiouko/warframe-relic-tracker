from fastapi import APIRouter, Query
from src.services.collection import toggle_obtained, set_quantity

router = APIRouter(prefix="/api", tags=["collection"])

@router.post("/collection/{relic_id}/toggle")
async def toggle(relic_id: int):
    return await toggle_obtained(relic_id)

@router.post("/collection/{relic_id}/quantity")
async def quantity(relic_id: int, qty: int = Query(...)):
    return await set_quantity(relic_id, qty)
