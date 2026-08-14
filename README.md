# Quantalche Nexus

A modular signal engine for forex and crypto that combines multiple analytical
approaches — drawn from a 22-document source corpus on the "Alchemist" trading
methodology (and the frameworks it synthesizes: ICT, SMC, MSNR, CRT, Quarterly
Theory, SMT/SSMT, and others) — into limit-order entry/stop/TP signals.

The architecture is deliberately adaptive rather than fixed: the exact modules
in play, and how they combine, are determined by what the source material
actually specifies, not by a generic invented framework. See
[`docs/architecture.md`](docs/architecture.md) for the full design.

## Ground rules

- **Multiple modules can disagree.** Disagreement between components is
  surfaced, not silently averaged away, unless the source material says
  otherwise.
- **Non-repainting.** Any price-based detection is only "confirmed" on
  closed-bar data.
- **Backtests are treated as optimistic by default.** Combining multiple
  factors makes overfitting easier, not harder.
- **Decision support, not certainty.** Every module's individual read is
  shown alongside the combined signal — never just a black-box output.
- **Document-as-ground-truth.** Every rule-check function cites which source
  document and section it implements. Where the source material doesn't
  specify how components combine, that gap is documented as a judgment call,
  never silently invented.

## Status

Project is in **Phase 0 — Knowledge Extraction**: reading the full source
corpus and producing the module inventory + combination-rule map that scopes
every phase after it. No engine code is written until that scoping document
is reviewed.

## Repo practice

- One branch per phase (`phase-0-...`, `phase-1-...`, etc.), merged to `main`
  only after that phase's validation step passes.
- Each merged phase is tagged as a checkpoint (`v0.0`, `v0.1`, ...).
- Commits are pushed at every meaningful step so progress and regressions are
  traceable.

## Disclaimer

This is a personal decision-support tool, not financial advice, and is not
intended for distribution to others in its current form. See
`docs/architecture.md` §5 for compliance notes if that ever changes.
