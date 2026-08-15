from __future__ import annotations

from datetime import datetime, timezone

from .base import AnalysisModule
from .models import Bias, ModuleSignal
from .swings import find_swings
from ..ingestion.models import OHLCBar


class PremiumDiscountModule(AnalysisModule):
    """Layer 2 module: Premium/Discount dealing-range bias.

    Rule sources (docs/rule-mapping.md): docs 08 p.57 and 11 p.96-97,
    explicitly labeled "in the ICT (Inner Circle Trader) concept" in both --
    "Dealing Range High (DRH) = highest point of a move (swing high);
    Dealing Range Low (DRL) = lowest point (swing low). Premium Zone
    (0-0.5) = upper half, considered a sell area ('expensive'); Discount
    Zone (0.5-1) = lower half, considered a buy area ('cheap'); Midpoint
    (0.5) = boundary." Doc 13 corroborates independently ("Price moves
    between: Premium zone -> ideal for sell; Discount zone -> ideal for
    buy... Every impulse forms a dealing range... Equilibrium (50%) becomes
    a magnet point," p.10) and uses it as a take-profit reference ("HTF
    Premium/Discount Array as target," p.97/103). Doc 10 uses it as an
    explicit entry filter: "Ideal BUY entries are taken: In discount...
    Reaction from a Key Level or SNR zone" (p.17) -- the mirror condition
    for sells is implied, not separately quoted.

    Doc 02 also uses the words "premium"/"discount" (p.14, p.18, p.57) but
    for a DIFFERENT, incompatible mechanic -- price above/below the 00:00
    and 09:30 True Open reference prices, not a swing-range midpoint. This
    is a genuine corpus ambiguity (two documents reusing the same term for
    different definitions), same category as the QM/QML resolution
    (Phase0 S7 item 2). Resolved here by implementing docs 08/11/13's
    version: it's the one with a precise, checkable formula shared across
    three independent documents, and doc 02's own True-Open bias is
    already implemented separately (`quarterly_theory.py`) -- not
    duplicated or reconciled here, just documented as the other reading.

    Dealing range = the two most recent confirmed swing points (`swings.py`
    -- the corpus never gives a swing-formation rule, so the same external
    fractal/pivot convention already used by `market_structure.py` and
    `liquidity_sweep.py` is reused here, not re-derived). `swing_strength`
    defaults to 2, matching `market_structure.py`'s validated default,
    since P/D's own sources don't specify one either. Using the *last two*
    swings (guaranteed high/low alternating by `find_swings`) reads as
    "every impulse forms a dealing range" (doc 13) -- the range updates to
    the latest leg as soon as a new swing confirms, rather than anchoring
    to some older, larger range.

    Confidence is a flat 0.5 when price sits in discount or premium, not a
    depth-scaled gradient -- none of the three corroborating documents
    describe premium/discount as a strength-scored signal; doc 10's own
    usage is a binary filter ("in discount" or not), and doc 08/11's own
    definition draws a hard 0.5 boundary rather than a continuum. Scaling
    confidence by distance from the midpoint would be an invented
    precision the sources don't support.

    Like `quarterly_theory.py`'s True-Open bias, this module is always
    non-neutral once a dealing range exists (price is always on one side
    of the midpoint or exactly on it) -- see `pipeline.py`'s
    `default_pipeline` docstring for why an always-on module is a
    materially different risk under HARD_GATE than a normal setup-based
    module, and why this one is validated the same way before any
    default-pipeline inclusion decision.
    """

    name = "premium_discount"

    def __init__(self, swing_strength: int = 2) -> None:
        self.swing_strength = swing_strength

    def evaluate(self, bars: list[OHLCBar]) -> ModuleSignal:
        if not bars:
            return ModuleSignal(
                module=self.name,
                bias=Bias.NEUTRAL,
                confidence=0.0,
                reason="No bars.",
                bar_time=datetime.now(timezone.utc),
            )

        last = bars[-1]
        swings = find_swings(bars, self.swing_strength)
        if len(swings) < 2:
            return ModuleSignal(
                module=self.name,
                bias=Bias.NEUTRAL,
                confidence=0.0,
                reason="Not enough confirmed swings yet to form a dealing range.",
                bar_time=last.open_time,
            )

        recent = swings[-2:]
        drh = max(s.price for s in recent)
        drl = min(s.price for s in recent)
        if drh <= drl:
            return ModuleSignal(
                module=self.name,
                bias=Bias.NEUTRAL,
                confidence=0.0,
                reason="Degenerate dealing range (zero range).",
                bar_time=last.open_time,
            )

        midpoint = (drh + drl) / 2
        price = last.close

        if price < midpoint:
            bias = Bias.BULLISH
            zone = "discount"
        elif price > midpoint:
            bias = Bias.BEARISH
            zone = "premium"
        else:
            bias = Bias.NEUTRAL
            zone = "equilibrium"

        confidence = 0.5 if bias is not Bias.NEUTRAL else 0.0
        reason = (
            f"Price {price:.5f} in the {zone} half of the dealing range "
            f"({drl:.5f}-{drh:.5f}, equilibrium {midpoint:.5f})."
        )
        return ModuleSignal(
            module=self.name,
            bias=bias,
            confidence=confidence,
            reason=reason,
            bar_time=last.open_time,
            level=midpoint,
        )
