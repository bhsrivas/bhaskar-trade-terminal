from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, HTTPException

from app.core.config import settings
from app.decision.viability import analyse_viability
from app.models.viability import ViabilityRequest, ViabilityResponse
from app.services.market_data import get_chain, get_expiries

router = APIRouter(prefix="/api")


@router.get("/health")
async def health() -> dict:
    return {
        "status": "ok",
        "version": "3.0-sprint1",
        "mode": settings.app_mode,
        "credentials_configured": bool(
            settings.dhan_client_id and settings.dhan_access_token
        ),
        "timestamp": datetime.now().isoformat(),
    }


@router.get("/config")
async def config() -> dict:
    return {
        "lot_size": settings.lot_size,
        "target_net": settings.target_net,
        "charge_buffer": settings.charge_buffer,
        "poll_seconds": settings.poll_seconds,
        "mode": settings.app_mode,
    }


@router.get("/expiries")
async def expiries() -> dict:
    return {"status": "success", "data": await get_expiries()}


@router.get("/chain")
async def chain(expiry: str) -> dict:
    snapshot = await get_chain(expiry)
    return snapshot.model_dump()


@router.post("/viability", response_model=ViabilityResponse)
async def viability(request: ViabilityRequest) -> ViabilityResponse:
    try:
        snapshot = await get_chain(request.expiry)
        return analyse_viability(snapshot, request)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
