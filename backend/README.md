# Quantalche Nexus — Backend

Phase 1: OHLC data ingestion for forex (Twelve Data) and crypto (Binance).
See `../docs/architecture.md` (Layer 1) and
`../docs/phase0-knowledge-extraction.md` for why these two feeds and no
others.

## Setup

```
cd backend
python -m venv .venv
.venv\Scripts\activate      # Windows
pip install -e .
```

Copy `.env.example` to `.env` and add your Twelve Data API key (free tier:
https://twelvedata.com/). Binance's public market-data endpoints need no key.

## Manual validation

```
python scripts/fetch_sample.py
```

Prints the last 5 closed bars from each configured source — compare by eye
against a real chart (e.g. TradingView) per the Phase 1 validation step in
`docs/architecture.md`. This is intentionally a manual spot-check script,
not an automated test suite — that's what the architecture doc calls for at
this phase.

## Non-repainting

Both clients drop the current, still-forming bar before returning results —
only fully closed bars are ever handed back, per `docs/architecture.md`
ground rule #2. See the `close_time`/bar-duration checks in
`binance_client.py` and `twelvedata_client.py`.
