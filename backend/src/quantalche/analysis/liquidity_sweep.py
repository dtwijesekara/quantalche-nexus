from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel

from ..ingestion.models import OHLCBar
from .base import AnalysisModule
from .models import Bias, ModuleSignal
from .swings import SwingKind, find_swings


class LiquidityLevelType(str, Enum):
    BSL = "bsl"  # buy-side liquidity: above swing highs, sell-stops rest here
    SSL = "ssl"  # sell-side liquidity: below swing lows, buy-stops rest here


class LiquidityLevel(BaseModel):
    level_type: LiquidityLevelType
    price: float
    formed_at: datetime
    swept: bool = False
    swept_at: datetime | None = None
    cluster_size: int = 1
    """>=2 means this level is part of an EQH/EQL cluster (docs 08 S55,
    13 SS92-97) -- several swing extremes close enough together to read as
    "equal," implying more resting stops than a single isolated swing.
    """


class SweepEvent(BaseModel):
    level_type: LiquidityLevelType
    level_price: float
    at: datetime
    wick_extreme: float
    close_price: float
    cluster_size: int = 1


class LiquiditySweepModule(AnalysisModule):
    """Layer 2 module: liquidity pools (BSL/SSL) at swing highs/lows, and
    the sweep event that precedes a reversal.

    Rule source (docs/phase0-knowledge-extraction.md S2.2; full citations
    in docs/rule-mapping.md): the single most-corroborated mechanic in the
    entire 22-document corpus -- every document that discusses reversals
    independently asserts some version of "stops get run before the real
    move." Naming is wildly inconsistent across the corpus (BSL/SSL,
    inducement, IDM, "Trap," "TS"/"Target Sweep"/"Turtle Soup") but the
    mechanic itself is never contradicted anywhere:
      - BSL = liquidity above swing highs, where retail sell-stops rest
        (doc 08 S53).
      - SSL = liquidity below swing lows, mirror definition (doc 08 S53).
      - Sweep = a bar's wick clears the level but its *body* closes back on
        the origin side -- the level's stops get taken without the level
        being genuinely broken. This is what distinguishes a sweep from an
        actual structure break (see market_structure.py's BOS/CHoCH, which
        requires a full-body close *through* the level; a sweep is
        specifically the case where that does NOT happen).

    Swing-point formation is shared with market_structure.py via
    swings.py -- same non-sourced fractal convention, same non-repainting
    confirmation lag. See that module's docstring for the full rationale.

    ``swing_strength`` default (5, not market_structure.py's 2) is a
    second addition found by live validation, not a source-stated value.
    At strength=2, swing highs/lows are so minor and closely-spaced that
    46 of 299 BTCUSDT 1h bars (15.4%) registered a sweep -- roughly one
    every six bars, which reads as routine price wobble, not the somewhat
    decisive "smart money grabbed liquidity" event the source material
    describes. The swept/detected-level ratio stayed roughly constant
    (~70-75%) across every strength tested (2/3/5/8/12) -- confirming this
    is a level-granularity choice, not a bug in the sweep-detection logic
    itself. Strength=5 (9.4% sweep rate on the same data) was chosen as a
    middle ground. The corpus names both minor liquidity (any swing high/
    low) and major liquidity (PWH/PWL/PDH/PDL, EQH/EQL clusters, docs 08
    S55-56, 13 SS92-97) without giving a formula that separates them --
    ``swing_strength`` is this module's stand-in lever for that distinction
    until EQH/EQL clustering is built.

    EQH/EQL clustering: grouping nearby same-kind swing extremes into one
    stronger liquidity pool, per docs 08 S55 and 13 SS92-97 -- doc 08's
    "Smart Money playbook" narrative singles out equal-level sweeps as a
    stronger tell than an isolated swing sweep. Implemented as a greedy,
    price-sorted chain clustering: consecutive same-kind swings (sorted by
    price) within ``eq_tolerance_ratio`` x average bar range of their
    neighbor join one cluster. ``eq_tolerance_ratio`` is NOT source-stated
    -- "how close counts as equal" is never quantified in the corpus --
    same materiality-filter pattern as SNR Zone's min_gap_ratio, tuned the
    same way: checked empirically against live data rather than guessed
    (see rule-mapping.md for the actual numbers). A swept cluster
    (cluster_size >= 2) gets a real confidence bump over an isolated sweep
    in evaluate() below, not just a label.
    """

    name = "liquidity_sweep"

    def __init__(self, swing_strength: int = 5, eq_tolerance_ratio: float = 0.05) -> None:
        self.swing_strength = swing_strength
        self.eq_tolerance_ratio = eq_tolerance_ratio

    def _cluster_sizes(self, swings, avg_range: float) -> dict[int, int]:
        tolerance = avg_range * self.eq_tolerance_ratio
        sizes: dict[int, int] = {}
        for kind in (SwingKind.HIGH, SwingKind.LOW):
            same_kind = sorted(
                (s for s in swings if s.kind is kind), key=lambda s: s.price
            )
            cluster: list = []
            for sp in same_kind:
                if cluster and sp.price - cluster[-1].price > tolerance:
                    for member in cluster:
                        sizes[member.index] = len(cluster)
                    cluster = []
                cluster.append(sp)
            for member in cluster:
                sizes[member.index] = len(cluster)
        return sizes

    def detect_levels_and_sweeps(
        self, bars: list[OHLCBar]
    ) -> tuple[list[LiquidityLevel], list[SweepEvent]]:
        swings = find_swings(bars, self.swing_strength)
        avg_range = sum(b.high - b.low for b in bars) / len(bars) if bars else 0.0
        cluster_sizes = self._cluster_sizes(swings, avg_range)
        levels: list[LiquidityLevel] = []
        sweeps: list[SweepEvent] = []

        # A swing at index j is confirmed (known) at index j + swing_strength,
        # same non-repainting lag as market_structure.py.
        pending: dict[int, list] = {}
        for sp in swings:
            pending.setdefault(sp.index, []).append(sp)

        active: list[LiquidityLevel] = []
        for i, bar in enumerate(bars):
            confirmed_idx = i - self.swing_strength
            for sp in pending.get(confirmed_idx, []):
                level = LiquidityLevel(
                    level_type=(
                        LiquidityLevelType.BSL
                        if sp.kind is SwingKind.HIGH
                        else LiquidityLevelType.SSL
                    ),
                    price=sp.price,
                    formed_at=sp.at,
                    cluster_size=cluster_sizes.get(sp.index, 1),
                )
                levels.append(level)
                active.append(level)

            for level in active:
                if level.swept or level.formed_at >= bar.open_time:
                    continue
                if level.level_type is LiquidityLevelType.BSL:
                    wicked_through = bar.high > level.price
                    closed_back = bar.close <= level.price
                else:
                    wicked_through = bar.low < level.price
                    closed_back = bar.close >= level.price

                if wicked_through and closed_back:
                    level.swept = True
                    level.swept_at = bar.open_time
                    sweeps.append(
                        SweepEvent(
                            level_type=level.level_type,
                            level_price=level.price,
                            at=bar.open_time,
                            wick_extreme=(
                                bar.high
                                if level.level_type is LiquidityLevelType.BSL
                                else bar.low
                            ),
                            close_price=bar.close,
                            cluster_size=level.cluster_size,
                        )
                    )

            active = [lvl for lvl in active if not lvl.swept]

        return levels, sweeps

    def evaluate(self, bars: list[OHLCBar]) -> ModuleSignal:
        min_bars = 2 * self.swing_strength + 3
        if len(bars) < min_bars:
            return ModuleSignal(
                module=self.name,
                bias=Bias.NEUTRAL,
                confidence=0.0,
                reason="Not enough closed bars to detect any liquidity level.",
                bar_time=bars[-1].open_time if bars else datetime.now(timezone.utc),
            )

        _, sweeps = self.detect_levels_and_sweeps(bars)
        last = bars[-1]

        fresh_sweeps = [s for s in sweeps if s.at == last.open_time]
        if not fresh_sweeps:
            return ModuleSignal(
                module=self.name,
                bias=Bias.NEUTRAL,
                confidence=0.0,
                reason="No liquidity sweep on the latest closed bar.",
                bar_time=last.open_time,
            )

        # A sweep is a contrarian signal: BSL swept (stops above a high
        # taken, price closed back below) => bearish; SSL swept => bullish.
        sweep = fresh_sweeps[-1]
        is_eq_cluster = sweep.cluster_size >= 2
        level_label = (
            f"{'EQH' if sweep.level_type is LiquidityLevelType.BSL else 'EQL'} "
            f"({sweep.cluster_size}x)"
            if is_eq_cluster
            else sweep.level_type.value.upper()
        )
        if sweep.level_type is LiquidityLevelType.BSL:
            bias = Bias.BEARISH
            reason = (
                f"{level_label} swept at {sweep.level_price:.5f} (wick to "
                f"{sweep.wick_extreme:.5f}), closed back below at "
                f"{sweep.close_price:.5f} -- bearish."
            )
        else:
            bias = Bias.BULLISH
            reason = (
                f"{level_label} swept at {sweep.level_price:.5f} (wick to "
                f"{sweep.wick_extreme:.5f}), closed back above at "
                f"{sweep.close_price:.5f} -- bullish."
            )

        return ModuleSignal(
            module=self.name,
            bias=bias,
            confidence=0.8 if is_eq_cluster else 0.6,
            reason=reason,
            bar_time=last.open_time,
            level=sweep.level_price,
        )
