# DSNreader — Contrôle DSN

DSN parser + analysis web app. Powers the **Contrôle DSN** simulator on linc.fr (URSSAF reconciliation, apprentice handling, comparison views).

## Where it lives

- **Local checkout (canonical):** `/Users/clement/projects/DSNreader`
  (macOS APFS is case-insensitive, so `dsnreader` resolves to the same folder — there is only one checkout.)
- **GitHub:** [clementrog/DSNreader](https://github.com/clementrog/DSNreader) — branch `main`

## Production deploys

This single repo is deployed to **two** Koyeb services. Both auto-deploy from `main`, but if a deploy doesn't fire, redeploy manually with the IDs below.

| Public URL | Koyeb app | Service ID | Mode |
|---|---|---|---|
| <https://www.linc.fr/ressources/controle-dsn/simulateur> | `dsn-path` | `eb94028a` | path-mode (proxied by linc-next-site via `CONTROLE_DSN_PATH_ORIGIN`) |
| <https://dsn-reader-linc-production-3e7c895b.koyeb.app> | `dsn-reader` | `aa81c1cb` | root-mode (direct) |

The path-mode service runs with `BASE_PATH=/ressources/controle-dsn/simulateur` so all asset URLs and API routes are prefixed correctly behind the linc.fr rewrite.

### Redeploy

```sh
koyeb services redeploy aa81c1cb   # dsn-reader (direct)
koyeb services redeploy eb94028a   # dsn-path (linc.fr proxy)
```

After a CSS/JS change, both services should be redeployed — `index.html` cache-busts assets via `?v=<mtime>`, but the HTML itself is served from the FastAPI app and only updates on redeploy.

## Stack

- Python + FastAPI (`server/`)
- Deterministic DSN parser + Pydantic models (`dsn_extractor/`)
- Pytest under `tests/`
- Static frontend in `server/static/` (vanilla HTML/CSS/JS, no build step)
- Dockerfile for Koyeb builds

## Run locally

```sh
.venv/bin/uvicorn server.app:app --reload
```

## Related repos

- [`linc-next-site`](file:///Users/clement/clients/linc/repos/linc-next-site) — owns the linc.fr Next.js shell and the rewrite to this app
- [`dsn-facturation`](file:///Users/clement/clients/linc/repos/dsn-facturation) — shares `dsn_extractor/` (extracted 2026-04-14, source commit `0b0dac3`)

## Project docs

- [`PROJECT_STATE.md`](./PROJECT_STATE.md) — current focus + recent decisions
- [`TODO.md`](./TODO.md) — active backlog
- [`CLAUDE.md`](./CLAUDE.md) — session protocol for AI assistants
- [`spec.md`](./spec.md), [`spec-cotisations-comparaison.md`](./spec-cotisations-comparaison.md) — parser behavior reference
