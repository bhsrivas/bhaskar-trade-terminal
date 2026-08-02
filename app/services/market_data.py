from __future__ import annotations

from app.broker.dhan import fetch_chain, fetch_expiries
from app.core.config import settings
from app.models.market import ChainSnapshot
from app.services.demo import demo_chain, demo_expiries


async def get_expiries() -> list[str]:
    if settings.app_mode == "demo":
        return demo_expiries()
    return await fetch_expiries()


async def get_chain(expiry: str) -> ChainSnapshot:
    if settings.app_mode == "demo":
        return demo_chain(expiry)
    return await fetch_chain(expiry)
