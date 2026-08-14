from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class Bias(str, Enum):
    BULLISH = "bullish"
    BEARISH = "bearish"
    NEUTRAL = "neutral"


class ModuleSignal(BaseModel):
    """The one thing every Layer 2 module produces: its own directional
    read and confidence, in isolation -- never a final decision. Layer 3
    (not built yet) is the only place these get combined, per
    architecture.md's "modules stay fully independent" rule.
    """

    module: str
    bias: Bias
    confidence: float = Field(ge=0.0, le=1.0)
    reason: str
    bar_time: datetime
