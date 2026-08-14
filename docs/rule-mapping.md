# Rule Mapping Reference

Per `architecture.md` §1 (document-as-ground-truth convention): every
rule-check function in the engine cites which source document and section it
implements. This file is that cross-reference, kept up to date as each
module is built from Phase 2 onward.

Source documents are referenced by number and short name, matching
`phase0-knowledge-extraction.md` §1 (e.g. "doc 06/16/20" for the confirmed
single-source cluster, "doc 02" for `02-unified-logic-market-structure.md`).

Add one row per rule-check function as it's written. If a function
implements a judgment call rather than a directly-sourced rule (see Phase 0
§7), say so explicitly in the "Source" column instead of citing a document —
never attribute an invented rule to the material.

| Function | Document / Section | Plain-English rule | Notes |
|---|---|---|---|
| `SNRZoneModule._detect_zones` (zone formation) | Docs 09 p.9-11, 16 p.9, 20 p.9 ("GAP (Open-Close) SNR"); corroborated generically across docs 04-07, 10, 12, 15, 18 ("ignore the wicks" rule) | A support/resistance zone forms in the gap between one closed candle's body close and the next candle's body open. Wicks are ignored. | Phase0 §2.3. |
| `SNRZoneModule._detect_zones` (fresh → unfresh) | Doc 20 §14 (Fresh/Unfresh lifecycle) | A zone starts "fresh"; the first bar whose wick range touches the zone without fully closing through it flips the zone to "unfresh." | Phase0 §2.3. |
| `SNRZoneModule._detect_zones` (flip / RBS-SBR) | Doc 20 §15; universal RBS/SBR mechanic (docs 04-07, 10, 12, 13, 15, 16, 18, 20) | A bar whose *close* fully breaks through the zone flips its role (support↔resistance) and resets it to fresh in the new role. | Phase0 §2.3. |
| `SNRZoneModule.evaluate` (bias direction) | Doc 06/16/20 "A"-shape resistance rejection / "V"-shape support rejection (candle-close-based, not wick-based) | A bullish-bodied bar closing back above a support zone's bottom = bullish rejection; a bearish-bodied bar closing back below a resistance zone's top = bearish rejection. | Phase0 §2.3, §4. |
| `SNRZoneModule.__init__` (`min_gap_ratio` threshold) | Not source-stated — Phase0 §7 item pattern (judgment call, documented not invented) | A close→open gap must be ≥ a fraction of the instrument's average bar range to count as a zone. | Added after live validation showed the raw "any gap" rule producing sub-cent noise zones on Binance BTCUSDT 1h data. Default (0.08) calibrated off the EUR/USD gap-size distribution, where the concept is actually applicable — see `snr_zone.py` docstring. On continuous markets (Binance-style crypto) this module correctly detects few/no zones; that's expected, not a bug — see next row. |
| `SNRZoneModule` scope limitation (continuous markets) | Not source-stated — empirical finding from Phase 2 validation | This module's zone concept doesn't transfer to 24/7 continuous markets (crypto): live-data testing showed BTCUSDT close→open gaps sitting at 0.01–0.07% of average bar range even at the 99th percentile, vs. EUR/USD's real distribution (~9% at the 90th percentile, concentrated at the 21:00 UTC forex session rollover). | A different, swing-based zone-formation rule would be needed for crypto; deliberately not force-fit into this module. Candidate follow-up module. |
| Swing-high/low ("Classic V/A") zones | Not implemented | — | Deliberately deferred: the source material never gives a swing-formation rule (doc 08 itself notes swing highs/lows are diagrammed but never formally defined). Implementing one would mean inventing an un-sourced convention. Candidate follow-up module, flagged not silently added. |
