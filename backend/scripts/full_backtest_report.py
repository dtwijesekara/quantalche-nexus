"""Generates a comprehensive backtest report across every instrument in
the dashboard's default watchlist, both aggregation modes, with
walk-forward segmentation and per-module accuracy -- for a one-shot
full report rather than the piecemeal per-module validation scripts.

Writes structured JSON to stdout-adjacent file for the report builder to
consume; also prints a condensed human-readable summary.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone

from quantalche.aggregation.models import AggregationMode
from quantalche.aggregation.pipeline import default_pipeline
from quantalche.backtest.backtester import Backtester
from quantalche.backtest.models import BacktestReport
from quantalche.config import TWELVE_DATA_API_KEY
from quantalche.execution.confirmation import ConfirmationLayer
from quantalche.ingestion.binance_client import BinanceClient
from quantalche.ingestion.models import OHLCBar, Timeframe
from quantalche.ingestion.twelvedata_client import TwelveDataClient

INSTRUMENTS = [
    ("binance", "BTCUSDT", "BTC/USDT"),
    ("binance", "ETHUSDT", "ETH/USDT"),
    ("binance", "XRPUSDT", "XRP/USDT"),
    ("binance", "SOLUSDT", "SOL/USDT"),
    ("twelvedata", "EUR/USD", "EUR/USD"),
    ("twelvedata", "GBP/USD", "GBP/USD"),
    ("twelvedata", "XAU/USD", "XAU/USD"),
]

TIMEFRAME = Timeframe.H1
BAR_LIMIT = 1000
SEGMENTS = 3


def report_to_dict(report: BacktestReport) -> dict:
    def seg(s):
        return {
            "label": s.label,
            "start_time": s.start_time.isoformat() if s.start_time else None,
            "end_time": s.end_time.isoformat() if s.end_time else None,
            "bar_count": s.bar_count,
            "total_signals": s.total_signals,
            "filled": s.filled,
            "resolved": s.resolved,
            "wins": s.wins,
            "losses": s.losses,
            "win_rate": s.win_rate,
            "expectancy_r": s.expectancy_r,
            "module_accuracy": [
                {
                    "module": m.module,
                    "scored_signals": m.scored_signals,
                    "correct": m.correct,
                    "incorrect": m.incorrect,
                    "accuracy": m.accuracy,
                }
                for m in s.module_accuracy
            ],
            "trades": [
                {
                    "direction": t.direction.value,
                    "entry": t.entry,
                    "stop_loss": t.stop_loss,
                    "take_profit": t.take_profit,
                    "risk_reward": t.risk_reward,
                    "confidence": t.confidence,
                    "signal_time": t.signal_time.isoformat(),
                    "fill_time": t.fill_time.isoformat() if t.fill_time else None,
                    "exit_time": t.exit_time.isoformat() if t.exit_time else None,
                    "outcome": t.outcome,
                }
                for t in s.trades
            ],
        }

    return {
        "label": report.label,
        "overall": seg(report.overall),
        "walk_forward_segments": [seg(s) for s in report.walk_forward_segments],
    }


def fetch(source: str, symbol: str) -> list[OHLCBar] | None:
    if source == "binance":
        client = BinanceClient()
    else:
        if not TWELVE_DATA_API_KEY:
            return None
        client = TwelveDataClient(api_key=TWELVE_DATA_API_KEY)
    try:
        return client.get_ohlc(symbol, TIMEFRAME, limit=BAR_LIMIT)
    finally:
        client.close()


def main() -> None:
    results = []
    for source, symbol, label in INSTRUMENTS:
        print(f"Fetching {label} ({source})...")
        bars = fetch(source, symbol)
        if bars is None:
            print(f"  skipped -- {source} unavailable")
            continue
        print(f"  {len(bars)} bars")

        instrument_result = {
            "source": source,
            "symbol": symbol,
            "label": label,
            "bar_count": len(bars),
            "modes": {},
        }
        for mode in (AggregationMode.HARD_GATE, AggregationMode.SOFT_SCORE):
            pipeline = default_pipeline(mode)
            backtester = Backtester(pipeline, ConfirmationLayer())
            report = backtester.run(bars, label=f"{label} [{mode.value}]", segments=SEGMENTS)
            instrument_result["modes"][mode.value] = report_to_dict(report)
            o = report.overall
            print(
                f"  [{mode.value}] signals={o.total_signals} filled={o.filled} "
                f"resolved={o.resolved} win_rate={o.win_rate} expectancy={o.expectancy_r}"
            )
        results.append(instrument_result)

    output = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "timeframe": TIMEFRAME.value,
        "bar_limit": BAR_LIMIT,
        "segments": SEGMENTS,
        "instruments": results,
    }

    out_path = "full_backtest_report.json"
    with open(out_path, "w") as f:
        json.dump(output, f, indent=2)
    print(f"\nWrote {out_path}")


if __name__ == "__main__":
    main()
