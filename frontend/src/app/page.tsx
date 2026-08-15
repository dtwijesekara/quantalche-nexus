"use client";

import { useEffect, useState } from "react";
import { fetchBars } from "@/lib/api";
import { useSignalStream } from "@/lib/useSignalStream";
import { useBinanceLiveKline } from "@/lib/useBinanceLiveKline";
import { INSTRUMENTS, type InstrumentOption, type OHLCBar, type Timeframe } from "@/lib/types";
import { ControlBar } from "@/components/ControlBar";
import { PriceChart } from "@/components/PriceChart";
import { AnalysisTerminal } from "@/components/AnalysisTerminal";

// How often the forex chart re-fetches with the still-forming bar included,
// for a "live-ish" candle without a real push stream (Twelve Data's free
// tier has no public unauthenticated WebSocket the way Binance does).
// Deliberately conservative -- not source-stated, just a sustainable
// interval against the free-tier rate limit; the backend's 20s cache
// absorbs bursts from other concurrent requests on top of this.
const FOREX_LIVE_POLL_MS = 20_000;

export default function Home() {
  const [instrument, setInstrument] = useState<InstrumentOption>(INSTRUMENTS[0]);
  const [timeframe, setTimeframe] = useState<Timeframe>("1h");
  const [bars, setBars] = useState<OHLCBar[]>([]);

  const isCrypto = instrument.source === "binance";
  // Live signals only run hard-gate: soft-score's confidence-weighted
  // average blends module disagreement into one number rather than
  // surfacing it, which doesn't fit a "trade what's live" dashboard --
  // it stays available server-side for backtest comparison
  // (full_backtest_report.py), just not exposed as a live-trading option.
  const { signal, connected, error } = useSignalStream(
    instrument.source,
    instrument.symbol,
    timeframe,
    "hard_gate"
  );

  // Real-time last-candle ticks for crypto, straight from Binance's public
  // WebSocket -- see useBinanceLiveKline for why this bypasses the backend
  // entirely. Only ever non-null when isCrypto is true.
  const liveCandle = useBinanceLiveKline(isCrypto, instrument.symbol, timeframe);

  useEffect(() => {
    let cancelled = false;
    fetchBars(instrument.source, instrument.symbol, timeframe, 300)
      .then((data) => {
        if (!cancelled) setBars(data);
      })
      .catch(() => {
        if (!cancelled) setBars([]);
      });
    return () => {
      cancelled = true;
    };
  }, [instrument.source, instrument.symbol, timeframe]);

  // Refresh the chart whenever a new signal tick reports a new bar.
  useEffect(() => {
    if (!signal) return;
    fetchBars(instrument.source, instrument.symbol, timeframe, 300).then(setBars).catch(() => {});
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [signal?.bar_time]);

  // Forex has no live push stream (unlike crypto's Binance WebSocket
  // above) -- approximate "live" with a conservative REST poll that
  // includes the still-forming bar, display-only (never fed to the signal
  // pipeline, which always fetches with include_forming's default False).
  useEffect(() => {
    if (isCrypto) return;
    const interval = setInterval(() => {
      fetchBars(instrument.source, instrument.symbol, timeframe, 300, true)
        .then(setBars)
        .catch(() => {});
    }, FOREX_LIVE_POLL_MS);
    return () => clearInterval(interval);
  }, [isCrypto, instrument.source, instrument.symbol, timeframe]);

  const trade = signal?.active_trade ?? signal?.pending_trade ?? null;

  return (
    <div className="flex h-screen flex-col bg-[#0a0e17] text-slate-200">
      <ControlBar
        instrument={instrument}
        onInstrumentChange={setInstrument}
        timeframe={timeframe}
        onTimeframeChange={setTimeframe}
        connected={connected}
      />
      {error && (
        <div className="bg-red-500/10 px-4 py-2 text-xs text-red-400">{error}</div>
      )}
      <div className="flex min-h-0 flex-1">
        <div className="min-w-0 flex-1 border-r border-slate-800 p-2">
          <PriceChart bars={bars} trade={trade} liveCandle={isCrypto ? liveCandle : null} />
        </div>
        <div className="w-[380px] shrink-0 border-l border-slate-800 bg-slate-950/60">
          <AnalysisTerminal signal={signal} />
        </div>
      </div>
    </div>
  );
}
