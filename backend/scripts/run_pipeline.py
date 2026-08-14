"""Phase 4 validation script for the aggregation layer.

Shows the full "decision support, not certainty" output architecture.md
calls for: every module's individual read, alongside the combined signal
in both configurable modes -- never just a black-box final number. Then
replays both modes across the full bar history to see how often each
lands on bullish/bearish/neutral/conflict, per the Phase 4 validation step
("compare aggregated output against manual reasoning on real cases").
"""

from __future__ import annotations

from collections import Counter

from quantalche.aggregation.models import AggregationMode
from quantalche.aggregation.pipeline import default_pipeline
from quantalche.config import TWELVE_DATA_API_KEY
from quantalche.ingestion.binance_client import BinanceClient
from quantalche.ingestion.models import OHLCBar, Timeframe
from quantalche.ingestion.twelvedata_client import TwelveDataClient


def _snapshot(label: str, bars: list[OHLCBar]) -> None:
    print(f"\n=== {label}: current read ({len(bars)} bars) ===")

    hard = default_pipeline(AggregationMode.HARD_GATE)
    soft = default_pipeline(AggregationMode.SOFT_SCORE)

    hard_signal = hard.run(bars)
    soft_signal = soft.run(bars)

    print("  Per-module reads:")
    for sig in hard_signal.module_signals:
        print(f"    {sig.module:<22} {sig.bias.value:<8} conf={sig.confidence:.2f}  {sig.reason}")

    print(f"  HARD_GATE  -> {hard_signal.bias.value:<8} conf={hard_signal.confidence:.2f}  {hard_signal.reason}")
    print(f"  SOFT_SCORE -> {soft_signal.bias.value:<8} conf={soft_signal.confidence:.2f}  {soft_signal.reason}")


def _replay(label: str, bars: list[OHLCBar]) -> None:
    hard_counts: Counter[str] = Counter()
    soft_counts: Counter[str] = Counter()

    hard = default_pipeline(AggregationMode.HARD_GATE)
    soft = default_pipeline(AggregationMode.SOFT_SCORE)

    min_len = 20  # smallest window any module needs a sane read from
    for i in range(min_len, len(bars) + 1):
        window = bars[:i]
        hard_counts[hard.run(window).bias.value] += 1
        soft_counts[soft.run(window).bias.value] += 1

    total = len(bars) - min_len + 1
    print(f"\n=== {label}: distribution over {total} bars of replay ===")
    print(f"  HARD_GATE : {dict(hard_counts)}")
    print(f"  SOFT_SCORE: {dict(soft_counts)}")


def main() -> None:
    binance = BinanceClient()
    try:
        bars = binance.get_ohlc("BTCUSDT", Timeframe.H1, limit=300)
        _snapshot("Binance BTCUSDT 1h", bars)
        _replay("Binance BTCUSDT 1h", bars)
    finally:
        binance.close()

    if TWELVE_DATA_API_KEY:
        twelvedata = TwelveDataClient(api_key=TWELVE_DATA_API_KEY)
        try:
            bars = twelvedata.get_ohlc("EUR/USD", Timeframe.H1, limit=300)
            _snapshot("Twelve Data EUR/USD 1h", bars)
            _replay("Twelve Data EUR/USD 1h", bars)
        finally:
            twelvedata.close()


if __name__ == "__main__":
    main()
