from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field

from ..analysis.models import ModuleSignal


class AggregationMode(str, Enum):
    HARD_GATE = "hard_gate"
    SOFT_SCORE = "soft_score"


class AggregatedBias(str, Enum):
    BULLISH = "bullish"
    BEARISH = "bearish"
    NEUTRAL = "neutral"
    CONFLICT = "conflict"  # modules actively disagree -- surfaced, never averaged away


class AggregatedSignal(BaseModel):
    """Layer 3 output: the combined read, always alongside every module's
    individual read that fed it -- architecture.md's "decision support, not
    certainty" ground rule requires showing both, never just the combined
    number.
    """

    bias: AggregatedBias
    confidence: float = Field(ge=0.0, le=1.0)
    mode: AggregationMode
    reason: str
    bar_time: datetime
    module_signals: list[ModuleSignal]
