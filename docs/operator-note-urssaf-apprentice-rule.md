# Operator Note - URSSAF apprentice redistribution

This is a business rule.

## Current rule

- `100P` may receive apprentice excess above threshold.
- `726P` keeps the apprentice under-threshold share.
- `100D` receives the apprentice excess above threshold.
- `726D` keeps only the apprentice under-threshold share.

## Why this matters

Payroll users compare the rebuilt establishment basket against the employee-side
subtotal. To stay comparable on `D` rows, the apprentice excess must move from
`726D` to `100D`, just like on the establishment side.

## What operators should expect

- `P` rows can legitimately move apprentice amounts between `726P` and `100P`.
- `D` rows now replay that move too, so the displayed employee subtotal matches
  the audited basket perimeter.
- Reconstructed `D` rows can appear as informational only:
  - the backend will keep the displayed amounts
  - the backend can hide the delta with `comparison_mode=informational_partial`
