from __future__ import annotations

from enum import Enum

from pydantic import BaseModel
from datetime import datetime

from ..ingestion.models import OHLCBar


class SwingKind(str, Enum):
    HIGH = "high"
    LOW = "low"


class SwingPoint(BaseModel):
    kind: SwingKind
    index: int
    price: float
    at: datetime


def find_swings(bars: list[OHLCBar], strength: int) -> list[SwingPoint]:
    """Standard fractal/pivot swing detection: bar i is a swing high/low if
    its high/low is strictly the most extreme within `strength` bars on
    each side. Consecutive same-kind candidates collapse to the most
    extreme one, so the returned sequence strictly alternates high/low.

    Shared by every module that needs a swing-point concept (Market
    Structure, Liquidity/Sweep, and future ones) -- this is stateless
    utility math, not the kind of module cross-talk architecture.md rules
    out (which is about one module's *signal* feeding another's, not
    reusing a shared geometric definition). NOT a source-stated rule --
    see market_structure.py's docstring for why an external convention was
    needed here.
    """
    n = len(bars)
    raw: list[SwingPoint] = []
    for i in range(strength, n - strength):
        window_idx = [j for j in range(i - strength, i + strength + 1) if j != i]
        if all(bars[i].high > bars[j].high for j in window_idx):
            raw.append(
                SwingPoint(
                    kind=SwingKind.HIGH, index=i, price=bars[i].high, at=bars[i].open_time
                )
            )
        if all(bars[i].low < bars[j].low for j in window_idx):
            raw.append(
                SwingPoint(
                    kind=SwingKind.LOW, index=i, price=bars[i].low, at=bars[i].open_time
                )
            )

    swings: list[SwingPoint] = []
    for point in raw:
        if swings and swings[-1].kind == point.kind:
            more_extreme = (
                point.kind is SwingKind.HIGH and point.price > swings[-1].price
            ) or (point.kind is SwingKind.LOW and point.price < swings[-1].price)
            if more_extreme:
                swings[-1] = point
        else:
            swings.append(point)
    return swings
