# Phase 0 — Knowledge Extraction & Module Inventory

**Status: complete. Judgment calls resolved 2026-08-15 (see §7) — project
owner reviewed the corpus findings and delegated the specific choices to
Claude Code's judgment. Every decision below is an editorial synthesis
choice, not a rule the source material itself states, and is documented as
such so it stays overridable.**

This document is the Layer 0 deliverable required by `architecture.md`: (1) a
structured inventory of every distinct analytical component the source
material uses, and (2) the explicit rule the material gives for how those
components combine into one decision — or, where no such rule exists, that
gap flagged rather than filled in silently.

Source corpus: 22 PDFs, each already converted into a structured
"Extraction Notes" document (`C:\Users\DT Wijesekara\Desktop\Alchemist MD\`),
covering core concepts, entry/SL/TP rules, MTF logic, and — usefully — each
document's own self-flagged internal ambiguities. All 22 were read in full
(2 directly, 20 via parallel research passes) to produce this synthesis.

---

## 1. The central finding: this is not one methodology

The corpus is not a single "Alchemist" specification with 22 supporting
chapters. It's **at least 9 independently-authored courses/notebooks** that
share a common vocabulary root (SMC/ICT concepts, a support-resistance
framework called "MSNR," liquidity-sweep-before-reversal logic, and
HTF-bias→LTF-entry cascades) but were built by different people, at
different times, with different — sometimes contradictory — rules bolted on
top of that shared root.

Identified authors/sources:

| Author / brand | Documents | Notes |
|---|---|---|
| AbayFX (@AbayFX) | 08, 11 | **08 and 11 are byte-identical (confirmed via MD5)** — same PDF, two filenames. Treat as one source. |
| Kit X Alchemist | 02 | Explicitly a personal synthesis of named external frameworks (ICT, SMC, CRT, MSNR, Quarterly Theory, SMT/SSMT); most citation-conscious document in the corpus. |
| PAKDE | 03 | Short, narrow, single-topic (inducement/BOS validity). |
| Unattributed ("Alchemist SnR") | 04, 05 | Near-duplicate pair, same title, likely two captures of one source lesson. |
| Yanu Emmanuel F. / Alchemy Traders Network | 06, 16, 20, 22 | **06, 16, and 20 are very likely the same underlying book** ("MSNR x SMC x ICT") — not byte-identical (16 is a compressed re-export per its filename), but identical title, identical 51-page count, and word-for-word matching quotes landing on the *same page numbers* across all three independent extractions. 22 ("EMS Trinity") is a confirmed, explicit sequel by the same author. **Treat 06/16/20 as one source, not three**, when weighing corroboration. |
| BamfearlessFX | 07 | Cites "I Adegboyega." |
| White Srp (+ "Warriors Trader," credited inline) | 09 | Machine-translated (Thai→English), partly not original to the credited author. |
| @abayforex/AbayFX (expanded manual) | 10 | Much larger and more systematic than 08/11 despite similar branding — likely a later/expanded work by the same author, not the same document. |
| MSNR Turtle / "SL 10 PIPS" | 12 | No individual author named. |
| make.no1000 / TradeSL10PIPS | 14 | Thai-language, image-only. |
| N!GHT | 15 | Polished, Cambodian-origin (EN/Khmer), best-organized glossary in the corpus. |
| MST | 17 | Explicitly a paid-community teaser; SL/TP deliberately withheld. |
| SYFIRE | 01 | Explicitly labeled "Part 1 of 2 — foundation only." |
| Unattributed ("Alchemist Notes" scrapbook) | 13 | Compilation of 3+ unattributed sub-sources stitched together. |
| REX / "BERKUSA ARSIV" archive | 18 | Arabic-language redistribution, minimal original text. |
| AbayFX (cheat-sheet) | 19 | 5-page personal visual notes, near-zero prose. |
| Stranger | 21 | Personal hand-authored notes, heavy typos, zero prose bridging its own sub-sections. |

**Practical implication:** where a rule appears in several documents, check
this table before treating that as independent corroboration — several
"agreements" in the raw batch reports are really one author's material
appearing more than once.

---

## 2. Component inventory (candidate Layer 2 modules)

Organized by family. Each entry notes how well-corroborated it is *after*
correcting for the authorship overlaps in §1, and flags where the source
material itself is internally inconsistent.

### 2.1 Market structure
| Component | Definition (converged reading) | Corroboration |
|---|---|---|
| Swing structure (HH/HL/LH/LL) | Standard higher-high/higher-low/lower-high/lower-low classification | Universal, no conflicts |
| BOS (Break of Structure) | Trend-continuation break | Universal, no conflicts |
| CHoCH (Change of Character) | Reversal signal | Widespread, but formally *defined* (full-body close required through the level, wick-only doesn't count) in only doc 20 — no other document states a validity test this precisely |
| MSS (Market Structure Shift) | Inconsistently either a synonym for CHoCH, or (doc 12) a distinct post-liquidity-sweep reversal signal separate from both BOS and CHoCH | **Conflict — needs a chosen definition** |

### 2.2 Liquidity
| Component | Definition | Corroboration |
|---|---|---|
| BSL / SSL (buy-side / sell-side liquidity) | Resting stops above/below swing highs/lows | Universal, consistent |
| EQH / EQL (equal highs/lows) | Clustered stop pools | Universal, consistent |
| ERL / IRL (external/internal range liquidity) | ERL = liquidity beyond the dealing range; IRL = imbalance/liquidity inside it (often equated with FVG) | Consistent across docs 02, 08/11, 13 |
| PWH/PWL/PDH/PDL | Prior week/day high/low as liquidity references | Consistent across docs 08/11, 13 |
| Inducement / IDM / "Trap" (doc 15's rename) / "TS" | A smaller liquidity pocket swept *before* the real structural point is considered valid | **The single most-corroborated mechanic in the entire corpus** — every document that discusses reversals independently asserts some version of "stops get run before the real move." Naming is wildly inconsistent (IDM, Trap, TS = "Target Sweep"/"Turtle Soup"/unglossed in different docs) but the underlying mechanic is never contradicted anywhere. |
| DOL (Draw on Liquidity) | The liquidity pool price is "delivered" toward — used generically as the target concept | Consistent across docs 02, 08/11, 13, 19 |

### 2.3 POI / zone types
| Component | Definition | Corroboration |
|---|---|---|
| SNR zone (open/close-based) | Zone drawn from candle **body** open/close, wicks explicitly ignored; resistance = "A" shape, support = "V" shape | **Strongly corroborated and consistent** — explicit in docs 04, 05, 06/16/20, 07, 09, 10, 12, 15, 18. One of the most reliable rules in the whole corpus. |
| Fresh / Unfresh lifecycle | Untouched = fresh (holds "uncollected liquidity"); wick-touch = unfresh; full-body close through = flips (RBS/SBR); flipped level can become "fresh again" | Best-specified in doc 20; corroborated (less detail) in docs 06, 10, 13, 16 |
| RBS / SBR (level flip) | Resistance-becomes-support / support-becomes-resistance after a body-close break + retest | Universal core mechanic. Naming varies (doc 04/05 use "S2R/R2S" for the same idea). Doc 07 has a likely typo stating both flip "to the upside." |
| OCL (Open-Close Level) | HTF-candle-derived open/close level, a "hidden"/"magnetic" zone | Mostly consistent, **except doc 14 gives 3 mutually incompatible definitions within its own single document** (open/close level vs. "order cluster level" vs. "order block low") |
| Classic V / Classic A | Fast wick-rejection shape at support (V) / resistance (A) | Consistent across docs 04, 05, 06, 08/11, 13, 15 |
| **QM / QML / QMR / QMM / QMC ("Quasimodo" family)** | No converged definition exists | **The messiest term in the corpus.** At least 4 incompatible scopings found: doc 01's 4-variant taxonomy (QM/QMR/QMM/QMC as reversal/manipulation/continuation variants); doc 06's narrow "QM = left shoulder of a head-and-shoulders" (and doc 06 itself doesn't consistently honor this definition in its own later pages); doc 09's "QML = QM," treated as fully synonymous; doc 10's "QM = the pattern, QML = the level" plus QMR/QMM/QMC as further named siblings. **Needs an explicit chosen canonical definition before this can become one module — this is the single highest-priority judgment call in the whole inventory.** |
| OB (Order Block) | Generically: "last candle before a strong displacement" | Consistent as a bare definition; almost no document gives mitigation/reuse/freshness rules beyond doc 01's 2-touch reuse cap. Doc 09's equating of SBR/RBS with "Breaker Block" is a one-off, not corroborated elsewhere. |
| FVG (Fair Value Gap) | Imbalance area between candles; CE = 50% midpoint | Consistent wherever defined |
| Breaker Block | A broken structure level that becomes a new POI on retest | Only lightly specified (docs 02, 22); doc 09's OB/Breaker-Block/SBR equation is idiosyncratic |
| Engulfing OB / engulfing-candle logic | Engulfing candle as institutional-orderflow confirmation | Most fully developed in doc 22 ("EMS Trinity"), including an explicit "engulfing failure" definition; lighter treatment in docs 09, 12 |

**Overloaded acronym warning:** "CE" is used for two *different* concepts —
**Consequent Encroachment** (50% midpoint of an FVG) and **Candle
Equilibrium** (45–50% midpoint of a single candle's range) — and at least
one source document (01) uses "CE" for both without disambiguating. Code
must never use a bare `CE` identifier; name these two things separately
(e.g. `fvg_midpoint` / `candle_equilibrium`).

### 2.4 Confluence / refinement tools
| Component | Definition | Corroboration |
|---|---|---|
| Trendline + SNR confluence ("Marriage Concept" / "X Factor" / "QMX") | A trendline intersecting an SNR/QM level raises confidence in that level | Widespread naming, but the specific numbered rule ("enter on touch #3, never touch #2") comes from the doc 06/16/20 single-author cluster — treat as one source's rule, not three. Doc 04/05 give a *different* numbered rule set for nominally the same idea, including a quantified 45–60° trendline-angle constraint absent everywhere else. **Not reconciled.** |
| Quarterly Theory / session kill-zones | Fractal time cycles (Year→Quarter→Month→Week→Day→90-min), with London/NY sessions treated as higher-quality than Asia | Widespread (01, 02, 08/11, 09, 13, 17, 19, 21) but **timezone conventions conflict** — doc 01/09/13 use GMT+7, doc 02 uses NY time (UTC-4) — and the two tables are never cross-referenced by any document. A canonical timezone/table must be chosen. |
| SMT / SSMT (inter-market divergence) | Correlated-pair divergence (e.g. BTC/ETH, XAU/XAG, EURUSD/DXY) as a reversal tell | Consistent concept across docs 02, 08/11, 09. **Notably, this is one of the only places where multiple independent documents explicitly agree it should be a soft, optional confirmation layer, not a standalone trigger** — doc 02: "treated as a confirmatory tool, not a standalone signal"; doc 17: "an auxiliary factor... if found, probability increases." |
| CRT (Candle Range Theory / PO3) | 3-candle Accumulation→Manipulation→Distribution model, attributed to @Romeopt/ICT | Consistent 3-phase model across docs 02, 07, 08/11-adjacent, 09. Doc 02 uniquely gives explicit, generalizable SL/TP rules for it (see §4). |
| Fibonacci retracement/extension | Secondary/confirming tool only — **never** a standalone trigger in any document | Used almost everywhere, but ratio sets are inconsistent. A specific unusual custom ratio set (0.109, 0.127, 0.145, 0.214, 0.232, 0.25, 0.618, 0.636, 0.654, 0.786, 0.804, 0.822, 1) appears **verbatim** in docs 07, 09, and 10 despite three different attributed authors — this is a shared-template signal, not independent corroboration of that specific ratio set's validity. |

### 2.5 Multi-timeframe / storyline framework
| Component | Definition | Corroboration |
|---|---|---|
| HTF bias → LTF entry cascade | General principle: read direction on a higher timeframe, execute on a lower one | Universal principle; **exact timeframe pairings vary per document** (H4→M15, Weekly→H4→H1→M15, Daily→H1, etc.) — no single pairing is corroborated across unrelated authors |
| "Storyline" state machine + fresh/rejection/breakout hard gate | A formal per-timeframe directional narrative that requires all three of {fresh level, wick rejection, one-timeframe-lower external breakout} before being valid | **Single-author-cluster only** (doc 06/16/20 = one book). This is the clearest, most explicit hard-gate rule found anywhere in the corpus, but it has one source, not three. |
| "2 TF's Confirmation Rule" (Weekly setup → H4 confirmation, Daily setup → H1 confirmation) | Same doc 06/16/20 cluster | Single source |
| EMS Trinity 4-stage cascade (bias → engulfing confirmation → SMC structure → execution, all within one aligned "EMS Zone") | Doc 22 (same author's sequel book) | Single source, but **the most operationally complete combination-logic statement in the entire 22-document corpus** |

---

## 3. Entry / stop-loss / take-profit inventory

This is the corpus's weakest area by a wide margin, and it matters most —
it's exactly what Layers 5/6 (confirmation trigger, signal lifecycle) need.

**Entry:** Every document gives *some* entry description, ranging from
precise numbered rules (doc 06/16/20's "touch #3, not #2"; doc 22's 4-stage
cascade) to vague confluence lists with no stated precedence. No corpus-wide
convergence on order type (limit vs. market-on-confirmation) — doc 08/11
explicitly flags this as ambiguous in its own text.

**Stop-loss — almost entirely absent.** Of 22 documents:
- **Explicit, generalizable SL rules exist in only two places:** doc 02
  ("place stop loss at the nearest OB or liquidity zone") and doc 22, which
  *defers* SL methodology entirely to external video content not included in
  the PDF.
- Everywhere else, SL is either never mentioned, or only shown as a number
  on a worked chart example with no stated placement logic (docs 09, 12,
  15, 18, 19, 20, 21), or given only as a contextual/implicit rule (doc 08's
  "SL IN SWPT" flagged "HIGH RISK," implying — but never stating — that the
  stop belongs beyond the swept wick, not inside it).
- Doc 12's entire brand is "SL 10 PIPS" and the number is never taught,
  derived, or connected to any rule anywhere in the document.

**Take-profit — similarly thin.** The one recurring idea across the corpus
is "target = the opposing liquidity pool" (DOL/opposite liquidity), stated
explicitly in docs 08/11, 13, and implied elsewhere. Only three documents
give any quantified rule: doc 01 (RR ≥ 1:1.5 floor), doc 08/11-adjacent doc
10 (RR ≥ 1:1.5, plus conservative/aggressive dual targets), and doc 22
(RR 1:3–1:7, with partial profit-taking). **Doc 22's risk-management figures
are an outlier worth treating with real skepticism**: 5–12% risk per trade,
justified only by an assumed 80% win rate with no losing-streak modeling —
well outside conventional risk-management norms, and the extraction agent
flagged this itself as unrealistic.

**Conclusion:** the source material does not contain a usable, corpus-wide
SL/TP formula. This cannot be extracted — it has to be designed, and
documented explicitly as a design decision rather than attributed to the
material (per the project's own document-as-ground-truth rule).

---

## 4. Combination logic — the Layer 3 question

This is the second deliverable Layer 0 is supposed to produce, and the
honest answer is: **no single combination rule is stated consistently across
the corpus.** Here is everything that was actually found, so the choice in
§7 is made with full visibility into the source material rather than
against a blank page.

**Explicit hard-gate statements found:**
- Doc 06/16/20 (one source): *"NO FRESH SNR LEVEL → NO STORYLINE, NO TRADE. NO REJECTION SNR LEVEL → NO STORYLINE, NO TRADE. NO BREAKOUT SNR LEVEL → NO STORYLINE, NO TRADE."* — three named conditions, all individually required.
- Doc 22 (same author, sequel book): explicit sequential 4-stage AND-gate (MSNR bias → engulfing confirmation → SMC structure confirmation → refinement/execution), each stage a prerequisite for the next, inside one aligned zone.
- Doc 03: inducement-sweep-before-valid-structure, stated as a hard precondition, but scoped narrowly (structure validity only, not a whole-system combination rule).
- Doc 21: an order block is explicitly "FAILED" if the prior liquidity level wasn't swept first — same pattern, narrow scope.

**Explicit soft/scoring statements found:**
- Doc 01: *"When two or three of these factors align at the same level, that area becomes the strongest zone"* — but the same document **directly contradicts itself** elsewhere on whether a confirmation candle is even required, and its own extraction flags this as unresolved.
- Doc 02: SMT/SSMT explicitly demoted to "confirmatory... not a standalone signal."
- Doc 17: SMT/Fibonacci explicitly demoted to "auxiliary... if found, probability increases," while inducement/CHoCH are treated as near-mandatory in the same document — i.e. **doc 17 mixes both modes explicitly, per-component**, rather than picking one universally.

**Documents that never address the question at all** (present sequential
checklists that read like gates but never state gate-vs-score explicitly):
03, 04, 05, 07, 09, 12, 13, 14, 15, 18, 19.

**The corpus's single largest and most internally self-aware document (doc
10) states a hard-gate checklist in one place and then directly contradicts
it elsewhere** ("No need to wait for an extra confirmation candle — your
plan already tells you this is the entry point"), and its own extraction
notes flag this as an unresolved internal disagreement, not an extraction
error.

**Bottom line:** the only fully coherent, unambiguous, end-to-end
combination rule in the entire corpus belongs to one author (Yanu Emmanuel
F., docs 06/16/20 + 22). Every other document is either silent, partially
explicit, or self-contradictory. Adopting that author's model as the
default is a legitimate, well-reasoned starting point — but it is a
**choice**, not something "the material" says as a whole, and it should be
labeled as exactly that in code and docs if adopted.

---

## 5. MSNR — resolving (or not) the corpus's core naming conflict

"MSNR" is the term used most often across the corpus and defined least
consistently. Full tally across all 22 documents:

- **"Malaysian Support and Resistance"** — docs 02, 07, 10, 15 ("Malaysian /
  Support / And / Resistance"), 18, 22. **6 documents, the plurality
  reading.** Doc 02 additionally credits a named originator: *"MSNR... is a
  trading framework pioneered by Udara Shehan (Alchemist FX)."*
- **"Market Structure + Support & Resistance"** — docs 08/11 (one source),
  13.
- **"Market Storyline & Narrative"** — doc 02 only, offered as a *second*,
  unreconciled reading in the same document that also gives the "Malaysian"
  reading — doc 02 itself never resolves which one it means.
- **No expansion given at all — used purely as a brand/system name** — docs
  06/16/20 (one source), 09, 12, 14, 17, 19, 21. This is actually the
  **most common pattern**: most documents never spell out what the letters
  stand for.
- Doc 02 itself preserves a self-aware community critique worth keeping
  visible: *"Some trading communities argue that MSNR is essentially a
  re-branding of the classic concept of Support–Resistance plus Smart Money
  Concept (SMC), rather than a fully new methodology."*

**Recommendation (flagged as an editorial call, not a source-stated fact):**
"Malaysian Support and Resistance" has the strongest independent
corroboration once the doc 06/16/20 and 08/11 duplicates are collapsed to
one vote each. Suggest adopting it as the canonical gloss in documentation,
while keeping "MSNR" itself as an opaque module/brand name in code (it
functions as one regardless of which expansion is "correct") so nothing
downstream depends on resolving this precisely.

---

## 6. Provenance notes worth keeping visible

- **08 = 11**, byte-identical (MD5-confirmed). One source.
- **06 ≈ 16 ≈ 20**, almost certainly one book ("MSNR x SMC x ICT" by Yanu
  Emmanuel F.) captured three times — not byte-identical, but identical
  title, identical 51-page count, and word-for-word matching quotes at
  matching page numbers across three independently-run extractions. One
  source.
- **20 → 22** is a confirmed, explicit sequel relationship (22 calls itself
  the author's "second published work, following The Alchemist MSNR × SMC ×
  ICT").
- The unusual custom Fibonacci ratio set in §2.4 appearing verbatim across
  docs 07/09/10 (three different credited authors) suggests a shared
  upstream template being copied between communities, not independent
  discovery — worth remembering before treating cross-document agreement as
  automatic validation anywhere in this corpus, not just for Fibonacci.
- Several documents are explicitly partial/non-canonical by their own
  admission: doc 01 ("Part 1 of 2 — foundation only"), doc 17 (paid-preview
  teaser, SL/TP deliberately withheld), doc 02 (author repeatedly states the
  whole book is "a personal compilation... not a replacement for the
  original creators' material").

---

## 7. Judgment calls — resolved 2026-08-15

Per the project's ground rules, none of these are stated by the source
material as a whole — each is an explicit editorial decision, made by
Claude Code after the project owner reviewed the corpus findings above and
delegated the specific choice. Every rule-check function built against one
of these should cite this section (not a source document) as its authority,
per `rule-mapping.md`.

1. **Combination logic (§4) — configurable, hard-gate cascade as default
   preset.** Layer 3 (aggregation) is built with gate strictness as a
   tunable parameter rather than one hard-coded rule. The default preset
   mirrors Yanu Emmanuel F.'s model (docs 06/16/20 + 22) — bias confirmed →
   rejection/engulfing confirmed → structure confirmed → execution, each
   stage a prerequisite for the next — since it's the only fully
   self-consistent combination rule in the entire corpus. A soft
   weighted-scoring preset is also implemented so Layer 7 can backtest both
   and measure which one actually performs better, per Layer 7's own stated
   purpose.
2. **QM/QML/QMR/QMM/QMC (§2.3) — doc 10's taxonomy adopted.** QM = the
   reversal pattern (structural sequence), QML = the specific price level
   the pattern marks, QMR/QMM/QMC = reversal/manipulation/continuation
   sub-variants. Chosen over docs 01/06/09's competing readings because it's
   the most complete attempt at internal disambiguation in the corpus, even
   though doc 10 itself doesn't fully resolve every edge case.
3. **MSS vs. CHoCH (§2.1) — treated as synonyms.** Both refer to the
   reversal/change-of-character signal. Validity test adopted from doc 20 —
   the level must be broken by a full-body candle close, not a wick alone —
   since doc 20 is the only document precise enough to be directly
   implementable. BOS remains a separate, distinct continuation signal.
4. **Trendline-touch entry rule (§2.4) — both rules implemented as
   configurable variants.** Doc 06/16/20's rule (enter only on the 3rd
   touch, with wick rejection, explicitly never on touch #2) and doc 04/05's
   rule (engulfing candles required at touches #1–#2, 2nd touch must break
   prior structure, 3rd touch requires HTF POI alignment, plus a 45–60°
   trendline-angle constraint) come from unrelated, non-corroborating
   sources — rather than picking one, both are built as named strategy
   variants so Layer 7 can compare them empirically instead of the choice
   being made blind.
5. **Stop-loss placement (§3) — structural invalidation point, not a fixed
   distance.** No corpus-wide formula exists; doc 02's rule ("place stop
   loss at the nearest OB or liquidity zone") is adopted as the concrete
   default, generalized as: the stop sits just beyond — never inside — the
   structural zone that gated entry (nearest OB/liquidity zone/swept-zone
   extreme, depending on which module triggered the signal), consistent
   with doc 08/11's implicit "SL IN SWPT = HIGH RISK" warning against
   placing a stop inside an already-swept zone. This slots directly into
   Layer 6 as already designed — the confirmation/aggregation logic already
   has to define an invalidation point, so SL placement is that point, not
   a separately invented rule.
6. **Take-profit (§3) — opposing liquidity pool, 1:1.5 minimum RR floor.**
   Primary target = the opposing liquidity pool/DOL, the most common idea
   across the corpus. Minimum RR floor of 1:1.5 adopted because it's the
   one quantified figure two independent sources (docs 01 and 10) actually
   agree on. Doc 22's 5–12%-risk / 1:3–1:7 model is explicitly **rejected**
   as an outlier not grounded in any risk model — not adopted, not even as
   a secondary preset, without further review.
7. **Risk management / position sizing — sourced outside the corpus,
   explicitly labeled as such.** The source material gives essentially
   nothing usable here. Default: 0.5–1% account risk per trade, standard
   conservative practice, not attributed to any Alchemist document anywhere
   in code or docs.
8. **Session/timezone convention (§2.4) — UTC internally, standard session
   windows.** All timestamps and session logic are stored/computed in UTC.
   Asia/London/NY session windows use standard real-world hours rather than
   either of the corpus's two conflicting Quarterly Theory tables (GMT+7 vs.
   NY/UTC-4) — those specific tables only matter if a dedicated Quarterly
   Theory module gets built later, at which point this decision should be
   revisited specifically for that module.
9. **MSNR canonical gloss (§5) — "Malaysian Support and Resistance."**
   Adopted as the documented working definition (the plurality reading once
   duplicate sources are collapsed). "MSNR" remains an opaque module/brand
   name in code regardless — nothing downstream depends on this gloss being
   precisely correct.

---

## 8. Next step

Phase 0 is complete. Per the project's GitHub practice, this branch merges
to `main` and gets tagged `v0.0` as the Phase 0 checkpoint. Phase 1 (data
ingestion) starts next: base OHLC feeds for forex and crypto, per
`architecture.md` Layer 1 — nothing in the extracted material calls for
COT/economic-calendar/sentiment feeds as a hard requirement, so those stay
out of scope unless a specific module built later needs one.

A `docs/rule-mapping.md` template has been created alongside this document
— every module built from Phase 2 onward should get an entry there citing
either a source document/section, or this document's §7 where the rule is
an editorial decision rather than something the material states, per the
project's document-as-ground-truth convention.
