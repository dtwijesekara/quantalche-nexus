from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel

from ..ingestion.models import OHLCBar
from .base import AnalysisModule
from .models import Bias, ModuleSignal
from .swings import SwingKind, find_swings


class TrendlineType(str, Enum):
    SUPPORT = "support"
    RESISTANCE = "resistance"


class TrendlineVariant(str, Enum):
    TOUCH3_SIMPLE = "touch3_simple"
    TOUCH3_ENGULFING = "touch3_engulfing"


class Trendline(BaseModel):
    line_type: TrendlineType
    anchor1_index: int
    anchor2_index: int
    anchor1_price: float
    anchor2_price: float

    @property
    def slope(self) -> float:
        return (self.anchor2_price - self.anchor1_price) / (
            self.anchor2_index - self.anchor1_index
        )

    def price_at(self, index: int) -> float:
        return self.anchor1_price + self.slope * (index - self.anchor1_index)


def _is_bullish_engulfing(prev: OHLCBar, cur: OHLCBar) -> bool:
    return (
        cur.close > cur.open
        and prev.close < prev.open
        and cur.close >= prev.open
        and cur.open <= prev.close
    )


def _is_bearish_engulfing(prev: OHLCBar, cur: OHLCBar) -> bool:
    return (
        cur.close < cur.open
        and prev.close > prev.open
        and cur.open >= prev.close
        and cur.close <= prev.open
    )


