"""Phase 3 validation script for the Market Structure module.

Prints every confirmed BOS/CHoCH event plus the module's current signal, so
the output can be checked by eye against a real chart -- per the Phase 3
validation step in docs/architecture.md ("same discipline, per module").
"""

from __future__ import annotations

from quantalche.analysis.market_structure import MarketStructureModule
from quantalche.config import TWELVE_DATA_API_KEY
from quantalche.ingestion.binance_client import BinanceClient
from quantalche.ingestion.models import OHLCBar, Timeframe
from quantalche.ingestion.twelvedata_client import TwelveDataClient


def _run(label: str, bars: list[OHLCBar]) -> None:
    module = MarketStructureModule()
    events, trend = module._structure_events(bars)  # noqa: SLF001 -- validation script

    print(f"\n--- {label}: {len(bars)} bars, {len(events)} structure events ---")
    for event in events[-10:]:
        print(
            f"  {event.event.value.upper():<6} {event.direction.value:<8} "
            f"at {event.at.isoformat()}  broke {event.broken_level:.5f}  "
            f"close {event.close_price:.5f}"
        )
    print(f"  Current trend: {trend.value}")

    signal = module.evaluate(bars)
    print(
        f"  CURRENT SIGNAL: bias={signal.bias.value} "
        f"confidence={signal.confidence:.2f}  {signal.reason}"
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
