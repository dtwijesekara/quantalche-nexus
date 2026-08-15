"use client";

import { useEffect, useRef } from "react";
import {
  CandlestickSeries,
  ColorType,
  LineStyle,
  createChart,
  type IChartApi,
  type ISeriesApi,
  type IPriceLine,
  type UTCTimestamp,
} from "lightweight-charts";
import type { OHLCBar, TradeSignal } from "@/lib/types";
import type { LiveCandle } from "@/lib/useBinanceLiveKline";

interface PriceChartProps {
  bars: OHLCBar[];
  trade: TradeSignal | null;
  /** Live-ticking current candle (crypto only, via Binance's WebSocket
   * stream -- see useBinanceLiveKline). Null/undefined for forex, where
   * "live" instead comes from bars itself being refetched with
   * include_forming=true on an interval (see page.tsx). */
  liveCandle?: LiveCandle | null;
}

export function PriceChart({ bars, trade, liveCandle }: PriceChartProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const seriesRef = useRef<ISeriesApi<"Candlestick"> | null>(null);
  const priceLinesRef = useRef<IPriceLine[]>([]);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    const chart = createChart(container, {
      layout: {
        background: { type: ColorType.Solid, color: "#0a0e17" },
        textColor: "#94a3b8",
        fontSize: 12,
      },
      grid: {
        vertLines: { color: "#131b2c" },
        horzLines: { color: "#131b2c" },
      },
      rightPriceScale: { borderColor: "#1e293b" },
      timeScale: { borderColor: "#1e293b", timeVisible: true },
      crosshair: { mode: 0 },
      width: container.clientWidth,
      height: container.clientHeight,
    });

    const series = chart.addSeries(CandlestickSeries, {
      upColor: "#10b981",
      downColor: "#ef4444",
      borderVisible: false,
      wickUpColor: "#10b981",
      wickDownColor: "#ef4444",
    });

    chartRef.current = chart;
    seriesRef.current = series;

    const resizeObserver = new ResizeObserver((entries) => {
      const entry = entries[0];
      if (!entry) return;
      chart.applyOptions({
        width: entry.contentRect.width,
        height: entry.contentRect.height,
      });
    });
    resizeObserver.observe(container);

    return () => {
      resizeObserver.disconnect();
      chart.remove();
      chartRef.current = null;
      seriesRef.current = null;
    };
  }, []);

  useEffect(() => {
    const series = seriesRef.current;
    if (!series || bars.length === 0) return;
    series.setData(
      bars.map((bar) => ({
        time: (Date.parse(bar.open_time) / 1000) as UTCTimestamp,
        open: bar.open,
        high: bar.high,
        low: bar.low,
        close: bar.close,
      }))
    );
    chartRef.current?.timeScale().fitContent();
  }, [bars]);

  useEffect(() => {
    const series = seriesRef.current;
    if (!series || !liveCandle) return;
    // Live-updates the currently-forming candle in place (or appends it as
    // a new one once its timestamp moves past the last closed bar) --
    // lightweight-charts' update() is built for exactly this, no need to
    // re-run setData() on every tick.
    series.update({
      time: liveCandle.time as UTCTimestamp,
      open: liveCandle.open,
      high: liveCandle.high,
      low: liveCandle.low,
      close: liveCandle.close,
    });
  }, [liveCandle]);

  useEffect(() => {
    const series = seriesRef.current;
    if (!series) return;

    for (const line of priceLinesRef.current) {
      series.removePriceLine(line);
    }
    priceLinesRef.current = [];

    if (!trade) return;

    priceLinesRef.current.push(
      series.createPriceLine({
        price: trade.entry,
        color: "#f59e0b",
        lineWidth: 2,
        lineStyle: LineStyle.Dotted,
        axisLabelVisible: true,
        title: "ENTRY",
      }),
      series.createPriceLine({
        price: trade.stop_loss,
        color: "#ef4444",
        lineWidth: 2,
        lineStyle: LineStyle.Solid,
        axisLabelVisible: true,
        title: "SL",
      }),
      series.createPriceLine({
        price: trade.take_profit,
        color: "#10b981",
        lineWidth: 2,
        lineStyle: LineStyle.Solid,
        axisLabelVisible: true,
        title: "TP",
      })
    );
  }, [trade]);

  return <div ref={containerRef} className="h-full w-full" />;
}
