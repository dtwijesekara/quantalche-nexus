from __future__ import annotations

from datetime import datetime, timezone

import httpx

from .base import OHLCClient
from .models import OHLCBar, Timeframe

_BASE_URL = "https://api.binance.com/api/v3/klines"

# Binance's interval strings happen to match our Timeframe values exactly
# (1m, 5m, 15m, 30m, 1h, 4h, 1d), so no mapping table is needed here.
_SUPPORTED = {tf.value for tf in Timeframe}


class BinanceClient(OHLCClient):
    """Crypto OHLC via Binance's public market-data REST API.

    No API key required for klines — this is Binance's public,
    unauthenticated market-data endpoint.
    """

    source_name = "binance"

    def __init__(self, timeout: float = 10.0) -> None:
        self._client = httpx.Client(timeout=timeout)

    def get_ohlc(
        self,
        symbol: str,
        timeframe: Timeframe,
        limit: int = 500,
        end_time: datetime | None = None,
    ) -> list[OHLCBar]:
        if timeframe.value not in _SUPPORTED:
            raise ValueError(f"Unsupported timeframe: {timeframe}")

        params: dict[str, str | int] = {
            "symbol": symbol.upper(),
            "interval": timeframe.value,
            "limit": min(limit, 1000),
        }
        if end_time is not None:
            params["endTime"] = int(end_time.timestamp() * 1000)

        response = self._client.get(_BASE_URL, params=params)
        response.raise_for_status()
        raw = response.json()

        now_ms = datetime.now(timezone.utc).timestamp() * 1000
        bars: list[OHLCBar] = []
        for row in raw:
            open_time_ms, open_, high, low, close, volume, close_time_ms = row[:7]
            if close_time_ms >= now_ms:
                # Still-forming bar -- exclude per the non-repainting rule.
                continue
            bars.append(
                OHLCBar(
                    symbol=symbol.upper(),
                    timeframe=timeframe,
                    open_time=datetime.fromtimestamp(
                        open_time_ms / 1000, tz=timezone.utc
                    ),
                    open=float(open_),
                    high=float(high),
                    low=float(low),
                    close=float(close),
                    volume=float(volume),
                    source=self.source_name,
                )
            )
        return bars

    def close(self) -> None:
        self._client.close()
