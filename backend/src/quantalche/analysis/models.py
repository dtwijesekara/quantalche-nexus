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
    level: float | None = None
    """The specific price this signal is anchored to (a zone edge, a broken
    swing level, a swept liquidity price, a QML, a trendline touch price),
    when the module has one. None for a NEUTRAL signal, or when no single
    price is meaningful. Layer 5 (confirmation/execution) uses this to
    compute a real limit-order entry price instead of the current close --
    architecture.md's Layer 6 calls for "entry as limit order," which needs
    to be a price the modules actually reacted to.
    """
