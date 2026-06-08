# AGENTS.md — DSNreader

## Project
DSNreader — DSN parser + analysis web app (URSSAF reconciliation, apprentice handling, comparison views).
Type: self
Status: active

## Stack
- Python + FastAPI (`server/`)
- Deterministic DSN parser + Pydantic models (`dsn_extractor/`)
- pytest test suite under `tests/`

## Conventions
- Deterministic parsing; Pydantic-typed outputs
- Keep spec docs in sync with parser behavior
- Tests under `tests/`

## Session protocol
At the end of any session where files changed or decisions were made, update:

1. `TODO.md`
   - Move done items to `## Done` as `- [x] YYYY-MM-DD — <what>`
   - Add new items discovered this session to `## Now` / `## Next` / `## Later`
   - Add blockers to `## Blocked` with reason + what unblocks
2. `PROJECT_STATE.md`
   - Bump `Last touched:` to today
   - Rewrite `## Current focus` if it shifted (max 3 lines)
   - Append to `## Recent decisions` if anything was decided
Keep both tight. Bullets, not paragraphs. Do this without being asked.

## Related docs
- ./TODO.md
- ./PROJECT_STATE.md
- ./CLAUDE.md
- ./roadmap.md
- ./spec.md
- ./spec-cotisations-comparaison.md
