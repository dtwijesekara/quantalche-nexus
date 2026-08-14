"""Phase 3 validation script for the Liquidity/Sweep module.

Prints every detected sweep event plus the module's current signal, so the
output can be checked by eye against a real chart -- per the Phase 3
validation step in docs/architecture.md.
"""

from __future__ import annotations

from quantalche.analysis.liquidity_sweep import LiquiditySweepModule
from quantalche.config import TWELVE_DATA_API_KEY
from quantalche.ingestion.binance_client import BinanceClient
from quantalche.ingestion.models import OHLCBar, Timeframe
from quantalche.ingestion.twelvedata_client import TwelveDataClient


def _run(label: str, bars: list[OHLCBar]) -> None:
    module = LiquiditySweepModule()
    levels, sweeps = module._levels_and_sweeps(bars)  # noqa: SLF001 -- validation script

    print(
        f"\n--- {label}: {len(bars)} bars, {len(levels)} levels, "
        f"{len(sweeps)} sweeps ---"
    )
    for sweep in sweeps[-10:]:
        print(
            f"  {sweep.level_type.value.upper():<4} swept at {sweep.at.isoformat()}  "
            f"level={sweep.level_price:.5f}  wick={sweep.wick_extreme:.5f}  "
            f"close={sweep.close_price:.5f}"
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
