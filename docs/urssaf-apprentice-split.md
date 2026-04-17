# URSSAF Apprentice Split Notes

This note documents the current implementation choices for the apprentice `726 -> 100` split.

## Current product rule: redistribution is P-side only

Post-merge hardening (2026-04-15) narrowed the business behavior explicitly:

- `100P` may receive the apprentice excess above threshold.
- `726P` keeps the apprentice under-threshold share.
- `100D` receives the apprentice excess above threshold.
- `726D` keeps only the apprentice under-threshold share.

This is intentional.

The earlier implementation applied apprentice redistribution to both `P` and
`D` rows. That created wrong employee subtotals on real files: the `D` side
was moving apprentice amounts that the validated business parity expected to
stay on `726D` only up to the threshold.

Practical consequence for developers:

- only `100P` / `726P` should call the threshold allocator
- `100D` must include the apprentice excess above threshold
- `726D` must keep only the under-threshold share

## Source basis

- `docs/13. DSN/13.3-dsn-donnees-paie-rh.publicodes`
  - `100 920/921` routes apprentice assiette to `salarié . contrat . apprentissage . assiette réduite apprentissage`
  - `726 920/921` caps the apprentice assiette at `50% * SMIC` from `03/2025`, otherwise `79% * SMIC`
- `docs/13. DSN/13.1-cotisations-dsn.publicodes`
  - `076` has explicit apprentice-specific rates:
    - base `03`: `2.02%` under threshold, `2.42%` above threshold
    - base `02`: `8.55%` under threshold, `15.45%` above threshold
  - `045 / 068 / 074 / 075` are defined as ordinary `amount = assiette × taux` individual contributions. The docs do not expose a separate apprentice-only fixed rate table for these codes.

## Why `045 / 068 / 074 / 075` use a derived rate

For these codes, the legal rule change is on the assiette split, not on a dedicated apprentice rate table.

That means:

- the exact assiette routed to `726` is the under-threshold portion
- the exact assiette routed to `100` is the excess portion
- the code-specific rate is the same one already embedded in the original S81 row

In practice, the extractor derives that rate from the row itself:

- `derived_rate = abs(S81.004) / row_base`

Where `row_base` means:

- `S21.G00.81.003` when present on the employee row
- otherwise `S21.G00.78.004` from the parent assiette block

Then it reapplies that same rate to:

- `min(base, threshold)` for `726`
- `max(base - threshold, 0)` for `100`

This is intentionally not a heuristic shortcut. It is equivalent to replaying the publicodes formula for codes whose source rule is still `assiette × taux`, while avoiding invented hard-coded rates that the source docs do not define.

For `076`, there is one extra guard:

- if the DSN already carries a row-level apprentice split (for example
  separate `076` rows with `2.02%` / `2.42%` or `8.55%` / `1.45%`),
  the extractor routes those rows directly to the observed target CTP
  instead of splitting them a second time.

## SMIC support window

The internal SMIC table is only guaranteed from `2024-11-01` onward.

If apprentice allocation is requested for an earlier `reference_date`, the extractor raises loudly instead of silently using the wrong threshold.

## Multi-contract apprentice limitation

Current behavior is intentionally conservative.

If a single employee block carries:

- more than one `S21.G00.40.001` contract start date, or
- mixed contract natures including apprentice status

then the extractor does **not** guess which contract should own which `S78/S81` row.

Instead it:

- keeps valid employee allocations from other rows
- excludes only the ambiguous apprentice row
- surfaces `unsupported_multi_contract_context` as an explicit warning

This is an intentional product limitation until per-contract linkage is implemented.

## Informational D rows

Some reconstructed `D` rows compare:

- a full URSSAF amount rebuilt from assiette × reference rate
- against an employee subtotal that is only partially calculable from the DSN

When that happens, the backend now emits:

- warning text explaining the comparison is informational only
- `comparison_mode="informational_partial"` on the `UrssafCodeBreakdown`

The purpose is simple: downstream code must not infer this state by parsing the
French warning string. The machine-readable flag is the source of truth.
