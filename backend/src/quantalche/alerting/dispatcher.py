from __future__ import annotations

from .. import config
from ..execution.models import TradeSignal
from ..execution.state_machine import SignalState
from .senders import AlertSender, DiscordAlertSender, TelegramAlertSender, WebhookAlertSender

_ALERT_STATES = {
    SignalState.PENDING,
    SignalState.SIGNAL_ACTIVE,
    SignalState.TP_HIT,
    SignalState.STOPPED_OUT,
    SignalState.EXPIRED,
}


def format_alert(
    source: str,
    symbol: str,
    timeframe: str,
    new_state: SignalState,
    trade: TradeSignal | None,
) -> str | None:
    """None for state transitions that aren't alert-worthy (e.g. IDLE, or
    a state that -- shouldn't happen, but defensively -- has no trade
    context to report).
    """
    label = f"{symbol} ({timeframe}, {source})"

    if new_state is SignalState.PENDING and trade is not None:
        direction = "LONG" if trade.direction.value == "long" else "SHORT"
        return (
            f"New {direction} signal -- {label}\n"
            f"Entry: {trade.entry:.5f}\n"
            f"Stop Loss: {trade.stop_loss:.5f}\n"
            f"Take Profit: {trade.take_profit:.5f}\n"
            f"R:R {trade.risk_reward:.2f}  Confidence {trade.confidence:.0%}"
        )
    if new_state is SignalState.SIGNAL_ACTIVE and trade is not None:
        return f"Order filled -- {label} entered at {trade.entry:.5f}"
    if new_state is SignalState.TP_HIT and trade is not None:
        return f"Take profit hit -- {label} +{trade.risk_reward:.2f}R"
    if new_state is SignalState.STOPPED_OUT:
        return f"Stopped out -- {label} -1R"
    if new_state is SignalState.EXPIRED:
        return f"Pending order expired unfilled -- {label}"
    return None


class AlertDispatcher:
    """Fires alerts on signal state transitions (architecture.md Layer 9:
    "once the signal state machine is live"). Wired into api/state.py's
    SignalRegistry -- only called on a *genuine* state change (see that
    module's idempotency guard), never once per poll.
    """

    def __init__(self, senders: list[AlertSender]) -> None:
        self.senders = senders

    def notify(
        self,
        source: str,
        symbol: str,
        timeframe: str,
        old_state: SignalState,
        new_state: SignalState,
        trade: TradeSignal | None,
    ) -> None:
        if not self.senders or old_state == new_state or new_state not in _ALERT_STATES:
            return
        message = format_alert(source, symbol, timeframe, new_state, trade)
        if message is None:
            return
        for sender in self.senders:
            sender.send(message)


def build_dispatcher_from_env() -> AlertDispatcher:
    """Enables each channel only if its env var(s) are set -- none
    configured means no-op alerting (AlertDispatcher.notify short-circuits
    on an empty sender list), not an error.
    """
    senders: list[AlertSender] = []
    if config.ALERT_WEBHOOK_URL:
        senders.append(WebhookAlertSender(config.ALERT_WEBHOOK_URL))
    if config.DISCORD_WEBHOOK_URL:
        senders.append(DiscordAlertSender(config.DISCORD_WEBHOOK_URL))
    if config.TELEGRAM_BOT_TOKEN and config.TELEGRAM_CHAT_ID:
        senders.append(
            TelegramAlertSender(config.TELEGRAM_BOT_TOKEN, config.TELEGRAM_CHAT_ID)
        )
    return AlertDispatcher(senders)
