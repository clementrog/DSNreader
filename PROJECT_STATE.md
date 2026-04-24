# DSNreader — State

Last touched: 2026-04-24
Status: active
Type: self

## What it is
DSN parser + analysis web app (FastAPI + deterministic Pydantic parser). Handles URSSAF reconciliation, apprentice splits, D reconstruction, and comparison views. Source of `dsn_extractor/` shared with dsn-facturation.

## Current focus
- URSSAF reconciliation rules, especially CTP-to-salaried drill-down accuracy.
- Apprentice handling remains hardened (split, D reconstruction).
- DSN upload view defaults collapsed/unfiltered.

## Recent decisions
- 2026-04-24 — CTP `668` / `669` both map to individual code `018`; employee rows are split by S81 amount sign, and `669` may use a reconstructed 100% CTP amount when `.005` is absent.
- 2026-04-14 — Extracted `Tracking gestionnaire` into standalone dsn-facturation repo (source commit `0b0dac3`).

## Open questions
- TODO: fill in

## Related docs
- ./TODO.md
- ./CLAUDE.md
- ./AGENTS.md
- ./roadmap.md
- ./spec.md
- ./spec-cotisations-comparaison.md
