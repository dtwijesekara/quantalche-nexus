"use client";

import { useEffect, useState } from "react";
import { fetchBars } from "@/lib/api";
import { useSignalStream } from "@/lib/useSignalStream";
import { INSTRUMENTS, type AggregationMode, type OHLCBar, type Timeframe } from "@/lib/types";
import { ControlBar } from "@/components/ControlBar";
import { PriceChart } from "@/components/PriceChart";
import { AnalysisTerminal } from "@/components/AnalysisTerminal";

export default function Home() {
  const [instrumentIndex, setInstrumentIndex] = useState(0);
  const [timeframe, setTimeframe] = useState<Timeframe>("1h");
  const [mode, setMode] = useState<AggregationMode>("hard_gate");
  const [bars, setBars] = useState<OHLCBar[]>([]);

  const instrument = INSTRUMENTS[instrumentIndex];
  const { signal, connected, error } = useSignalStream(
    instrument.source,
    instrument.symbol,
    timeframe,
    mode
  );

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

  const trade = signal?.active_trade ?? signal?.pending_trade ?? null;

  return (
    <div className="flex h-screen flex-col bg-[#0a0e17] text-slate-200">
      <ControlBar
        instrumentIndex={instrumentIndex}
        onInstrumentChange={setInstrumentIndex}
        timeframe={timeframe}
        onTimeframeChange={setTimeframe}
        mode={mode}
        onModeChange={setMode}
        connected={connected}
      />
      {error && (
        <div className="bg-red-500/10 px-4 py-2 text-xs text-red-400">{error}</div>
      )}
      <div className="flex min-h-0 flex-1">
        <div className="min-w-0 flex-1 border-r border-slate-800 p-2">
          <PriceChart bars={bars} trade={trade} />
        </div>
        <div className="w-[380px] shrink-0 border-l border-slate-800 bg-slate-950/60">
          <AnalysisTerminal signal={signal} />
        </div>
      </div>
    </div>
  );
}
