"""Phase 3 validation script for the Trendline Confluence module.

Runs both configurable variants (TOUCH3_SIMPLE and TOUCH3_ENGULFING) over
the same bar history, so their outputs can be compared -- per the Phase 3
validation step in docs/architecture.md.
"""

from __future__ import annotations

from quantalche.analysis.trendline_confluence import (
    TrendlineConfluenceModule,
    TrendlineVariant,
)
from quantalche.config import TWELVE_DATA_API_KEY
from quantalche.ingestion.binance_client import BinanceClient
from quantalche.ingestion.models import OHLCBar, Timeframe
from quantalche.ingestion.twelvedata_client import TwelveDataClient


def _count_signals(bars: list[OHLCBar], variant: TrendlineVariant) -> int:
    """Walk the bar history forward, calling evaluate() on growing slices
    (non-repainting replay), and count how many bars produced a non-neutral
    signal -- gives a sense of overall signal frequency, not just the
    final bar's read.
    """
    module = TrendlineConfluenceModule(variant=variant)
    count = 0
    min_len = 2 * module.swing_strength + 5
    for i in range(min_len, len(bars) + 1):
        signal = module.evaluate(bars[:i])
        if signal.bias.value != "neutral":
            count += 1
    return count


def _run(label: str, bars: list[OHLCBar]) -> None:
    print(f"\n--- {label}: {len(bars)} bars ---")
    for variant in (TrendlineVariant.TOUCH3_SIMPLE, TrendlineVariant.TOUCH3_ENGULFING):
        module = TrendlineConfluenceModule(variant=variant)
        lines = module._build_trendlines(bars)  # noqa: SLF001 -- validation script
        signal_count = _count_signals(bars, variant)
        final_signal = module.evaluate(bars)
        print(
            f"  {variant.value:<18} {len(lines):>3} candidate lines, "
            f"{signal_count:>3} non-neutral signals over history  |  "
            f"current: bias={final_signal.bias.value} conf={final_signal.confidence:.2f}"
        )


def main() -> None:
    binance = BinanceClient()
    try:
        for tf in (Timeframe.H1, Timeframe.H4, Timeframe.D1):
            _run(
                f"Binance BTCUSDT {tf.value}",
                binance.get_ohlc("BTCUSDT", tf, limit=300),
            )
    finally:
        binance.close()

    if TWELVE_DATA_API_KEY:
        twelvedata = TwelveDataClient(api_key=TWELVE_DATA_API_KEY)
        try:
            for tf in (Timeframe.H1, Timeframe.H4, Timeframe.D1):
                _run(
                    f"Twelve Data EUR/USD {tf.value}",
                    twelvedata.get_ohlc("EUR/USD", tf, limit=300),
                )
        finally:
            twelvedata.close()


if __name__ == "__main__":
    main()
