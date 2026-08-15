from __future__ import annotations

from datetime import datetime, timezone

from .base import AnalysisModule
from .models import Bias, ModuleSignal
from ..ingestion.models import OHLCBar


class CRTModule(AnalysisModule):
    """Layer 2 module: CRT (Candle Range Theory) / PO3
    (Accumulation-Manipulation-Distribution).

    Rule source (docs/phase0-knowledge-extraction.md S2.4; full citations
    in docs/rule-mapping.md): a 3-candle model, attributed in the corpus
    to @Romeopt/ICT (doc 02 S5, S19), appearing consistently across docs
    02, 07, 09:
      - Candle 1 = Accumulation: establishes a reference range
        [CRL, CRH] = [low, high] ("Candle Range Low/High").
      - Candle 2 = Manipulation: a liquidity sweep of that range -- wicks
        beyond CRH or CRL without a genuine breakout.
      - Candle 3 = Distribution: the *real* move, in the direction
        opposite the manipulation wick (doc 02 S19-20: "Entry: after
        liquidity sweep and PO3 Phase 3 confirmation").
    A sweep of CRL (fake breakdown) implies bullish distribution; a sweep
    of CRH (fake breakout) implies bearish distribution. A candle 2 that
    sweeps *both* sides (an outside bar) or *neither* side isn't a clean
    CRT setup and is treated as neutral -- doc 02 doesn't address that
    case, and inventing a tie-break would be a judgment call presented as
    a rule.

    "Phase 3 confirmation" is formalized as: candle 3's close continues in
    the distribution direction (past candle 2's close) and closes back on
    the side of the range the sweep denied -- i.e. the fakeout is
    invalidated by the close, not just implied by the wick.

    Doc 02 S20 also gives this pattern's own explicit SL/TP rule ("place
    stop loss at the nearest OB or liquidity zone... target = next
    structural resistance/support or BOS level") -- not duplicated here.
    It's the same rule already generalized into
    execution/confirmation.py's ConfirmationLayer (Phase0 S7 items 4-5),
    which applies uniformly across every module's signals, this one
    included.

    Evaluated on a fixed trailing 3-bar window each call -- doc 07 states
    CRT is usable "across H1-H4, Daily-Weekly-Monthly," i.e. at whatever
    single timeframe is being evaluated, not a fixed HTF; this module
    doesn't pick a timeframe for the caller.
    """

    name = "crt_pattern"

    def evaluate(self, bars: list[OHLCBar]) -> ModuleSignal:
        if len(bars) < 3:
            return ModuleSignal(
                module=self.name,
                bias=Bias.NEUTRAL,
                confidence=0.0,
                reason="Not enough bars for a 3-candle CRT/PO3 sequence.",
                bar_time=bars[-1].open_time if bars else datetime.now(timezone.utc),
            )

        c1, c2, c3 = bars[-3], bars[-2], bars[-1]
        crh, crl = c1.high, c1.low
        swept_low = c2.low < crl
        swept_high = c2.high > crh

        if swept_low and not swept_high:
            direction_bias = Bias.BULLISH
            confirmed = c3.close > c2.close and c3.close >= crl
            level = crl
            label = "below CRL"
        elif swept_high and not swept_low:
            direction_bias = Bias.BEARISH
            confirmed = c3.close < c2.close and c3.close <= crh
            level = crh
            label = "above CRH"
        else:
            return ModuleSignal(
                module=self.name,
                bias=Bias.NEUTRAL,
                confidence=0.0,
                reason=(
                    "No clean CRT/PO3 manipulation candle -- swept both sides "
                    "or neither."
                ),
                bar_time=c3.open_time,
            )

        if not confirmed:
            return ModuleSignal(
                module=self.name,
                bias=Bias.NEUTRAL,
                confidence=0.0,
                reason=(
                    f"Candle 2 swept {label} (CRH {crh:.5f} / CRL {crl:.5f}) but "
                    f"candle 3 didn't confirm distribution."
                ),
                bar_time=c3.open_time,
            )

        reason = (
            f"CRT/PO3 {direction_bias.value}: candle 2 swept {label} "
            f"(CRH {crh:.5f} / CRL {crl:.5f}), candle 3 confirmed distribution "
            f"at close {c3.close:.5f}."
        )
        return ModuleSignal(
            module=self.name,
            bias=direction_bias,
            confidence=0.6,
            reason=reason,
            bar_time=c3.open_time,
            level=level,
        )
