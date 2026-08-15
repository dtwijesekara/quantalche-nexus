from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel

from ..ingestion.models import OHLCBar
from .base import AnalysisModule
from .models import Bias, ModuleSignal
from .swings import SwingKind, find_swings


class ZoneType(str, Enum):
    SUPPORT = "support"
    RESISTANCE = "resistance"


class ZoneState(str, Enum):
    FRESH = "fresh"
    UNFRESH = "unfresh"


class ZoneSource(str, Enum):
    GAP = "gap"
    CLASSIC = "classic"


class ZoneEventType(str, Enum):
    TOUCHED = "touched"
    FLIPPED = "flipped"


class ZoneEvent(BaseModel):
    event: ZoneEventType
    at: datetime
    bar_close: float


class SNRZone(BaseModel):
    """An SNR zone (either an open/close "gap" zone or a Classic V/A
    swing-rejection zone) with its fresh/unfresh/flip history.

    See docs/rule-mapping.md for exact source citations.
    """

    zone_type: ZoneType
    source: ZoneSource
    top: float
    bottom: float
    formed_at: datetime
    state: ZoneState = ZoneState.FRESH
    events: list[ZoneEvent] = []


class SNRZoneModule(AnalysisModule):
    """Layer 2 module: open/close ("gap") SNR zones with a
    fresh -> unfresh -> flip lifecycle.

    Rule sources (docs/phase0-knowledge-extraction.md S2.3, S7 item 5;
    full citations in docs/rule-mapping.md):
      - Zone formation: a gap between one bar's close and the next bar's
        open (the "OCL"/"GAP SNR" concept -- docs 09, 16, 20). Wicks are
        explicitly ignored per the corpus-wide "ignore the wicks" rule.
      - Fresh -> unfresh: a bar's wick range touches the zone without a
        full-body close through it (doc 20 S14).
      - Flip (RBS/SBR): a bar's *close* breaks fully through the zone --
        the zone's role flips (support<->resistance) and resets to fresh in
        its new role (doc 20 S15; universal RBS/SBR mechanic).
      - Classic V/A: a fast wick-rejection at a swing extreme -- "V" at a
        swing low (bullish), "A" at a swing high (bearish), per docs 04,
        05, 06, 08/11, 13, 15's consistent description: "fast rejection
        (bullish candle right after touch) -> buy bias" (doc 08 S7).
        Formalized here as: the bar immediately after a confirmed swing
        low/high closes back beyond the swing bar's own high/low with a
        same-direction body -- a checkable proxy for "fast rejection"
        that wasn't available when this module was first built (Phase 2,
        before swings.py existed for market_structure.py). Represented as
        a zero-width zone anchored at the swing price -- reuses the same
        fresh/unfresh/flip lifecycle and touch logic as gap zones, no
        separate code path needed.

    Minimum gap size (``min_gap_ratio``) is a second addition NOT stated by
    any of the 22 documents. Validating this module against live Binance
    and Twelve Data 1h bars showed the raw "any gap" rule producing zones a
    single cent wide on a $63k BTC bar -- tick noise, not a real support/
    resistance level.

    Checking the actual gap-size distribution (as a fraction of average bar
    range) on live data showed something more structural than a threshold
    problem: BTCUSDT gaps sit at 0.01-0.07% of average range even at the
    99th percentile -- Binance is a continuous 24/7 market, so a candle's
    close and the next candle's open are almost always the same price.
    There is no meaningful gap to find there at any threshold. EUR/USD has
    a real distribution (90th percentile close-to-9% of average range),
    consistent with forex's session-driven micro-gaps and with the source
    documents describing this concept as "often a Hidden Zone on HTF"
    (docs 09/16/20) -- i.e. a forex-appropriate concept, not one that
    transfers to continuous crypto markets. The default threshold below is
    calibrated off the EUR/USD distribution (roughly its 90th percentile);
    on Binance-style continuous instruments this module will correctly
    detect few or no zones rather than fabricating noise -- that is
    expected behavior, not a bug. A different, swing-based zone-formation
    rule would be needed for continuous markets; deliberately not force-fit
    into this module (see the Classic V/A note above).
    """

    name = "snr_zone"

    def __init__(self, min_gap_ratio: float = 0.08, swing_strength: int = 2) -> None:
        self.min_gap_ratio = min_gap_ratio
        self.swing_strength = swing_strength

    def _detect_gap_zones(self, bars: list[OHLCBar]) -> list[SNRZone]:
        avg_range = sum(b.high - b.low for b in bars) / len(bars)
        min_gap = avg_range * self.min_gap_ratio

        zones: list[SNRZone] = []
        for i in range(len(bars) - 1):
            prev, nxt = bars[i], bars[i + 1]
            gap = nxt.open - prev.close
            if gap >= min_gap:
                zones.append(
                    SNRZone(
                        zone_type=ZoneType.SUPPORT,
                        source=ZoneSource.GAP,
                        top=nxt.open,
                        bottom=prev.close,
                        formed_at=nxt.open_time,
                    )
                )
            elif -gap >= min_gap:
                zones.append(
                    SNRZone(
                        zone_type=ZoneType.RESISTANCE,
                        source=ZoneSource.GAP,
                        top=prev.close,
                        bottom=nxt.open,
                        formed_at=nxt.open_time,
                    )
                )
        return zones

    def _detect_classic_zones(self, bars: list[OHLCBar]) -> list[SNRZone]:
        swings = find_swings(bars, self.swing_strength)
        zones: list[SNRZone] = []
        for sp in swings:
            next_idx = sp.index + 1
            if next_idx >= len(bars):
                continue
            nxt = bars[next_idx]

            if sp.kind is SwingKind.LOW:
                fast_rejection = nxt.close > nxt.open and nxt.close > sp.price
                zone_type = ZoneType.SUPPORT
            else:
                fast_rejection = nxt.close < nxt.open and nxt.close < sp.price
                zone_type = ZoneType.RESISTANCE

            if fast_rejection:
                zones.append(
                    SNRZone(
                        zone_type=zone_type,
                        source=ZoneSource.CLASSIC,
                        top=sp.price,
                        bottom=sp.price,
                        formed_at=nxt.open_time,
                    )
                )
        return zones

    def _detect_zones(self, bars: list[OHLCBar]) -> list[SNRZone]:
        if len(bars) < 2:
            return []

        zones = self._detect_gap_zones(bars) + self._detect_classic_zones(bars)

        for zone in zones:
            for bar in bars:
                if bar.open_time <= zone.formed_at:
                    continue
                wick_touches = bar.low <= zone.top and bar.high >= zone.bottom
                if not wick_touches:
                    continue

                broke_through = (
                    zone.zone_type is ZoneType.SUPPORT and bar.close < zone.bottom
                ) or (
                    zone.zone_type is ZoneType.RESISTANCE and bar.close > zone.top
                )
                if broke_through:
                    zone.zone_type = (
                        ZoneType.RESISTANCE
                        if zone.zone_type is ZoneType.SUPPORT
                        else ZoneType.SUPPORT
                    )
                    zone.state = ZoneState.FRESH
                    zone.events.append(
                        ZoneEvent(
                            event=ZoneEventType.FLIPPED,
                            at=bar.open_time,
                            bar_close=bar.close,
                        )
                    )
                elif zone.state is ZoneState.FRESH:
                    zone.state = ZoneState.UNFRESH
                    zone.events.append(
                        ZoneEvent(
                            event=ZoneEventType.TOUCHED,
                            at=bar.open_time,
                            bar_close=bar.close,
                        )
                    )
        return zones

    def evaluate(self, bars: list[OHLCBar]) -> ModuleSignal:
        if len(bars) < 2:
            return ModuleSignal(
                module=self.name,
                bias=Bias.NEUTRAL,
                confidence=0.0,
                reason="Not enough closed bars to detect a zone.",
                bar_time=bars[-1].open_time if bars else datetime.now(timezone.utc),
            )

        zones = self._detect_zones(bars)
        last = bars[-1]

        # A zone can't react to the very bar that created it.
        candidates = [z for z in zones if z.formed_at < last.open_time]
        reacting = [
            z for z in candidates if last.low <= z.top and last.high >= z.bottom
        ]
        if not reacting:
            return ModuleSignal(
                module=self.name,
                bias=Bias.NEUTRAL,
                confidence=0.0,
                reason="No active zone interaction on the latest closed bar.",
                bar_time=last.open_time,
            )

        zone = max(reacting, key=lambda z: z.formed_at)
        bullish_body = last.close > last.open
        bearish_body = last.close < last.open

        level: float | None = None
        if (
            zone.zone_type is ZoneType.SUPPORT
            and bullish_body
            and last.close >= zone.bottom
        ):
            bias = Bias.BULLISH
            level = zone.bottom
            zone_label = "Classic V" if zone.source is ZoneSource.CLASSIC else "gap"
            reason = (
                f"Bullish rejection off a {zone.state.value} {zone_label} support "
                f"zone [{zone.bottom:.5f}, {zone.top:.5f}]."
            )
        elif (
            zone.zone_type is ZoneType.RESISTANCE
            and bearish_body
            and last.close <= zone.top
        ):
            bias = Bias.BEARISH
            level = zone.top
            zone_label = "Classic A" if zone.source is ZoneSource.CLASSIC else "gap"
            reason = (
                f"Bearish rejection off a {zone.state.value} {zone_label} "
                f"resistance zone [{zone.bottom:.5f}, {zone.top:.5f}]."
            )
        else:
            bias = Bias.NEUTRAL
            reason = (
                f"Price inside a {zone.zone_type.value} zone but no clear "
                f"rejection on this bar."
            )

        confidence = 0.0
        if bias is not Bias.NEUTRAL:
            confidence = {ZoneState.FRESH: 0.75, ZoneState.UNFRESH: 0.4}[zone.state]

        return ModuleSignal(
            module=self.name,
            bias=bias,
            confidence=confidence,
            reason=reason,
            bar_time=last.open_time,
            level=level,
        )
