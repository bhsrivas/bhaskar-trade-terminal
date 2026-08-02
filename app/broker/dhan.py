from __future__ import annotations

from datetime import datetime
from typing import Any

import httpx
from fastapi import HTTPException

from app.core.config import settings
from app.models.market import ChainSnapshot, Greeks, OptionContract


def _headers() -> dict[str, str]:
    if not settings.dhan_client_id or not settings.dhan_access_token:
        raise HTTPException(status_code=503, detail="Dhan credentials are not configured.")
    return {
        "Content-Type": "application/json",
        "access-token": settings.dhan_access_token,
        "client-id": settings.dhan_client_id,
    }


def _number(value: Any, default: float = 0.0) -> float:
    try:
        if value is None or value == "":
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _first(mapping: dict[str, Any], *keys: str, default: Any = None) -> Any:
    for key in keys:
        if key in mapping and mapping[key] is not None:
            return mapping[key]
    return default


def _extract_side_node(node: dict[str, Any], side: str) -> dict[str, Any]:
    aliases = {
        "ce": ("ce", "CE", "call", "CALL", "Call"),
        "pe": ("pe", "PE", "put", "PUT", "Put"),
    }
    for key in aliases[side]:
        value = node.get(key)
        if isinstance(value, dict):
            return value
    return {}


def _normalise_contract(strike: float, side: str, raw: dict[str, Any]) -> OptionContract:
    greeks_raw = raw.get("greeks") if isinstance(raw.get("greeks"), dict) else {}

    last_price = _number(_first(raw, "last_price", "ltp", "LTP", "lastPrice"))
    bid = _number(_first(raw, "top_bid_price", "bid", "best_bid_price", "bidPrice"))
    ask = _number(_first(raw, "top_ask_price", "ask", "best_ask_price", "askPrice"))

    return OptionContract(
        side=side,
        strike=strike,
        last_price=last_price,
        bid=bid,
        ask=ask,
        implied_volatility=_number(
            _first(raw, "implied_volatility", "iv", "IV", "impliedVolatility")
        ),
        oi=_number(_first(raw, "oi", "open_interest", "openInterest")),
        previous_oi=_number(
            _first(raw, "previous_oi", "previous_open_interest", "prev_oi", "previousOi")
        ),
        volume=_number(_first(raw, "volume", "traded_volume", "tradedVolume")),
        greeks=Greeks(
            delta=_number(_first(greeks_raw, "delta", "Delta")),
            gamma=_number(_first(greeks_raw, "gamma", "Gamma")),
            theta=_number(_first(greeks_raw, "theta", "Theta")),
            vega=_number(_first(greeks_raw, "vega", "Vega")),
        ),
    )


def normalise_dhan_chain(payload: dict[str, Any], expiry: str, mode: str = "live") -> ChainSnapshot:
    body = payload.get("data") if isinstance(payload.get("data"), dict) else payload
    spot = _number(_first(body, "last_price", "underlying_ltp", "spot", "underlyingPrice"))

    chain_raw = _first(body, "oc", "option_chain", "optionChain", default={})
    contracts: list[OptionContract] = []

    if isinstance(chain_raw, dict):
        items = chain_raw.items()
    elif isinstance(chain_raw, list):
        items = []
        for item in chain_raw:
            if not isinstance(item, dict):
                continue
            strike_value = _first(item, "strike", "strike_price", "strikePrice")
            items.append((str(strike_value), item))
    else:
        items = []

    for strike_key, node in items:
        if not isinstance(node, dict):
            continue
        strike = _number(_first(node, "strike", "strike_price", "strikePrice", default=strike_key))
        if strike <= 0:
            continue
        for side in ("ce", "pe"):
            side_node = _extract_side_node(node, side)
            if not side_node:
                continue
            contracts.append(_normalise_contract(strike, side, side_node))

    return ChainSnapshot(
        spot=spot,
        expiry=expiry,
        as_of=datetime.now().isoformat(),
        mode=mode,
        contracts=contracts,
    )


async def fetch_expiries() -> list[str]:
    payload = {
        "UnderlyingScrip": settings.nifty_security_id,
        "UnderlyingSeg": settings.nifty_segment,
    }
    async with httpx.AsyncClient(timeout=15) as client:
        response = await client.post(
            f"{settings.dhan_base_url}/optionchain/expirylist",
            headers=_headers(),
            json=payload,
        )
    if response.status_code >= 400:
        raise HTTPException(response.status_code, response.text)

    body = response.json()
    data = body.get("data", body)
    if isinstance(data, list):
        return [str(x) for x in data]
    if isinstance(data, dict):
        for key in ("data", "expiries", "expiry_list", "expiryList"):
            value = data.get(key)
            if isinstance(value, list):
                return [str(x) for x in value]
    return []


async def fetch_chain(expiry: str) -> ChainSnapshot:
    payload = {
        "UnderlyingScrip": settings.nifty_security_id,
        "UnderlyingSeg": settings.nifty_segment,
        "Expiry": expiry,
    }
    async with httpx.AsyncClient(timeout=15) as client:
        response = await client.post(
            f"{settings.dhan_base_url}/optionchain",
            headers=_headers(),
            json=payload,
        )
    if response.status_code >= 400:
        raise HTTPException(response.status_code, response.text)
    return normalise_dhan_chain(response.json(), expiry=expiry, mode="live")
