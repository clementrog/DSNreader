# DSNreader — State

Last touched: 2026-04-27
Status: active
Type: self

## What it is
DSN parser + analysis web app (FastAPI + deterministic Pydantic parser). Handles URSSAF reconciliation, apprentice splits, D reconstruction, and comparison views. Source of `dsn_extractor/` shared with dsn-facturation.

## Current focus
- Demo-ready DSN fixture from Ben Consulting source with full URSSAF CTP list.
- Keep contribution reconciliation behavior deterministic through targeted tests.
- Apprentice handling remains hardened (split, D reconstruction).

## Recent decisions
- 2026-04-27 — Added top promo banner linking to linc.fr (matches RGDU/tranches simulators), tagged `utm_source=dsn-reader&utm_medium=banner&utm_campaign=logiciel-paie-cabinets`.
- 2026-04-27 — Demo DSN now starts from the 7-employee Ben Consulting source and keeps the full URSSAF CTP list; intentional failures are PAS +9.79, URSSAF CTP 959 +6.01, and a contract exit missing rupture code.
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
