"""Phase 6 validation script -- the backtest/walk-forward framework.

Per the Phase 6 validation step in docs/architecture.md: "manually
cross-check a handful of trades for hindsight leakage." Pulls the largest
practical history from each source, runs the full backtest with walk-
forward segmentation, then spot-checks a few resolved trades by hand.
"""

from __future__ import annotations

from quantalche.aggregation.models import AggregationMode
from quantalche.aggregation.pipeline import default_pipeline
from quantalche.backtest.backtester import Backtester
from quantalche.backtest.models import BacktestReport
from quantalche.config import TWELVE_DATA_API_KEY
from quantalche.execution.confirmation import ConfirmationLayer
from quantalche.ingestion.binance_client import BinanceClient
from quantalche.ingestion.models import OHLCBar, Timeframe
from quantalche.ingestion.twelvedata_client import TwelveDataClient


def _print_report(report: BacktestReport) -> None:
    print(f"\n=== {report.label} ===")
    o = report.overall
    print(
        f"  OVERALL [{o.start_time.date() if o.start_time else '?'} -> "
        f"{o.end_time.date() if o.end_time else '?'}]  {o.bar_count} bars"
    )
    print(
        f"    signals={o.total_signals} filled={o.filled} resolved={o.resolved} "
        f"wins={o.wins} losses={o.losses} "
        f"win_rate={o.win_rate:.2%} expectancy={o.expectancy_r:+.2f}R"
        if o.resolved
        else f"    signals={o.total_signals} filled={o.filled} resolved=0 (no completed trades)"
    )
    print("    Per-module directional accuracy (not trade-based, see Backtester docstring):")
    for m in o.module_accuracy:
        acc = f"{m.accuracy:.1%}" if m.accuracy is not None else "n/a"
        print(f"      {m.module:<22} {m.scored_signals:>3} scored  accuracy={acc}")

    for seg in report.walk_forward_segments:
        if seg.resolved:
            print(
                f"  {seg.label}: [{seg.start_time.date()} -> {seg.end_time.date()}] "
                f"resolved={seg.resolved} win_rate={seg.win_rate:.2%} "
                f"expectancy={seg.expectancy_r:+.2f}R"
            )
        else:
            print(
                f"  {seg.label}: [{seg.start_time.date()} -> {seg.end_time.date()}] "
                f"resolved=0 (no completed trades in this segment)"
            )


def _spot_check_leakage(report: BacktestReport, bars: list[OHLCBar]) -> None:
    print("\n  Hindsight-leakage spot-check (first 3 resolved trades):")
    resolved = [t for t in report.overall.trades if t.outcome in ("tp_hit", "stopped_out")]
    by_time = {b.open_time: b for b in bars}
    for t in resolved[:3]:
        signal_bar = by_time[t.signal_time]
        exit_bar = by_time[t.exit_time] if t.exit_time else None
        ok = t.exit_time is not None and t.exit_time > t.signal_time
        print(
            f"    {t.direction.value:<5} signal@{t.signal_time.isoformat()} "
            f"(close={signal_bar.close:.5f}) -> exit@{t.exit_time.isoformat() if t.exit_time else '?'} "
            f"({t.outcome})  chronological_order={'OK' if ok else 'VIOLATION'}"
        )


def main() -> None:
    binance = BinanceClient()
    try:
        bars = binance.get_ohlc("BTCUSDT", Timeframe.H1, limit=1000)
        pipeline = default_pipeline(AggregationMode.HARD_GATE)
        backtester = Backtester(pipeline, ConfirmationLayer())
        report = backtester.run(bars, label="Binance BTCUSDT 1h [hard_gate]", segments=3)
        _print_report(report)
        _spot_check_leakage(report, bars)
    finally:
        binance.close()

    if TWELVE_DATA_API_KEY:
        twelvedata = TwelveDataClient(api_key=TWELVE_DATA_API_KEY)
        try:
            bars = twelvedata.get_ohlc("EUR/USD", Timeframe.H1, limit=1000)
            pipeline = default_pipeline(AggregationMode.HARD_GATE)
            backtester = Backtester(pipeline, ConfirmationLayer())
            report = backtester.run(bars, label="Twelve Data EUR/USD 1h [hard_gate]", segments=3)
            _print_report(report)
            _spot_check_leakage(report, bars)
        finally:
            twelvedata.close()


if __name__ == "__main__":
    main()
