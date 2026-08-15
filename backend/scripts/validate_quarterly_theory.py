"""Validation script for the Quarterly Theory module.

Unlike the price-pattern modules, this one is time-based -- prints the
session/quarter classification and True-Open bias across a run of bars so
the session-boundary logic (including the NY-timezone/DST handling) can be
checked by eye against real clock times.
"""

from __future__ import annotations

from quantalche.analysis.quarterly_theory import QuarterlyTheoryModule
from quantalche.config import TWELVE_DATA_API_KEY
from quantalche.ingestion.binance_client import BinanceClient
from quantalche.ingestion.models import OHLCBar, Timeframe
from quantalche.ingestion.twelvedata_client import TwelveDataClient


def _run(label: str, bars: list[OHLCBar]) -> None:
    module = QuarterlyTheoryModule()
    print(f"\n--- {label}: {len(bars)} bars ---")
    for i in range(1, len(bars) + 1):
        s = module.evaluate(bars[:i])
        if i > len(bars) - 8:
            print(
                f"  {bars[i-1].open_time.isoformat()}  close={bars[i-1].close:.5f}  "
                f"bias={s.bias.value:<8} conf={s.confidence:.2f}  {s.reason}"
            )


def main() -> None:
    binance = BinanceClient()
    try:
        _run("Binance BTCUSDT 1h", binance.get_ohlc("BTCUSDT", Timeframe.H1, limit=60))
    finally:
        binance.close()

    if TWELVE_DATA_API_KEY:
        twelvedata = TwelveDataClient(api_key=TWELVE_DATA_API_KEY)
        try:
            _run(
                "Twelve Data EUR/USD 1h",
                twelvedata.get_ohlc("EUR/USD", Timeframe.H1, limit=60),
            )
        finally:
            twelvedata.close()


if __name__ == "__main__":
    main()
