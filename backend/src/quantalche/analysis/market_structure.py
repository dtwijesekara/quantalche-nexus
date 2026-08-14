from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel

from ..ingestion.models import OHLCBar
from .base import AnalysisModule
from .models import Bias, ModuleSignal
from .swings import SwingKind, SwingPoint, find_swings


class StructureEventType(str, Enum):
    BOS = "bos"  # continuation
    CHOCH = "choch"  # reversal -- treated as synonymous with MSS, see below


class StructureEvent(BaseModel):
    event: StructureEventType
    direction: Bias
    at: datetime
    broken_level: float
    close_price: float


class MarketStructureModule(AnalysisModule):
    """Layer 2 module: BOS (continuation) / CHoCH (reversal) structure
    breaks, derived from a swing-high/swing-low sequence.

    Rule sources (docs/phase0-knowledge-extraction.md S2.1, S7 item 3;
    full citations in docs/rule-mapping.md):
      - BOS = trend continuation, CHoCH = reversal signal (doc 06 p.8 and
        corroborated corpus-wide).
      - Break validity: a bar's *close* must fully break the reference
        swing level -- a wick alone does not count (doc 20 SS36-37, the
        only document precise enough to state a mechanical test).
      - MSS (Market Structure Shift) is treated as a synonym for CHoCH, not
        a third distinct signal -- an explicit Phase 0 judgment call
        (S7 item 3), since the corpus doesn't converge on treating them as
        different (doc 12 draws a three-way distinction; most other
        documents use MSS and CHoCH interchangeably).

    Swing-point formation (``swing_strength``) is NOT stated by any of the
    22 documents -- BOS/CHoCH is universally used as a concept, but no
    document gives a formation rule for the swing highs/lows structure is
    built from (doc 08 explicitly notes this gap in its own text). A
    standard fractal/pivot convention is adopted here instead of inventing
    something corpus-specific: bar i is a swing high if its high is
    strictly greater than every other bar's high in a window of
    ``swing_strength`` bars on each side (mirror rule for swing lows).
    Default of 2 matches the common "5-bar fractal" convention. This is an
    explicit, documented addition, not a source-stated rule.

    Non-repainting note: a swing point at index j is only usable once
    ``swing_strength`` bars have closed after it (that's what makes it a
    confirmed local extreme) -- i.e. it becomes known at index
    j + swing_strength, never earlier. This module enforces that lag
    explicitly so it never "knows" about a swing before a live system
    would have.
    """

    name = "market_structure"

    def __init__(self, swing_strength: int = 2) -> None:
        self.swing_strength = swing_strength

    def _structure_events(
        self, bars: list[OHLCBar]
    ) -> tuple[list[StructureEvent], Bias]:
        swings = find_swings(bars, self.swing_strength)
        swing_by_index: dict[int, list[SwingPoint]] = {}
        for sp in swings:
            swing_by_index.setdefault(sp.index, []).append(sp)

        events: list[StructureEvent] = []
        trend: Bias = Bias.NEUTRAL
        last_high: SwingPoint | None = None
        last_low: SwingPoint | None = None

        for i, bar in enumerate(bars):
            confirmed_idx = i - self.swing_strength
            for sp in swing_by_index.get(confirmed_idx, []):
                if sp.kind is SwingKind.HIGH:
                    last_high = sp
                else:
                    last_low = sp

            if last_high is not None and bar.close > last_high.price:
                event_type = (
                    StructureEventType.BOS
                    if trend in (Bias.BULLISH, Bias.NEUTRAL)
                    else StructureEventType.CHOCH
                )
                events.append(
                    StructureEvent(
                        event=event_type,
                        direction=Bias.BULLISH,
                        at=bar.open_time,
                        broken_level=last_high.price,
                        close_price=bar.close,
                    )
                )
                trend = Bias.BULLISH
                last_high = None
            elif last_low is not None and bar.close < last_low.price:
                event_type = (
                    StructureEventType.BOS
                    if trend in (Bias.BEARISH, Bias.NEUTRAL)
                    else StructureEventType.CHOCH
                )
                events.append(
                    StructureEvent(
                        event=event_type,
                        direction=Bias.BEARISH,
                        at=bar.open_time,
                        broken_level=last_low.price,
                        close_price=bar.close,
                    )
                )
                trend = Bias.BEARISH
                last_low = None

        return events, trend

    def evaluate(self, bars: list[OHLCBar]) -> ModuleSignal:
        min_bars = 2 * self.swing_strength + 3
        if len(bars) < min_bars:
            return ModuleSignal(
                module=self.name,
                bias=Bias.NEUTRAL,
                confidence=0.0,
                reason="Not enough closed bars to confirm any swing structure.",
                bar_time=bars[-1].open_time if bars else datetime.now(timezone.utc),
            )

        events, trend = self._structure_events(bars)
        last = bars[-1]

        if trend is Bias.NEUTRAL or not events:
            return ModuleSignal(
                module=self.name,
                bias=Bias.NEUTRAL,
                confidence=0.0,
                reason="No confirmed structure break yet.",
                bar_time=last.open_time,
            )

        last_event = events[-1]
        fresh = last_event.at == last.open_time

        if fresh:
            confidence = 0.8 if last_event.event is StructureEventType.CHOCH else 0.65
            label = (
                "CHoCH/MSS (reversal)"
                if last_event.event is StructureEventType.CHOCH
                else "BOS (continuation)"
            )
            level_kind = "swing high" if last_event.direction is Bias.BULLISH else "swing low"
            reason = (
                f"Fresh {label} on this bar -- close {last_event.close_price:.5f} "
                f"broke the {level_kind} at {last_event.broken_level:.5f}."
            )
        else:
            confidence = 0.35
            reason = (
                f"Structure still {trend.value} from the last confirmed break; "
                f"no new break on this bar."
            )

        return ModuleSignal(
            module=self.name,
            bias=trend,
            confidence=confidence,
            reason=reason,
            bar_time=last.open_time,
        )
