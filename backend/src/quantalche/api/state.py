from __future__ import annotations

from datetime import datetime

from ..aggregation.models import AggregatedSignal, AggregationMode
from ..aggregation.pipeline import default_pipeline
from ..execution.confirmation import ConfirmationLayer
from ..execution.models import ConfirmationResult
from ..execution.state_machine import SignalState, SignalStateMachine, SignalStateMachineRegistry
from ..ingestion.models import OHLCBar, Timeframe


class SignalRegistry:
    """Server-side, process-lifetime state for the API layer.

    Wraps SignalStateMachineRegistry with idempotent per-bar processing --
    NOT source-stated, an API-layer correctness requirement rather than a
    trading-methodology rule. A live client (frontend poll, WebSocket tick)
    may call ``update`` many times while the same underlying bar is still
    the latest closed one; ``process_bar`` must only actually advance the
    state machine once per newly-closed bar per (source, symbol,
    timeframe), or repeated calls would double-process transitions --
    e.g. re-triggering a fresh IDLE->PENDING using stale data on every
    poll, since STOPPED_OUT/TP_HIT/EXPIRED reset to IDLE on the *next*
    ``process_bar`` call by design (execution/state_machine.py).

    One registry instance is shared across the FastAPI app's lifetime
    (see app.py) -- this is what "one signal per symbol+timeframe per
    request" (architecture.md Layer 6) actually requires: real, persistent
    server-side state, not a fresh state machine per HTTP request.
    """

    def __init__(self) -> None:
        self._machines = SignalStateMachineRegistry()
        self._last_processed: dict[tuple[str, Timeframe], datetime] = {}
        self._confirmation_layer = ConfirmationLayer()

    def update(
        self,
        registry_key: str,
        timeframe: Timeframe,
        bars: list[OHLCBar],
        mode: AggregationMode,
    ) -> tuple[SignalState, SignalStateMachine, AggregatedSignal, ConfirmationResult]:
        pipeline = default_pipeline(mode)
        aggregated = pipeline.run(bars)
        confirmation = self._confirmation_layer.confirm(aggregated, bars)

        machine = self._machines.get(registry_key, timeframe)
        cache_key = (registry_key, timeframe)
        last_bar = bars[-1]
        last_time = self._last_processed.get(cache_key)

        if last_time is None or last_bar.open_time > last_time:
            machine.process_bar(last_bar, confirmation)
            self._last_processed[cache_key] = last_bar.open_time

        return machine.state, machine, aggregated, confirmation


# One instance for the app's lifetime -- see the note in the class
# docstring on why this can't be per-request.
signal_registry = SignalRegistry()
