from __future__ import annotations

from ..aggregation.models import AggregatedBias, AggregatedSignal
from ..analysis.liquidity_sweep import LiquidityLevelType, LiquiditySweepModule
from ..analysis.models import Bias
from ..analysis.snr_zone import SNRZoneModule, ZoneType
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
        found anywhere in the corpus. Implemented as the nearest edge of
        an opposing SNR zone (snr_zone.py -- the corpus's own "MSNR"
        module: gap zones + Classic V/A) or swing point (swings.py,
        fallback when no zone exists nearby), plus a small buffer.
      - Take-profit: "target = opposite liquidity" is the single
        most-repeated TP idea across the corpus (docs 08/11, 13, and
        implied elsewhere). Implemented as the nearest opposing BSL/SSL
        liquidity level (liquidity_sweep.py) or swing point (fallback),
        beyond entry.
      - Minimum reward:risk: docs 01 and 10 both independently state
        "Maintain RR >= 1:1.5" in a general "Quick Rules Summary" meant to
        apply to every trade -- two different authors (SYFIRE; AbayFX's
        expanded manual), both general-baseline claims, both verified
        directly against the source PDF text (not just the MD notes).
        Doc 22 separately states a HIGHER floor, "RR >= 1:3," but that
        figure is not a competing general baseline -- it's stated inside
        one specific, aggressive account-compounding strategy (5-12% risk
        per trade, an unvalidated assumed 80% win rate used only in two
        hypothetical worked examples) that this project's own analysis
        already flags as an outlier not to trust (see rule-mapping.md).
        1:1.5 was kept as the default because it's the figure with
        independent general-context corroboration; 1:3 was previously
        omitted from this docstring entirely, which incorrectly implied
        no competing figure existed -- found and corrected after a direct
        request to re-audit this exact rule against the source PDFs, not
        a routine pass. Enforced here as a hard confirmation gate, not a
        suggestion: if the nearest opposing candidate doesn't clear it,
        the next one out is tried; if none does, the signal is rejected as
        unconfirmed rather than force-fit into a trade.

    SL/TP candidates are pooled from THREE sources -- SNR zones, liquidity
    levels, and raw swing points -- rather than swing points alone (the
    original Phase 5 version). This directly reuses the already-validated
    snr_zone.py and liquidity_sweep.py modules' own detection instead of
    re-deriving a disconnected approximation in this layer, which is what
    "aligned to Alchemist MSNR" concretely means here: MSNR *is* the SNR
    Zone module in this corpus's own vocabulary (Phase0 §5), so the stop
    should be able to land on an actual MSNR zone edge, not just a generic
    swing high/low that happens to be nearby. Raw swings stay in the pool
    as a fallback so confirmation doesn't get *more* restrictive than
    before on bars where no zone/liquidity level exists close enough.

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
        self._zone_module = SNRZoneModule()
        self._liquidity_module = LiquiditySweepModule()

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
        zones = self._zone_module.detect_zones(bars)
        levels, _ = self._liquidity_module.detect_levels_and_sweeps(bars)
        avg_range = sum(b.high - b.low for b in bars) / len(bars)
        buffer = avg_range * self.sl_buffer_ratio

        stop = self._nearest_stop(swings, zones, entry, direction, buffer)
        if stop is None:
            return ConfirmationResult(
                confirmed=False,
                rejection_reason=RejectionReason.NO_STOP_REFERENCE,
                detail="No SNR zone or swing point found to anchor a stop loss.",
            )

        risk = abs(entry - stop)
        target = self._nearest_target(swings, levels, entry, direction, risk)
        if target is None:
            return ConfirmationResult(
                confirmed=False,
                rejection_reason=RejectionReason.INSUFFICIENT_RR,
                detail=(
                    f"No liquidity level or swing in the trade direction clears "
                    f"the {self.min_risk_reward} minimum reward:risk."
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
        self, swings, zones, entry: float, direction: TradeDirection, buffer: float
    ) -> float | None:
        if direction is TradeDirection.LONG:
            candidates = [
                s.price for s in swings if s.kind is SwingKind.LOW and s.price < entry
            ]
            candidates += [
                z.bottom
                for z in zones
                if z.zone_type is ZoneType.SUPPORT and z.bottom < entry
            ]
            return (max(candidates) - buffer) if candidates else None

        candidates = [
            s.price for s in swings if s.kind is SwingKind.HIGH and s.price > entry
        ]
        candidates += [
            z.top for z in zones if z.zone_type is ZoneType.RESISTANCE and z.top > entry
        ]
        return (min(candidates) + buffer) if candidates else None

    def _nearest_target(
        self, swings, levels, entry: float, direction: TradeDirection, risk: float
    ) -> float | None:
        if risk <= 0:
            return None
        if direction is TradeDirection.LONG:
            candidates = sorted(
                {s.price for s in swings if s.kind is SwingKind.HIGH and s.price > entry}
                | {
                    lvl.price
                    for lvl in levels
                    if lvl.level_type is LiquidityLevelType.BSL and lvl.price > entry
                }
            )
        else:
            candidates = sorted(
                {s.price for s in swings if s.kind is SwingKind.LOW and s.price < entry}
                | {
                    lvl.price
                    for lvl in levels
                    if lvl.level_type is LiquidityLevelType.SSL and lvl.price < entry
                },
                reverse=True,
            )
        for level in candidates:
            if abs(level - entry) / risk >= self.min_risk_reward:
                return level
        return None
