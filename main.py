\
from __future__ import annotations

import math
import os
from datetime import date, datetime, timedelta
from typing import Any

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

load_dotenv()

app = FastAPI(title="Bhaskar Trade Terminal", version="0.1.0")
app.mount("/static", StaticFiles(directory="static"), name="static")

APP_MODE = os.getenv("APP_MODE", "demo").lower()
DHAN_CLIENT_ID = os.getenv("DHAN_CLIENT_ID", "")
DHAN_ACCESS_TOKEN = os.getenv("DHAN_ACCESS_TOKEN", "")
NIFTY_SECURITY_ID = int(os.getenv("NIFTY_SECURITY_ID", "13"))
NIFTY_SEGMENT = os.getenv("NIFTY_SEGMENT", "IDX_I")
DEFAULT_LOT_SIZE = int(os.getenv("DEFAULT_LOT_SIZE", "65"))
DEFAULT_TARGET_NET = float(os.getenv("DEFAULT_TARGET_NET", "5000"))
CHARGE_BUFFER = float(os.getenv("CHARGE_BUFFER", "150"))

DHAN_BASE = "https://api.dhan.co/v2"


@app.get("/")
async def home() -> FileResponse:
    return FileResponse("static/index.html")


@app.get("/api/health")
async def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "mode": APP_MODE,
        "credentials_configured": bool(DHAN_CLIENT_ID and DHAN_ACCESS_TOKEN),
        "timestamp": datetime.now().isoformat(),
    }


def dhan_headers() -> dict[str, str]:
    if not DHAN_CLIENT_ID or not DHAN_ACCESS_TOKEN:
        raise HTTPException(
            status_code=503,
            detail="Dhan credentials are not configured. Add DHAN_CLIENT_ID and DHAN_ACCESS_TOKEN.",
        )
    return {
        "Content-Type": "application/json",
        "access-token": DHAN_ACCESS_TOKEN,
        "client-id": DHAN_CLIENT_ID,
    }


@app.get("/api/expiries")
async def expiries() -> dict[str, Any]:
    if APP_MODE == "demo":
        today = date.today()
        # NIFTY weekly expiry configured as Tuesday for this terminal.
        days = (1 - today.weekday()) % 7
        first = today + timedelta(days=days or 7)
        return {"status": "success", "data": [(first + timedelta(days=7*i)).isoformat() for i in range(4)]}

    payload = {"UnderlyingScrip": NIFTY_SECURITY_ID, "UnderlyingSeg": NIFTY_SEGMENT}
    async with httpx.AsyncClient(timeout=12) as client:
        response = await client.post(
            f"{DHAN_BASE}/optionchain/expirylist",
            headers=dhan_headers(),
            json=payload,
        )
    if response.status_code >= 400:
        raise HTTPException(response.status_code, response.text)
    return response.json()


def option_payload(
    ltp: float, delta: float, gamma: float, theta: float, vega: float,
    iv: float, oi: int, previous_oi: int, bid: float, ask: float, volume: int
) -> dict[str, Any]:
    return {
        "last_price": round(ltp, 2),
        "greeks": {
            "delta": round(delta, 4),
            "gamma": round(gamma, 6),
            "theta": round(theta, 3),
            "vega": round(vega, 3),
        },
        "implied_volatility": round(iv, 2),
        "oi": oi,
        "previous_oi": previous_oi,
        "top_bid_price": round(bid, 2),
        "top_ask_price": round(ask, 2),
        "volume": volume,
    }


def demo_chain() -> dict[str, Any]:
    spot = 24317.15
    strikes: dict[str, Any] = {}
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
        ce_prev = int(ce_oi * (0.82 if strike >= 24300 else 1.12))
        pe_prev = int(pe_oi * (0.74 if strike <= 24300 else 0.92))
        strikes[f"{strike:.6f}"] = {
            "ce": option_payload(
                ce_ltp, call_delta, gamma, -11, 11, iv,
                ce_oi, ce_prev, max(0.05, ce_ltp - 0.25), ce_ltp + 0.25, ce_oi * 4
            ),
            "pe": option_payload(
                pe_ltp, put_delta, gamma, -11, 11, iv + 0.2,
                pe_oi, pe_prev, max(0.05, pe_ltp - 0.25), pe_ltp + 0.25, pe_oi * 4
            ),
        }
    return {
        "status": "success",
        "data": {"last_price": spot, "oc": strikes},
        "mode": "demo",
        "as_of": datetime.now().isoformat(),
    }


@app.get("/api/chain")
async def chain(expiry: str = Query(..., pattern=r"^\d{4}-\d{2}-\d{2}$")) -> dict[str, Any]:
    if APP_MODE == "demo":
        return demo_chain()

    payload = {
        "UnderlyingScrip": NIFTY_SECURITY_ID,
        "UnderlyingSeg": NIFTY_SEGMENT,
        "Expiry": expiry,
    }
    async with httpx.AsyncClient(timeout=12) as client:
        response = await client.post(
            f"{DHAN_BASE}/optionchain",
            headers=dhan_headers(),
            json=payload,
        )
    if response.status_code >= 400:
        raise HTTPException(response.status_code, response.text)
    result = response.json()
    result["mode"] = "live"
    result["as_of"] = datetime.now().isoformat()
    return result


@app.get("/api/config")
async def config() -> dict[str, Any]:
    return {
        "lot_size": DEFAULT_LOT_SIZE,
        "target_net": DEFAULT_TARGET_NET,
        "charge_buffer": CHARGE_BUFFER,
        "poll_seconds": 3,
        "mode": APP_MODE,
    }
