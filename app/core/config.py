from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    base_dir: Path = Path(__file__).resolve().parents[2]
    app_mode: str = os.getenv("APP_MODE", "demo").lower()
    dhan_client_id: str = os.getenv("DHAN_CLIENT_ID", "")
    dhan_access_token: str = os.getenv("DHAN_ACCESS_TOKEN", "")
    nifty_security_id: int = int(os.getenv("NIFTY_SECURITY_ID", "13"))
    nifty_segment: str = os.getenv("NIFTY_SEGMENT", "IDX_I")
    lot_size: int = int(os.getenv("DEFAULT_LOT_SIZE", "65"))
    target_net: float = float(os.getenv("DEFAULT_TARGET_NET", "5000"))
    charge_buffer: float = float(os.getenv("CHARGE_BUFFER", "150"))
    poll_seconds: int = 3
    dhan_base_url: str = "https://api.dhan.co/v2"


settings = Settings()
