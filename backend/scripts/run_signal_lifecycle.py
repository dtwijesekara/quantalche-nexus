"""Phase 5 validation script -- the full pipeline end to end.

Non-repainting bar-by-bar replay: modules -> aggregation -> confirmation
(entry/SL/TP) -> state machine (IDLE/SIGNAL_ACTIVE/STOPPED_OUT/TP_HIT).
This is the first point where the whole system can be watched taking and
resolving trades, not just producing isolated reads. Per the Phase 5
validation step in docs/architecture.md: "confirm no duplicate signals;
confirm signals fire only post-confirmation."
"""

from __future__ import annotations

from quantalche.aggregation.models import AggregationMode
from quantalche.aggregation.pipeline import default_pipeline
from quantalche.config import TWELVE_DATA_API_KEY
from quantalche.execution.confirmation import ConfirmationLayer
from quantalche.execution.state_machine import SignalState, SignalStateMachine
from quantalche.ingestion.binance_client import BinanceClient
from quantalche.ingestion.models import OHLCBar, Timeframe
from quantalche.ingestion.twelvedata_client import TwelveDataClient


def _replay(label: str, bars: list[OHLCBar], mode: AggregationMode) -> None:
    pipeline = default_pipeline(mode)
    confirmation_layer = ConfirmationLayer()
    machine = SignalStateMachine()

    min_len = 40
    trades: list[dict] = []
    prev_state = SignalState.IDLE
    corrupted_trade_ref = 0  # sanity check: active/pending trade object must not change mid-lifecycle
    last_seen_trade_id = None

    for i in range(min_len, len(bars) + 1):
        window = bars[:i]
        current_bar = window[-1]
        aggregated = pipeline.run(window)
        result = confirmation_layer.confirm(aggregated, window)
        state = machine.process_bar(current_bar, result)

        current_trade = machine.pending_trade or machine.active_trade
        if state in (SignalState.PENDING, SignalState.SIGNAL_ACTIVE):
            trade_id = id(current_trade)
            if prev_state in (SignalState.PENDING, SignalState.SIGNAL_ACTIVE) and last_seen_trade_id != trade_id:
                corrupted_trade_ref += 1  # would indicate a real duplicate/overwrite bug
            last_seen_trade_id = trade_id
        else:
            last_seen_trade_id = None

        if prev_state is SignalState.IDLE and state is SignalState.PENDING:
            trades.append(
                {
                    "signal_time": current_bar.open_time,
                    "trade": machine.pending_trade,
                    "fill_time": None,
                    "outcome": None,
                    "exit_time": None,
                }
            )
        if prev_state is SignalState.PENDING and state is SignalState.SIGNAL_ACTIVE:
            trades[-1]["fill_time"] = current_bar.open_time
        if state in (SignalState.STOPPED_OUT, SignalState.TP_HIT, SignalState.EXPIRED):
            trades[-1]["outcome"] = state.value
            trades[-1]["exit_time"] = current_bar.open_time

        prev_state = state

    filled = [t for t in trades if t["fill_time"] is not None]
    resolved = [t for t in filled if t["outcome"] in ("stopped_out", "tp_hit")]
    expired = [t for t in trades if t["outcome"] == "expired"]
    wins = sum(1 for t in resolved if t["outcome"] == "tp_hit")
    print(
        f"\n--- {label} [{mode.value}]: {len(trades)} signals over "
        f"{len(bars) - min_len + 1} bars -- {len(expired)} expired unfilled, "
        f"{len(filled)} filled, {len(resolved)} resolved, {wins}/{len(resolved)} hit TP ---"
    )
    print(
        f"  Trade-object-integrity check: "
        f"{'PASS (0)' if corrupted_trade_ref == 0 else f'FAIL ({corrupted_trade_ref})'}"
    )
    for t in trades[-5:]:
        trade = t["trade"]
        fill_note = "unfilled" if t["fill_time"] is None else f"filled {t['fill_time'].isoformat()}"
        print(
            f"  {trade.direction.value:<5} entry={trade.entry:.5f} "
            f"SL={trade.stop_loss:.5f} TP={trade.take_profit:.5f} "
            f"RR={trade.risk_reward:.2f}  {fill_note}  outcome={t['outcome']}"
        )


def main() -> None:
    binance = BinanceClient()
    try:
        bars = binance.get_ohlc("BTCUSDT", Timeframe.H1, limit=500)
        _replay("Binance BTCUSDT 1h", bars, AggregationMode.HARD_GATE)
        _replay("Binance BTCUSDT 1h", bars, AggregationMode.SOFT_SCORE)
    finally:
        binance.close()

    if TWELVE_DATA_API_KEY:
        twelvedata = TwelveDataClient(api_key=TWELVE_DATA_API_KEY)
        try:
            bars = twelvedata.get_ohlc("EUR/USD", Timeframe.H1, limit=500)
            _replay("Twelve Data EUR/USD 1h", bars, AggregationMode.HARD_GATE)
            _replay("Twelve Data EUR/USD 1h", bars, AggregationMode.SOFT_SCORE)
        finally:
            twelvedata.close()


if __name__ == "__main__":
    main()
