from __future__ import annotations

from enum import Enum

from ..ingestion.models import OHLCBar, Timeframe
from .confirmation import ConfirmationResult
from .models import TradeDirection, TradeSignal


class SignalState(str, Enum):
    IDLE = "idle"
    PENDING = "pending"
    SIGNAL_ACTIVE = "signal_active"
    STOPPED_OUT = "stopped_out"
    TP_HIT = "tp_hit"
    EXPIRED = "expired"


class SignalStateMachine:
    """Layer 6: IDLE -> PENDING -> SIGNAL_ACTIVE -> STOPPED_OUT | TP_HIT ->
    IDLE, with PENDING -> EXPIRED -> IDLE as the unfilled-order path.

    The PENDING state is NOT in architecture.md's original 4-state sketch
    (IDLE -> SIGNAL_ACTIVE -> STOPPED_OUT | TP_HIT -> IDLE) -- it was added
    after live validation surfaced a real bug in the simpler version: entry
    price comes from ModuleSignal.level, which can be a price from several
    bars back (e.g. market_structure.py's broken_level, from a strong
    displacement candle that closed well past the level it broke). The
    original design treated the confirmed signal as filling *instantly* at
    that price the moment it confirmed, regardless of where current price
    actually was. Concretely, on live BTCUSDT 1h data this produced an
    11-for-11 (100%) win rate, with 8 of 11 trades resolving in exactly one
    bar -- current price had, in some cases, already moved *past* the
    take-profit by the time the "entry" was recorded, crediting the trade
    with favorable movement that happened before the theoretical entry.

    PENDING fixes this at the root by modeling ``entry`` as an actual
    resting limit order: the trade only becomes SIGNAL_ACTIVE once a
    subsequent bar's range genuinely trades through the entry price. This
    is a more faithful implementation of architecture.md's own "entry as
    limit order" language, not a deviation from it -- an unfilled limit
    order is precisely a pending state. ``max_pending_bars`` (order expiry)
    is NOT source-stated -- standard trading-system practice, not left
    open-ended, documented here as an explicit addition.

    STOPPED_OUT/TP_HIT/EXPIRED are each visible for exactly one
    ``process_bar`` call -- the bar the outcome became known on -- then the
    machine resets to IDLE on the following call.

    A trade is never checked against its stop/target on the same bar it
    fills: the fill happens on this bar's close (bar's range crossed the
    limit price); monitoring starts from the next bar. The equivalent
    same-bar stop-vs-target ambiguity (a wide-range bar clearing both
    levels) is resolved by assuming the stop was hit first -- a
    conservative, NOT source-stated assumption, since OHLC data alone can't
    reveal intrabar sequencing.
    """

    def __init__(self, max_pending_bars: int = 10) -> None:
        self.state: SignalState = SignalState.IDLE
        self.pending_trade: TradeSignal | None = None
        self.active_trade: TradeSignal | None = None
        self.max_pending_bars = max_pending_bars
        self._pending_bars_elapsed = 0

    def process_bar(
        self, bar: OHLCBar, confirmation_result: ConfirmationResult | None
    ) -> SignalState:
        if self.state in (
            SignalState.STOPPED_OUT,
            SignalState.TP_HIT,
            SignalState.EXPIRED,
        ):
            self.state = SignalState.IDLE
            self.active_trade = None
            self.pending_trade = None
            self._pending_bars_elapsed = 0

        if self.state is SignalState.IDLE:
            if confirmation_result is not None and confirmation_result.confirmed:
                self.pending_trade = confirmation_result.trade_signal
                self.state = SignalState.PENDING
                self._pending_bars_elapsed = 0
            return self.state

        if self.state is SignalState.PENDING:
            trade = self.pending_trade
            assert trade is not None
            self._pending_bars_elapsed += 1

            if trade.direction is TradeDirection.LONG:
                filled = bar.low <= trade.entry
            else:
                filled = bar.high >= trade.entry

            if filled:
                self.active_trade = trade
                self.pending_trade = None
                self.state = SignalState.SIGNAL_ACTIVE
            elif self._pending_bars_elapsed >= self.max_pending_bars:
                self.state = SignalState.EXPIRED
            return self.state

        # SIGNAL_ACTIVE
        trade = self.active_trade
        assert trade is not None

        if trade.direction is TradeDirection.LONG:
            hit_stop = bar.low <= trade.stop_loss
            hit_tp = bar.high >= trade.take_profit
        else:
            hit_stop = bar.high >= trade.stop_loss
            hit_tp = bar.low <= trade.take_profit

        if hit_stop:
            self.state = SignalState.STOPPED_OUT
        elif hit_tp:
            self.state = SignalState.TP_HIT
        return self.state


class SignalStateMachineRegistry:
    """One SignalStateMachine per (symbol, timeframe), per architecture.md
    Layer 6 ("one signal per symbol+timeframe per request").
    """

    def __init__(self) -> None:
        self._machines: dict[tuple[str, Timeframe], SignalStateMachine] = {}

    def get(self, symbol: str, timeframe: Timeframe) -> SignalStateMachine:
        key = (symbol, timeframe)
        if key not in self._machines:
            self._machines[key] = SignalStateMachine()
        return self._machines[key]

    def process(
        self,
        symbol: str,
        timeframe: Timeframe,
        bar: OHLCBar,
        confirmation_result: ConfirmationResult | None,
    ) -> SignalState:
        return self.get(symbol, timeframe).process_bar(bar, confirmation_result)
