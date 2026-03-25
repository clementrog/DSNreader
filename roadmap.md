# DSN Reader — Roadmap

---

# Phase 1 — MVP (deterministic extractor + CLI)

**Dependencies:** `pydantic`, `pytest`

### Out of scope for MVP

- Full DSN compliance validation
- DPAE / signalement reconstruction
- Narrative interpretation of payroll events
- Payroll item inference beyond explicit DSN coding
- Web interface, Docker, deployment

---

## Slice 0 — Project scaffold

- [ ] Init Python 3.12 project with `pyproject.toml`
- [ ] Install MVP deps: `pydantic`, `pytest`
- [ ] Create package structure:
  ```
  dsn_extractor/
    __init__.py
    __main__.py
    parser.py
    models.py
    normalize.py
    extractors.py
    enums.py
  tests/
    conftest.py
    test_parser.py
    test_extractors.py
    test_normalize.py
    fixtures/
      single_establishment.dsn
      multi_establishment.dsn
      no_s54_blocks.dsn
      unknown_enum_codes.dsn
      missing_contract_fields.dsn
  ```

---

## Slice 1 — Line parser + block segmentation

**Files:** `parser.py`

- [ ] Regex line parser: `r"^(S\d+\.G\d+\.\d+\.\d+),'(.*)'$"`
- [ ] Produce ordered list of `(code, raw_value, line_number)` records
- [ ] Split into:
  - file-level rubrics: `S10.*`, `S20.*`, `S90.*`
  - establishment-level rubrics: `S21.G00.06.*`, `S21.G00.11.*`
  - employee-level blocks
- [ ] Establishment context tracking:
  - maintain current active establishment from `S21.G00.11` blocks
  - assign subsequent employee blocks (`S21.G00.30.*`) to the active establishment context
  - assign `S21.G00.54` blocks to the active establishment context
  - if an employee or `S21.G00.54` block appears before any establishment context is set, place it in an "unassigned" bucket and emit a global warning
- [ ] Employee boundary: new block on each `S21.G00.30.001`
- [ ] Tests:
  - line count preserved, no line dropped
  - single-establishment: one establishment, correct employee count
  - multi-establishment: multiple establishments, employees assigned correctly
  - unassigned blocks: employee before any establishment context triggers warning

---

## Slice 2 — Pydantic models + normalization

**Files:** `models.py`, `normalize.py`, `enums.py`

### Output model

Top-level structure:

```
source_file
declaration { ... }
company { ... }
establishments [ { identity, counts, amounts, extras, quality } ]
global_counts { ... }
global_amounts { ... }
global_quality { ... }
```

Each establishment entry contains its own `counts`, `amounts`, `extras`, `quality`.
Global sections aggregate across all establishments.

### Normalization

- [ ] Date: `YYYYMMDD` → `YYYY-MM-DD`
- [ ] Decimal: `decimal.Decimal`
- [ ] Empty string → `None`

### Enums

- [ ] Retirement category (`S21.G00.40.003`):
  - `01` → `cadre`, `02` → `extension_cadre`, `04` → `non_cadre`
  - `98` → `other_no_cadre_split`, `99` → `no_complementary_retirement`
- [ ] Contract nature (`S21.G00.40.007`):
  - `01` → `cdi_prive`, `02` → `cdd_prive`, `29` → `convention_stage`
- [ ] Conventional status (`S21.G00.40.002`): raw code grouping only — no normalized label map unless enum table is explicitly implemented and tested
- [ ] Unknown codes: preserve raw value, never fail extraction, emit warning

### Tests

- [ ] Round-trip date/decimal normalization
- [ ] Unknown enum codes pass through without error

---

## Slice 3 — Extractors

**Files:** `extractors.py`

### 3a — Declaration metadata

- [ ] `norm_version` ← `S10.G00.00.001`
- [ ] `declaration_nature_code` ← `S20.G00.05.001`
- [ ] `declaration_kind_code` ← `S20.G00.05.002`
- [ ] `declaration_rank_code` ← `S20.G00.05.003`
- [ ] `period_start` ← `S20.G00.05.005`
- [ ] `period_end` ← `S20.G00.05.007`
- [ ] `month` = `YYYY-MM` from `period_start`
- [ ] `dsn_id` ← `S20.G00.05.009`

### 3b — Company

