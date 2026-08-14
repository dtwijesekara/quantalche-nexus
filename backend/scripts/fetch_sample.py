"""Manual spot-check script for Phase 1 validation.

Fetches a handful of recent closed bars from each configured source and
prints them so they can be compared by eye against a real chart (e.g.
TradingView) -- per the Phase 1 validation step in docs/architecture.md.
Not an automated test suite; that's not what this phase calls for.
"""

from __future__ import annotations

from quantalche.config import TWELVE_DATA_API_KEY
from quantalche.ingestion.binance_client import BinanceClient
from quantalche.ingestion.models import OHLCBar, Timeframe
from quantalche.ingestion.twelvedata_client import TwelveDataClient


def _print_bars(label: str, bars: list[OHLCBar]) -> None:
    print(f"\n--- {label} ({len(bars)} bars) ---")
    for bar in bars[-5:]:
        print(
            f"{bar.open_time.isoformat()}  "
            f"O:{bar.open:<12} H:{bar.high:<12} L:{bar.low:<12} C:{bar.close:<12} "
            f"V:{bar.volume}"
        )


def main() -> None:
    binance = BinanceClient()
    try:
        _print_bars(
            "Binance BTCUSDT 1h",
            binance.get_ohlc("BTCUSDT", Timeframe.H1, limit=20),
        )
    finally:
        binance.close()

    if TWELVE_DATA_API_KEY:
        twelvedata = TwelveDataClient(api_key=TWELVE_DATA_API_KEY)
        try:
            _print_bars(
                "Twelve Data EUR/USD 1h",
                twelvedata.get_ohlc("EUR/USD", Timeframe.H1, limit=20),
            )
        finally:
            twelvedata.close()
    else:
        print(
            "\nTWELVE_DATA_API_KEY not set -- skipping forex fetch. "
            "Add it to backend/.env (see backend/.env.example)."
        )


if __name__ == "__main__":
    main()
