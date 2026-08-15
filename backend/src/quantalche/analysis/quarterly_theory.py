from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time, timezone
from zoneinfo import ZoneInfo

from .base import AnalysisModule
from .models import Bias, ModuleSignal
from ..ingestion.models import OHLCBar

_NY = ZoneInfo("America/New_York")


@dataclass(frozen=True)
class _SessionQuarter:
    session: str
    quarter: str
    start: time
    end: time
    high_quality: bool


# NY-local session/quarter table (doc 02 S13). Phase0 S7 item 7 flagged
# that the corpus never reconciles this GMT+7 (docs 01/09/13) against NY/
# UTC-4 (doc 02) -- doc 02's table is adopted as canonical here since it's
# the most citation-conscious, fully-specified version, and is paired with
# doc 02's own True Open entry rule (below), which the GMT+7 tables don't
# carry. An explicit Phase-N judgment call, documented as such.
#
# Real IANA tz (America/New_York) is used rather than a fixed UTC-4
# offset -- doc 02 states "UTC-4" but that's Eastern *Daylight* Time only;
# a fixed offset would silently misalign every session boundary by an
# hour for half the year. Using the real timezone is a correction, not a
# deviation, from what "NY time" is actually supposed to mean.
#
# London Q4 (05:30-07:00) and NYAM Q1 (06:00-07:30) overlap in the source
# table itself -- resolved by taking the first match in this list order.
# 18:00-19:00 NY is not covered by any session in the source table either;
# left unclassified rather than inventing a session to fill the gap.
_TABLE: list[_SessionQuarter] = [
    _SessionQuarter("Asia", "Q1", time(19, 0), time(20, 30), False),
    _SessionQuarter("Asia", "Q2", time(20, 30), time(22, 0), False),
    _SessionQuarter("Asia", "Q3", time(22, 0), time(23, 30), False),
    _SessionQuarter("London", "Q1", time(1, 0), time(2, 30), True),
    _SessionQuarter("London", "Q2", time(2, 30), time(4, 0), True),
    _SessionQuarter("London", "Q3", time(4, 0), time(5, 30), True),
    _SessionQuarter("London", "Q4", time(5, 30), time(7, 0), True),
    _SessionQuarter("NYAM", "Q1", time(6, 0), time(7, 30), True),
    _SessionQuarter("NYAM", "Q2", time(7, 30), time(9, 0), True),
    _SessionQuarter("NYAM", "Q3", time(9, 0), time(10, 30), True),
    _SessionQuarter("NYAM", "Q4", time(10, 30), time(12, 0), True),
    _SessionQuarter("NYPM", "Q1", time(12, 0), time(13, 30), True),
    _SessionQuarter("NYPM", "Q2", time(13, 30), time(15, 0), True),
    _SessionQuarter("NYPM", "Q3", time(15, 0), time(16, 30), True),
    _SessionQuarter("NYPM", "Q4", time(16, 30), time(18, 0), True),
]


def _classify(ny_time: time) -> tuple[str, str, bool]:
    for entry in _TABLE:
        if entry.start <= ny_time < entry.end:
            return entry.session, entry.quarter, entry.high_quality
    if ny_time >= time(23, 30) or ny_time < time(1, 0):
        return "Asia", "Q4", False
    return "Unclassified", "-", False


def _true_open_price(bars: list[OHLCBar]) -> float | None:
    last_ny = bars[-1].open_time.astimezone(_NY)
    midnight_ny = last_ny.replace(hour=0, minute=0, second=0, microsecond=0)
    candidates = [b for b in bars if b.open_time.astimezone(_NY) >= midnight_ny]
    return candidates[0].open if candidates else None


class QuarterlyTheoryModule(AnalysisModule):
    """Layer 2 module: Quarterly Theory session/True-Open bias.

    Rule source (docs/phase0-knowledge-extraction.md S2.4, S7 item 7; full
    citations in docs/rule-mapping.md): doc 02 S14, quoted directly:
    "Bullish Bias: Look for buys below the True Open. Bearish Bias: Look
    for sells above the True Open." Day True Open = "00:00" NY time (doc
    02 S14) -- implemented as the open price of the first bar at/after the
    most recent NY midnight.

    Unlike every other Layer 2 module, this one is time-based, not
    price-pattern-based -- it always has an opinion (price is always
    either above or below the True Open) rather than firing only on
    specific setups. Confidence, not direction, encodes the corpus's
    "London/NY sessions are higher-quality than Asia" framing (widespread
    across docs 01, 02, 08/11, 09, 13, 17, 19, 21, but stated qualitatively
    everywhere, never as a hard gate) -- implemented as a soft confidence
    scale (London/NYAM/NYPM vs. Asia/unclassified), not a hard session
    filter that would silently zero out Asia-session signals the source
    material never says to discard entirely.

    Only the Daily True Open + Bullish/Bearish Bias rule is implemented.
    The nested Year/Month/Week/90-min True Opens and the "Quarter
    Principle" narrative (doc 02: "Q1 sets the tone for Q2-Q4... if Q1
    expands, Q2 often consolidates") are NOT implemented -- the Quarter
    Principle requires classifying a quarter's price action as "expansion"
    vs. "consolidation," a judgment call the source material never defines
    numerically. Implementing it would mean inventing that definition, not
    extracting one.
    """

    name = "quarterly_theory"

    def evaluate(self, bars: list[OHLCBar]) -> ModuleSignal:
        if not bars:
            return ModuleSignal(
                module=self.name,
                bias=Bias.NEUTRAL,
                confidence=0.0,
                reason="No bars.",
                bar_time=datetime.now(timezone.utc),
            )

        last = bars[-1]
        true_open = _true_open_price(bars)
        if true_open is None:
            return ModuleSignal(
                module=self.name,
                bias=Bias.NEUTRAL,
                confidence=0.0,
                reason="Could not determine the daily True Open from the supplied bars.",
                bar_time=last.open_time,
            )

        ny_time_of_day = last.open_time.astimezone(_NY).time()
        session, quarter, high_quality = _classify(ny_time_of_day)

        if last.close < true_open:
            bias = Bias.BULLISH
            relation = "below"
        elif last.close > true_open:
            bias = Bias.BEARISH
            relation = "above"
        else:
            bias = Bias.NEUTRAL
            relation = "at"

        confidence = 0.0
        if bias is not Bias.NEUTRAL:
            confidence = 0.5 if high_quality else 0.25

        quality_label = "higher" if high_quality else "lower"
        reason = (
            f"{session} {quarter}: price {relation} the daily True Open "
            f"({true_open:.5f}); {quality_label}-quality session."
        )
        return ModuleSignal(
            module=self.name,
            bias=bias,
            confidence=confidence,
            reason=reason,
            bar_time=last.open_time,
            level=true_open,
        )
