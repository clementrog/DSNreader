# TODO — DSNreader

> Maintained by Claude Code / Codex at end of each session.

## Now
- [ ] No active item

## Next
- [ ] Make PAS écart tolerance fraction-aware (~0,50€ × nb fractions) instead of flat 2€ — exact arrondi bound, removes the masked-small-error / cumulative-overflow trade-off (see `_PAS_EUR_TOL` note)
- [ ] Multi-establishment header: consider a real entreprise raison sociale label instead of "N établissements" if/when we extract one

## Later
- [ ] No active item

## Blocked
- [ ] None

## Done
- [x] 2026-06-02 — Header title fallback now prefers a readable name before SIRET (`establishment name → company/file name → SIRET`), fixing DSNs where `S21.G00.11.008` is absent (Capsule SARL showed `81912945300034` as the title)
- [x] 2026-06-02 — Review round 3: extractor entreprise-SIREN resolution is now 3-tier (`enterprise_siren` → S21.G00.06.001 record → émetteur), resilient to manually-built blocks; `sharedSiren` enforces `/^\d{14}$/` not just length
- [x] 2026-06-02 — Review round 2: parser carries entreprise SIREN (S21.G00.06.001) onto every following S21.G00.11 establishment via `EstablishmentBlock.enterprise_siren`, fixing multi-establishment cabinet files where site 2+ got `cabinet SIREN + client NIC`; `sharedSiren` (app.js) now only returns a SIREN when every site has a valid 14-digit SIRET sharing the same prefix; spec PAS section relabelled as product tolerance with the trade-off
- [x] 2026-06-02 — Review fixes: SIRET only built when SIREN(9)+NIC(5) valid (no more 18-digit SIRETs); S11-absent fallback uses head-office NIC S21.G00.06.002, never the SIREN; scope-aware header (multi-est global → "N établissements" + shared SIREN); PAS tolerance bumped to 2€ + labelled as product tolerance; fixed _rounded_to_unit_ok docstring drift
- [x] 2026-06-02 — Header now shows the employer establishment (S21.G00.06.001 client SIREN + S21.G00.11 NIC/enseigne) instead of the émetteur/cabinet (S10.G00.01); fixed establishment SIRET to use client SIREN with émetteur fallback (extractors.py) + app.js renderHeader rewire + tests
- [x] 2026-06-02 — PAS arrondi: tolerate `abs(delta) < 2.00€` so euro-rounded DGFIP versement vs centime-level individuals (cumul multi-fractions) no longer surfaces a false écart; spec + tests updated
- [x] 2026-04-29 — Keep URSSAF salarié info tooltips above sticky headers/subheaders without hover flicker
- [x] 2026-04-29 — Give expanded URSSAF salarié names enough room while right-aligning `Individuel` amounts on the parent CTP rail
- [x] 2026-04-29 — Fix URSSAF UI status pills so material CTP drill-down gaps turn the family/card status red
- [x] 2026-04-29 — Fix demo DSN contract exit so the quality warning panel stays clean
- [x] 2026-04-28 — Add SEO/canonical contract to landing head: title `Simulateur Contrôle DSN | Linc`, canonical to `https://www.linc.fr/ressources/controle-dsn/simulateur`, refreshed truthful description, `robots: index, follow`, full Open Graph block (type/url/title/description/image/site_name/locale), Twitter `summary_large_image`. OG image `https://www.linc.fr/og-images/controle-dsn/simulateur.png` (hosted from `linc-next-site`). Commit `551b55c` on `main`. Both Koyeb services redeployed (`eb94028a` dsn-path, `aa81c1cb` dsn-reader) and HEALTHY. Verification: production HTML head contains all expected tags; `pnpm seo:path-mode-gate https://www.linc.fr` 45/45 PASS; `pnpm seo:smoke https://www.linc.fr` green; production HTML contains zero `koyeb` substring.
- [x] 2026-04-27 — Add top Linc.fr promo banner (matches RGDU/tranches simulator pages)
- [x] 2026-04-27 — Add realistic demo DSN from Ben Consulting source with full URSSAF CTP list and intentional PAS and CTP 959 anomalies
- [x] 2026-04-24 — Fix URSSAF 668/669 reduction-general regularization split by S81 sign
- [x] 2026-04-17 — Refine URSSAF reconciliation rules and UI
- [x] 2026-04-15 — Polish URSSAF comparison UI and messaging
- [x] 2026-04-15 — Harden URSSAF apprentice comparison handling
- [x] 2026-04-15 — Harden apprentice URSSAF split and D reconstruction
- [x] 2026-04-15 — Default DSN upload view to collapsed and unfiltered
