"""Phase 3 validation script for the QM (Quasimodo) pattern module.

Backtest-style replay across the full bar history (not just the final bar),
same discipline as validate_trendline_confluence.py -- per the Phase 3
validation step in docs/architecture.md.
"""

from __future__ import annotations

from quantalche.analysis.qm_pattern import QMModule
from quantalche.config import TWELVE_DATA_API_KEY
from quantalche.ingestion.binance_client import BinanceClient
from quantalche.ingestion.models import OHLCBar, Timeframe
from quantalche.ingestion.twelvedata_client import TwelveDataClient


def _run(label: str, bars: list[OHLCBar]) -> None:
    module = QMModule()
    patterns = module._find_patterns(bars)  # noqa: SLF001 -- validation script

    min_len = 4 * module.swing_strength + 8
    signal_count = 0
    for i in range(min_len, len(bars) + 1):
        if module.evaluate(bars[:i]).bias.value != "neutral":
            signal_count += 1

    final = module.evaluate(bars)
    print(
        f"{label:<28} {len(bars):>4} bars  {len(patterns):>3} QM patterns  "
        f"{signal_count:>3} non-neutral signals over history  |  "
        f"current: bias={final.bias.value} conf={final.confidence:.2f}"
    )
    for p in patterns[-3:]:
        print(
            f"    {p.direction.value:<8} QML={p.qm_level:.5f}  "
            f"confirmed {p.confirmed_at.isoformat()}"
        )


def main() -> None:
    binance = BinanceClient()
    try:
        for tf in (Timeframe.H1, Timeframe.H4, Timeframe.D1):
            _run(f"Binance BTCUSDT {tf.value}", binance.get_ohlc("BTCUSDT", tf, limit=300))
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
