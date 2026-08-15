"use client";

import type {
  AggregatedBias,
  Bias,
  ModuleSignal,
  SignalResponse,
  SignalState,
} from "@/lib/types";

const BIAS_STYLES: Record<AggregatedBias, { text: string; bg: string; ring: string }> = {
  bullish: { text: "text-emerald-400", bg: "bg-emerald-500/10", ring: "ring-emerald-500/30" },
  bearish: { text: "text-red-400", bg: "bg-red-500/10", ring: "ring-red-500/30" },
  neutral: { text: "text-slate-400", bg: "bg-slate-500/10", ring: "ring-slate-500/30" },
  conflict: { text: "text-amber-400", bg: "bg-amber-500/10", ring: "ring-amber-500/30" },
};

const STATE_LABELS: Record<SignalState, string> = {
  idle: "Idle",
  pending: "Pending Limit Order",
  signal_active: "Position Active",
  stopped_out: "Stopped Out",
  tp_hit: "Take Profit Hit",
  expired: "Order Expired",
};

function BiasBadge({ bias }: { bias: AggregatedBias | Bias }) {
  const style = BIAS_STYLES[bias];
  return (
    <span
      className={`inline-flex items-center rounded-md px-2 py-0.5 text-xs font-semibold uppercase tracking-wide ring-1 ${style.text} ${style.bg} ${style.ring}`}
    >
      {bias}
    </span>
  );
}

function ConfidenceBar({ value }: { value: number }) {
  return (
    <div className="h-1.5 w-full overflow-hidden rounded-full bg-slate-800">
      <div
        className="h-full rounded-full bg-cyan-500"
        style={{ width: `${Math.round(value * 100)}%` }}
      />
    </div>
  );
}

function ModuleRow({ signal }: { signal: ModuleSignal }) {
  return (
    <div className="border-b border-slate-800/60 py-3 last:border-0">
      <div className="flex items-center justify-between gap-2">
        <span className="font-mono text-sm text-slate-200">{signal.module}</span>
        <BiasBadge bias={signal.bias} />
      </div>
      <div className="mt-2">
        <ConfidenceBar value={signal.confidence} />
      </div>
      <p className="mt-2 text-xs leading-relaxed text-slate-500">{signal.reason}</p>
    </div>
  );
}

function TradeLevel({
  label,
  price,
  colorClass,
  icon,
}: {
  label: string;
  price: number;
  colorClass: string;
  icon: string;
}) {
  return (
    <div className={`flex items-center gap-3 rounded-lg border-l-4 bg-slate-900/60 px-4 py-3 ${colorClass}`}>
      <span className="text-lg">{icon}</span>
      <div>
        <div className="text-[10px] font-semibold uppercase tracking-widest text-slate-400">
          {label}
        </div>
        <div className="font-mono text-lg text-slate-100">{price.toFixed(5)}</div>
      </div>
    </div>
  );
}

export function AnalysisTerminal({ signal }: { signal: SignalResponse | null }) {
  if (!signal) {
    return (
      <div className="flex h-full items-center justify-center text-sm text-slate-500">
        Connecting to signal stream...
      </div>
    );
  }

  const trade = signal.active_trade ?? signal.pending_trade;
  const agg = signal.aggregated_signal;

  return (
    <div className="flex h-full flex-col overflow-y-auto p-4">
      <div className="mb-4 flex items-center justify-between">
        <div>
          <div className="text-xs uppercase tracking-widest text-slate-500">
            Analysis Terminal
          </div>
          <div className="font-mono text-sm text-slate-300">
            {signal.symbol} &middot; {signal.timeframe} &middot; {signal.source}
          </div>
        </div>
        <span className="rounded-md bg-slate-800 px-2 py-1 text-xs font-medium text-slate-300">
          {STATE_LABELS[signal.state]}
        </span>
      </div>

      <div className="mb-4 rounded-lg border border-slate-800 bg-slate-900/40 p-4">
        <div className="flex items-center justify-between">
          <span className="text-xs uppercase tracking-widest text-slate-500">
            Combined Signal ({agg.mode === "hard_gate" ? "Hard Gate" : "Soft Score"})
          </span>
          <BiasBadge bias={agg.bias} />
        </div>
        <div className="mt-2">
          <ConfidenceBar value={agg.confidence} />
        </div>
        <p className="mt-2 text-xs leading-relaxed text-slate-400">{agg.reason}</p>
      </div>

      {trade && (
        <div className="mb-4 space-y-2">
          <TradeLevel
            label="Entry Zone"
            price={trade.entry}
            colorClass="border-amber-500"
            icon="\u{1F3AF}"
          />
          <TradeLevel
            label="Stop Loss"
            price={trade.stop_loss}
            colorClass="border-red-500"
            icon="❌"
          />
          <TradeLevel
            label="Take Profit"
            price={trade.take_profit}
            colorClass="border-emerald-500"
            icon="✅"
          />
          <div className="flex items-center justify-between px-1 text-xs text-slate-500">
            <span>{trade.direction === "long" ? "LONG" : "SHORT"}</span>
            <span>RR {trade.risk_reward.toFixed(2)}</span>
            <span>Confidence {(trade.confidence * 100).toFixed(0)}%</span>
          </div>
        </div>
      )}

      <div className="mb-2 text-xs uppercase tracking-widest text-slate-500">
        Per-Module Reads
      </div>
      <div className="flex-1">
        {agg.module_signals.map((moduleSignal) => (
          <ModuleRow key={moduleSignal.module} signal={moduleSignal} />
        ))}
      </div>
    </div>
  );
}
