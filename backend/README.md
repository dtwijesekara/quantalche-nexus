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
| 2 — Analysis modules | `quantalche.analysis` | 9 independent modules (see below) |
| 3 — Aggregation | `quantalche.aggregation` | Combines module signals — `hard_gate` (default, live) or `soft_score` mode (backtest comparison only) |
| 5/6 — Confirmation + lifecycle | `quantalche.execution` | Entry/SL/TP calculation, `IDLE → PENDING → SIGNAL_ACTIVE → STOPPED_OUT \| TP_HIT \| EXPIRED → IDLE` state machine |
| 7 — Backtesting | `quantalche.backtest` | Bar-by-bar replay, walk-forward segmentation, per-module accuracy reporting |
| 8 — API | `quantalche.api` | FastAPI: REST (`/bars`, `/signals`) + WebSocket (`/ws/signals`) |
| 9 — Alerting | `quantalche.alerting` | Fires on signal state transitions (new/filled/TP/SL/expired) via webhook, Discord, and/or Telegram |

### Layer 2 modules

| Module | In `default_pipeline()`? | What it reads |
|---|---|---|
| `snr_zone` | Yes | Body-close open/close gap zones + Classic V/A rejection shapes |
| `market_structure` | Yes | BOS (continuation) / CHoCH (reversal) swing breaks |
| `liquidity_sweep` | Yes | BSL/SSL wick-through-then-close-back sweeps, incl. EQH/EQL clustering |
| `trendline_confluence` | Yes | 3rd-touch trendline rejection |
| `qm_pattern` | Yes | Quasimodo (QM/QML) 4-point reversal structure |
| `crt_pattern` | Yes | 3-candle Candle Range Theory / Power-of-3 (accumulation → manipulation → distribution) |
| `quarterly_theory` | No — opt-in | Session/True-Open bias (always non-neutral; see below for why it's excluded by default) |
| `premium_discount` | No — opt-in | Dealing-range Premium/Discount bias (same always-on exclusion reason) |
| `smt_divergence` | No — opt-in, separate interface | Inter-market divergence (e.g. BTC/ETH); needs two instruments' bars at once, wired in via `pipeline.run_with_correlated()` rather than `AnalysisModule` |

`quarterly_theory` and `premium_discount` are built, live-validated, and available, but excluded from the default pipeline for an empirically-confirmed reason: both are *always* non-neutral (price is always on one side of a reference level), and under `HARD_GATE`'s unanimity rule an always-on module becomes a near-permanent filter rather than an occasional vote — live backtests showed it collapsing signal count toward zero. See `docs/rule-mapping.md` and `aggregation/pipeline.py`'s `default_pipeline` docstring for the numbers and the reasoning.

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
| `scripts/validate_crt_pattern.py` | CRT/PO3 pattern module |
| `scripts/validate_quarterly_theory.py` | Quarterly Theory session/True-Open module |
| `scripts/validate_smt_divergence.py` | SMT inter-market divergence module |
| `scripts/validate_premium_discount.py` | Premium/Discount module, incl. the HARD_GATE signal-frequency comparison that justified excluding it from `default_pipeline` |
| `scripts/run_pipeline.py` | Phase 4 — full aggregation, single snapshot + history replay |
| `scripts/run_signal_lifecycle.py` | Phase 5 — confirmation + state machine, full lifecycle replay |
| `scripts/run_backtest.py` | Phase 6 — backtest/walk-forward report + leakage spot-check |
| `scripts/full_backtest_report.py` | Full report across every dashboard instrument, both modes, walk-forward segmented — writes `full_backtest_report.json` |

## Non-repainting

Every data client drops the current, still-forming bar before returning
results — only fully closed bars are ever handed back, per
`docs/architecture.md` ground rule #2. Every module built on top of that
data preserves the same guarantee (e.g. swing-point confirmation lags in
`analysis/swings.py`).
