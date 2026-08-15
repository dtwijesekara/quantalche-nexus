# Quantalche Nexus — Backend

The signal engine described in `../docs/architecture.md`. Every rule this
code implements cites its source document/section in
`../docs/rule-mapping.md` — that file is the ground-truth cross-reference,
this README is just setup/usage.

## Setup

```
cd backend
python -m venv .venv
.venv\Scripts\activate      # Windows
pip install -e .
```

Copy `.env.example` to `.env` and add your Twelve Data API key (free tier:
https://twelvedata.com/). Binance's public market-data endpoints need no key.

## Layers implemented so far

| Layer | Package | What it is |
|---|---|---|
| 1 — Data ingestion | `quantalche.ingestion` | Binance (crypto) + Twelve Data (forex) OHLC clients |
| 2 — Analysis modules | `quantalche.analysis` | 5 independent modules: `snr_zone`, `market_structure`, `liquidity_sweep`, `trendline_confluence`, `qm_pattern` |
| 3 — Aggregation | `quantalche.aggregation` | Combines module signals — `hard_gate` (default) or `soft_score` mode |
| 5/6 — Confirmation + lifecycle | `quantalche.execution` | Entry/SL/TP calculation, `IDLE → PENDING → SIGNAL_ACTIVE → STOPPED_OUT \| TP_HIT \| EXPIRED → IDLE` state machine |
| 7 — Backtesting | `quantalche.backtest` | Bar-by-bar replay, walk-forward segmentation, per-module accuracy reporting |
| 8 — API | `quantalche.api` | FastAPI: REST (`/bars`, `/signals`) + WebSocket (`/ws/signals`) |
| 9 — Alerting | `quantalche.alerting` | Fires on signal state transitions (new/filled/TP/SL/expired) via webhook, Discord, and/or Telegram |

## Running the API

```
python -m uvicorn quantalche.api.app:app --reload --port 8000
```

Then, e.g.:

```
curl "http://127.0.0.1:8000/signals?source=binance&symbol=BTCUSDT&timeframe=1h"
curl "http://127.0.0.1:8000/signals?source=twelvedata&symbol=EUR/USD&timeframe=1h&mode=soft_score"
```

Interactive docs at `http://127.0.0.1:8000/docs`. WebSocket:
`ws://127.0.0.1:8000/ws/signals?source=binance&symbol=BTCUSDT&timeframe=1h`.

State is held server-side per `(source, symbol, timeframe)` for the life of
the process — see `quantalche/api/state.py` for why this can't be
per-request (architecture.md Layer 6's "one signal per symbol+timeframe").

## Alerting

Set any of `ALERT_WEBHOOK_URL` / `DISCORD_WEBHOOK_URL` /
(`TELEGRAM_BOT_TOKEN` + `TELEGRAM_CHAT_ID`) in `.env` to receive a message
whenever a signal transitions state (new signal, filled, take-profit hit,
stopped out, or an unfilled order expiring). None set means no alerts, not
an error. Webhook and Discord senders are verified against a local mock
server (message formatting + delivery, exactly-once-per-transition);
Telegram is implemented directly from the Bot API spec but has not been
exercised against a real bot/chat — this project has no Telegram
credentials to test with. See `quantalche/alerting/senders.py`.

## Manual validation scripts

Each of these is the validation step called for by the relevant phase in
`docs/architecture.md` — a manual spot-check against real data, not an
automated test suite:

| Script | Validates |
|---|---|
| `scripts/fetch_sample.py` | Phase 1 — raw OHLC bars against a real chart |
| `scripts/validate_snr_zone.py` | SNR Zone module |
| `scripts/validate_market_structure.py` | Market Structure (BOS/CHoCH) module |
| `scripts/validate_liquidity_sweep.py` | Liquidity/Sweep module |
| `scripts/validate_trendline_confluence.py` | Trendline Confluence module (both variants) |
| `scripts/validate_qm_pattern.py` | QM (Quasimodo) pattern module |
| `scripts/run_pipeline.py` | Phase 4 — full aggregation, single snapshot + history replay |
| `scripts/run_signal_lifecycle.py` | Phase 5 — confirmation + state machine, full lifecycle replay |
| `scripts/run_backtest.py` | Phase 6 — backtest/walk-forward report + leakage spot-check |

## Non-repainting

Every data client drops the current, still-forming bar before returning
results — only fully closed bars are ever handed back, per
`docs/architecture.md` ground rule #2. Every module built on top of that
data preserves the same guarantee (e.g. swing-point confirmation lags in
`analysis/swings.py`).
