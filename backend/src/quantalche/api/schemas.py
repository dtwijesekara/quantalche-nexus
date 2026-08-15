from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from ..aggregation.models import AggregatedSignal, AggregationMode
from ..execution.models import TradeSignal
from ..execution.state_machine import SignalState
from ..ingestion.models import Timeframe


class SignalResponse(BaseModel):
    """The API's single response shape for a signal request -- always
    includes the full per-module breakdown alongside the combined read,
    per architecture.md's "decision support, not certainty" ground rule.
    """

    source: str
    symbol: str
    timeframe: Timeframe
    mode: AggregationMode
    bar_time: datetime
    state: SignalState
    aggregated_signal: AggregatedSignal
    pending_trade: TradeSignal | None
    active_trade: TradeSignal | None


class ErrorResponse(BaseModel):
    detail: str
