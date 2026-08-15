from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel

from ..ingestion.models import OHLCBar
from .base import AnalysisModule
from .models import Bias, ModuleSignal
from .swings import SwingKind, SwingPoint, find_swings


class QMDirection(str, Enum):
    BEARISH = "bearish"
    BULLISH = "bullish"


class QMPattern(BaseModel):
    direction: QMDirection
    p1: SwingPoint
    p2: SwingPoint
    p3: SwingPoint  # the "QM Level" -- the pre-break level price retraces to
    p4: SwingPoint
    qm_level: float
    confirmed_at: datetime


class QMModule(AnalysisModule):
    """Layer 2 module: the QM ("Quasimodo") reversal pattern.

    Rule source (docs/phase0-knowledge-extraction.md S2.3, S7 item 2; full
    citations in docs/rule-mapping.md): doc 10's taxonomy was adopted as
    the canonical definition (QM = the pattern, QML = the specific level it
    marks) over three other incompatible readings found elsewhere in the
    corpus -- an explicit Phase 0 judgment call, not a corpus consensus.

    Pattern definition, from doc 08 S5 (the clearest sequential statement
    in the corpus): "Bearish structure = Higher High -> Higher Low -> Lower
    High -> Lower Low; bullish structure = Lower Low -> Lower High -> Higher
    Low -> Higher High... entry at the retrace Lower High/Higher Low that
    sits at the pre-break level (QM Level)." Formalized here as 4
    consecutive confirmed swing points (p1..p4):
      - Bearish: High, Low, High, Low, where p3 < p1 (failed to make a new
        high -- the "Lower High") and p4 < p2 (breaks the prior low). QML =
        p3's price -- the failed-high retracement zone to watch for a
        retest.
      - Bullish: mirror image (Low, High, Low, High; p3 > p1, p4 > p2).

    Only the base QM/QMR (reversal) pattern is implemented. QMM
    (manipulation) and QMC (continuation) sub-variants, named in docs 01
    and 10, are NOT implemented -- their source descriptions ("manipulation
    fake-break," "continuation fake-break") are narrative, not a checkable
    rule, and Phase 0's own corpus review found these sub-variants aren't
    consistently distinguished even within their own source documents.
    Implementing a distinguishing rule here would mean inventing one, not
    extracting one. Flagged as a candidate follow-up once/if a real
    distinguishing rule turns up elsewhere in the corpus.

    Swing-point formation is shared via swings.py, same non-repainting
    confirmation lag as the other structure-based modules.
    """

    name = "qm_pattern"

    def __init__(
        self,
        swing_strength: int = 2,
        retest_tolerance_ratio: float = 0.15,
        max_pattern_age_bars: int = 80,
    ) -> None:
        self.swing_strength = swing_strength
        self.retest_tolerance_ratio = retest_tolerance_ratio
        self.max_pattern_age_bars = max_pattern_age_bars

    def _match(
        self,
        p1: SwingPoint,
        p2: SwingPoint,
        p3: SwingPoint,
        p4: SwingPoint,
        confirmed_at: datetime,
    ) -> QMPattern | None:
        if (
            p1.kind is SwingKind.HIGH
            and p2.kind is SwingKind.LOW
            and p3.kind is SwingKind.HIGH
            and p4.kind is SwingKind.LOW
        ):
            if p3.price < p1.price and p4.price < p2.price:
                return QMPattern(
                    direction=QMDirection.BEARISH,
                    p1=p1,
                    p2=p2,
                    p3=p3,
                    p4=p4,
                    qm_level=p3.price,
                    confirmed_at=confirmed_at,
                )
        elif (
            p1.kind is SwingKind.LOW
            and p2.kind is SwingKind.HIGH
            and p3.kind is SwingKind.LOW
            and p4.kind is SwingKind.HIGH
        ):
            if p3.price > p1.price and p4.price > p2.price:
                return QMPattern(
                    direction=QMDirection.BULLISH,
                    p1=p1,
                    p2=p2,
                    p3=p3,
                    p4=p4,
                    qm_level=p3.price,
                    confirmed_at=confirmed_at,
                )
        return None

    def _find_patterns(self, bars: list[OHLCBar]) -> list[QMPattern]:
        swings = find_swings(bars, self.swing_strength)
        swing_by_index: dict[int, list[SwingPoint]] = {}
        for sp in swings:
            swing_by_index.setdefault(sp.index, []).append(sp)

        confirmed: list[SwingPoint] = []
        patterns: list[QMPattern] = []
        for i, bar in enumerate(bars):
            confirmed_idx = i - self.swing_strength
            for sp in swing_by_index.get(confirmed_idx, []):
                confirmed.append(sp)
                if len(confirmed) >= 4:
                    p1, p2, p3, p4 = confirmed[-4:]
                    pattern = self._match(p1, p2, p3, p4, bar.open_time)
                    if pattern is not None:
                        patterns.append(pattern)
        return patterns

    def evaluate(self, bars: list[OHLCBar]) -> ModuleSignal:
        if len(bars) < 4 * self.swing_strength + 8:
            return ModuleSignal(
                module=self.name,
                bias=Bias.NEUTRAL,
                confidence=0.0,
                reason="Not enough closed bars to confirm a 4-point QM pattern.",
                bar_time=bars[-1].open_time if bars else datetime.now(timezone.utc),
            )

        patterns = self._find_patterns(bars)
        last = bars[-1]
        last_idx = len(bars) - 1

        if not patterns:
            return ModuleSignal(
                module=self.name,
                bias=Bias.NEUTRAL,
                confidence=0.0,
                reason="No confirmed QM pattern yet.",
                bar_time=last.open_time,
            )

        avg_range = sum(b.high - b.low for b in bars) / len(bars)
        tolerance = avg_range * self.retest_tolerance_ratio

        candidates = [
            p
            for p in patterns
            if p.p4.index < last_idx
            and (last_idx - p.p4.index) <= self.max_pattern_age_bars
        ]

        for pattern in reversed(candidates):
            level = pattern.qm_level
            in_range = (last.low - tolerance) <= level <= (last.high + tolerance)
            if not in_range:
                continue

            if pattern.direction is QMDirection.BEARISH:
                rejected = last.close < last.open and last.close <= level
                bias = Bias.BEARISH
            else:
                rejected = last.close > last.open and last.close >= level
                bias = Bias.BULLISH

            if rejected:
                reason = (
                    f"QM {pattern.direction.value} pattern retest at QML "
                    f"{level:.5f} (pattern confirmed {pattern.confirmed_at.isoformat()})."
                )
                return ModuleSignal(
                    module=self.name,
                    bias=bias,
                    confidence=0.65,
                    reason=reason,
                    bar_time=last.open_time,
                    level=level,
                )

        return ModuleSignal(
            module=self.name,
            bias=Bias.NEUTRAL,
            confidence=0.0,
            reason="No QM level retest with rejection on the latest closed bar.",
            bar_time=last.open_time,
        )
