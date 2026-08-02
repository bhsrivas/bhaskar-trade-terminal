from __future__ import annotations

import math
from datetime import date, datetime, timedelta

from app.models.market import ChainSnapshot, Greeks, OptionContract


def demo_expiries() -> list[str]:
    today = date.today()
    days = (1 - today.weekday()) % 7
    first = today + timedelta(days=days or 7)
    return [(first + timedelta(days=7 * i)).isoformat() for i in range(4)]


def demo_chain(expiry: str) -> ChainSnapshot:
    spot = 24317.15
    contracts: list[OptionContract] = []

    for strike in range(23700, 24901, 50):
        m = spot - strike
        call_delta = max(0.04, min(0.96, 0.5 + m / 950))
        put_delta = -(1 - call_delta)
        gamma = max(0.00025, 0.00145 - abs(m) / 700000)
        time_value = max(7, 108 - abs(m) * 0.14)

        ce_ltp = max(3.0, max(m, 0) + time_value)
        pe_ltp = max(3.0, max(-m, 0) + time_value)
        iv = max(8.5, 9.7 + abs(m) / 350)
        distance = abs(strike - round(spot / 50) * 50)
        base_oi = int(6_000_000 * math.exp(-distance / 400) + 400_000)

        ce_oi = int(base_oi * (1.3 if strike >= 24500 else 0.9))
        pe_oi = int(base_oi * (1.35 if strike <= 24300 else 0.75))

        contracts.append(
            OptionContract(
                side="ce",
                strike=strike,
                last_price=round(ce_ltp, 2),
                bid=round(max(0.05, ce_ltp - 0.25), 2),
                ask=round(ce_ltp + 0.25, 2),
                implied_volatility=iv,
                oi=ce_oi,
                previous_oi=int(ce_oi * 0.82),
                volume=ce_oi * 4,
                greeks=Greeks(delta=call_delta, gamma=gamma, theta=-11, vega=11),
            )
        )

        contracts.append(
            OptionContract(
                side="pe",
                strike=strike,
                last_price=round(pe_ltp, 2),
                bid=round(max(0.05, pe_ltp - 0.25), 2),
                ask=round(pe_ltp + 0.25, 2),
                implied_volatility=iv + 0.2,
                oi=pe_oi,
                previous_oi=int(pe_oi * 0.74),
                volume=pe_oi * 4,
                greeks=Greeks(delta=put_delta, gamma=gamma, theta=-11, vega=11),
            )
        )

    return ChainSnapshot(
        spot=spot,
        expiry=expiry,
        as_of=datetime.now().isoformat(),
        mode="demo",
        contracts=contracts,
    )
