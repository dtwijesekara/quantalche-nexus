"""Validation script for the CRT (Candle Range Theory) module.

Backtest-style replay across the full bar history, same discipline as the
other module validation scripts -- per docs/architecture.md's per-module
validation step.
"""

from __future__ import annotations

from quantalche.analysis.crt_pattern import CRTModule
from quantalche.config import TWELVE_DATA_API_KEY
from quantalche.ingestion.binance_client import BinanceClient
from quantalche.ingestion.models import OHLCBar, Timeframe
from quantalche.ingestion.twelvedata_client import TwelveDataClient


def _run(label: str, bars: list[OHLCBar]) -> None:
    module = CRTModule()
    signal_count = 0
    bullish = bearish = 0
    for i in range(3, len(bars) + 1):
        s = module.evaluate(bars[:i])
        if s.bias.value != "neutral":
            signal_count += 1
            if s.bias.value == "bullish":
                bullish += 1
            else:
                bearish += 1

    final = module.evaluate(bars)
    print(
        f"{label:<28} {len(bars):>4} bars  {signal_count:>3} non-neutral "
        f"({bullish} bull / {bearish} bear) over {len(bars) - 2} windows  |  "
        f"current: bias={final.bias.value} conf={final.confidence:.2f}  {final.reason}"
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
