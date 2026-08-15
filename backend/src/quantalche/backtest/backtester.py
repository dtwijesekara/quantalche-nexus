from __future__ import annotations

from collections import defaultdict

from ..aggregation.pipeline import SignalPipeline
from ..analysis.models import Bias
from ..execution.confirmation import ConfirmationLayer
from ..execution.state_machine import SignalState, SignalStateMachine
from ..ingestion.models import OHLCBar
from .models import BacktestReport, ModuleAccuracyStat, SegmentReport, TradeRecord


class Backtester:
    """Layer 7: bar-by-bar non-repainting replay across full history,
    logging every module's individual read and the aggregated decision
    exactly as they existed at that point in time -- never letting the
    engine "see" later data before labeling an earlier point
    (architecture.md Layer 7). Reports each module's individual accuracy
    alongside the combined signal's performance, so a dead-weight or
    actively-harmful component can be identified -- Layer 7's own stated
    purpose.

    Module accuracy methodology is NOT source-stated. The corpus never
    specifies how to score an individual module's correctness, since
    individual modules don't carry their own SL/TP -- only the combined
    system does, via ConfirmationLayer. A module's non-neutral signal here
    is scored "correct" if price ``accuracy_horizon_bars`` bars later
    closed in the predicted direction relative to the signal bar's close,
    "incorrect" otherwise. This is a simple directional-accuracy
    convention chosen for this project, not extracted from the material --
    documented as such.

    "Walk-forward" here means chronological segmentation, not parameter
    re-fitting -- these are rule-based modules, not a fitted model, so
    there is nothing to "train" on an in-sample window. Splitting the
    replay into sequential, non-overlapping out-of-sample segments and
    reporting each one separately is this project's reading of
    "walk-forward": checking whether performance holds up consistently
    across different chronological periods rather than only in one lucky
    stretch, directly serving architecture.md S5's warning that "multi-
    module systems can look deceptively strong in backtest purely from
    combining several factors."
    """

    def __init__(
        self,
        pipeline: SignalPipeline,
        confirmation_layer: ConfirmationLayer,
        accuracy_horizon_bars: int = 5,
        min_bars: int = 40,
    ) -> None:
        self.pipeline = pipeline
        self.confirmation_layer = confirmation_layer
        self.accuracy_horizon_bars = accuracy_horizon_bars
        self.min_bars = min_bars

    def run(
        self, bars: list[OHLCBar], label: str = "backtest", segments: int = 1
    ) -> BacktestReport:
        overall = self._run_segment(bars, f"{label} (full)")

        walk_forward: list[SegmentReport] = []
        if segments > 1:
            chunk = len(bars) // segments
            for s in range(segments):
                start = s * chunk
                end = len(bars) if s == segments - 1 else (s + 1) * chunk
                chunk_bars = bars[start:end]
                walk_forward.append(
                    self._run_segment(chunk_bars, f"{label} (segment {s + 1}/{segments})")
                )

        return BacktestReport(label=label, overall=overall, walk_forward_segments=walk_forward)

    def _run_segment(self, bars: list[OHLCBar], label: str) -> SegmentReport:
        if len(bars) < self.min_bars + 1:
            return SegmentReport(
                label=label,
                start_time=bars[0].open_time if bars else None,
                end_time=bars[-1].open_time if bars else None,
                bar_count=len(bars),
                trades=[],
                total_signals=0,
                filled=0,
                resolved=0,
                wins=0,
                losses=0,
                win_rate=None,
                expectancy_r=None,
                module_accuracy=[],
            )

        machine = SignalStateMachine()
        trades: list[TradeRecord] = []
        prev_state = SignalState.IDLE

        pending_calls: list[tuple[str, Bias, float, int]] = []
        module_correct: dict[str, int] = defaultdict(int)
        module_incorrect: dict[str, int] = defaultdict(int)

        for i in range(self.min_bars, len(bars) + 1):
            window = bars[:i]
            current_bar = window[-1]
            signal_bar_index = i - 1
            aggregated = self.pipeline.run(window)

            for sig in aggregated.module_signals:
                if sig.bias is not Bias.NEUTRAL:
                    pending_calls.append(
                        (sig.module, sig.bias, current_bar.close, signal_bar_index)
                    )

            still_pending: list[tuple[str, Bias, float, int]] = []
            for module_name, bias, ref_close, idx in pending_calls:
                target_index = idx + self.accuracy_horizon_bars
                if target_index <= signal_bar_index:
                    future_close = bars[target_index].close
                    correct = (
                        (future_close > ref_close)
                        if bias is Bias.BULLISH
                        else (future_close < ref_close)
                    )
                    if correct:
                        module_correct[module_name] += 1
                    else:
                        module_incorrect[module_name] += 1
                else:
                    still_pending.append((module_name, bias, ref_close, idx))
            pending_calls = still_pending

            result = self.confirmation_layer.confirm(aggregated, window)
            state = machine.process_bar(current_bar, result)

            if prev_state is SignalState.IDLE and state is SignalState.PENDING:
                pt = machine.pending_trade
                assert pt is not None
                trades.append(
                    TradeRecord(
                        direction=pt.direction,
                        entry=pt.entry,
                        stop_loss=pt.stop_loss,
                        take_profit=pt.take_profit,
                        risk_reward=pt.risk_reward,
                        confidence=pt.confidence,
                        signal_time=current_bar.open_time,
                    )
                )
            if prev_state is SignalState.PENDING and state is SignalState.SIGNAL_ACTIVE:
                trades[-1].fill_time = current_bar.open_time
            if state in (
                SignalState.STOPPED_OUT,
                SignalState.TP_HIT,
                SignalState.EXPIRED,
            ):
                trades[-1].outcome = state.value
                trades[-1].exit_time = current_bar.open_time

            prev_state = state

        filled = [t for t in trades if t.fill_time is not None]
        resolved = [t for t in filled if t.outcome in ("tp_hit", "stopped_out")]
        wins = sum(1 for t in resolved if t.outcome == "tp_hit")
        losses = len(resolved) - wins
        win_rate = wins / len(resolved) if resolved else None

        r_values = [
            t.risk_reward if t.outcome == "tp_hit" else -1.0 for t in resolved
        ]
        expectancy_r = sum(r_values) / len(r_values) if r_values else None

        module_names = sorted(set(module_correct) | set(module_incorrect))
        module_accuracy = [
            ModuleAccuracyStat(
                module=name,
                scored_signals=module_correct[name] + module_incorrect[name],
                correct=module_correct[name],
                incorrect=module_incorrect[name],
                accuracy=(
                    module_correct[name] / (module_correct[name] + module_incorrect[name])
                    if (module_correct[name] + module_incorrect[name]) > 0
                    else None
                ),
            )
            for name in module_names
        ]

        return SegmentReport(
            label=label,
            start_time=bars[0].open_time,
            end_time=bars[-1].open_time,
            bar_count=len(bars),
            trades=trades,
            total_signals=len(trades),
            filled=len(filled),
            resolved=len(resolved),
            wins=wins,
            losses=losses,
            win_rate=win_rate,
            expectancy_r=expectancy_r,
            module_accuracy=module_accuracy,
        )
