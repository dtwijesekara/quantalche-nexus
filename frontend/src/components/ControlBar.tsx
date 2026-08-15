"use client";

import { INSTRUMENTS, TIMEFRAMES, type AggregationMode, type Timeframe } from "@/lib/types";

interface ControlBarProps {
  instrumentIndex: number;
  onInstrumentChange: (index: number) => void;
  timeframe: Timeframe;
  onTimeframeChange: (timeframe: Timeframe) => void;
  mode: AggregationMode;
  onModeChange: (mode: AggregationMode) => void;
  connected: boolean;
}

export function ControlBar({
  instrumentIndex,
  onInstrumentChange,
  timeframe,
  onTimeframeChange,
  mode,
  onModeChange,
  connected,
}: ControlBarProps) {
  return (
    <div className="flex flex-wrap items-center gap-3 border-b border-slate-800 bg-slate-950 px-4 py-3">
      <div className="mr-2 flex items-center gap-2">
        <span
          className={`h-2 w-2 rounded-full ${connected ? "bg-emerald-500" : "bg-slate-600"}`}
        />
        <span className="font-semibold tracking-tight text-slate-100">
          Quantalche <span className="text-cyan-400">Nexus</span>
        </span>
      </div>

      <select
        className="rounded-md border border-slate-700 bg-slate-900 px-3 py-1.5 text-sm text-slate-200 focus:border-cyan-500 focus:outline-none"
        value={instrumentIndex}
        onChange={(e) => onInstrumentChange(Number(e.target.value))}
      >
        {INSTRUMENTS.map((inst, i) => (
          <option key={`${inst.source}:${inst.symbol}`} value={i}>
            {inst.label}
          </option>
        ))}
      </select>

      <select
        className="rounded-md border border-slate-700 bg-slate-900 px-3 py-1.5 text-sm text-slate-200 focus:border-cyan-500 focus:outline-none"
        value={timeframe}
        onChange={(e) => onTimeframeChange(e.target.value as Timeframe)}
      >
        {TIMEFRAMES.map((tf) => (
          <option key={tf} value={tf}>
            {tf}
          </option>
        ))}
      </select>

      <div className="flex rounded-md border border-slate-700 bg-slate-900 p-0.5 text-sm">
        {(["hard_gate", "soft_score"] as AggregationMode[]).map((m) => (
          <button
            key={m}
            onClick={() => onModeChange(m)}
            className={`rounded px-2.5 py-1 transition-colors ${
              mode === m
                ? "bg-cyan-600 text-white"
                : "text-slate-400 hover:text-slate-200"
            }`}
          >
            {m === "hard_gate" ? "Hard Gate" : "Soft Score"}
          </button>
        ))}
      </div>
    </div>
  );
}
