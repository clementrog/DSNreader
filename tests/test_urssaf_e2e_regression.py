"""End-to-end regression for the URSSAF 7-issue fix (staging-v2, 2026-04).

Fixture path taken: **SYNTHESIZED DETERMINISTIC** (plan 1.8, path 2).

Numeric choices are anchored to the parity check performed against the real
failing DSN ``DSN_DSN-mensuelle_YZZY_16_employees_2026-03 (4).dsn`` on
2026-04-14. Per-CTP observations from that run:

    027D: decl=7.05  ind=7.07        delta=-0.02       within_unit=True
    100D: decl=reconstruit ind=1510.13 delta=...       rattachable
    100P: decl=6297.27 ind=6255.56   delta=41.71       rattachable
    726D: decl=None  ind=36.82       delta=None        rattachable
    726P: decl=77.98 ind=119.38      delta=-41.40      rattachable
    863D: decl=None  ind=23.24       delta=None        rattachable
    863P: decl=101.97 ind=101.97     delta=0.00        within_unit=True
    668P: decl=3232.00 ind=???       status=rattachable (after gate relax)
    003P: decl=325.00 ind=-323.85    delta=648.85      abs gap 1.15
    004P: decl=151.00 ind=-153.06    delta=304.06      abs gap 2.06

The fixture below reconstructs equivalent numeric conditions on a
simpler two-employee establishment so assertions can be precise. Parity
between this synthesized fixture and the real DSN is structural (same
shape, same flags, same delta-sign semantics), not numeric.

The seven behaviors asserted in a single test body:

1. 027 row with sub-1€ delta flags delta_within_unit=True, rattachable.
2. CTP 100 produces both 100D and 100P mapped_code rows.
3. 100P individual_amount equals the sum of per-employee amounts
   (person-side, not aggregate).
4. 100D is rattachable even without .005 and carries a reconstructed amount.
5. One row per employee under 100P; individual_codes lists contributing codes.
6. 668 rattachable with display_absolute=True and matching S81 018,
   regardless of declared sign (relaxed gate for reduction rules).
7. display_absolute is True for 668/003/004 and False for 669.
"""

from __future__ import annotations

import datetime as dt
from decimal import Decimal
from pathlib import Path

from dsn_extractor.contributions import compute_contribution_comparisons
from dsn_extractor.parser import DSNRecord, EmployeeBlock, EstablishmentBlock, parse_lines, segment


REFERENCE_DATE = dt.date(2025, 1, 1)


def _r(code: str, value: str, line: int = 1) -> DSNRecord:
    return DSNRecord(code=code, raw_value=value, line_number=line)


def _employee(
    empno: str,
    nom: str,
    prenom: str,
    s81_rows: list[tuple[str, str, str]],  # (code_81, amount, base_code_78)
    contract_nature: str | None = "01",
    start_line: int = 1000,
) -> EmployeeBlock:
    records: list[DSNRecord] = [
        _r("S21.G00.30.001", empno, start_line),
        _r("S21.G00.30.002", nom, start_line + 1),
        _r("S21.G00.30.004", prenom, start_line + 2),
    ]
    if contract_nature:
        records.append(_r("S21.G00.40.007", contract_nature, start_line + 3))
    for i, (code_81, amount, base_78) in enumerate(s81_rows):
        block_line = start_line + 10 + i * 10
        records.extend([
            _r("S21.G00.78.001", base_78, block_line),
            _r("S21.G00.78.004", "1000.00", block_line + 1),
            _r("S21.G00.81.001", code_81, block_line + 2),
            _r("S21.G00.81.004", amount, block_line + 3),
        ])
    return EmployeeBlock(records=records)


