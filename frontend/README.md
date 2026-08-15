# Quantalche Nexus — Frontend

The Layer 8 dashboard (`docs/architecture.md`): live price chart with
entry/SL/TP overlay, plus an "Analysis Terminal" panel showing every
module's individual read alongside the combined signal — never just a
black-box final number, per the project's "decision support, not
certainty" ground rule.

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
| `src/app/page.tsx` | The dashboard — instrument/timeframe/mode controls, chart, terminal |
| `src/components/PriceChart.tsx` | Candlestick chart (`lightweight-charts`) with entry/SL/TP price lines |
| `src/components/AnalysisTerminal.tsx` | Per-module reads + combined signal + trade levels |
| `src/components/ControlBar.tsx` | Instrument/timeframe/aggregation-mode selectors |
| `src/lib/api.ts` | REST client (`/bars`, `/signals`) |
| `src/lib/useSignalStream.ts` | WebSocket hook (`/ws/signals`), auto-reconnecting |
| `src/lib/types.ts` | Mirrors `backend/src/quantalche/api/schemas.py` field-for-field |

`INSTRUMENTS` in `src/lib/types.ts` is a static, hand-picked list — neither
backend data source exposes a "list all instruments" endpoint yet.

## Manual validation

Live-tested with Playwright against a running backend + dev server: chart
renders real candles, switching instrument/timeframe updates both the
chart and the Analysis Terminal from live data (verified: `market_structure`
correctly read differently across BTC/USDT 1h vs. 4h vs. EUR/USD 4h in the
same session), zero browser console errors across all interactions.
