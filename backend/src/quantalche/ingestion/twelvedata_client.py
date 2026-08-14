from __future__ import annotations

from datetime import datetime, timedelta, timezone

import httpx

from .base import OHLCClient
from .models import OHLCBar, Timeframe

_BASE_URL = "https://api.twelvedata.com/time_series"

_INTERVAL_MAP: dict[Timeframe, str] = {
    Timeframe.M1: "1min",
    Timeframe.M5: "5min",
    Timeframe.M15: "15min",
    Timeframe.M30: "30min",
    Timeframe.H1: "1h",
    Timeframe.H4: "4h",
    Timeframe.D1: "1day",
}

_BAR_DURATION: dict[Timeframe, timedelta] = {
    Timeframe.M1: timedelta(minutes=1),
    Timeframe.M5: timedelta(minutes=5),
    Timeframe.M15: timedelta(minutes=15),
    Timeframe.M30: timedelta(minutes=30),
    Timeframe.H1: timedelta(hours=1),
    Timeframe.H4: timedelta(hours=4),
    Timeframe.D1: timedelta(days=1),
}


class TwelveDataClient(OHLCClient):
    """Forex (and broader multi-asset) OHLC via the Twelve Data REST API.

    Requires a free API key from https://twelvedata.com/ — see
    backend/.env.example.
    """

    source_name = "twelvedata"

    def __init__(self, api_key: str, timeout: float = 10.0) -> None:
        if not api_key:
            raise ValueError(
                "Twelve Data requires an API key -- set TWELVE_DATA_API_KEY "
                "in backend/.env (see backend/.env.example)."
            )
        self._api_key = api_key
        self._client = httpx.Client(timeout=timeout)

    def get_ohlc(
        self,
        symbol: str,
        timeframe: Timeframe,
        limit: int = 500,
        end_time: datetime | None = None,
    ) -> list[OHLCBar]:
        interval = _INTERVAL_MAP.get(timeframe)
        if interval is None:
            raise ValueError(f"Unsupported timeframe: {timeframe}")

        params: dict[str, str | int] = {
            "symbol": symbol,
            "interval": interval,
            "outputsize": min(limit, 5000),
            "timezone": "UTC",
            "order": "ASC",
            "apikey": self._api_key,
        }
        if end_time is not None:
            params["end_date"] = end_time.strftime("%Y-%m-%d %H:%M:%S")

        response = self._client.get(_BASE_URL, params=params)
        response.raise_for_status()
        payload = response.json()

        if payload.get("status") == "error":
            raise RuntimeError(f"Twelve Data error: {payload.get('message')}")

        duration = _BAR_DURATION[timeframe]
        now = datetime.now(timezone.utc)
        bars: list[OHLCBar] = []
        for row in payload.get("values", []):
            open_time = datetime.strptime(
                row["datetime"], "%Y-%m-%d %H:%M:%S"
            ).replace(tzinfo=timezone.utc)
            if open_time + duration > now:
                # Still-forming bar -- exclude per the non-repainting rule.
                continue
            bars.append(
                OHLCBar(
                    symbol=symbol,
                    timeframe=timeframe,
                    open_time=open_time,
                    open=float(row["open"]),
                    high=float(row["high"]),
                    low=float(row["low"]),
                    close=float(row["close"]),
                    volume=float(row.get("volume") or 0.0),
                    source=self.source_name,
                )
            )
        return bars

    def close(self) -> None:
        self._client.close()