def _build_fixture_establishment() -> EstablishmentBlock:
    """Establishment reproducing the seven URSSAF behaviors.

    DSN sign conventions mirrored from the real sample:

    - CTP 668 declared is POSITIVE (+120) in .005 even though the reduction
      is conceptually negative; S81 018 stays NEGATIVE (-120). The
      display_absolute flag makes both render as +120.
    - CTP 003/004 declared is POSITIVE (325/151); S81 114/021 are NEGATIVE
      (-323.85 / -153.06). Business tolerance compares |decl| vs |ind|.
    """
    alice = _employee(
        empno="1",
        nom="DURAND",
        prenom="Alice",
        s81_rows=[
            # 100D (920, base 03): 1468.42
            ("045", "1468.42", "03"),
            # 100P (921, base 02): 3148.635
            ("076", "3148.635", "02"),
            # 027D (920, base 03): 7.07
            ("100", "7.07", "03"),
            # 668 (920, base 03): -120.00 signed per DSN S81 convention
            ("018", "-120.00", "03"),
            # 003 (920, base 03): -323.85 signed
            ("114", "-323.85", "03"),
            # 004 (920, base 03): -153.06 signed
            ("021", "-153.06", "03"),
        ],
        start_line=1000,
    )
    bob = _employee(
        empno="2",
        nom="MARTIN",
        prenom="Bob",
        s81_rows=[
            # 100P (921, base 02): second employee, 3148.635
            ("076", "3148.635", "02"),
        ],
        start_line=2000,
    )
    est_records: list[DSNRecord] = [
        _r("S21.G00.20.001", "78861779300013", 1),
        _r("S21.G00.20.005", "10000.00", 2),
        _r("S21.G00.22.001", "78861779300013", 3),
        _r("S21.G00.22.005", "10000.00", 4),

        # CTP 100 qualifier 920 — AT rate only (no .005)
        _r("S21.G00.23.001", "100", 10),
        _r("S21.G00.23.002", "920", 11),
        _r("S21.G00.23.003", "0.71", 12),
        _r("S21.G00.23.004", "10000.00", 13),

        # CTP 100 qualifier 921 — declared 6297.27
        _r("S21.G00.23.001", "100", 20),
        _r("S21.G00.23.002", "921", 21),
        _r("S21.G00.23.005", "6297.27", 22),

        # CTP 027 qualifier 920 — declared 7.05
        _r("S21.G00.23.001", "027", 30),
        _r("S21.G00.23.002", "920", 31),
        _r("S21.G00.23.005", "7.05", 32),

        # CTP 668 qualifier 920 — declared +120.00 (real-DSN convention).
        # With display_absolute=True the row attaches despite
        # sign_condition="negative" on the underlying rule.
        _r("S21.G00.23.001", "668", 40),
        _r("S21.G00.23.002", "920", 41),
        _r("S21.G00.23.005", "120.00", 42),

        # CTP 003 qualifier 920 — declared +325.00
        _r("S21.G00.23.001", "003", 50),
        _r("S21.G00.23.002", "920", 51),
        _r("S21.G00.23.005", "325.00", 52),

        # CTP 004 qualifier 920 — declared +151.00
        _r("S21.G00.23.001", "004", 60),
        _r("S21.G00.23.002", "920", 61),
        _r("S21.G00.23.005", "151.00", 62),

        # CTP 669 qualifier 920 — declared +50.00 (sign=positive, default rule)
        _r("S21.G00.23.001", "669", 70),
        _r("S21.G00.23.002", "920", 71),
        _r("S21.G00.23.005", "50.00", 72),
    ]
    est = EstablishmentBlock(records=est_records)
    est.employee_blocks = [alice, bob]
    return est


def _get_urssaf(est: EstablishmentBlock):
    cc = compute_contribution_comparisons(est, reference_date=REFERENCE_DATE)
    return [i for i in cc.items if i.family == "urssaf"][0]


def test_urssaf_seven_issues_regression():
    urssaf = _get_urssaf(_build_fixture_establishment())
    bds = urssaf.urssaf_code_breakdowns

    # ---- Behavior 1: 027 sub-1€ delta flagged within_unit ---------------
    row_027 = [b for b in bds if b.ctp_code == "027"]
    assert len(row_027) == 1, f"expected one 027 row, got {len(row_027)}"
    b027 = row_027[0]
    assert b027.mapping_status == "rattachable"
    assert b027.declared_amount == Decimal("7.05")
    assert b027.individual_amount == Decimal("7.07")
    assert b027.delta == Decimal("-0.02")
    assert b027.delta_within_unit is True

    # ---- Behavior 2: CTP 100 splits into 100D and 100P ------------------
    rows_100 = [b for b in bds if b.ctp_code == "100"]
    mapped_100 = {b.mapped_code for b in rows_100}
    assert mapped_100 == {"100D", "100P"}, f"expected 100D+100P split, got {mapped_100}"

    b100D = [b for b in rows_100 if b.mapped_code == "100D"][0]
    b100P = [b for b in rows_100 if b.mapped_code == "100P"][0]

    # ---- Behavior 3: 100P individual is the person-side sum -------------
    emp_sum_100P = sum(
        (e.amount for e in b100P.employees),
        Decimal(0),
    )
    assert b100P.individual_amount == emp_sum_100P, (
        "100P individual_amount must equal the sum of per-employee amounts "
        "(person-side, not all-qualifier aggregate)"
    )
    assert b100P.individual_amount == Decimal("6297.27")

    # ---- Behavior 4: 100D stays informational when employee side is partial -
    assert b100D.mapping_status == "rattachable"
    assert b100D.declared_amount == Decimal("1317.00")
    assert b100D.amount_source == "reconstructed"
    assert b100D.individual_amount == Decimal("1468.42")
    assert b100D.delta is None
    assert b100D.comparison_mode == "informational_partial"
    assert any("Comparaison informative uniquement" in warning for warning in b100D.warnings)

    # ---- Behavior 5: one row per employee under 100P --------------------
    emp_ids_100P = [e.employee_name for e in b100P.employees]
    assert len(emp_ids_100P) == len(set(emp_ids_100P))
    assert len(b100P.employees) == 2, f"expected 2 employees under 100P, got {len(b100P.employees)}"
    for emp_row in b100P.employees:
        assert emp_row.individual_codes == ["076"], emp_row.individual_codes

    # ---- Behavior 6: 668 rattachable even with positive declared --------
    row_668 = [b for b in bds if b.ctp_code == "668"]
    assert len(row_668) == 1
    b668 = row_668[0]
    assert b668.mapping_status == "rattachable", (
        f"668 must attach via relaxed gate; got {b668.mapping_status} "
        f"reason={b668.mapping_reason}"
    )
    assert b668.display_absolute is True
    assert b668.declared_amount == Decimal("120.00")
    assert b668.individual_amount == Decimal("-120.00")
    assert "018" in b668.applied_individual_codes
    # Business (abs) tolerance check: |120| vs |-120| = 0 → within_unit.
    assert b668.delta_within_unit is True

    # ---- Behavior 7: display_absolute by CTP ----------------------------
    def _flag(ctp: str) -> bool:
        row = [b for b in bds if b.ctp_code == ctp]
        assert row, f"expected a row for CTP {ctp}"
        return row[0].display_absolute

    assert _flag("668") is True
    assert _flag("003") is True
    assert _flag("004") is True
    assert _flag("669") is False

    # Extra sanity: 003/004 signed delta differs from abs delta, yet
    # delta_within_unit reflects the business (abs) comparison.
    b003 = [b for b in bds if b.ctp_code == "003"][0]
    assert b003.declared_amount == Decimal("325.00")
    assert b003.individual_amount == Decimal("-323.85")
    assert b003.delta == Decimal("648.85")  # signed, audit
    # abs delta is |325| - |-323.85| = 1.15 → above 1€, not within_unit
    assert b003.delta_within_unit is False