- [ ] `siren` ← `S10.G00.01.001`
- [ ] `nic` ← `S10.G00.01.002`
- [ ] `siret` = `siren + nic`
- [ ] `name`, `address`, `postal_code`, `city`, `country_code`

### 3c — Establishments (per-establishment)

- [ ] Primary source: `S21.G00.11.*` fields (nic, naf, address, name, ccn)
- [ ] Fallback: `S21.G00.06.*` when `S21.G00.11` absent — emit warning
- [ ] CCN: primary `S21.G00.11.022`; fallback: unique `S21.G00.40.017` across employees of that establishment
  - if multiple different employee-level `S21.G00.40.017` values exist, set `ccn_code = null` and emit warning
- [ ] `siret` = company siren + establishment nic

### 3d — Counts (per-establishment, then aggregated to global)

- [ ] `employee_blocks_count` = count of `S21.G00.30.001` occurrences in this establishment
  - This is the user-facing "number of bulletins (employés)" for MVP. It is a structural count of DSN employee sections, not a deduplicated headcount.
- [ ] `stagiaires` = employees where `S21.G00.40.007 == "29"`
- [ ] `employees_by_retirement_category_code` + `employees_by_retirement_category_label`
- [ ] `employees_by_conventional_status_code` (raw grouping, no label map)
- [ ] `employees_by_contract_nature_code`
- [ ] `new_employees_in_month` = employees where contract start date (`S21.G00.40.001`) falls inside `[period_start, period_end]`
  - Note: this is a monthly-DSN proxy for new hires, not a DPAE count
- [ ] `exiting_employees_in_month` = employees where contract end date (`S21.G00.62.001`) falls inside `[period_start, period_end]` and rupture code (`S21.G00.62.002`) ≠ `"099"`

### 3e — Amounts (per-establishment, then aggregated to global)

- [ ] `tickets_restaurant_employer_contribution_total` = sum of `S21.G00.54.002` where `S21.G00.54.001 == "17"`
  - Note: this represents the employer contribution as coded in DSN. It does not represent the full employee-facing ticket restaurant value when payroll software does not encode it explicitly this way.
  - Return `null` when no type `17` block is present for the establishment (types `18`/`19` may still exist)
- [ ] `transport_public_total` = sum where type `18` (return `null` when no type `18` present)
- [ ] `transport_personal_total` = sum where type `19` (return `null` when no type `19` present)

### 3f — Extras (per-establishment, then aggregated to global)

- [ ] `net_fiscal_sum` ← sum `S21.G00.50.002`
- [ ] `net_paid_sum` ← sum `S21.G00.50.004`
- [ ] `pas_sum` ← sum `S21.G00.50.009`
- [ ] `gross_sum_from_salary_bases` (optional)

### 3g — Quality warnings

Per-establishment and global. The extractor must never invent values; ambiguous or missing data must surface as warnings.

- [ ] Multiple establishments detected in file
- [ ] Missing `S21.G00.11` — fallback to `S21.G00.06` used
- [ ] Missing or invalid period dates (`S20.G00.05.005` / `S20.G00.05.007`)
- [ ] Employee block missing contract start date (`S21.G00.40.001`)
- [ ] Contract end block (`S21.G00.62`) missing rupture code (`S21.G00.62.002`)
- [ ] Unknown retirement category code (not in enum map)
- [ ] Unknown contract nature code (not in enum map)
- [ ] No `S21.G00.54` block family present in establishment
- [ ] Employee or amount block could not be assigned to an establishment
- [ ] Conflicting employee-level CCN (`S21.G00.40.017`) values prevent establishment CCN derivation

### Global aggregation

- [ ] `global_counts`: sum all per-establishment counts
- [ ] `global_amounts`: sum all per-establishment amounts
- [ ] `global_quality`: merge all per-establishment warnings + file-level warnings

---

## Slice 4 — Tests

**Files:** `tests/`

### Fixtures

- [ ] `single_establishment.dsn` — one establishment, standard employee mix
- [ ] `multi_establishment.dsn` — two+ establishments, employees split across them
- [ ] `no_s54_blocks.dsn` — no `S21.G00.54` family at all
- [ ] `unknown_enum_codes.dsn` — retirement/contract codes not in enum map
- [ ] `missing_contract_fields.dsn` — employee blocks with missing contract start or end fields

### Test cases

