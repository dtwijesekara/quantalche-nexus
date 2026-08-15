from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field

from ..aggregation.models import AggregatedSignal


class TradeDirection(str, Enum):
    LONG = "long"
    SHORT = "short"


class RejectionReason(str, Enum):
    NOT_DIRECTIONAL = "not_directional"
    LOW_CONFIDENCE = "low_confidence"
    NO_STOP_REFERENCE = "no_stop_reference"
    INSUFFICIENT_RR = "insufficient_rr"


class TradeSignal(BaseModel):
    """A confirmed, tradable signal -- entry as a limit order, per
    architecture.md Layer 6.
    """

    direction: TradeDirection
    entry: float
    stop_loss: float
    take_profit: float
    risk_reward: float = Field(ge=0.0)
    confidence: float = Field(ge=0.0, le=1.0)
    bar_time: datetime
    aggregated_signal: AggregatedSignal
    reason: str


class ConfirmationResult(BaseModel):
    """Layer 5 output: either a tradable TradeSignal, or an explicit
    rejection reason -- architecture.md's "decision support, not
    certainty" ground rule means a rejected/provisional signal is reported
    with its reason, not silently dropped.
    """

    confirmed: bool
    trade_signal: TradeSignal | None = None
    rejection_reason: RejectionReason | None = None
    detail: str
