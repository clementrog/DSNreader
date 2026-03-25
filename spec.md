# Basic DSN extractor spec

## 1. Goal

Build a deterministic extractor that reads one **monthly DSN text file** and outputs a single JSON object containing:

* company-level metadata
* declaration period metadata
* employee counts
* counts by category
* hires / exits in the declared month
* stagiaire count
* meal voucher amount if present
* a few useful extras

No narrative interpretation. No payroll reasoning beyond explicit extraction rules and simple month-based counting.

## 2. Implementation language

**Python 3.12**

Recommended libraries:

* `re` for line parsing
* `datetime` for date normalization
* `decimal.Decimal` for money
* `collections` for counts
* `pydantic` for output validation
* optional: `pytest` for fixture-based tests

Why Python:

* easiest for LLM-generated maintenance
* very good string handling
* easy typed JSON output
* simple deterministic parser, no parser generator needed

## 3. Supported input

A text file where each line matches this pattern:

```text
Sxx.Gyy.zz.aaa,'value'
```

Example from DSN norms and from your files: rubrics such as declaration period, convention code, employee contract fields, other gross income, and contract end fields are all encoded this way. ([net-entreprises.fr][1])

## 4. Non-goals

This extractor does **not**:

* validate full DSN compliance
* infer business events beyond explicit counting rules
* reconcile multiple DSN months
* reconstruct DPAE signalements
* infer hidden payroll elements not explicitly coded

## 5. Parsing model

## 5.1 Line parser

For each non-empty line:

1. match regex:

   ```python
   r"^(S\d+\.G\d+\.\d+\.\d+),'(.*)'$"
   ```
2. store:

   * `code`
   * `raw_value`
   * `line_number`

## 5.2 Block segmentation

The extractor must keep three layers:

* **file-level rubrics**: `S10.*`, `S20.*`, `S90.*`
* **establishment-level rubrics**: `S21.G00.06`, `S21.G00.11`
* **employee-level blocks**: each employee starts at `S21.G00.30.001`

Employee block boundary rule:

* start a new employee when `S21.G00.30.001` appears
* all following `S21.*` rubrics belong to that employee until the next `S21.G00.30.001` or EOF

This works for your uploaded file shape, where employee sections repeat cleanly.

## 5.3 Data typing

Convert by rubric family:

* dates: `YYYYMMDD` → ISO `YYYY-MM-DD`
* decimals: use `Decimal`
* enums: keep both raw code and optional normalized label
* empty string: convert to `null`

---

# 6. Output contract

```json
{
  "source_file": "string",
  "declaration": {
    "norm_version": "string|null",
    "declaration_nature_code": "string|null",
    "declaration_kind_code": "string|null",
    "declaration_rank_code": "string|null",
    "period_start": "YYYY-MM-DD|null",
    "period_end": "YYYY-MM-DD|null",
    "month": "YYYY-MM|null",
    "dsn_id": "string|null"
  },
  "company": {
    "siren": "string|null",
    "nic": "string|null",
    "siret": "string|null",
    "name": "string|null",
    "address": "string|null",
    "postal_code": "string|null",
    "city": "string|null",
    "country_code": "string|null"
  },
  "establishment": {
    "nic": "string|null",
    "siret": "string|null",
    "name": "string|null",
    "naf_code": "string|null",
    "ccn_code": "string|null",
    "address": "string|null",
    "postal_code": "string|null",
    "city": "string|null",
    "employee_band_code": "string|null"
  },
  "counts": {
    "bulletins_employees": 0,
    "stagiaires": 0,
    "new_employees_in_month": 0,
    "exiting_employees_in_month": 0,
    "employees_by_retirement_category_code": {},
    "employees_by_retirement_category_label": {},
    "employees_by_conventional_status_code": {},
    "employees_by_conventional_status_label": {},
    "employees_by_contract_nature_code": {}
  },
  "amounts": {
    "tickets_restaurant_total": null,
    "tickets_restaurant_employee_share_total": null,
    "tickets_restaurant_employer_share_total": null
  },
  "extras": {
    "transport_public_total": null,
    "transport_personal_total": null,
    "gross_sum_from_salary_bases": null,
    "net_fiscal_sum": null,
    "net_paid_sum": null,
    "pas_sum": null
  },
  "quality": {
    "warnings": [],
    "missing_expected_blocks": []
  }
}
```

---

# 7. Field extraction rules

## 7.1 Declaration-level

### Month

Use `S20.G00.05.005` = start date of the main declared month.
Normalize to:

* `period_start`
* `month = YYYY-MM`

Use `S20.G00.05.007` for `period_end` when present.

The DSN monthly declaration metadata is carried by block `S20.G00.05`, including declaration nature and period fields. ([net-entreprises.fr][1])

### Suggested mappings

