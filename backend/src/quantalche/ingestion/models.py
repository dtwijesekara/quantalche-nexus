from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel, field_validator


class Timeframe(str, Enum):
    M1 = "1m"
    M5 = "5m"
    M15 = "15m"
    M30 = "30m"
    H1 = "1h"
    H4 = "4h"
    D1 = "1d"


class OHLCBar(BaseModel):
    """One fully closed OHLC bar.

    Non-repainting (architecture.md ground rule #2): every client in this
    package must exclude the still-forming current bar before constructing
    these, so an ``OHLCBar`` instance always represents a settled price.
    """

    symbol: str
    timeframe: Timeframe
    open_time: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float
    source: str

    @field_validator("open_time")
    @classmethod
    def _ensure_utc(cls, v: datetime) -> datetime:
        if v.tzinfo is None:
            return v.replace(tzinfo=timezone.utc)
        return v.astimezone(timezone.utc)