- [ ] Parser: line count, block segmentation, establishment assignment
- [ ] Single-establishment: all fields extracted, counts correct
- [ ] Multi-establishment: per-establishment counts correct, global aggregates match sum
- [ ] No S54: `tickets_restaurant_employer_contribution_total` is `null`, warning emitted
- [ ] Unknown codes: extraction succeeds, raw codes preserved, warnings emitted
- [ ] Missing fields: extraction succeeds, warnings list missing expected data
- [ ] Acceptance criteria validated against both per-establishment and global output

---

## Slice 5 — CLI

**Files:** `dsn_extractor/__main__.py`

- [ ] `python -m dsn_extractor path/to/file.dsn` → JSON to stdout
- [ ] `--pretty` — indented output
- [ ] `--per-establishment` — output per-establishment detail (default)
- [ ] `--global-only` — output only global aggregates, omit per-establishment detail
- [ ] Exit code 0 on success, 1 on parse failure

---

## MVP acceptance checklist

1. Parses every line without losing order
2. Segments establishments correctly; assigns employees to parent establishment
3. `employee_blocks_count` matches actual `S21.G00.30.001` occurrences per establishment
4. Returns `month`, `company`, per-establishment `ccn_code`
5. Groups employees by `S21.G00.40.003` (retirement category) per establishment
6. Counts `new_employees_in_month` by `S21.G00.40.001` inside month window — not labeled as DPAE
7. Counts `exiting_employees_in_month` by `S21.G00.62.001` inside month window, rupture ≠ `"099"`
8. Returns `tickets_restaurant_employer_contribution_total = null` when type `17` absent
9. Unknown enum codes preserved as raw values, never cause extraction failure
10. Warnings emitted for all ambiguous/missing data cases
11. Global aggregates equal sum of per-establishment values
12. Never invents values not present in the file
13. Establishment CCN from employee-level fallback (`S21.G00.40.017`) only used when unique within the establishment; conflicting values → `ccn_code = null` + warning

---

# Phase 2 — Web interface + deployment

**Additional dependencies:** `fastapi`, `uvicorn`, `python-multipart`

---

## Slice 6 — Web API (FastAPI)

**Files:** `server/app.py`

- [ ] `POST /api/extract` — accepts multipart `.dsn` upload, returns full JSON output
- [ ] `GET /health` — health check
- [ ] `GET /` — serves static frontend
- [ ] CORS config for deploy domain
- [ ] Max upload size: 10 MB
- [ ] Error responses: 400 on parse failure with quality warnings

---

## Slice 7 — Frontend (drop zone + results)

**Files:** `server/static/index.html`, `style.css`, `app.js`

Design: Linear / Vercel / Attio density. Dark surface, Inter + JetBrains Mono, 13px body, fine-line borders, 4px spacing grid.

### Drop zone

- [ ] Full-viewport centered drop area
- [ ] Drag-over state with border highlight
- [ ] File input fallback button
- [ ] Accepts `.dsn` files only
- [ ] Upload spinner

### Results view

- [ ] Header: company name, SIRET, period month
- [ ] Establishment selector (tabs/dropdown) when multiple present
- [ ] Summary cards: employee count, hires, exits, stagiaires
- [ ] Table: employees by retirement category (code + label + count)
- [ ] Table: employees by contract nature
- [ ] Amounts: tickets restaurant employer contribution, transport (`—` when null)
- [ ] Extras: net fiscal, net paid, PAS totals
- [ ] Quality warnings banner
- [ ] Global vs per-establishment toggle
- [ ] "Upload another" reset

### Design tokens

- [ ] Background hierarchy: root → surface → surface-hover → surface-active
- [ ] Borders as primary spatial separators
- [ ] Shadows: sm on cards, md on overlays
- [ ] Radius: 6px components, 12px containers
- [ ] All interactive elements: hover + active states
- [ ] Status colors: info / success / warning / error
- [ ] Monospace for codes, SIRET, amounts; sans for labels

---

## Slice 8 — Docker + Koyeb deploy

- [ ] Dockerfile: Python 3.12 slim, install deps, run uvicorn
- [ ] `koyeb.yaml` or GitHub integration deploy
- [ ] Health check: `GET /health`
- [ ] Target: single service, 256 MB RAM, 0.1 vCPU
- [ ] Custom domain (optional)