def test_thomas_like_shareable_fixture_end_to_end_100p_726p_ok():
    """Closest legally shareable Thomas regression fixture: parses from DSN
    text and asserts final 100P / 726P behavior end-to-end."""
    fixture = Path(__file__).parent / "fixtures" / "thomas_like_100_726_ok_minimized.dsn"
    records, skipped = parse_lines(fixture.read_text(encoding="utf-8"))
    assert skipped == []
    parsed = segment(records, skipped)
    assert len(parsed.establishments) == 1

    urssaf = _get_urssaf(parsed.establishments[0])
    rows = {b.mapped_code: b for b in urssaf.urssaf_code_breakdowns if b.ctp_code in {"100", "726"}}

    assert urssaf.status == "ok"
    assert rows["100P"].mapping_status == "rattachable"
    assert rows["726P"].mapping_status == "rattachable"
    assert rows["100P"].individual_amount == Decimal("6425.37")
    assert rows["726P"].individual_amount == Decimal("77.03")
    assert rows["100P"].delta == Decimal("0.00")
    assert rows["726P"].delta == Decimal("0.00")
    assert rows["100P"].delta_within_unit is True
    assert rows["726P"].delta_within_unit is True


def test_real_regression_shape_fixture_fixes_split_and_downgrades_partial_d_rows():
    """Minimized DSN fixture preserving the real regression shape:
    already-split apprentice 076 rows plus reconstructed D rows whose
    employee side remains partial by construction."""
    fixture = Path(__file__).parent / "fixtures" / "real_regression_apprentice_partial_d_minimized.dsn"
    records, skipped = parse_lines(fixture.read_text(encoding="utf-8"))
    assert skipped == []
    parsed = segment(records, skipped)
    assert len(parsed.establishments) == 1

    urssaf = [
        i
        for i in compute_contribution_comparisons(
            parsed.establishments[0],
            reference_date=dt.date(2026, 3, 31),
        ).items
        if i.family == "urssaf"
    ][0]
    rows = {
        b.mapped_code: b
        for b in urssaf.urssaf_code_breakdowns
        if b.mapped_code in {"100D", "100P", "726D", "726P", "863D", "863P"}
    }

    assert urssaf.aggregate_amount == Decimal("221.39")
    assert urssaf.bordereau_amount == Decimal("221.39")
    assert urssaf.component_amount is None
    assert urssaf.bordereau_vs_component_delta is None
    assert any("Sous-total composant URSSAF non affiché" in warning for warning in urssaf.warnings)

    assert rows["726P"].individual_amount == Decimal("77.94")
    assert rows["726P"].delta == Decimal("0.04")
    assert rows["726P"].delta_within_unit is True

    assert rows["100P"].individual_amount == Decimal("41.44")
    assert rows["100P"].delta == Decimal("0.00")
    assert rows["100P"].delta_within_unit is True

    assert rows["726D"].individual_amount == Decimal("36.82")
    assert rows["726D"].delta is None
    assert any("Comparaison informative uniquement" in warning for warning in rows["726D"].warnings)

    assert rows["100D"].individual_amount == Decimal("1510.13")
    assert rows["100D"].delta is None
    assert any("Comparaison informative uniquement" in warning for warning in rows["100D"].warnings)

    assert rows["863D"].individual_amount == Decimal("23.24")
    assert rows["863D"].delta is None
    assert any("Comparaison informative uniquement" in warning for warning in rows["863D"].warnings)

    assert rows["863P"].individual_amount == Decimal("101.97")
    assert rows["863P"].delta == Decimal("0.00")
    assert rows["863P"].delta_within_unit is True
