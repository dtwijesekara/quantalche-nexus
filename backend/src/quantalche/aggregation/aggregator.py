from __future__ import annotations

from datetime import datetime

from ..analysis.models import Bias, ModuleSignal
from .models import AggregatedBias, AggregatedSignal, AggregationMode


class Aggregator:
    """Layer 3: combines Layer 2 module signals into one decision.

    Rule source (docs/phase0-knowledge-extraction.md S4, S7 item 1): no
    single combination rule is stated consistently across the corpus --
    every document is either silent on how components combine, or
    internally self-contradictory about it. The one exception (Yanu
    Emmanuel F., docs 06/16/20 + 22) states a fully self-consistent hard
    AND-gate, but it's one author's model, not a corpus consensus. Phase 0
    S7 item 1 resolved this by making combination logic configurable
    rather than committing to one model, with HARD_GATE as the default
    preset (spiritually modeled on that hard-gate cascade) and SOFT_SCORE
    as the alternative, so Layer 7 (backtesting) can compare both
    empirically -- exactly what Layer 7 exists to do.

    HARD_GATE makes architecture.md's ground rule #0 literal: "Multiple
    modules can disagree... surface it, don't average it away silently."
    When active modules actively disagree (not just some being neutral),
    the result is CONFLICT -- not an averaged-away NEUTRAL, not a
    majority-vote winner. SOFT_SCORE, by contrast, deliberately blends
    everything into one weighted number; that's the whole point of the
    distinction architecture.md draws between the two philosophies, and
    why Phase 0 flagged it as consequential rather than cosmetic.

    ``min_agreeing_modules`` (HARD_GATE only) is NOT source-stated -- the
    Yanu Emmanuel model describes named pipeline *stages* (bias, then
    confirmation, then structure, then execution), not "N of M modules
    agree." Since this project's 5 modules don't map cleanly onto his
    specific 4 stages, requiring a minimum count of independently-agreeing
    modules is this project's generalization of his gate philosophy, not a
    literal implementation of it -- documented as an explicit Phase 4
    design choice.
    """

    def __init__(
        self,
        mode: AggregationMode = AggregationMode.HARD_GATE,
        min_agreeing_modules: int = 2,
    ) -> None:
        self.mode = mode
        self.min_agreeing_modules = min_agreeing_modules

    def combine(self, signals: list[ModuleSignal]) -> AggregatedSignal:
        if not signals:
            raise ValueError("combine() requires at least one module signal")

        bar_time = signals[0].bar_time
        if self.mode is AggregationMode.HARD_GATE:
            return self._hard_gate(signals, bar_time)
        return self._soft_score(signals, bar_time)

    def _hard_gate(
        self, signals: list[ModuleSignal], bar_time: datetime
    ) -> AggregatedSignal:
        active = [s for s in signals if s.bias is not Bias.NEUTRAL]
        bullish = [s for s in active if s.bias is Bias.BULLISH]
        bearish = [s for s in active if s.bias is Bias.BEARISH]

        if bullish and bearish:
            reason = (
                f"{len(bullish)} module(s) bullish "
                f"({', '.join(s.module for s in bullish)}) vs. "
                f"{len(bearish)} bearish ({', '.join(s.module for s in bearish)}) "
                f"-- surfaced as conflict, not averaged away."
            )
            return AggregatedSignal(
                bias=AggregatedBias.CONFLICT,
                confidence=0.0,
                mode=self.mode,
                reason=reason,
                bar_time=bar_time,
                module_signals=signals,
            )

        if not active:
            return AggregatedSignal(
                bias=AggregatedBias.NEUTRAL,
                confidence=0.0,
                mode=self.mode,
                reason="No module has an opinion on this bar.",
                bar_time=bar_time,
                module_signals=signals,
            )

        agreeing = bullish or bearish
        if len(agreeing) < self.min_agreeing_modules:
            names = ", ".join(s.module for s in agreeing)
            reason = (
                f"Only {len(agreeing)} module(s) agree ({names}); hard gate "
                f"requires {self.min_agreeing_modules}."
            )
            return AggregatedSignal(
                bias=AggregatedBias.NEUTRAL,
                confidence=0.0,
                mode=self.mode,
                reason=reason,
                bar_time=bar_time,
                module_signals=signals,
            )

        bias = AggregatedBias.BULLISH if bullish else AggregatedBias.BEARISH
        # An AND-gate is only as strong as its weakest link.
        confidence = min(s.confidence for s in agreeing)
        names = ", ".join(f"{s.module}({s.confidence:.2f})" for s in agreeing)
        reason = f"Hard gate: {len(agreeing)} modules unanimously {bias.value} -- {names}."
        return AggregatedSignal(
            bias=bias,
            confidence=confidence,
            mode=self.mode,
            reason=reason,
            bar_time=bar_time,
            module_signals=signals,
        )

    def _soft_score(
        self, signals: list[ModuleSignal], bar_time: datetime
    ) -> AggregatedSignal:
        net = 0.0
        for s in signals:
            if s.bias is Bias.BULLISH:
                net += s.confidence
            elif s.bias is Bias.BEARISH:
                net -= s.confidence
        average = net / len(signals)
        contributors = ", ".join(
            f"{s.module}={s.bias.value}({s.confidence:.2f})" for s in signals
        )

        if abs(average) < 0.05:
            return AggregatedSignal(
                bias=AggregatedBias.NEUTRAL,
                confidence=0.0,
                mode=self.mode,
                reason=(
                    f"Net weighted score {average:+.2f} too close to zero "
                    f"-- {contributors}."
                ),
                bar_time=bar_time,
                module_signals=signals,
            )

        bias = AggregatedBias.BULLISH if average > 0 else AggregatedBias.BEARISH
        reason = (
            f"Soft score: net weighted average {average:+.2f} across "
            f"{len(signals)} modules -- {contributors}."
        )
        return AggregatedSignal(
            bias=bias,
            confidence=abs(average),
            mode=self.mode,
            reason=reason,
            bar_time=bar_time,
            module_signals=signals,
        )
