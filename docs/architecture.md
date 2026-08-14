# Quantalche Nexus — Architecture & Build Plan

A modular signal engine that combines multiple analytical approaches, per the
Alchemist source material, into limit-order entry/stop/TP signals across
forex and crypto. Architecture is deliberately adaptive rather than fixed,
since the exact components in play depend on the 22 source documents.

---

## 0. Ground rules

- **Multiple modules can disagree.** Unlike a single-theory system, this one
  has to handle internal disagreement between components explicitly —
  surface it, don't average it away silently unless the source material
  specifically says to.
- **Non-repainting wherever price-based detection is used** — a structural or
  price-based read is only "confirmed" using closed-bar data.
- **Backtests are optimistic by default** — more so here, since combining
  multiple factors makes overfitting easier, not harder.
- **Decision support, not certainty.** Show each module's individual read
  plus the combined signal, not just a final black-box output.

---

## 1. Document-as-ground-truth convention

The 22 source documents are treated as the sole source of truth.

- Every rule-check function cites which document and section it implements.
- Maintain a rule-mapping reference (function → document/section → plain
  English restatement) so drift between code and source material is always
  checkable at a glance.
- If the combination logic between components isn't explicit in the
  material, that gap gets flagged rather than filled with an invented
  weighting scheme.

---

## 2. Architecture layers

### Layer 0 — Knowledge Extraction (output, not code)
- Read all 22 documents and produce two things before any engine code is
  written:
  1. A structured inventory of every distinct analytical component the
     method uses.
  2. The explicit rule the source material specifies for how those
     components combine into one decision — hard gating ("only signal when
     X and Y agree") versus soft scoring ("each factor adds to a
     composite"), or whatever the material actually defines.
- This becomes the scoping document for every layer below, reviewed before
  Phase 1 starts.

### Layer 1 — Data Ingestion
- Base: OHLC price data for forex and crypto (e.g. OANDA/Twelve Data/
  Polygon.io for forex, Binance/Bybit for crypto).
- Additional feeds (COT reports, economic calendar, order flow, sentiment
  indices, etc.) added only if Layer 0's extraction shows the method
  actually requires them — no feed gets built speculatively.

### Layer 2 — Modular Analysis Engine
- Each component identified in Layer 0 becomes an independent module with
  one job: given current market data, output a directional bias and
  confidence score for that component alone.
- Modules stay fully independent at this layer — no shared state, no
  cross-talk. Each one gets validated against the source material on its
  own — screenshot or output review against real charts — before being
  wired into anything else.

### Layer 3 — Confluence / Aggregation Layer
- Combines module outputs using the source material's own stated
  combination logic from Layer 0 — never a generically invented weighted
  average.
- Preserves the exact combination behavior specified in the material (hard
  gate vs. soft score), since that distinction changes system behavior
  substantially.
- Surfaces disagreement between modules rather than silently resolving it.

### Layer 4 — Multi-Timeframe / Multi-Degree Gate
- Included only if the source material defines a cross-timeframe alignment
  requirement. Not force-fit if the material doesn't call for it.

### Layer 5 — Confirmation & Trigger Layer
- Defines the exact condition, per the source material, required before an
  aggregated signal is accepted as tradable rather than provisional.

### Layer 6 — Signal Generation & Lifecycle State Machine
- One signal per symbol+timeframe per request, built as a real finite-state
  machine: `IDLE → SIGNAL_ACTIVE → STOPPED_OUT | TP_HIT → IDLE`. No new
  signal generated while a symbol+timeframe is active.
- Entry as limit order; stop at the invalidation point defined by the
  aggregation/confirmation logic; TP per whatever target method the
  material specifies.

### Layer 7 — Backtesting & Walk-Forward Validation
- Replays history bar-by-bar, logging each module's read and the aggregated
  decision exactly as they existed at that point in time — never letting the
  engine "see" later data before labeling an earlier point.
- Additionally reports each module's individual accuracy alongside the
  combined signal's performance — this is how a dead-weight or actively
  harmful component gets found.

### Layer 8 — API + Web App
- Backend: FastAPI, REST for on-demand signal requests plus WebSocket for
  live updates.
- Frontend: Next.js, presenting each module's individual read alongside the
  aggregated signal.

### Layer 9 — Alerting
- Delivered via Telegram/Discord bot, webhook, or email once the signal
  state machine is live.

---

## 3. Phased build plan

| Phase | Deliverable | Validation |
|---|---|---|
| 0 | Document ingestion + module inventory + combination-rule extraction | Scoping output reviewed before Phase 1 begins |
| 1 | Data pipeline for whatever feeds Phase 0 determined are needed | Manual spot-check against known data |
| 2 | First module built and validated in isolation | Screenshot/output review against source material |
| 3 | Remaining modules built one at a time, each validated in isolation | Same discipline, per module |
| 4 | Confluence/aggregation layer, built exactly to the extracted combination rule | Compare aggregated output against manual reasoning on real cases |
| 5 | Confirmation/trigger layer + signal state machine | Confirm no duplicate signals; confirm signals fire only post-confirmation |
| 6 | Backtest/walk-forward framework, including per-module reporting | Manually cross-check a handful of trades for hindsight leakage |
| 7 | Web app + API + alerting | End-to-end live signal request through to delivery |
| 8 | (Only if distributing to others) Compliance review | Legal consult on adviser/CTA-style registration requirements |

---

## 4. GitHub practice

- Own dedicated repo (`quantalche-nexus`).
- One branch per phase, merged to `main` only after that phase's validation
  step passes.
- Tag each merged phase as a checkpoint (`v0.0`, `v0.1`, ...) so there's
  always a working, validated version to roll back to.
- File and folder architecture determined as each phase is built, not
  scaffolded speculatively ahead of need.

---

## 5. Limitations to keep visible

- Multi-module systems can look deceptively strong in backtest purely from
  combining several factors — validate the combination logic out-of-sample
  specifically, not just each module individually.
- Where the source documents don't specify exact combination logic, any
  judgment call made to fill the gap is documented as a judgment call, not
  presented as if it came from the material.
- If this is ever offered to others rather than used personally, several
  jurisdictions treat paid signal provision as regulated activity — worth a
  legal consult before monetizing.
