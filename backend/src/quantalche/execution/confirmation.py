from __future__ import annotations

from ..aggregation.models import AggregatedBias, AggregatedSignal
from ..analysis.models import Bias
from ..analysis.swings import SwingKind, find_swings
from ..ingestion.models import OHLCBar
from .models import ConfirmationResult, RejectionReason, TradeDirection, TradeSignal


class ConfirmationLayer:
    """Layer 5: decides whether an aggregated signal is tradable, and if so
    computes entry/stop-loss/take-profit.

    Rule sources (docs/phase0-knowledge-extraction.md S3, S7 items 4-5):
    the corpus gives almost no usable, generalizable SL/TP formula -- of 22
    documents, only two state any generalizable SL rule at all, and TP is
    scarcely better. This layer's SL/TP logic is a Phase 5 design choice
    built from the corpus's best-corroborated fragments, not a literal
    source rule -- documented as such, same convention as every Layer 2
    module's non-sourced additions:

      - Stop-loss: doc 02's rule ("place stop loss at the nearest OB or
        liquidity zone") is the only fully explicit, generalizable SL rule
        found anywhere in the corpus. Implemented here as the nearest
        swing point (swings.py) structurally opposing the trade direction,
        plus a small buffer.
      - Take-profit: "target = opposite liquidity" is the single
        most-repeated TP idea across the corpus (docs 08/11, 13, and
        implied elsewhere). Implemented as the nearest swing high (for
        longs) / swing low (for shorts) beyond entry -- exactly where
        liquidity_sweep.py's own BSL/SSL definition says that liquidity
        rests, reusing the same concept without re-deriving it.
      - Minimum 1:1.5 reward:risk is the only quantified TP floor found
        anywhere in the corpus (docs 01, 10). Enforced here as a hard
        confirmation gate, not a suggestion: if the nearest opposing swing
        doesn't clear it, the next one out is tried; if none does, the
        signal is rejected as unconfirmed rather than force-fit into a
        trade.

    Entry is the average of the price level(s) the *agreeing* modules
    actually anchored their signal to (ModuleSignal.level), not the
    current market close -- architecture.md's Layer 6 calls for "entry as
    limit order," which needs to be a price the modules reacted to.

    ``min_confidence``, ``sl_buffer_ratio``, and the swing-based stop/target
    convention are NOT source-stated -- documented Phase 5 additions.
    """

    def __init__(
        self,
        min_confidence: float = 0.5,
        min_risk_reward: float = 1.5,
        sl_buffer_ratio: float = 0.1,
        swing_strength: int = 2,
    ) -> None:
        self.min_confidence = min_confidence
        self.min_risk_reward = min_risk_reward
        self.sl_buffer_ratio = sl_buffer_ratio
        self.swing_strength = swing_strength

    def confirm(
        self, aggregated: AggregatedSignal, bars: list[OHLCBar]
    ) -> ConfirmationResult:
        if aggregated.bias not in (AggregatedBias.BULLISH, AggregatedBias.BEARISH):
            return ConfirmationResult(
                confirmed=False,
                rejection_reason=RejectionReason.NOT_DIRECTIONAL,
                detail=f"Aggregated bias is {aggregated.bias.value}, not directional.",
            )

        if aggregated.confidence < self.min_confidence:
            return ConfirmationResult(
                confirmed=False,
                rejection_reason=RejectionReason.LOW_CONFIDENCE,
                detail=(
                    f"Confidence {aggregated.confidence:.2f} below minimum "
                    f"{self.min_confidence:.2f}."
                ),
            )

        direction = (
            TradeDirection.LONG
            if aggregated.bias is AggregatedBias.BULLISH
            else TradeDirection.SHORT
        )
        target_bias = Bias.BULLISH if direction is TradeDirection.LONG else Bias.BEARISH
        levels = [
            s.level
            for s in aggregated.module_signals
            if s.bias is target_bias and s.level is not None
        ]
        entry = sum(levels) / len(levels) if levels else bars[-1].close

        swings = find_swings(bars, self.swing_strength)
        avg_range = sum(b.high - b.low for b in bars) / len(bars)
        buffer = avg_range * self.sl_buffer_ratio

        stop = self._nearest_stop(swings, entry, direction, buffer)
        if stop is None:
            return ConfirmationResult(
                confirmed=False,
                rejection_reason=RejectionReason.NO_STOP_REFERENCE,
                detail="No swing point found to anchor a stop loss.",
            )

        risk = abs(entry - stop)
        target = self._nearest_target(swings, entry, direction, risk)
        if target is None:
            return ConfirmationResult(
                confirmed=False,
                rejection_reason=RejectionReason.INSUFFICIENT_RR,
                detail=(
                    f"No swing level in the trade direction clears the "
                    f"{self.min_risk_reward} minimum reward:risk."
                ),
            )

        rr = abs(target - entry) / risk
        trade = TradeSignal(
            direction=direction,
            entry=entry,
            stop_loss=stop,
            take_profit=target,
            risk_reward=rr,
            confidence=aggregated.confidence,
            bar_time=aggregated.bar_time,
            aggregated_signal=aggregated,
            reason=(
                f"{direction.value} @ {entry:.5f}, SL {stop:.5f}, "
                f"TP {target:.5f}, RR {rr:.2f}."
            ),
        )
        return ConfirmationResult(confirmed=True, trade_signal=trade, detail=trade.reason)

    def _nearest_stop(
        self, swings, entry: float, direction: TradeDirection, buffer: float
    ) -> float | None:
        if direction is TradeDirection.LONG:
            lows = [s.price for s in swings if s.kind is SwingKind.LOW and s.price < entry]
            return (max(lows) - buffer) if lows else None
        highs = [s.price for s in swings if s.kind is SwingKind.HIGH and s.price > entry]
        return (min(highs) + buffer) if highs else None

    def _nearest_target(
        self, swings, entry: float, direction: TradeDirection, risk: float
    ) -> float | None:
        if risk <= 0:
            return None
        if direction is TradeDirection.LONG:
            candidates = sorted(
                s.price for s in swings if s.kind is SwingKind.HIGH and s.price > entry
            )
        else:
            candidates = sorted(
                (s.price for s in swings if s.kind is SwingKind.LOW and s.price < entry),
                reverse=True,
            )
        for level in candidates:
            if abs(level - entry) / risk >= self.min_risk_reward:
                return level
        return None
