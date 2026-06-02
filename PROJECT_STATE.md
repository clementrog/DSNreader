# DSNreader — State

Last touched: 2026-06-02
Status: active
Type: self

## What it is
DSN parser + analysis web app (FastAPI + deterministic Pydantic parser). Handles URSSAF reconciliation, apprentice splits, D reconstruction, and comparison views. Source of `dsn_extractor/` shared with dsn-facturation.

## Current focus
- Header employer identity must never display the cabinet/émetteur as the client employer.
- Demo-ready DSN fixture from Ben Consulting source with full URSSAF CTP list and clean quality warnings.
- URSSAF comparison UI/status and drill-down details stay demo-ready through targeted tests.

## Recent decisions
- 2026-06-02 — Header employer-name fallback corrected again after `capsule-sarl-avril-2026.dsn`: `S21.G00.11.008` is effectif, not an establishment name, and `S10.G00.01.003` is the émetteur/cabinet unless its SIREN matches the employer SIREN. Cabinet-filed DSNs with no trusted employer name now show neutral `Entreprise déclarée` + employer SIRET, never the cabinet name.
- 2026-06-02 — Superseded header fallback attempt: when `S21.G00.11.008` was absent, `renderHeader` briefly fell back to `company.name`; wrong for cabinet-filed files because `company` is the émetteur. The second line remained the corrected establishment SIRET.
- 2026-06-02 — Review round 2: the entreprise SIREN (`S21.G00.06.001`) is declared once but can be followed by several `S21.G00.11` establishments; the parser now carries it onto each via `EstablishmentBlock.enterprise_siren`, and `extractors` reads that field instead of rediscovering from per-establishment records. Fixes multi-establishment cabinet files where site 2+ previously got `cabinet SIREN + client NIC`. `sharedSiren` (header, multi-est global view) tightened: returns a SIREN only when every establishment has a valid 14-digit SIRET sharing the same first 9 digits. Spec PAS section now states the 2€ is a product tolerance, not a derived bound.
- 2026-06-02 — Review hardening: establishment SIRET is now built only when SIREN (9 digits) and NIC (5 digits) are both valid — else null + warning, killing the impossible 18-digit SIRET (real SIREN in S21.G00.06.001 + missing S21.G00.11). The S11-absent fallback reads the head-office NIC `S21.G00.06.002` instead of mis-reading the SIREN `S21.G00.06.001` as a NIC. Header is scope-aware: establishment scope shows the active site; global+single shows it; global+multi shows "N établissements" + shared SIREN (no misleading single SIRET). PAS tolerance raised to 2€ and explicitly documented as a *product* tolerance (masks sub-2€ single-fraction errors; fraction-aware bound is the follow-up in TODO).
- 2026-06-02 — Header identity bug (reported by Séverine): the UI top-left showed the émetteur/cabinet (S10.G00.01) instead of the client employer. Two stacked bugs fixed — (a) `app.js renderHeader` now reads `establishments[0].identity` not `d.company`; (b) establishment SIRET was built from the émetteur SIREN — now uses the client SIREN `S21.G00.06.001` (9-digit), falling back to émetteur only when absent. Fixtures encode a simplified model where émetteur SIREN == client SIREN, so the length-gated fallback keeps them green; new `TestEstablishmentIdentityCabinetFiled` covers the cabinet-filed case.
- 2026-06-02 — PAS arrondi tolerance raised to `abs(delta) < 2.00€` (was 0.50€ half-up via `_rounded_to_unit_ok`). Rationale: DGFIP versement `S21.G00.20.005` is rounded to the euro, PAS individuels `S21.G00.50.009` to the centime (DSN-info fiche 1802), and the rounding cumulates across fractions for a same SIRET, so a few-euro écart is a pure arrondi — 2,00€ confirmed product policy (Séverine). `_rounded_to_unit_ok` is untouched (still used by Ctrl1/Ctrl2). Demo's intentional PAS +9.79 still surfaces.
- 2026-04-29 — Expanded URSSAF salarié rows reuse the parent CTP grid with no expansion-cell side padding; employee names span `Libellé` + `Déclaré`, and employee amounts right-align in the parent `Individuel` column while info icons stay out of the numeric rail.
- 2026-04-29 — URSSAF salarié info tooltips elevate their row/ancestors on hover so they render above sticky headers/subheaders without changing the icon positioning.
- 2026-04-29 — URSSAF tab/card display status is derived from material CTP drill-down issues; a top-level `ok` item turns red when a CTP row has a non-tolerated delta or non-rattachable mapping.
- 2026-04-29 — Demo DSN keeps RABY Augustin's exit event, now with rupture code `034`, so the quality warning panel stays clean.
- 2026-04-28 — Landing `server/static/index.html` now ships its own SEO/canonical contract for the linc.fr proxy at `/ressources/controle-dsn/simulateur`: refreshed `<title>` (`Simulateur Contrôle DSN | Linc`), canonical, truthful description, `robots: index, follow`, Open Graph + Twitter blocks. OG image is hosted from `linc-next-site` at `/og-images/controle-dsn/simulateur.png`. Marketing-side `pnpm seo:path-mode-gate https://www.linc.fr` (45/45 PASS) and `pnpm seo:smoke` are green; production HTML carries zero Koyeb origin substring. Commit `551b55c`; redeployed `eb94028a` (dsn-path) + `aa81c1cb` (dsn-reader) — auto-deploy from `main` did not fire, manual `koyeb services redeploy` was needed.
- 2026-04-27 — Added top promo banner linking to linc.fr (matches RGDU/tranches simulators), tagged `utm_source=dsn-reader&utm_medium=banner&utm_campaign=logiciel-paie-cabinets`.
- 2026-04-27 — Demo DSN now starts from the 7-employee Ben Consulting source and keeps the full URSSAF CTP list; intentional failures are PAS +9.79 and URSSAF CTP 959 +6.01.
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
