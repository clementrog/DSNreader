# TODO — DSNreader

> Maintained by Claude Code / Codex at end of each session.

## Now
- [ ] No active item

## Next
- [ ] No active item

## Later
- [ ] No active item

## Blocked
- [ ] None

## Done
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
