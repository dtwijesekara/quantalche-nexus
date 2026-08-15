"use client";

import { useEffect, useState } from "react";
import type { Timeframe } from "./types";

export interface LiveCandle {
  time: number; // unix seconds
  open: number;
  high: number;
  low: number;
  close: number;
}

/**
 * Connects directly from the browser to Binance's public kline WebSocket
 * stream (no API key needed, no backend involved) for genuinely real-time
 * price updates on the currently-forming candle -- TradingView-style live
 * movement, which polling can't match.
 *
 * Deliberately bypasses the backend entirely: this is display-only data
 * (the chart's live candle), never fed into the signal pipeline, so there
 * is no non-repainting concern here and no reason to route it through
 * quantalche's own rate-limited/cached bars endpoint. Only usable for
 * Binance (crypto) -- Twelve Data's free tier has no equivalent public,
 * unauthenticated live stream, so forex uses a slower REST poll instead
 * (see page.tsx's forming-bar interval).
 *
 * Binance's kline interval strings happen to match this project's
 * Timeframe values exactly (1m/5m/15m/30m/1h/4h/1d), same coincidence
 * already noted in backend/binance_client.py.
 */
export function useBinanceLiveKline(
  enabled: boolean,
  symbol: string,
  timeframe: Timeframe
): LiveCandle | null {
  const [candle, setCandle] = useState<LiveCandle | null>(null);

  useEffect(() => {
    if (!enabled) return;

    let ws: WebSocket | null = null;
    let cancelled = false;
    let reconnectTimer: ReturnType<typeof setTimeout> | null = null;

    function connect() {
      if (cancelled) return;
      const stream = `${symbol.toLowerCase()}@kline_${timeframe}`;
      ws = new WebSocket(`wss://stream.binance.com:9443/ws/${stream}`);

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          const k = data.k;
          if (!k) return;
          setCandle({
            time: Math.floor(k.t / 1000),
            open: parseFloat(k.o),
            high: parseFloat(k.h),
            low: parseFloat(k.l),
            close: parseFloat(k.c),
          });
        } catch {
          // ignore malformed frame
        }
      };
      ws.onclose = () => {
        if (!cancelled) reconnectTimer = setTimeout(connect, 3000);
      };
      ws.onerror = () => ws?.close();
    }

    connect();
    return () => {
      cancelled = true;
      if (reconnectTimer) clearTimeout(reconnectTimer);
      ws?.close();
      // Runs before the next effect (enabled/symbol/timeframe change)
      // starts -- clears the previous pair's stale live price rather than
      // leaving it displayed while the new stream connects. The consumer
      // (page.tsx) also gates this behind isCrypto independently, so a
      // stale value briefly surviving the !enabled early-return above
      // never actually reaches the chart either way.
      setCandle(null);
    };
  }, [enabled, symbol, timeframe]);

  return candle;
}
