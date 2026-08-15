from __future__ import annotations

import asyncio
import logging

from fastapi import APIRouter, HTTPException, Query, WebSocket, WebSocketDisconnect
from starlette.concurrency import run_in_threadpool

from ..aggregation.models import AggregationMode
from ..ingestion.models import OHLCBar, Timeframe
from .schemas import SignalResponse
from .service import SignalServiceError, build_signal_response, fetch_bars

logger = logging.getLogger("quantalche.api")

router = APIRouter()


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/bars", response_model=list[OHLCBar])
def get_bars(
    source: str = Query(..., pattern="^(binance|twelvedata)$"),
    symbol: str = Query(..., min_length=1),
    timeframe: Timeframe = Query(Timeframe.H1),
    limit: int = Query(300, ge=1, le=1000),
) -> list[OHLCBar]:
    """Raw closed OHLC bars -- what the frontend's price chart renders.
    Separate from /signals since a chart needs the underlying series, not
    just the derived signal.
    """
    try:
        return fetch_bars(source, symbol, timeframe, limit)
    except SignalServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc


@router.get("/signals", response_model=SignalResponse)
def get_signal(
    source: str = Query(..., pattern="^(binance|twelvedata)$"),
    symbol: str = Query(..., min_length=1),
    timeframe: Timeframe = Query(Timeframe.H1),
    mode: AggregationMode = Query(AggregationMode.HARD_GATE),
    limit: int = Query(300, ge=60, le=1000),
) -> SignalResponse:
    """On-demand signal request (architecture.md Layer 8). Runs the full
    pipeline live and advances that (source, symbol, timeframe)'s
    persistent state machine -- safe to call repeatedly, see
    SignalRegistry's docstring.
    """
    try:
        return build_signal_response(source, symbol, timeframe, mode, limit)
    except SignalServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc


@router.websocket("/ws/signals")
async def ws_signals(
    websocket: WebSocket,
    source: str,
    symbol: str,
    timeframe: Timeframe = Timeframe.H1,
    mode: AggregationMode = AggregationMode.HARD_GATE,
    limit: int = 300,
    poll_seconds: float = 30.0,
) -> None:
    """Live updates for one (source, symbol, timeframe) (architecture.md
    Layer 8's WebSocket requirement). Polls at ``poll_seconds`` and pushes
    a fresh SignalResponse each tick -- the underlying REST call is
    idempotent (SignalRegistry), so polling faster than a new bar closes
    is harmless, just redundant.

    ``poll_seconds`` is NOT source-stated -- a reasonable default balancing
    freshness against hammering the upstream data provider on every tick.
    """
    await websocket.accept()
    poll_seconds = max(poll_seconds, 5.0)  # floor to avoid accidental hammering
    try:
        while True:
            try:
                response = await run_in_threadpool(
                    build_signal_response, source, symbol, timeframe, mode, limit
                )
                await websocket.send_json(response.model_dump(mode="json"))
            except SignalServiceError as exc:
                await websocket.send_json({"error": exc.message})
            await asyncio.sleep(poll_seconds)
    except WebSocketDisconnect:
        logger.info("WebSocket disconnected: %s %s %s", source, symbol, timeframe.value)
