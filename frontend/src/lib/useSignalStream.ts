"use client";

import { useEffect, useState } from "react";
import { signalsWebSocketUrl } from "./api";
import type { AggregationMode, SignalResponse, Source, Timeframe } from "./types";

export function useSignalStream(
  source: Source,
  symbol: string,
  timeframe: Timeframe,
  mode: AggregationMode,
  pollSeconds = 20
) {
  const [signal, setSignal] = useState<SignalResponse | null>(null);
  const [connected, setConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setSignal(null);
    setError(null);
    let cancelled = false;
    let ws: WebSocket | null = null;
    let reconnectTimer: ReturnType<typeof setTimeout> | null = null;

    function connect() {
      if (cancelled) return;
      const url = signalsWebSocketUrl(source, symbol, timeframe, mode, pollSeconds);
      ws = new WebSocket(url);

      ws.onopen = () => setConnected(true);
      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (data && typeof data === "object" && "error" in data) {
            setError(String(data.error));
          } else {
            setError(null);
            setSignal(data as SignalResponse);
          }
        } catch {
          // ignore malformed frame
        }
      };
      ws.onclose = () => {
        setConnected(false);
        if (!cancelled) {
          reconnectTimer = setTimeout(connect, 3000);
        }
      };
      ws.onerror = () => {
        ws?.close();
      };
    }

    connect();

    return () => {
      cancelled = true;
      if (reconnectTimer) clearTimeout(reconnectTimer);
      ws?.close();
    };
  }, [source, symbol, timeframe, mode, pollSeconds]);

  return { signal, connected, error };
}
