# Release Notes - 2026-04-15 - URSSAF apprentice hardening

## Scope

Post-merge hardening for the URSSAF apprentice patch.

## Behavior change

Apprentice redistribution is now explicitly **P-side only**:

- `100P` may receive apprentice excess above threshold.
- `726P` keeps the apprentice under-threshold share.
- `100D` excludes apprentice rows.
- `726D` keeps apprentice D rows as declared / matched.

This replaces the earlier broader redistribution that also touched `D` rows and
produced wrong employee subtotals on real DSNs.

## Already-split apprentice rows

When the DSN already carries row-level split apprentice `076` rows, the backend
no longer splits them again.

Typical example:

- under-threshold rows stay on `726`
- excess rows stay on `100`

The routing uses the observed row-level base and rate instead of replaying the
split from the parent `S78` assiette.

## Informational D rows

Reconstructed `D` rows may now carry:

- `comparison_mode="informational_partial"`

This means the row is intentionally not compared as a trustworthy declared vs
employee delta because the employee subtotal is only partial relative to the
reconstructed URSSAF basket.

Current backend behavior in that mode:

- keep the declared reconstructed amount
- keep the employee subtotal
- suppress `delta`
- attach a warning explaining the row is informational only

## Regression coverage

The hardening is covered by:

- P-side no-double-split regressions
- D-side parity regression from the real-file shape
- a regression where informational downgrade is triggered by excluded /
  unmatched component rows, not only by missing employee amounts