* `norm_version` ← `S10.G00.00.001`
* `declaration_nature_code` ← `S20.G00.05.001`
* `declaration_kind_code` ← `S20.G00.05.002`
* `declaration_rank_code` ← `S20.G00.05.003`
* `period_start` ← `S20.G00.05.005`
* `period_end` ← `S20.G00.05.007`
* `dsn_id` ← `S20.G00.05.009`

## 7.2 Company

Use company-identification rubrics from `S10.G00.01`.

Mappings:

* `siren` ← `S10.G00.01.001`
* `nic` ← `S10.G00.01.002`
* `siret` = `siren + nic`
* `name` ← `S10.G00.01.003`
* `address` ← `S10.G00.01.004`
* `postal_code` ← `S10.G00.01.005`
* `city` ← `S10.G00.01.006`
* `country_code` ← `S10.G00.01.007`

## 7.3 Establishment

Use `S21.G00.11` primarily. If missing, fall back to `S21.G00.06`.

Mappings:

* `nic` ← `S21.G00.11.001`
* `naf_code` ← `S21.G00.11.002`
* `address` ← `S21.G00.11.003`
* `postal_code` ← `S21.G00.11.004`
* `city` ← `S21.G00.11.005`
* `name` ← `S21.G00.11.008`
* `ccn_code` ← `S21.G00.11.022`

The spec explicitly defines `S21.G00.11.022` as the **Code convention collective principale**. ([net-entreprises.fr][1])

If `S21.G00.11.022` is absent, fallback to employee contract CCN when all employees share the same contract CCN:

* `S21.G00.40.040` if unique across employees

## 7.4 Number of bulletins / employees

Definition for the basic extractor:

* count employee blocks
* an employee block starts at `S21.G00.30.001`

Formula:

```python
bulletins_employees = count_occurrences("S21.G00.30.001")
```

This is a structural count, not a payroll semantic count.

## 7.5 Number of stagiaires

Use contract nature from `S21.G00.40.007`.

The DSN contract-nature rubric is `S21.G00.40.007`. The spec enumerates contract natures there, and internship can be represented as `29 - Convention de stage`. ([net-entreprises.fr][1])

Rule:

```python
stagiaires = count(employee where S21.G00.40.007 == "29")
```

Optional stricter rule:

* also keep raw count by `contract_nature_code`

## 7.6 People per category

Use **retirement category code** from `S21.G00.40.003`.

The DSN spec states that `S21.G00.40.003` is the **Code statut catégoriel Retraite Complémentaire obligatoire**, with values including:

* `01 = cadre`
* `04 = non cadre`
* `98 = retraite complémentaire ne définissant pas de statut cadre/non-cadre`
* `99 = pas de retraite complémentaire` ([net-entreprises.fr][1])

Primary count:

```python
employees_by_retirement_category_code[code] += 1
```

Normalized labels:

* `01` → `cadre`
* `04` → `non_cadre`
* `98` → `other_no_cadre_split`
* `99` → `no_complementary_retirement`

Also expose the conventional-status count from `S21.G00.40.002` as a separate raw grouping, because that is a different DSN concept. The spec identifies `S21.G00.40.002` as **Statut du salarié (conventionnel)**. ([net-entreprises.fr][1])

## 7.7 Number of new employees

For a **monthly DSN extractor**, define this as:

* employee where `S21.G00.40.001` falls inside the declared month

Use:

* `S21.G00.40.001` = contract start date
* month window from `S20.G00.05.005` / `S20.G00.05.007`

Rule:

```python
new_employees_in_month = count(
    employee where period_start <= contract_start_date <= period_end
)
```

Important nuance: this is a **monthly-DSN proxy for new hires**, not the count of actual DPAE signalements. Since 2026, DPAE can be declared through a dedicated DSN signalement, so a monthly DSN alone does not guarantee the actual DPAE count. ([net-entreprises.fr][2])

Expose both names in code/docs:

* `new_employees_in_month`
* not `dpae_count`

## 7.8 Number of exiting employees

Use the contract-end block `S21.G00.62`.

The DSN contract-end block includes:

* `S21.G00.62.001` = date de fin de contrat
* `S21.G00.62.002` = motif de rupture
* `S21.G00.62.006` = dernier jour travaillé et payé au salaire habituel ([net-entreprises.fr][1])

Rule:

```python
exiting_employees_in_month = count(
    employee where S21.G00.62.001 is present
    and period_start <= end_date <= period_end
    and rupture_code != "099"
)
```

Store optional raw breakouts:

* by rupture code
* by end date

## 7.9 Tickets restaurant value

Use block `S21.G00.54` = **Autre élément de revenu brut**.

The DSN spec lists:

* `S21.G00.54.001 = 17` → participation patronale au financement des titres-restaurant
* `18` → participation patronale aux frais de transports publics
* `19` → participation patronale aux frais de transports personnels ([net-entreprises.fr][1])

Basic extractor rule:

```python
tickets_restaurant_total = sum(
    S21.G00.54.002 for each S21.G00.54 block where S21.G00.54.001 == "17"
)
```

For this uploaded file, I do **not** see `S21.G00.54` blocks, so this field should return `null` or `0.00` depending on your API preference.

Recommended behavior:

* `null` if rubric family absent
* numeric total if present

Also extract:

* `transport_public_total` from type `18`
* `transport_personal_total` from type `19`

## 7.10 Useful extras

These are easy and often helpful.

Per employee:

* `net_fiscal` ← `S21.G00.50.002`
* `net_paid` ← `S21.G00.50.004`
* `pas_withheld` ← `S21.G00.50.009`

The `S21.G00.50` block includes remuneration nette fiscale and related net/payment fields. ([net-entreprises.fr][1])

Aggregate sums:

```python
net_fiscal_sum = sum(S21.G00.50.002)
net_paid_sum = sum(S21.G00.50.004)
pas_sum = sum(S21.G00.50.009)
```

Optional gross proxy:

* sum `S21.G00.78.004` for `S21.G00.78.001` codes you decide to include
* or simpler: sum `S21.G00.50.006` if you want a stable per-employee gross-like field for this file shape

---

# 8. Recommended normalized labels

## 8.1 Retirement category (`S21.G00.40.003`)

From DSN enumerations: ([net-entreprises.fr][1])

```python
RETIREMENT_CATEGORY_LABELS = {
    "01": "cadre",
    "02": "extension_cadre",
    "04": "non_cadre",
    "98": "other_no_cadre_split",
    "99": "no_complementary_retirement",
}
```

## 8.2 Contract nature (`S21.G00.40.007`)

Only normalize the values you need immediately:

* `01` → `cdi_prive`
* `02` → `cdd_prive`
* `29` → `convention_stage`

The full DSN enumeration is larger, but a basic extractor can safely normalize only these common values and keep the raw code for others. ([net-entreprises.fr][1])

---

# 9. Expected output for this uploaded file

Based on the uploaded file structure, the extractor should at minimum be able to produce:

* `month`
* `company`
* `ccn_code`
* `bulletins_employees`
* `stagiaires`
* `employees_by_retirement_category`
* `new_employees_in_month`
* `exiting_employees_in_month`
* `tickets_restaurant_total`

And for this file specifically, it should also handle:

* mixed category counts
* some employees with contract-end blocks
* hires starting in the declared month
* no visible `S21.G00.54` block family

---

# 10. Acceptance rules

The extractor is considered correct if:

1. it parses every line without losing order
2. it counts employee blocks correctly
3. it returns `month`, `company`, `ccn_code`
4. it groups employees by `S21.G00.40.003`
5. it counts hires by `S21.G00.40.001` inside month window
6. it counts exits by `S21.G00.62.001` inside month window
7. it returns `tickets_restaurant_total = null` when type `17` is absent
8. it never invents values not present in the file

---

# 11. Recommended project structure

```text
dsn_extractor/
  parser.py
  models.py
  normalize.py
  extractors.py
  enums.py
  tests/
    test_parser.py
    test_metrics.py
```

## Module responsibilities

### `parser.py`

* parse raw lines
* produce ordered `(code, value, line_no)` records
* split into file-level and employee-level sections

### `models.py`

* pydantic output schemas

### `normalize.py`

* date normalization
* decimal normalization
* enum labels

### `extractors.py`

* one function per metric family:

  * declaration
  * company
  * establishment
  * counts
  * amounts

### `enums.py`

* local enum maps for only the codes you actually expose

---

# 12. Minimal deterministic algorithm

```python
parse file into records
extract declaration metadata
extract company metadata
extract establishment metadata
split employees on S21.G00.30.001

for each employee:
    read contract fields
    increment employee count
    increment category counters
    increment contract nature counters
    if contract start date inside declared month: increment new_employees_in_month
    if contract end date inside declared month and rupture != 099: increment exiting_employees_in_month
    sum net fields

scan whole file for S21.G00.54 blocks:
    sum type 17 into tickets_restaurant_total
    sum type 18 into transport_public_total
    sum type 19 into transport_personal_total

return validated JSON
```

---

# 13. One implementation choice I recommend

Expose both:

* **raw DSN codes**
* **friendly labels**

Example:

```json
"employees_by_retirement_category_code": {
  "01": 10,
  "04": 40
},
"employees_by_retirement_category_label": {
  "cadre": 10,
  "non_cadre": 40
}
```

[1]: https://www.net-entreprises.fr/media/documentation/dsn-cahier-technique-2026.1.pdf "DSN_Tableau des Usages 2026.1.5T - 20250908a"
[2]: https://www.net-entreprises.fr/media/documentation/dsn-P26V01-note-differentielle-CT2025.1-CT2026.1.pdf?utm_source=chatgpt.com "DECLARATION SOCIALE NOMINATIVE"
