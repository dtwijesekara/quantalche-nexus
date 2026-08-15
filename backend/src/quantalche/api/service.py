from __future__ import annotations

from ..aggregation.models import AggregationMode
from ..config import TWELVE_DATA_API_KEY
from ..ingestion.base import OHLCClient
from ..ingestion.binance_client import BinanceClient
from ..ingestion.models import Timeframe
from ..ingestion.twelvedata_client import TwelveDataClient
from .schemas import SignalResponse
from .state import signal_registry

MIN_BARS_REQUIRED = 60


class SignalServiceError(Exception):
    """Raised for client-facing errors (bad source, missing key, not
    enough data) -- routes.py maps this to an HTTP 400/422/503.
    """

    def __init__(self, message: str, status_code: int = 400) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code


def _make_client(source: str) -> OHLCClient:
    if source == "binance":
        return BinanceClient()
    if source == "twelvedata":
        if not TWELVE_DATA_API_KEY:
            raise SignalServiceError(
                "Twelve Data source requires TWELVE_DATA_API_KEY to be configured "
                "on the server (see backend/.env.example).",
                status_code=503,
            )
        return TwelveDataClient(api_key=TWELVE_DATA_API_KEY)
    raise SignalServiceError(
        f"Unknown source '{source}' -- expected 'binance' or 'twelvedata'."
    )


def build_signal_response(
    source: str,
    symbol: str,
    timeframe: Timeframe,
    mode: AggregationMode,
    limit: int,
) -> SignalResponse:
    """Fetch fresh bars, run the pipeline, and advance this
    (source, symbol, timeframe)'s persistent state machine if a new bar
    has closed since the last call. Safe to call repeatedly for the same
    symbol -- see SignalRegistry's docstring for the idempotency guarantee.
    """
    client = _make_client(source)
    try:
        bars = client.get_ohlc(symbol, timeframe, limit=limit)
    finally:
        client.close()

    if len(bars) < MIN_BARS_REQUIRED:
        raise SignalServiceError(
            f"Only {len(bars)} closed bars available for {symbol} on {source} -- "
            f"need at least {MIN_BARS_REQUIRED} to evaluate the pipeline.",
            status_code=422,
        )

    registry_key = f"{source}:{symbol}"
    state, machine, aggregated, _confirmation = signal_registry.update(
        registry_key, timeframe, bars, mode
    )

    return SignalResponse(
        source=source,
        symbol=symbol,
        timeframe=timeframe,
        mode=mode,
        bar_time=bars[-1].open_time,
        state=state,
        aggregated_signal=aggregated,
        pending_trade=machine.pending_trade,
        active_trade=machine.active_trade,
    )