class TrendlineConfluenceModule(AnalysisModule):
    """Layer 2 module: trendline + SNR confluence, entered on the 3rd touch
    of a validated trendline.

    Two competing rule sets exist in the corpus for essentially the same
    idea, from unrelated, non-corroborating sources -- Phase 0 §7 item 4
    resolved this by implementing both as configurable variants rather than
    picking one (docs/phase0-knowledge-extraction.md §2.4, §7):

      - TOUCH3_SIMPLE (docs 06/16/20): "ONLY ENTER a trade when a candle's
        wick touches and rejects an SNR at point #3 of the trendline...
        DO NOT take a trade at point #2." Touches #1-#2 define the line;
        touch #3 is the entry.
      - TOUCH3_ENGULFING (docs 04/05): touches #1 and #2 must each be
        engulfing candles, the 2nd touch must break prior structure, the
        3rd touch requires alignment with an HTF POI, and the trendline
        must sit at a 45-60 degree angle.

    TOUCH3_ENGULFING is only a PARTIAL implementation of doc 04/05's rule.
    Two of its four conditions are NOT implemented, both flagged rather
    than approximated:
      - The 45-60 degree angle constraint has no principled numeric
        equivalent here. A trendline's on-chart angle depends on the
        chart's price/time axis scaling as drawn on a specific platform --
        raw OHLC data doesn't encode that scaling at all, so any numeric
        "angle" computed from price-per-bar slope would be an arbitrary
        normalization choice, not a faithful implementation of what the
        source document actually means. Left out rather than faked.
      - "2nd touch must break prior structure" and "3rd touch requires HTF
        POI alignment" would need this module to depend on
        market_structure.py's/snr_zone.py's *signals*, which would violate
        architecture.md's "modules stay fully independent, no cross-talk"
        rule at Layer 2 -- that kind of composition belongs in Layer 3
        (aggregation), not here. Left out, not silently dropped: documented
        so Layer 3 knows to potentially recombine these three modules'
        outputs to approximate the full doc 04/05 rule later.

    Swing-point formation is shared via swings.py.

    ``touch_tolerance_ratio`` (how close a wick needs to come to the
    extrapolated line to count as a "touch") and a maximum line age are
    both NOT source-stated -- see the note on max age below, added after
    live validation showed old, no-longer-relevant trendlines producing
    spurious touches purely from long-distance extrapolation.
    """

    name = "trendline_confluence"

    def __init__(
        self,
        variant: TrendlineVariant = TrendlineVariant.TOUCH3_SIMPLE,
        swing_strength: int = 2,
        touch_tolerance_ratio: float = 0.15,
        max_line_age_bars: int = 60,
    ) -> None:
        self.variant = variant
        self.swing_strength = swing_strength
        self.touch_tolerance_ratio = touch_tolerance_ratio
        self.max_line_age_bars = max_line_age_bars

    def _build_trendlines(self, bars: list[OHLCBar]) -> list[Trendline]:
        swings = find_swings(bars, self.swing_strength)
        lows = [s for s in swings if s.kind is SwingKind.LOW]
        highs = [s for s in swings if s.kind is SwingKind.HIGH]

        lines: list[Trendline] = []
        for i in range(len(lows) - 1):
            a, b = lows[i], lows[i + 1]
            if b.price > a.price:
                lines.append(
                    Trendline(
                        line_type=TrendlineType.SUPPORT,
                        anchor1_index=a.index,
                        anchor2_index=b.index,
                        anchor1_price=a.price,
                        anchor2_price=b.price,
                    )
                )
        for i in range(len(highs) - 1):
            a, b = highs[i], highs[i + 1]
            if b.price < a.price:
                lines.append(
                    Trendline(
                        line_type=TrendlineType.RESISTANCE,
                        anchor1_index=a.index,
                        anchor2_index=b.index,
                        anchor1_price=a.price,
                        anchor2_price=b.price,
                    )
                )
        return lines

    def _third_touch_signal(
        self, bars: list[OHLCBar], line: Trendline, avg_range: float
    ) -> ModuleSignal | None:
        last_idx = len(bars) - 1
        last = bars[last_idx]

        if last_idx <= line.anchor2_index:
            return None
        if last_idx - line.anchor2_index > self.max_line_age_bars:
            return None

        expected = line.price_at(last_idx)
        tolerance = avg_range * self.touch_tolerance_ratio

        if line.line_type is TrendlineType.SUPPORT:
            touched = abs(last.low - expected) <= tolerance
            rejected = last.close > last.open and last.close >= expected
        else:
            touched = abs(last.high - expected) <= tolerance
            rejected = last.close < last.open and last.close <= expected

        if not (touched and rejected):
            return None

        if self.variant is TrendlineVariant.TOUCH3_ENGULFING:
            a1, a2 = line.anchor1_index, line.anchor2_index
            if a1 == 0 or a2 == 0:
                return None
            if line.line_type is TrendlineType.SUPPORT:
                ok = _is_bullish_engulfing(
                    bars[a1 - 1], bars[a1]
                ) and _is_bullish_engulfing(bars[a2 - 1], bars[a2])
            else:
                ok = _is_bearish_engulfing(
                    bars[a1 - 1], bars[a1]
                ) and _is_bearish_engulfing(bars[a2 - 1], bars[a2])
            if not ok:
                return None

        bias = Bias.BULLISH if line.line_type is TrendlineType.SUPPORT else Bias.BEARISH
        confidence = 0.7 if self.variant is TrendlineVariant.TOUCH3_ENGULFING else 0.55
        reason = (
            f"{self.variant.value}: 3rd-touch rejection on a "
            f"{line.line_type.value} trendline near {expected:.5f} "
            f"(anchors at bars {line.anchor1_index}, {line.anchor2_index})."
        )
        return ModuleSignal(
            module=self.name,
            bias=bias,
            confidence=confidence,
            reason=reason,
            bar_time=last.open_time,
        )

    def evaluate(self, bars: list[OHLCBar]) -> ModuleSignal:
        if len(bars) < 2 * self.swing_strength + 5:
            return ModuleSignal(
                module=self.name,
                bias=Bias.NEUTRAL,
                confidence=0.0,
                reason="Not enough closed bars to build a trendline.",
                bar_time=bars[-1].open_time if bars else datetime.now(timezone.utc),
            )

        avg_range = sum(b.high - b.low for b in bars) / len(bars)
        lines = self._build_trendlines(bars)
        for line in lines:
            signal = self._third_touch_signal(bars, line, avg_range)
            if signal is not None:
                return signal

        return ModuleSignal(
            module=self.name,
            bias=Bias.NEUTRAL,
            confidence=0.0,
            reason="No valid 3rd-touch trendline signal on the latest closed bar.",
            bar_time=bars[-1].open_time,
        )
