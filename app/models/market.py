from __future__ import annotations

from pydantic import BaseModel, Field


class Greeks(BaseModel):
    delta: float = 0.0
    gamma: float = 0.0
    theta: float = 0.0
    vega: float = 0.0


class OptionContract(BaseModel):
    side: str
    strike: float
    last_price: float = 0.0
    bid: float = 0.0
    ask: float = 0.0
    implied_volatility: float = 0.0
    oi: float = 0.0
    previous_oi: float = 0.0
    volume: float = 0.0
    greeks: Greeks = Field(default_factory=Greeks)

    @property
    def oi_change(self) -> float:
        return self.oi - self.previous_oi

    @property
    def spread(self) -> float:
        if self.ask <= 0 or self.bid <= 0:
            return 0.0
        return max(0.0, self.ask - self.bid)

    @property
    def spread_pct(self) -> float:
        mid = (self.ask + self.bid) / 2
        return (self.spread / mid * 100) if mid > 0 else 0.0


class ChainSnapshot(BaseModel):
    spot: float
    expiry: str
    as_of: str
    mode: str
    contracts: list[OptionContract]
