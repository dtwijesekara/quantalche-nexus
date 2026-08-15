# Quantalche Nexus — Frontend

The Layer 8 dashboard (`docs/architecture.md`): live price chart with
entry/SL/TP overlay, plus an "Analysis Terminal" panel showing every
module's individual read alongside the combined signal — never just a
black-box final number, per the project's "decision support, not
certainty" ground rule.

Runs `hard_gate` only — the confidence-weighted `soft_score` mode blends
module disagreement into one number rather than surfacing it, so it's kept
as a backend-only option for backtest comparison, not exposed live. A
7-pair crypto/forex watchlist auto-refreshes in the background; the
"Analyze" control next to it runs the full pipeline on demand for any
other symbol (source + ticker, e.g. Binance `DOGEUSDT` or Twelve Data
`USD/JPY`) without needing to add it to the watchlist first.

## Setup

```
cd frontend
npm install
cp .env.local.example .env.local   # point at your running backend
npm run dev
```

Requires the backend (`../backend`) running — see its README for
`uvicorn quantalche.api.app:app --reload`.

## Structure

| Path | What it is |
|---|---|
| `src/app/page.tsx` | The dashboard — instrument/timeframe state, live data wiring, layout |
| `src/components/PriceChart.tsx` | Candlestick chart (`lightweight-charts`) with entry/SL/TP price lines |
| `src/components/AnalysisTerminal.tsx` | Per-module reads + combined signal + trade levels |
| `src/components/ControlBar.tsx` | Watchlist dropdown, segmented timeframe buttons, manual Analyze form |
| `src/lib/api.ts` | REST client (`/bars`, `/signals`) |
| `src/lib/useSignalStream.ts` | WebSocket hook (`/ws/signals`), auto-reconnecting |
| `src/lib/useBinanceLiveKline.ts` | Direct-to-Binance public WebSocket for sub-second last-candle ticks (crypto only — bypasses the backend entirely, display-only, never fed to the signal pipeline) |
| `src/lib/types.ts` | Mirrors `backend/src/quantalche/api/schemas.py` field-for-field |

`INSTRUMENTS` in `src/lib/types.ts` is a static, hand-picked 7-pair
watchlist for the auto-refreshing background list — not a restriction:
the backend accepts any `(source, symbol)` pair, which is what the
Analyze control exercises.

Twelve Data's free tier is rate-limited, so the forex side of the
watchlist polls conservatively (`FOREX_LIVE_POLL_MS` in `page.tsx`)
rather than streaming — crypto gets real push ticks via Binance's public
WebSocket instead.

## Manual validation

Live-tested with Playwright against a running backend + dev server: chart
renders real candles, switching instrument/timeframe updates both the
chart and the Analysis Terminal from live data (verified: `market_structure`
correctly read differently across BTC/USDT 1h vs. 4h vs. EUR/USD 4h in the
same session), the Analyze control correctly runs the full pipeline for
symbols outside the watchlist (verified: Binance `DOGEUSDT` and Twelve
Data `USD/JPY`, including switching back to the watchlist afterward),
zero browser console errors across all interactions.
