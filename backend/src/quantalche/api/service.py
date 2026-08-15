from __future__ import annotations

import httpx

from ..aggregation.models import AggregationMode
from ..config import TWELVE_DATA_API_KEY
from ..ingestion.base import OHLCClient
from ..ingestion.binance_client import BinanceClient
from ..ingestion.models import OHLCBar, Timeframe
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


def fetch_bars(
    source: str, symbol: str, timeframe: Timeframe, limit: int
) -> list[OHLCBar]:
    """Fetch bars from the upstream data source, converting upstream
    failures (rate limits, timeouts, bad symbols) into a clean
    SignalServiceError instead of letting them escape as an unhandled
    exception.

    This matters beyond error-message quality: an unhandled exception
    here produces a raw FastAPI 500 that doesn't reliably carry CORS
    response headers, which browsers then report as a generic "CORS
    policy" error -- hiding the real cause (e.g. a Twelve Data free-tier
    rate limit) behind a misleading one. Found via live browser testing,
    not a unit test -- see rule-mapping.md.
    """
    client = _make_client(source)
    try:
        return client.get_ohlc(symbol, timeframe, limit=limit)
    except SignalServiceError:
        raise
    except httpx.TimeoutException as exc:
        raise SignalServiceError(
            f"Timed out fetching data from {source} for {symbol}.", status_code=504
        ) from exc
    except httpx.HTTPStatusError as exc:
        raise SignalServiceError(
            f"{source} rejected the request for {symbol} "
            f"(HTTP {exc.response.status_code}) -- possibly an unsupported "
            f"symbol or a rate limit.",
            status_code=502,
        ) from exc
    except (httpx.HTTPError, RuntimeError, ValueError) as exc:
        raise SignalServiceError(
            f"Failed to fetch data from {source} for {symbol}: {exc}",
            status_code=502,
        ) from exc
    finally:
        client.close()


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
    bars = fetch_bars(source, symbol, timeframe, limit)

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
