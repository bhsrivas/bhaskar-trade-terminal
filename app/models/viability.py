from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class ViabilityRequest(BaseModel):
    expiry: str
    strike: float
    side: Literal["ce", "pe"]
    lots: int = Field(ge=1, le=100)
    target_net_profit: float = Field(gt=0)
    entry_price: float = Field(gt=0)
    charge_buffer: float = Field(ge=0, default=150)
    expected_range_remaining: float | None = Field(default=None, ge=0)


class ViabilityResponse(BaseModel):
    verdict: Literal["VIABLE", "MARGINAL", "NOT_VIABLE"]
    score: float
    selected_strike: float
    side: str
    lots: int
    quantity: int
    entry_price: float
    current_ltp: float
    current_bid: float
    current_ask: float
    required_exit_premium: float
    premium_gain_required: float
    required_nifty_move: float
    estimated_spot_target: float
    delta_efficiency: float
    gamma_support: float
    spread_pct: float
    liquidity_score: float
    oi_signal: str
    expected_range_remaining: float | None
    reasons: list[str]
    better_strike: float | None = None
    better_strike_score: float | None = None
