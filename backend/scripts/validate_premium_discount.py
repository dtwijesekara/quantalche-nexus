"""Validation script for the Premium/Discount dealing-range module.

Two checks, same methodology already applied to QuarterlyTheoryModule
(see pipeline.py's default_pipeline docstring and rule-mapping.md):

1. Standalone sanity -- print the bias/zone/equilibrium across a run of
   bars so the dealing-range math can be eyeballed against real price
   action.
2. The decisive check: since this module is always non-neutral (like
   QuarterlyTheoryModule), does adding it to default_pipeline() under
   HARD_GATE collapse signal frequency the same way? Same instrument
   (BTCUSDT 1h) and window (1000 bars) QuarterlyTheoryModule was tested
   with, for a direct comparison.
"""

from __future__ import annotations

from quantalche.aggregation.models import AggregationMode
from quantalche.aggregation.pipeline import default_pipeline
from quantalche.analysis.premium_discount import PremiumDiscountModule
from quantalche.backtest.backtester import Backtester
from quantalche.config import TWELVE_DATA_API_KEY
from quantalche.execution.confirmation import ConfirmationLayer
from quantalche.ingestion.binance_client import BinanceClient
from quantalche.ingestion.models import OHLCBar, Timeframe
from quantalche.ingestion.twelvedata_client import TwelveDataClient


def _run_standalone(label: str, bars: list[OHLCBar]) -> None:
    module = PremiumDiscountModule()
    print(f"\n--- {label}: {len(bars)} bars ---")
    for i in range(1, len(bars) + 1):
        s = module.evaluate(bars[:i])
        if i > len(bars) - 8:
            print(
                f"  {bars[i-1].open_time.isoformat()}  close={bars[i-1].close:.5f}  "
                f"bias={s.bias.value:<8} conf={s.confidence:.2f}  {s.reason}"
            )


def _compare_pipeline(label: str, bars: list[OHLCBar]) -> None:
    print(f"\n=== HARD_GATE signal-frequency comparison: {label} ({len(bars)} bars) ===")

    baseline = default_pipeline(AggregationMode.HARD_GATE)
    baseline_report = Backtester(baseline, ConfirmationLayer()).run(
        bars, label=f"{label} baseline", segments=1
    )
    print(
        f"  baseline (6 modules):            "
        f"signals={baseline_report.overall.total_signals} "
        f"resolved={baseline_report.overall.resolved} "
        f"win_rate={baseline_report.overall.win_rate:.2%} "
        f"expectancy={baseline_report.overall.expectancy_r:+.2f}R"
    )

    with_pd = default_pipeline(AggregationMode.HARD_GATE)
    with_pd.modules.append(PremiumDiscountModule())
    with_pd_report = Backtester(with_pd, ConfirmationLayer()).run(
        bars, label=f"{label} +premium_discount", segments=1
    )
    o2 = with_pd_report.overall
    wr = f"{o2.win_rate:.2%}" if o2.win_rate is not None else "n/a"
    exp = f"{o2.expectancy_r:+.2f}R" if o2.expectancy_r is not None else "n/a"
    print(
        f"  +premium_discount (7 modules):   "
        f"signals={o2.total_signals} resolved={o2.resolved} win_rate={wr} expectancy={exp}"
    )

    for m in with_pd_report.overall.module_accuracy:
        if m.module == "premium_discount":
            acc = f"{m.accuracy:.1%}" if m.accuracy is not None else "n/a"
            print(f"  premium_discount standalone accuracy: {m.scored_signals} scored, {acc}")


def main() -> None:
    binance = BinanceClient()
    try:
        bars = binance.get_ohlc("BTCUSDT", Timeframe.H1, limit=1000)
        _run_standalone("Binance BTCUSDT 1h", bars)
        _compare_pipeline("Binance BTCUSDT 1h", bars)
    finally:
        binance.close()

    if TWELVE_DATA_API_KEY:
        twelvedata = TwelveDataClient(api_key=TWELVE_DATA_API_KEY)
        try:
            bars = twelvedata.get_ohlc("EUR/USD", Timeframe.H1, limit=1000)
            _run_standalone("Twelve Data EUR/USD 1h", bars)
            _compare_pipeline("Twelve Data EUR/USD 1h", bars)
        finally:
            twelvedata.close()


if __name__ == "__main__":
    main()
