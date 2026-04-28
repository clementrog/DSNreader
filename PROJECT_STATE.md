# DSNreader — State

Last touched: 2026-04-28 (SEO/canonical patch on landing head; both Koyeb services redeployed)
Status: active
Type: self

## What it is
DSN parser + analysis web app (FastAPI + deterministic Pydantic parser). Handles URSSAF reconciliation, apprentice splits, D reconstruction, and comparison views. Source of `dsn_extractor/` shared with dsn-facturation.

## Current focus
- Demo-ready DSN fixture from Ben Consulting source with full URSSAF CTP list.
- Keep contribution reconciliation behavior deterministic through targeted tests.
- Apprentice handling remains hardened (split, D reconstruction).

## Recent decisions
- 2026-04-28 — Landing `server/static/index.html` now ships its own SEO/canonical contract for the linc.fr proxy at `/ressources/controle-dsn/simulateur`: refreshed `<title>` (`Simulateur Contrôle DSN | Linc`), canonical, truthful description, `robots: index, follow`, Open Graph + Twitter blocks. OG image is hosted from `linc-next-site` at `/og-images/controle-dsn/simulateur.png`. Marketing-side `pnpm seo:path-mode-gate https://www.linc.fr` (45/45 PASS) and `pnpm seo:smoke` are green; production HTML carries zero Koyeb origin substring. Commit `551b55c`; redeployed `eb94028a` (dsn-path) + `aa81c1cb` (dsn-reader) — auto-deploy from `main` did not fire, manual `koyeb services redeploy` was needed.
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
