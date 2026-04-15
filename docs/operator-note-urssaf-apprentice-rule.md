# Operator Note - URSSAF apprentice redistribution

This is a business rule.

## Current rule

- `100P` may receive apprentice excess above threshold.
- `726P` keeps the apprentice under-threshold share.
- `100D` excludes apprentice rows.
- `726D` keeps apprentice `D` rows exactly as declared / matched in the DSN.

## Why this matters

If a DSN already carries apprentice detail at employee-row level, replaying the
redistribution on the `D` side creates false employee subtotals and fake URSSAF
gaps.

## What operators should expect

- `P` rows can legitimately move apprentice amounts between `726P` and `100P`.
- `D` rows must not replay that move.
- Reconstructed `D` rows can appear as informational only:
  - the backend will keep the displayed amounts
  - the backend can hide the delta with `comparison_mode=informational_partial`

If a future regression shows apprentice amounts moving on `100D` / `726D`,
treat it as a product bug, not as an acceptable alternative implementation.
