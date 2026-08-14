"""Phase 2 validation script for the SNR Zone module.

Prints every detected zone (with its fresh/unfresh/flip history) plus the
module's current signal, so the output can be checked by eye against a real
chart (e.g. TradingView) -- per the Phase 2 validation step in
docs/architecture.md ("screenshot/output review against source material").
"""

from __future__ import annotations

from quantalche.analysis.snr_zone import SNRZoneModule
from quantalche.config import TWELVE_DATA_API_KEY
from quantalche.ingestion.binance_client import BinanceClient
from quantalche.ingestion.models import OHLCBar, Timeframe
from quantalche.ingestion.twelvedata_client import TwelveDataClient


def _run(label: str, bars: list[OHLCBar]) -> None:
    module = SNRZoneModule()
    zones = module._detect_zones(bars)  # noqa: SLF001 -- validation script, intentional

    print(f"\n--- {label}: {len(bars)} bars, {len(zones)} zones detected ---")
    for zone in zones[-10:]:
        flips = sum(1 for e in zone.events if e.event.value == "flipped")
        print(
            f"  {zone.zone_type.value:<10} [{zone.bottom:.5f}, {zone.top:.5f}] "
            f"formed {zone.formed_at.isoformat()}  state={zone.state.value}  "
            f"flips={flips}"
        )

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
                binance.get_ohlc("BTCUSDT", tf, limit=200),
            )
    finally:
        binance.close()

    if TWELVE_DATA_API_KEY:
        twelvedata = TwelveDataClient(api_key=TWELVE_DATA_API_KEY)
        try:
            for tf in (Timeframe.H1, Timeframe.H4, Timeframe.D1):
                _run(
                    f"Twelve Data EUR/USD {tf.value}",
                    twelvedata.get_ohlc("EUR/USD", tf, limit=200),
                )
        finally:
            twelvedata.close()


if __name__ == "__main__":
    main()
