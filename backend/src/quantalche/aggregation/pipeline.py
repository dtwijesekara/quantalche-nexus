from __future__ import annotations

from ..analysis.base import AnalysisModule
from ..analysis.crt_pattern import CRTModule
from ..analysis.liquidity_sweep import LiquiditySweepModule
from ..analysis.market_structure import MarketStructureModule
from ..analysis.qm_pattern import QMModule
from ..analysis.smt_divergence import SMTModule
from ..analysis.snr_zone import SNRZoneModule
from ..analysis.trendline_confluence import TrendlineConfluenceModule
from ..ingestion.models import OHLCBar
from .aggregator import Aggregator
from .models import AggregatedSignal, AggregationMode


class SignalPipeline:
    """Runs every configured Layer 2 module against the same bar history,
    then hands their signals to Layer 3 (Aggregator) for one combined
    decision. This is the object Layer 5/6 (confirmation, state machine)
    will eventually sit on top of.
    """

    def __init__(self, modules: list[AnalysisModule], aggregator: Aggregator) -> None:
        self.modules = modules
        self.aggregator = aggregator

    def run(self, bars: list[OHLCBar]) -> AggregatedSignal:
        signals = [module.evaluate(bars) for module in self.modules]
        return self.aggregator.combine(signals)


def run_with_correlated(
    pipeline: SignalPipeline,
    bars: list[OHLCBar],
    smt_module: SMTModule,
    correlated_bars: list[OHLCBar],
    correlated_symbol: str,
) -> AggregatedSignal:
    """Runs the standard single-symbol pipeline, then adds SMTModule's
    signal (which needs a second instrument's bars -- see smt_divergence.py
    for why it isn't a plain AnalysisModule) before aggregating.

    Deliberately a separate function rather than a SignalPipeline
    constructor option: SignalPipeline.run(bars) stays a clean,
    single-symbol, already-validated interface; this is an explicit,
    opt-in extension point for the one component that structurally can't
    fit that interface, not a change to it.
    """
    signals = [module.evaluate(bars) for module in pipeline.modules]
    signals.append(smt_module.evaluate(bars, correlated_bars, correlated_symbol))
    return pipeline.aggregator.combine(signals)


def default_pipeline(mode: AggregationMode = AggregationMode.HARD_GATE) -> SignalPipeline:
    """The validated Layer 2 modules with their validated defaults.

    TrendlineConfluenceModule's TOUCH3_ENGULFING variant is not included
    here by default (only TOUCH3_SIMPLE is) -- both share the same module
    name, and per rule-mapping.md, TOUCH3_ENGULFING fires extremely rarely.
    Add a second TrendlineConfluenceModule(variant=TOUCH3_ENGULFING)
    instance to `modules` directly if you want both in the pipeline.

    QuarterlyTheoryModule (analysis/quarterly_theory.py) is intentionally
    NOT included by default either, for a different and more consequential
    reason than TOUCH3_ENGULFING's rarity: unlike every other module here,
    it's *always* active (never neutral -- price is always above or below
    the daily True Open). Under HARD_GATE, an always-active module must
    unanimously agree with every other active module on every bar, which
    makes it a near-permanent filter rather than an occasional vote. Live
    backtest comparison (1000 bars, BTCUSDT 1h): adding it collapsed
    hard-gate signal count from 50 to 3 over the same window -- not
    because the module is weak (55.5% standalone directional accuracy,
    second only to liquidity_sweep's 58%), but because of how an always-on
    signal interacts with a unanimity gate specifically. Reported plainly
    rather than silently included or silently dropped: add
    QuarterlyTheoryModule() to `modules` directly if you want this
    trade-off (far fewer, more temporally-selective signals), same
    opt-in pattern as TOUCH3_ENGULFING above.
    """

    modules: list[AnalysisModule] = [
        SNRZoneModule(),
        MarketStructureModule(),
        LiquiditySweepModule(),
        TrendlineConfluenceModule(),
        QMModule(),
        CRTModule(),
    ]
    return SignalPipeline(modules=modules, aggregator=Aggregator(mode=mode))
