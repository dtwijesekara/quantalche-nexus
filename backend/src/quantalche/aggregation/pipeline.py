from __future__ import annotations

from ..analysis.base import AnalysisModule
from ..analysis.crt_pattern import CRTModule
from ..analysis.liquidity_sweep import LiquiditySweepModule
from ..analysis.market_structure import MarketStructureModule
from ..analysis.qm_pattern import QMModule
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


def default_pipeline(mode: AggregationMode = AggregationMode.HARD_GATE) -> SignalPipeline:
    """The validated Layer 2 modules with their validated defaults.

    TrendlineConfluenceModule's TOUCH3_ENGULFING variant is not included
    here by default (only TOUCH3_SIMPLE is) -- both share the same module
    name, and per rule-mapping.md, TOUCH3_ENGULFING fires extremely rarely.
    Add a second TrendlineConfluenceModule(variant=TOUCH3_ENGULFING)
    instance to `modules` directly if you want both in the pipeline.
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
