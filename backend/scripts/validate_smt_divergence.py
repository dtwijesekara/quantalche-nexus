"""Validation script for the SMT/SSMT inter-market divergence module.

Unlike every other module's validation script, this one fetches TWO
correlated instruments and checks the divergence logic between them --
per docs/architecture.md's per-module validation step, adapted for the
one component that structurally needs two data series.
"""

from __future__ import annotations

from quantalche.aggregation.models import AggregationMode
from quantalche.aggregation.pipeline import default_pipeline, run_with_correlated
from quantalche.analysis.smt_divergence import SMTModule
from quantalche.config import TWELVE_DATA_API_KEY
from quantalche.ingestion.binance_client import BinanceClient
from quantalche.ingestion.models import OHLCBar, Timeframe
from quantalche.ingestion.twelvedata_client import TwelveDataClient


def _run(
    label: str,
    primary_symbol: str,
    primary_bars: list[OHLCBar],
    secondary_symbol: str,
    secondary_bars: list[OHLCBar],
) -> None:
    module = SMTModule()

    # Backtest-style replay to see how often this fires over history, not
    # just the final bar -- same discipline as the price-pattern modules.
    # Both bar lists are truncated in sync: passing the full, un-truncated
    # secondary series at every step would leak future correlated-pair
    # data the primary side wouldn't have -- a look-ahead bug caught while
    # writing this validation script, not in SMTModule itself.
    signal_count = 0
    min_len = 2 * module.swing_strength + 3
    n = min(len(primary_bars), len(secondary_bars))
    for i in range(min_len, n + 1):
        s = module.evaluate(primary_bars[:i], secondary_bars[:i], secondary_symbol)
        if s.bias.value != "neutral":
            signal_count += 1

    final = module.evaluate(primary_bars, secondary_bars, secondary_symbol)
    print(
        f"\n--- {label}: {primary_symbol} vs {secondary_symbol}, "
        f"{len(primary_bars)}/{len(secondary_bars)} bars ---"
    )
    print(f"  {signal_count} non-neutral over {len(primary_bars) - min_len + 1} windows")
    print(f"  current: bias={final.bias.value} conf={final.confidence:.2f}  {final.reason}")

    # Full pipeline integration check.
    pipeline = default_pipeline(AggregationMode.HARD_GATE)
    aggregated = run_with_correlated(
        pipeline, primary_bars, module, secondary_bars, secondary_symbol
    )
    smt_signal = next(s for s in aggregated.module_signals if s.module == "smt_divergence")
    print(
        f"  pipeline integration: {len(aggregated.module_signals)} module signals "
        f"(smt_divergence present: {smt_signal.bias.value}), "
        f"combined={aggregated.bias.value}"
    )


def main() -> None:
    binance = BinanceClient()
    try:
        btc = binance.get_ohlc("BTCUSDT", Timeframe.H1, limit=999)
        eth = binance.get_ohlc("ETHUSDT", Timeframe.H1, limit=999)
        _run("Binance", "BTCUSDT", btc, "ETHUSDT", eth)
    finally:
        binance.close()

    if TWELVE_DATA_API_KEY:
        twelvedata = TwelveDataClient(api_key=TWELVE_DATA_API_KEY)
        try:
            xau = twelvedata.get_ohlc("XAU/USD", Timeframe.H1, limit=999)
            try:
                xag = twelvedata.get_ohlc("XAG/USD", Timeframe.H1, limit=999)
            except Exception as exc:  # noqa: BLE001 -- validation script, report and continue
                print(f"\nXAG/USD unavailable on this Twelve Data plan/symbol: {exc}")
                xag = None
            if xag:
                _run("Twelve Data", "XAU/USD", xau, "XAG/USD", xag)
        finally:
            twelvedata.close()


if __name__ == "__main__":
    main()
