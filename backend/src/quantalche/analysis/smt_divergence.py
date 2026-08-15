from __future__ import annotations

from datetime import datetime, timedelta, timezone

from ..ingestion.models import OHLCBar
from .models import Bias, ModuleSignal
from .swings import SwingKind, SwingPoint, find_swings


class SMTModule:
    """NOT a standard Layer 2 AnalysisModule -- SMT/SSMT is the one
    component in the whole corpus that structurally needs two instruments'
    data at once (docs/phase0-knowledge-extraction.md S2.4), which the
    single-bars-list AnalysisModule.evaluate(bars) contract (analysis/
    base.py) can't express. Deliberately kept outside that interface
    rather than forcing a square peg into it -- see
    aggregation/pipeline.py's run_with_correlated() for how it plugs into
    the pipeline as an explicit, opt-in second-instrument addition.

    Rule source (docs/phase0-knowledge-extraction.md S2.4; full citations
    in docs/rule-mapping.md): doc 02 SS6, 29-33. Named example pairs:
    BTC-ETH, EURUSD-DXY, XAU-XAG.
      - Bullish SMT: the primary instrument makes a new (lower) swing low
        while the correlated instrument's corresponding swing low does
        NOT make a new low -- "weakening sell pressure... potential
        reversal to the upside" (doc 02 S30).
      - Bearish SMT: mirror image at swing highs -- "fading buy
        pressure... precedes a distribution phase or bearish reversal."
      - SMT is explicitly framed as "a confirmatory tool, not a
        standalone signal" (doc 02 S29) -- one of the only places in the
        corpus where multiple independent documents agree a component
        should be a SOFT input, not a hard gate (Phase0 S2.4). Reflected
        here only as a moderate fixed confidence (0.5); enforcing
        "confirmatory only" as a combination rule is an aggregation-layer
        decision, not something this module can impose on its own output.

    Swing detection reuses swings.py, same non-sourced fractal convention
    as every other structural module (default strength=3, a middle ground
    between market_structure.py's 2 and liquidity_sweep.py's 5 -- SMT
    swings need to be significant enough to compare meaningfully across
    two different instruments, but this project has no live-traded pair
    with a stated "correct" strength to calibrate against the way
    liquidity_sweep.py's sweep rate was).

    ``max_time_gap`` (how close in time the two instruments' corresponding
    swings must land to be compared) is NOT source-stated -- the corpus
    never addresses swing alignment across two separate bar series.
    """

    name = "smt_divergence"

    def __init__(
        self,
        swing_strength: int = 3,
        max_time_gap: timedelta = timedelta(hours=12),
    ) -> None:
        self.swing_strength = swing_strength
        self.max_time_gap = max_time_gap

    def _last_two(
        self, bars: list[OHLCBar], kind: SwingKind
    ) -> tuple[SwingPoint, SwingPoint] | None:
        swings = [s for s in find_swings(bars, self.swing_strength) if s.kind is kind]
        if len(swings) < 2:
            return None
        return swings[-2], swings[-1]

    def evaluate(
        self,
        primary_bars: list[OHLCBar],
        secondary_bars: list[OHLCBar],
        secondary_symbol: str,
    ) -> ModuleSignal:
        min_bars = 2 * self.swing_strength + 3
        if len(primary_bars) < min_bars or len(secondary_bars) < min_bars:
            return ModuleSignal(
                module=self.name,
                bias=Bias.NEUTRAL,
                confidence=0.0,
                reason="Not enough bars in one or both instruments for SMT comparison.",
                bar_time=primary_bars[-1].open_time
                if primary_bars
                else datetime.now(timezone.utc),
            )

        last_bar_time = primary_bars[-1].open_time
        gap_seconds = self.max_time_gap.total_seconds()

        primary_lows = self._last_two(primary_bars, SwingKind.LOW)
        secondary_lows = self._last_two(secondary_bars, SwingKind.LOW)
        if primary_lows and secondary_lows:
            p_prev, p_last = primary_lows
            s_prev, s_last = secondary_lows
            if (
                abs((p_last.at - s_last.at).total_seconds()) <= gap_seconds
                and p_last.price < p_prev.price
                and s_last.price >= s_prev.price
            ):
                return ModuleSignal(
                    module=self.name,
                    bias=Bias.BULLISH,
                    confidence=0.5,
                    reason=(
                        f"Bullish SMT vs {secondary_symbol}: primary made a new low "
                        f"({p_last.price:.5f} < {p_prev.price:.5f}) but the correlated "
                        f"pair did not ({s_last.price:.5f} >= {s_prev.price:.5f})."
                    ),
                    bar_time=last_bar_time,
                    level=p_last.price,
                )

        primary_highs = self._last_two(primary_bars, SwingKind.HIGH)
        secondary_highs = self._last_two(secondary_bars, SwingKind.HIGH)
        if primary_highs and secondary_highs:
            p_prev, p_last = primary_highs
            s_prev, s_last = secondary_highs
            if (
                abs((p_last.at - s_last.at).total_seconds()) <= gap_seconds
                and p_last.price > p_prev.price
                and s_last.price <= s_prev.price
            ):
                return ModuleSignal(
                    module=self.name,
                    bias=Bias.BEARISH,
                    confidence=0.5,
                    reason=(
                        f"Bearish SMT vs {secondary_symbol}: primary made a new high "
                        f"({p_last.price:.5f} > {p_prev.price:.5f}) but the correlated "
                        f"pair did not ({s_last.price:.5f} <= {s_prev.price:.5f})."
                    ),
                    bar_time=last_bar_time,
                    level=p_last.price,
                )

        return ModuleSignal(
            module=self.name,
            bias=Bias.NEUTRAL,
            confidence=0.0,
            reason=f"No SMT divergence detected against {secondary_symbol} on the latest swings.",
            bar_time=last_bar_time,
        )
