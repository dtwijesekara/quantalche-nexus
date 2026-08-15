// Mirrors backend/src/quantalche/api/schemas.py and the models it composes.
// Keep field names/casing identical to the Pydantic models -- these are
// deserialized directly from FastAPI's JSON responses, no field mapping.

export type Timeframe = "1m" | "5m" | "15m" | "30m" | "1h" | "4h" | "1d";

export type Source = "binance" | "twelvedata";

export type AggregationMode = "hard_gate" | "soft_score";

export type Bias = "bullish" | "bearish" | "neutral";

export type AggregatedBias = "bullish" | "bearish" | "neutral" | "conflict";

export type SignalState =
  | "idle"
  | "pending"
  | "signal_active"
  | "stopped_out"
  | "tp_hit"
  | "expired";

export type TradeDirection = "long" | "short";

export interface OHLCBar {
  symbol: string;
  timeframe: Timeframe;
  open_time: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
  source: string;
}

export interface ModuleSignal {
  module: string;
  bias: Bias;
  confidence: number;
  reason: string;
  bar_time: string;
  level: number | null;
}

export interface AggregatedSignal {
  bias: AggregatedBias;
  confidence: number;
  mode: AggregationMode;
  reason: string;
  bar_time: string;
  module_signals: ModuleSignal[];
}

export interface TradeSignal {
  direction: TradeDirection;
  entry: number;
  stop_loss: number;
  take_profit: number;
  risk_reward: number;
  confidence: number;
  bar_time: string;
  aggregated_signal: AggregatedSignal;
  reason: string;
}

export interface SignalResponse {
  source: Source;
  symbol: string;
  timeframe: Timeframe;
  mode: AggregationMode;
  bar_time: string;
  state: SignalState;
  aggregated_signal: AggregatedSignal;
  pending_trade: TradeSignal | null;
  active_trade: TradeSignal | null;
}

export interface InstrumentOption {
  source: Source;
  symbol: string;
  label: string;
}

// A reasonable, hand-picked starter list -- neither backend exposes a
// "list all instruments" endpoint yet, so this is a static convenience
// list, not a source-derived one.
export const INSTRUMENTS: InstrumentOption[] = [
  { source: "binance", symbol: "BTCUSDT", label: "BTC/USDT" },
  { source: "binance", symbol: "ETHUSDT", label: "ETH/USDT" },
  { source: "binance", symbol: "XRPUSDT", label: "XRP/USDT" },
  { source: "binance", symbol: "SOLUSDT", label: "SOL/USDT" },
  { source: "twelvedata", symbol: "EUR/USD", label: "EUR/USD" },
  { source: "twelvedata", symbol: "GBP/USD", label: "GBP/USD" },
  { source: "twelvedata", symbol: "XAU/USD", label: "XAU/USD (Gold)" },
];

export const TIMEFRAMES: Timeframe[] = ["15m", "30m", "1h", "4h", "1d"];
