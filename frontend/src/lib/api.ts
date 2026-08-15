import type {
  AggregationMode,
  OHLCBar,
  SignalResponse,
  Source,
  Timeframe,
} from "./types";

const API_BASE =
  process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "") ?? "http://127.0.0.1:8000";

class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.status = status;
  }
}

async function getJson<T>(path: string, params: Record<string, string | number>): Promise<T> {
  const search = new URLSearchParams(
    Object.fromEntries(Object.entries(params).map(([k, v]) => [k, String(v)]))
  );
  const res = await fetch(`${API_BASE}${path}?${search.toString()}`);
  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: res.statusText }));
    throw new ApiError(body.detail ?? res.statusText, res.status);
  }
  return res.json() as Promise<T>;
}

export function fetchBars(
  source: Source,
  symbol: string,
  timeframe: Timeframe,
  limit = 300
): Promise<OHLCBar[]> {
  return getJson<OHLCBar[]>("/bars", { source, symbol, timeframe, limit });
}

export function fetchSignal(
  source: Source,
  symbol: string,
  timeframe: Timeframe,
  mode: AggregationMode,
  limit = 300
): Promise<SignalResponse> {
  return getJson<SignalResponse>("/signals", { source, symbol, timeframe, mode, limit });
}

export function signalsWebSocketUrl(
  source: Source,
  symbol: string,
  timeframe: Timeframe,
  mode: AggregationMode,
  pollSeconds = 30
): string {
  const wsBase = API_BASE.replace(/^http/, "ws");
  const search = new URLSearchParams({
    source,
    symbol,
    timeframe,
    mode,
    poll_seconds: String(pollSeconds),
  });
  return `${wsBase}/ws/signals?${search.toString()}`;
}

export { ApiError };
