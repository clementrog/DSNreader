"""Tests for Slice 3 — Extractors."""

from __future__ import annotations

import copy
import datetime
from decimal import Decimal

import pytest

from dsn_extractor.extractors import _sum_decimal, extract
from dsn_extractor.models import DSNOutput, PayrollTracking, SocialAnalysis
from dsn_extractor.parser import parse


def _extract_fixture(text: str, source_file: str = "test.dsn") -> DSNOutput:
    return extract(parse(text), source_file)


# ── helpers ────────────────────────────────────────────────────────────────


MINIMAL_HEADER = (
    "S10.G00.00.001,'P24V01'\n"
    "S10.G00.01.001,'999888777'\n"
    "S10.G00.01.002,'00099'\n"
    "S10.G00.01.003,'TEST CORP'\n"
    "S10.G00.01.004,'1 RUE TEST'\n"
    "S10.G00.01.005,'75000'\n"
    "S10.G00.01.006,'PARIS'\n"
    "S10.G00.01.007,'FR'\n"
    "S20.G00.05.001,'01'\n"
    "S20.G00.05.002,'01'\n"
    "S20.G00.05.003,'01'\n"
    "S20.G00.05.005,'01012025'\n"
    "S20.G00.05.007,'31012025'\n"
    "S20.G00.05.009,'DSN-TEST'\n"
)

MINIMAL_ESTABLISHMENT = (
    "S21.G00.06.001,'00099'\n"
    "S21.G00.11.001,'00099'\n"
    "S21.G00.11.002,'6201Z'\n"
    "S21.G00.11.003,'1 RUE TEST'\n"
    "S21.G00.11.004,'75000'\n"
    "S21.G00.11.005,'PARIS'\n"
    "S21.G00.11.008,'TEST PARIS'\n"
    "S21.G00.11.022,'1486'\n"
)


def _make_employee(
    name: str = "DOE",
    first: str = "JOHN",
    birth: str = "01011990",
    sex: str = "1",
    contract_start: str = "01032020",
    conv_status: str = "04",
    ret_cat: str = "01",
    nature: str = "01",
    net_fiscal: str = "2000.00",
    net_paid: str = "1800.00",
    pas: str = "200.00",
    ccn: str | None = None,
    contract_end: str | None = None,
    rupture: str | None = None,
    absences: list[str] | None = None,
) -> str:
    lines = [
        f"S21.G00.30.001,'{name}'",
        f"S21.G00.30.002,'{name}'",
        f"S21.G00.30.004,'{first}'",
        f"S21.G00.30.006,'{sex}'",
        f"S21.G00.40.001,'{contract_start}'",
        f"S21.G00.40.002,'{conv_status}'",
        f"S21.G00.40.003,'{ret_cat}'",
        f"S21.G00.40.007,'{nature}'",
    ]
    if ccn is not None:
        lines.append(f"S21.G00.40.017,'{ccn}'")
    lines += [
        f"S21.G00.50.002,'{net_fiscal}'",
        f"S21.G00.50.004,'{net_paid}'",
        f"S21.G00.50.009,'{pas}'",
    ]
    if absences:
        for motif_code in absences:
            lines.append(f"S21.G00.65.001,'{motif_code}'")
            lines.append(f"S21.G00.65.002,'01012025'")
            lines.append(f"S21.G00.65.003,'15012025'")
    if contract_end is not None:
        lines.append(f"S21.G00.62.001,'{contract_end}'")
        if rupture is not None:
            lines.append(f"S21.G00.62.002,'{rupture}'")
    return "\n".join(lines) + "\n"


FOOTER = "S90.G00.90.001,'1'\nS90.G00.90.002,'10'\n"


# ═══════════════════════════════════════════════════════════════════════════
# Declaration extraction
# ═══════════════════════════════════════════════════════════════════════════


class TestExtractDeclaration:
    def test_norm_version(self, single_establishment_text: str) -> None:
        out = _extract_fixture(single_establishment_text)
        assert out.declaration.norm_version == "P24V01"

    def test_declaration_codes(self, single_establishment_text: str) -> None:
        out = _extract_fixture(single_establishment_text)
        assert out.declaration.declaration_nature_code == "01"
        assert out.declaration.declaration_kind_code == "01"
        assert out.declaration.declaration_rank_code == "01"

    def test_period_start(self, single_establishment_text: str) -> None:
        out = _extract_fixture(single_establishment_text)
        assert out.declaration.period_start == datetime.date(2025, 1, 1)

    def test_period_end(self, single_establishment_text: str) -> None:
        out = _extract_fixture(single_establishment_text)
        assert out.declaration.period_end == datetime.date(2025, 1, 31)

    def test_month(self, single_establishment_text: str) -> None:
        out = _extract_fixture(single_establishment_text)
        assert out.declaration.month == "2025-01"

    def test_dsn_id(self, single_establishment_text: str) -> None:
        out = _extract_fixture(single_establishment_text)
        assert out.declaration.dsn_id == "DSN-2025-01"


# ═══════════════════════════════════════════════════════════════════════════
# Company extraction
# ═══════════════════════════════════════════════════════════════════════════


class TestExtractCompany:
    def test_siren(self, single_establishment_text: str) -> None:
        out = _extract_fixture(single_establishment_text)
        assert out.company.siren == "123456789"

    def test_nic(self, single_establishment_text: str) -> None:
        out = _extract_fixture(single_establishment_text)
        assert out.company.nic == "00011"

    def test_siret(self, single_establishment_text: str) -> None:
        out = _extract_fixture(single_establishment_text)
        assert out.company.siret == "12345678900011"

    def test_name(self, single_establishment_text: str) -> None:
        out = _extract_fixture(single_establishment_text)
        assert out.company.name == "ACME CORP"

    def test_address(self, single_establishment_text: str) -> None:
        out = _extract_fixture(single_establishment_text)
        assert out.company.address == "10 RUE DE LA PAIX"

    def test_postal_code(self, single_establishment_text: str) -> None:
        out = _extract_fixture(single_establishment_text)
        assert out.company.postal_code == "75001"

    def test_city(self, single_establishment_text: str) -> None:
        out = _extract_fixture(single_establishment_text)
        assert out.company.city == "PARIS"

    def test_country_code(self, single_establishment_text: str) -> None:
        out = _extract_fixture(single_establishment_text)
        assert out.company.country_code == "FR"


# ═══════════════════════════════════════════════════════════════════════════
# Establishment identity extraction
# ═══════════════════════════════════════════════════════════════════════════


class TestEstablishmentIdentitySingle:
    def test_nic(self, single_establishment_text: str) -> None:
        out = _extract_fixture(single_establishment_text)
        assert out.establishments[0].identity.nic == "00011"

    def test_siret(self, single_establishment_text: str) -> None:
        out = _extract_fixture(single_establishment_text)
        assert out.establishments[0].identity.siret == "12345678900011"

    def test_name(self, single_establishment_text: str) -> None:
        out = _extract_fixture(single_establishment_text)
        assert out.establishments[0].identity.name == "ACME PARIS"

    def test_naf_code(self, single_establishment_text: str) -> None:
        out = _extract_fixture(single_establishment_text)
        assert out.establishments[0].identity.naf_code == "6201Z"

    def test_ccn_code(self, single_establishment_text: str) -> None:
        out = _extract_fixture(single_establishment_text)
        assert out.establishments[0].identity.ccn_code == "1486"

    def test_address(self, single_establishment_text: str) -> None:
        out = _extract_fixture(single_establishment_text)
        assert out.establishments[0].identity.address == "10 RUE DE LA PAIX"
        assert out.establishments[0].identity.postal_code == "75001"
        assert out.establishments[0].identity.city == "PARIS"


class TestEstablishmentIdentityMulti:
    def test_two_establishments(self, multi_establishment_text: str) -> None:
        out = _extract_fixture(multi_establishment_text)
        assert len(out.establishments) == 2

    def test_first_establishment(self, multi_establishment_text: str) -> None:
        out = _extract_fixture(multi_establishment_text)
        est = out.establishments[0]
        assert est.identity.nic == "00011"
        assert est.identity.name == "ACME PARIS"
        assert est.identity.ccn_code == "1486"

    def test_second_establishment(self, multi_establishment_text: str) -> None:
        out = _extract_fixture(multi_establishment_text)
        est = out.establishments[1]
        assert est.identity.nic == "00022"
        assert est.identity.name == "ACME LYON"
        assert est.identity.ccn_code == "2120"

    def test_multiple_establishments_warning(self, multi_establishment_text: str) -> None:
        out = _extract_fixture(multi_establishment_text)
        assert any("Multiple establishments" in w for w in out.global_quality.warnings)


class TestEstablishmentIdentityFallback:
    def test_fallback_to_s06(self) -> None:
        text = (
            MINIMAL_HEADER
            + "S21.G00.06.001,'00099'\n"
            + "S21.G00.06.002,'11'\n"
            + _make_employee()
            + FOOTER
        )
        out = _extract_fixture(text)
        est = out.establishments[0]
        assert est.identity.nic == "00099"
        assert any("falling back to S21.G00.06" in w for w in est.quality.warnings)

    def test_ccn_fallback_from_uniform_employees(self) -> None:
        text = (
            MINIMAL_HEADER
            + "S21.G00.06.001,'00099'\n"
            + "S21.G00.06.002,'11'\n"
            + _make_employee(name="A", ccn="2345")
            + _make_employee(name="B", ccn="2345")
            + FOOTER
        )
        out = _extract_fixture(text)
        assert out.establishments[0].identity.ccn_code == "2345"

    def test_ccn_fallback_conflicting_employees(self) -> None:
        text = (
            MINIMAL_HEADER
            + "S21.G00.06.001,'00099'\n"
            + "S21.G00.06.002,'11'\n"
            + _make_employee(name="A", ccn="2345")
            + _make_employee(name="B", ccn="9999")
            + FOOTER
        )
        out = _extract_fixture(text)
        est = out.establishments[0]
        assert est.identity.ccn_code is None
        assert any("Conflicting employee CCN" in w for w in est.quality.warnings)

    def test_ccn_conflict_warning_exactly_once(self) -> None:
        text = (
            MINIMAL_HEADER
            + "S21.G00.06.001,'00099'\n"
            + "S21.G00.06.002,'11'\n"
            + _make_employee(name="A", ccn="2345")
            + _make_employee(name="B", ccn="9999")
            + _make_employee(name="C", ccn="1111")
            + FOOTER
        )
        out = _extract_fixture(text)
        ccn_warnings = [w for w in out.establishments[0].quality.warnings if "Conflicting employee CCN" in w]
        assert len(ccn_warnings) == 1


# ═══════════════════════════════════════════════════════════════════════════
# Counts extraction — single establishment
# ═══════════════════════════════════════════════════════════════════════════


class TestCountsSingleEstablishment:
    def test_employee_blocks_count(self, single_establishment_text: str) -> None:
        out = _extract_fixture(single_establishment_text)
        assert out.establishments[0].counts.employee_blocks_count == 3

    def test_stagiaires(self, single_establishment_text: str) -> None:
        out = _extract_fixture(single_establishment_text)
        assert out.establishments[0].counts.stagiaires == 1

    def test_by_retirement_category_code(self, single_establishment_text: str) -> None:
        out = _extract_fixture(single_establishment_text)
        expected = {"01": 1, "04": 1, "99": 1}
        assert out.establishments[0].counts.employees_by_retirement_category_code == expected

    def test_by_retirement_category_label(self, single_establishment_text: str) -> None:
        out = _extract_fixture(single_establishment_text)
        expected = {"cadre": 1, "non_cadre": 1, "no_complementary_retirement": 1}
        assert out.establishments[0].counts.employees_by_retirement_category_label == expected

    def test_by_conventional_status_code(self, single_establishment_text: str) -> None:
        out = _extract_fixture(single_establishment_text)
        expected = {"04": 1, "16": 1, "99": 1}
        assert out.establishments[0].counts.employees_by_conventional_status_code == expected

    def test_by_contract_nature_code(self, single_establishment_text: str) -> None:
        out = _extract_fixture(single_establishment_text)
        expected = {"01": 1, "02": 1, "29": 1}
        assert out.establishments[0].counts.employees_by_contract_nature_code == expected

    def test_new_employees_in_month(self, single_establishment_text: str) -> None:
        # MARTIN (15/01/2025) and PETIT (01/01/2025) are new; DUPONT (01/03/2020) is not
        out = _extract_fixture(single_establishment_text)
        assert out.establishments[0].counts.new_employees_in_month == 2

    def test_exiting_employees_in_month(self, single_establishment_text: str) -> None:
        # PETIT: end 31/01/2025, rupture 031 != 099
        out = _extract_fixture(single_establishment_text)
        assert out.establishments[0].counts.exiting_employees_in_month == 1


class TestCountsMultiEstablishment:
    def test_per_establishment_employee_count(self, multi_establishment_text: str) -> None:
        out = _extract_fixture(multi_establishment_text)
        assert out.establishments[0].counts.employee_blocks_count == 2  # DUPONT, MARTIN
        assert out.establishments[1].counts.employee_blocks_count == 1  # BERNARD

    def test_global_employee_count(self, multi_establishment_text: str) -> None:
        out = _extract_fixture(multi_establishment_text)
        assert out.global_counts.employee_blocks_count == 3

    def test_global_counts_are_sum_of_per_est(self, multi_establishment_text: str) -> None:
        out = _extract_fixture(multi_establishment_text)
        g = out.global_counts
        est_sum = sum(e.counts.employee_blocks_count for e in out.establishments)
        assert g.employee_blocks_count == est_sum
        assert g.stagiaires == sum(e.counts.stagiaires for e in out.establishments)
        assert g.new_employees_in_month == sum(
            e.counts.new_employees_in_month for e in out.establishments
        )
        assert g.exiting_employees_in_month == sum(
            e.counts.exiting_employees_in_month for e in out.establishments
        )


# ═══════════════════════════════════════════════════════════════════════════
# Amounts extraction
# ═══════════════════════════════════════════════════════════════════════════


class TestAmountsSingleEstablishment:
    def test_tickets_restaurant(self, single_establishment_text: str) -> None:
        out = _extract_fixture(single_establishment_text)
        assert out.establishments[0].amounts.tickets_restaurant_employer_contribution_total == Decimal("450.00")

    def test_transport_public(self, single_establishment_text: str) -> None:
        out = _extract_fixture(single_establishment_text)
        assert out.establishments[0].amounts.transport_public_total == Decimal("225.00")

    def test_transport_personal_absent(self, single_establishment_text: str) -> None:
        out = _extract_fixture(single_establishment_text)
        assert out.establishments[0].amounts.transport_personal_total is None


class TestAmountsMultiEstablishment:
    def test_est1_tickets(self, multi_establishment_text: str) -> None:
        out = _extract_fixture(multi_establishment_text)
        assert out.establishments[0].amounts.tickets_restaurant_employer_contribution_total == Decimal("300.00")

    def test_est2_tickets(self, multi_establishment_text: str) -> None:
        out = _extract_fixture(multi_establishment_text)
        assert out.establishments[1].amounts.tickets_restaurant_employer_contribution_total == Decimal("150.00")

    def test_est2_transport_personal(self, multi_establishment_text: str) -> None:
        out = _extract_fixture(multi_establishment_text)
        assert out.establishments[1].amounts.transport_personal_total == Decimal("75.00")

    def test_global_tickets(self, multi_establishment_text: str) -> None:
        out = _extract_fixture(multi_establishment_text)
        assert out.global_amounts.tickets_restaurant_employer_contribution_total == Decimal("450.00")

    def test_global_transport_public_null(self, multi_establishment_text: str) -> None:
        out = _extract_fixture(multi_establishment_text)
        # Neither establishment has type 18
        assert out.global_amounts.transport_public_total is None

    def test_global_transport_personal(self, multi_establishment_text: str) -> None:
        out = _extract_fixture(multi_establishment_text)
        # Only est2 has type 19
        assert out.global_amounts.transport_personal_total == Decimal("75.00")


class TestAmountsNoS54:
    def test_all_amounts_null(self, no_s54_blocks_text: str) -> None:
        out = _extract_fixture(no_s54_blocks_text)
        a = out.establishments[0].amounts
        assert a.tickets_restaurant_employer_contribution_total is None
        assert a.transport_public_total is None
        assert a.transport_personal_total is None

    def test_no_s54_warning(self, no_s54_blocks_text: str) -> None:
        out = _extract_fixture(no_s54_blocks_text)
        assert any("No S21.G00.54" in w for w in out.establishments[0].quality.warnings)


class TestAmountsWithS54:
    def test_all_three_types(self, with_s54_blocks_text: str) -> None:
        out = _extract_fixture(with_s54_blocks_text)
        a = out.establishments[0].amounts
        assert a.tickets_restaurant_employer_contribution_total == Decimal("500.00")
        assert a.transport_public_total == Decimal("280.00")
        assert a.transport_personal_total == Decimal("100.00")


# ═══════════════════════════════════════════════════════════════════════════
# Extras extraction
# ═══════════════════════════════════════════════════════════════════════════


class TestExtrasSingleEstablishment:
    def test_net_fiscal_sum(self, single_establishment_text: str) -> None:
        out = _extract_fixture(single_establishment_text)
        # 2500 + 1800 + 600
        assert out.establishments[0].extras.net_fiscal_sum == Decimal("4900.00")

    def test_net_paid_sum(self, single_establishment_text: str) -> None:
        out = _extract_fixture(single_establishment_text)
        # 2300 + 1650 + 580
        assert out.establishments[0].extras.net_paid_sum == Decimal("4530.00")

    def test_pas_sum(self, single_establishment_text: str) -> None:
        out = _extract_fixture(single_establishment_text)
        # 250 + 180 + 0
        assert out.establishments[0].extras.pas_sum == Decimal("430.00")

    def test_gross_sum_not_implemented(self, single_establishment_text: str) -> None:
        out = _extract_fixture(single_establishment_text)
        assert out.establishments[0].extras.gross_sum_from_salary_bases is None


# ═══════════════════════════════════════════════════════════════════════════
# Unknown enum codes
# ═══════════════════════════════════════════════════════════════════════════


class TestUnknownEnumCodes:
    def test_unknown_retirement_code_preserved(self, unknown_enum_codes_text: str) -> None:
        out = _extract_fixture(unknown_enum_codes_text)
        assert "03" in out.establishments[0].counts.employees_by_retirement_category_code

    def test_unknown_retirement_label_passthrough(self, unknown_enum_codes_text: str) -> None:
        out = _extract_fixture(unknown_enum_codes_text)
        # Unknown code "03" passes through as raw value in label dict
        assert "03" in out.establishments[0].counts.employees_by_retirement_category_label

    def test_unknown_retirement_warning(self, unknown_enum_codes_text: str) -> None:
        out = _extract_fixture(unknown_enum_codes_text)
        assert any("Unknown retirement category code: '03'" in w for w in out.global_quality.warnings)

    def test_unknown_contract_nature_preserved(self, unknown_enum_codes_text: str) -> None:
        out = _extract_fixture(unknown_enum_codes_text)
        assert "77" in out.establishments[0].counts.employees_by_contract_nature_code

    def test_unknown_contract_nature_warning(self, unknown_enum_codes_text: str) -> None:
        out = _extract_fixture(unknown_enum_codes_text)
        assert any("Unknown contract nature code: '77'" in w for w in out.global_quality.warnings)

    def test_extraction_succeeds(self, unknown_enum_codes_text: str) -> None:
        out = _extract_fixture(unknown_enum_codes_text)
        assert isinstance(out, DSNOutput)


# ═══════════════════════════════════════════════════════════════════════════
# Missing contract fields
# ═══════════════════════════════════════════════════════════════════════════


class TestMissingContractFields:
    def test_missing_contract_start_warning(self, missing_contract_fields_text: str) -> None:
        out = _extract_fixture(missing_contract_fields_text)
        assert any("missing contract start date" in w for w in out.global_quality.warnings)

    def test_missing_rupture_code_warning(self, missing_contract_fields_text: str) -> None:
        out = _extract_fixture(missing_contract_fields_text)
        assert any("missing rupture code" in w for w in out.global_quality.warnings)

    def test_employee_without_start_not_counted_as_new(
        self, missing_contract_fields_text: str
    ) -> None:
        # ROUX has no S21.G00.40.001; BLANC has start 01/06/2020 (outside Jan 2025)
        out = _extract_fixture(missing_contract_fields_text)
        assert out.establishments[0].counts.new_employees_in_month == 0

    def test_employee_with_end_but_no_rupture_counted_as_exiting(
        self, missing_contract_fields_text: str
    ) -> None:
        # BLANC has end 31/01/2025 in period, rupture_code is None != "099"
        out = _extract_fixture(missing_contract_fields_text)
        assert out.establishments[0].counts.exiting_employees_in_month == 1


# ═══════════════════════════════════════════════════════════════════════════
# Period-boundary logic
# ═══════════════════════════════════════════════════════════════════════════


class TestPeriodBoundary:
    """Verify inclusive [period_start, period_end] boundary for hires and exits."""

    def test_hire_on_period_start(self) -> None:
        text = (
            MINIMAL_HEADER + MINIMAL_ESTABLISHMENT
            + _make_employee(contract_start="01012025")
            + FOOTER
        )
        out = _extract_fixture(text)
        assert out.establishments[0].counts.new_employees_in_month == 1

    def test_hire_on_period_end(self) -> None:
        text = (
            MINIMAL_HEADER + MINIMAL_ESTABLISHMENT
            + _make_employee(contract_start="31012025")
            + FOOTER
        )
        out = _extract_fixture(text)
        assert out.establishments[0].counts.new_employees_in_month == 1

    def test_hire_before_period_not_counted(self) -> None:
        text = (
            MINIMAL_HEADER + MINIMAL_ESTABLISHMENT
            + _make_employee(contract_start="31122024")
            + FOOTER
        )
        out = _extract_fixture(text)
        assert out.establishments[0].counts.new_employees_in_month == 0

    def test_hire_after_period_not_counted(self) -> None:
        text = (
            MINIMAL_HEADER + MINIMAL_ESTABLISHMENT
            + _make_employee(contract_start="01022025")
            + FOOTER
        )
        out = _extract_fixture(text)
        assert out.establishments[0].counts.new_employees_in_month == 0

    def test_exit_on_period_start(self) -> None:
        text = (
            MINIMAL_HEADER + MINIMAL_ESTABLISHMENT
            + _make_employee(contract_end="01012025", rupture="031")
            + FOOTER
        )
        out = _extract_fixture(text)
        assert out.establishments[0].counts.exiting_employees_in_month == 1

    def test_exit_on_period_end(self) -> None:
        text = (
            MINIMAL_HEADER + MINIMAL_ESTABLISHMENT
            + _make_employee(contract_end="31012025", rupture="031")
            + FOOTER
        )
        out = _extract_fixture(text)
        assert out.establishments[0].counts.exiting_employees_in_month == 1

    def test_exit_outside_period_not_counted(self) -> None:
        text = (
            MINIMAL_HEADER + MINIMAL_ESTABLISHMENT
            + _make_employee(contract_end="01022025", rupture="031")
            + FOOTER
        )
        out = _extract_fixture(text)
        assert out.establishments[0].counts.exiting_employees_in_month == 0

    def test_exit_with_rupture_099_not_counted(self) -> None:
        text = (
            MINIMAL_HEADER + MINIMAL_ESTABLISHMENT
            + _make_employee(contract_end="15012025", rupture="099")
            + FOOTER
        )
        out = _extract_fixture(text)
        assert out.establishments[0].counts.exiting_employees_in_month == 0

    def test_invalid_contract_start_not_counted(self) -> None:
        text = (
            MINIMAL_HEADER + MINIMAL_ESTABLISHMENT
            + _make_employee(contract_start="INVALID")
            + FOOTER
        )
        out = _extract_fixture(text)
        assert out.establishments[0].counts.new_employees_in_month == 0

    def test_invalid_contract_end_not_counted(self) -> None:
        text = (
            MINIMAL_HEADER + MINIMAL_ESTABLISHMENT
            + _make_employee(contract_end="BADDATE", rupture="031")
            + FOOTER
        )
        out = _extract_fixture(text)
        assert out.establishments[0].counts.exiting_employees_in_month == 0


# ═══════════════════════════════════════════════════════════════════════════
# Null-vs-sum aggregation semantics
# ═══════════════════════════════════════════════════════════════════════════


class TestSumDecimalSemantics:
    def test_null_plus_null(self) -> None:
        assert _sum_decimal(None, None) is None

    def test_null_plus_value(self) -> None:
        assert _sum_decimal(None, Decimal("5")) == Decimal("5")

    def test_value_plus_null(self) -> None:
        assert _sum_decimal(Decimal("3"), None) == Decimal("3")

    def test_value_plus_value(self) -> None:
        assert _sum_decimal(Decimal("3"), Decimal("7")) == Decimal("10")


class TestNullAggregationGlobal:
    def test_all_null_stays_null(self) -> None:
        """When all establishments have None for a field, global stays None."""
        # no_s54 fixture: one establishment, all amounts null
        text = (
            MINIMAL_HEADER
            + "S21.G00.06.001,'00099'\n"
            + "S21.G00.11.001,'00099'\n"
            + "S21.G00.11.008,'EST1'\n"
            + _make_employee(name="A")
            + FOOTER
        )
        out = _extract_fixture(text)
        assert out.global_amounts.tickets_restaurant_employer_contribution_total is None
        assert out.global_amounts.transport_public_total is None
        assert out.global_amounts.transport_personal_total is None

    def test_any_present_becomes_sum(self) -> None:
        """When any establishment has a value, global becomes numeric sum."""
        # Two establishments, only one has S54 type 17
        text = (
            MINIMAL_HEADER
            + "S21.G00.06.001,'00011'\n"
            + "S21.G00.11.001,'00011'\n"
            + "S21.G00.11.008,'EST1'\n"
            + _make_employee(name="A")
            + "S21.G00.06.001,'00022'\n"
            + "S21.G00.11.001,'00022'\n"
            + "S21.G00.11.008,'EST2'\n"
            + _make_employee(name="B")
            + "S21.G00.54.001,'17'\n"
            + "S21.G00.54.002,'100.00'\n"
            + FOOTER
        )
        out = _extract_fixture(text)
        # Est1 has no S54 -> None; Est2 has type 17 -> 100
        assert out.establishments[0].amounts.tickets_restaurant_employer_contribution_total is None
        assert out.establishments[1].amounts.tickets_restaurant_employer_contribution_total == Decimal("100.00")
        # Global: None + 100 = 100
        assert out.global_amounts.tickets_restaurant_employer_contribution_total == Decimal("100.00")
        # Transport stays None for both
        assert out.global_amounts.transport_public_total is None

    def test_extras_null_when_no_employees(self) -> None:
        """Establishment with no employees has null extras."""
        text = (
            MINIMAL_HEADER + MINIMAL_ESTABLISHMENT + FOOTER
        )
        out = _extract_fixture(text)
        assert out.establishments[0].extras.net_fiscal_sum is None
        assert out.establishments[0].extras.net_paid_sum is None
        assert out.establishments[0].extras.pas_sum is None


# ═══════════════════════════════════════════════════════════════════════════
# Read-only / idempotency safeguard
# ═══════════════════════════════════════════════════════════════════════════


class TestReadOnlyIdempotency:
    def test_extract_twice_gives_identical_output(self, single_establishment_text: str) -> None:
        parsed = parse(single_establishment_text)
        out1 = extract(parsed, "test.dsn")
        out2 = extract(parsed, "test.dsn")
        assert out1.model_dump() == out2.model_dump()

    def test_parser_warnings_not_mutated(self, single_establishment_text: str) -> None:
        parsed = parse(single_establishment_text)
        original_warnings = list(parsed.warnings)
        extract(parsed, "test.dsn")
        assert parsed.warnings == original_warnings

    def test_employee_blocks_not_mutated(self, single_establishment_text: str) -> None:
        parsed = parse(single_establishment_text)
        original_count = sum(
            len(est.employee_blocks) for est in parsed.establishments
        )
        extract(parsed, "test.dsn")
        after_count = sum(
            len(est.employee_blocks) for est in parsed.establishments
        )
        assert after_count == original_count


# ═══════════════════════════════════════════════════════════════════════════
# Duplicate / ambiguous rubric occurrences
# ═══════════════════════════════════════════════════════════════════════════


class TestDuplicateRubrics:
    def test_duplicate_retirement_category_uses_first(self) -> None:
        """_find_value returns first match; duplicate retirement codes are ignored."""
        emp_lines = (
            "S21.G00.30.001,'DUPL'\n"
            "S21.G00.30.002,'TEST'\n"
            "S21.G00.30.004,'01011990'\n"
            "S21.G00.30.006,'1'\n"
            "S21.G00.40.001,'01032020'\n"
            "S21.G00.40.002,'04'\n"
            "S21.G00.40.003,'01'\n"  # first value: cadre
            "S21.G00.40.003,'04'\n"  # duplicate: non_cadre — should be ignored
            "S21.G00.40.007,'01'\n"
            "S21.G00.50.002,'1000.00'\n"
            "S21.G00.50.004,'900.00'\n"
            "S21.G00.50.009,'100.00'\n"
        )
        text = MINIMAL_HEADER + MINIMAL_ESTABLISHMENT + emp_lines + FOOTER
        out = _extract_fixture(text)
        # First match "01" (cadre) is used, not "04"
        assert out.establishments[0].counts.employees_by_retirement_category_code == {"01": 1}
        assert out.establishments[0].counts.employees_by_retirement_category_label == {"cadre": 1}

    def test_duplicate_net_fiscal_uses_first(self) -> None:
        """Only the first S21.G00.50.002 per employee is summed."""
        emp_lines = (
            "S21.G00.30.001,'DUPL'\n"
            "S21.G00.30.002,'TEST'\n"
            "S21.G00.30.004,'01011990'\n"
            "S21.G00.30.006,'1'\n"
            "S21.G00.40.001,'01032020'\n"
            "S21.G00.40.002,'04'\n"
            "S21.G00.40.003,'01'\n"
            "S21.G00.40.007,'01'\n"
            "S21.G00.50.002,'1000.00'\n"  # first
            "S21.G00.50.002,'9999.00'\n"  # duplicate — ignored
            "S21.G00.50.004,'900.00'\n"
            "S21.G00.50.009,'100.00'\n"
        )
        text = MINIMAL_HEADER + MINIMAL_ESTABLISHMENT + emp_lines + FOOTER
        out = _extract_fixture(text)
        assert out.establishments[0].extras.net_fiscal_sum == Decimal("1000.00")


# ═══════════════════════════════════════════════════════════════════════════
# Warning assertion rigor
# ═══════════════════════════════════════════════════════════════════════════


class TestWarningRigor:
    def test_unknown_enum_one_warning_per_employee(self) -> None:
        """Same unknown code on 2 employees -> exactly 2 warnings."""
        text = (
            MINIMAL_HEADER + MINIMAL_ESTABLISHMENT
            + _make_employee(name="A", ret_cat="77")
            + _make_employee(name="B", ret_cat="77")
            + FOOTER
        )
        out = _extract_fixture(text)
        ret_warnings = [w for w in out.global_quality.warnings if "Unknown retirement" in w]
        assert len(ret_warnings) == 2

    def test_missing_contract_start_one_per_employee(self) -> None:
        """Each employee missing start date gets exactly one warning."""
        emp_no_start = (
            "S21.G00.30.001,'NOSTART'\n"
            "S21.G00.30.002,'X'\n"
            "S21.G00.30.004,'01011990'\n"
            "S21.G00.30.006,'1'\n"
            "S21.G00.40.002,'04'\n"
            "S21.G00.40.003,'01'\n"
            "S21.G00.40.007,'01'\n"
            "S21.G00.50.002,'1000.00'\n"
            "S21.G00.50.004,'900.00'\n"
            "S21.G00.50.009,'100.00'\n"
        )
        text = MINIMAL_HEADER + MINIMAL_ESTABLISHMENT + emp_no_start + emp_no_start + FOOTER
        out = _extract_fixture(text)
        start_warnings = [w for w in out.global_quality.warnings if "missing contract start" in w]
        assert len(start_warnings) == 2

    def test_no_s54_warning_once_per_establishment(self) -> None:
        """Each establishment without S54 gets exactly one warning."""
        text = (
            MINIMAL_HEADER
            + "S21.G00.06.001,'00011'\n"
            + "S21.G00.11.001,'00011'\n"
            + "S21.G00.11.008,'EST1'\n"
            + _make_employee(name="A")
            + "S21.G00.06.001,'00022'\n"
            + "S21.G00.11.001,'00022'\n"
            + "S21.G00.11.008,'EST2'\n"
            + _make_employee(name="B")
            + FOOTER
        )
        out = _extract_fixture(text)
        s54_warnings = [w for w in out.global_quality.warnings if "No S21.G00.54" in w]
        assert len(s54_warnings) == 2  # one per establishment

    def test_warning_order_is_deterministic(self, single_establishment_text: str) -> None:
        """Warnings appear in the same order on repeated extraction."""
        parsed = parse(single_establishment_text)
        w1 = extract(parsed, "test.dsn").global_quality.warnings
        w2 = extract(parsed, "test.dsn").global_quality.warnings
        assert w1 == w2


# ═══════════════════════════════════════════════════════════════════════════
# Quality warnings — global level
# ═══════════════════════════════════════════════════════════════════════════


class TestQualityWarnings:
    def test_multiple_establishments_warning(self, multi_establishment_text: str) -> None:
        out = _extract_fixture(multi_establishment_text)
        assert any("Multiple establishments" in w for w in out.global_quality.warnings)

    def test_no_s54_warning_in_global(self, no_s54_blocks_text: str) -> None:
        out = _extract_fixture(no_s54_blocks_text)
        assert any("No S21.G00.54" in w for w in out.global_quality.warnings)

    def test_missing_period_start_warning(self) -> None:
        text = (
            "S10.G00.00.001,'P24V01'\n"
            "S10.G00.01.001,'999888777'\n"
            "S10.G00.01.002,'00099'\n"
            "S20.G00.05.007,'31012025'\n"
            + FOOTER
        )
        out = _extract_fixture(text)
        assert any("Missing or invalid period start" in w for w in out.global_quality.warnings)

    def test_missing_period_end_warning(self) -> None:
        text = (
            "S10.G00.00.001,'P24V01'\n"
            "S10.G00.01.001,'999888777'\n"
            "S10.G00.01.002,'00099'\n"
            "S20.G00.05.005,'01012025'\n"
            + FOOTER
        )
        out = _extract_fixture(text)
        assert any("Missing or invalid period end" in w for w in out.global_quality.warnings)


# ═══════════════════════════════════════════════════════════════════════════
# Edge cases
# ═══════════════════════════════════════════════════════════════════════════


class TestEdgeCases:
    def test_empty_file(self) -> None:
        out = _extract_fixture("", source_file="empty.dsn")
        assert out.source_file == "empty.dsn"
        assert out.declaration.month is None
        assert out.establishments == []
        assert out.global_counts.employee_blocks_count == 0

    def test_source_file_passthrough(self, single_establishment_text: str) -> None:
        out = _extract_fixture(single_establishment_text, source_file="my_file.dsn")
        assert out.source_file == "my_file.dsn"

    def test_establishment_without_employees(self) -> None:
        text = MINIMAL_HEADER + MINIMAL_ESTABLISHMENT + FOOTER
        out = _extract_fixture(text)
        assert out.establishments[0].counts.employee_blocks_count == 0
        assert out.establishments[0].counts.stagiaires == 0
        assert out.establishments[0].extras.net_fiscal_sum is None

    def test_no_establishments(self) -> None:
        text = (
            "S10.G00.00.001,'P24V01'\n"
            "S10.G00.01.001,'999888777'\n"
            "S10.G00.01.002,'00099'\n"
            "S20.G00.05.005,'01012025'\n"
            "S20.G00.05.007,'31012025'\n"
            + FOOTER
        )
        out = _extract_fixture(text)
        assert out.establishments == []
        assert out.global_counts.employee_blocks_count == 0
        assert out.global_amounts.tickets_restaurant_employer_contribution_total is None

    def test_ccn_null_when_no_source(self, no_s54_blocks_text: str) -> None:
        out = _extract_fixture(no_s54_blocks_text)
        # No S21.G00.11.022 and no S21.G00.40.017 in this fixture
        assert out.establishments[0].identity.ccn_code is None


# ═══════════════════════════════════════════════════════════════════════════
# Global aggregation
# ═══════════════════════════════════════════════════════════════════════════


class TestGlobalAggregation:
    def test_global_amounts_match_sum(self, multi_establishment_text: str) -> None:
        out = _extract_fixture(multi_establishment_text)
        for field in ("tickets_restaurant_employer_contribution_total", "transport_public_total", "transport_personal_total"):
            est_vals = [getattr(e.amounts, field) for e in out.establishments]
            expected = None
            for v in est_vals:
                if v is not None:
                    expected = (expected or Decimal(0)) + v
            assert getattr(out.global_amounts, field) == expected, f"Mismatch on {field}"

    def test_global_extras_match_sum(self, multi_establishment_text: str) -> None:
        out = _extract_fixture(multi_establishment_text)
        for field in ("net_fiscal_sum", "net_paid_sum", "pas_sum"):
            est_vals = [getattr(e.extras, field) for e in out.establishments]
            expected = None
            for v in est_vals:
                if v is not None:
                    expected = (expected or Decimal(0)) + v
            assert getattr(out.global_extras, field) == expected, f"Mismatch on {field}"

    def test_global_dict_counts_match_sum(self, multi_establishment_text: str) -> None:
        out = _extract_fixture(multi_establishment_text)
        # Check retirement category code dict is merged correctly
        merged: dict[str, int] = {}
        for e in out.establishments:
            for k, v in e.counts.employees_by_retirement_category_code.items():
                merged[k] = merged.get(k, 0) + v
        assert out.global_counts.employees_by_retirement_category_code == merged

    def test_global_new_count_fields_match_sum(self, multi_establishment_text: str) -> None:
        out = _extract_fixture(multi_establishment_text)
        g = out.global_counts
        assert g.absences_employees_count == sum(
            e.counts.absences_employees_count for e in out.establishments
        )
        assert g.absences_events_count == sum(
            e.counts.absences_events_count for e in out.establishments
        )
        for field in (
            "employees_by_contract_nature_label",
            "exit_reasons_by_code",
            "exit_reasons_by_label",
            "absences_by_code",
        ):
            merged: dict[str, int] = {}
            for e in out.establishments:
                for k, v in getattr(e.counts, field).items():
                    merged[k] = merged.get(k, 0) + v
            assert getattr(g, field) == merged, f"Mismatch on {field}"


# ═══════════════════════════════════════════════════════════════════════════
# Contract nature labels
# ═══════════════════════════════════════════════════════════════════════════


class TestContractNatureLabels:
    def test_known_code_has_label(self, single_establishment_text: str) -> None:
        out = _extract_fixture(single_establishment_text)
        labels = out.establishments[0].counts.employees_by_contract_nature_label
        assert "cdi_prive" in labels
        assert "cdd_prive" in labels
        assert "convention_stage" in labels

    def test_unknown_code_preserved_in_label_dict(self) -> None:
        text = (
            MINIMAL_HEADER + MINIMAL_ESTABLISHMENT
            + _make_employee(nature="77")
            + FOOTER
        )
        out = _extract_fixture(text)
        # Unknown code passes through as raw value in label dict
        assert "77" in out.establishments[0].counts.employees_by_contract_nature_label

    def test_all_enum_codes_no_unknown_warning(self) -> None:
        """Every code in CONTRACT_NATURE_LABELS must not generate a warning."""
        from dsn_extractor.enums import CONTRACT_NATURE_LABELS

        for code in CONTRACT_NATURE_LABELS:
            text = (
                MINIMAL_HEADER + MINIMAL_ESTABLISHMENT
                + _make_employee(nature=code)
                + FOOTER
            )
            out = _extract_fixture(text)
            contract_warnings = [
                w for w in out.global_quality.warnings if "Unknown contract nature" in w
            ]
            assert contract_warnings == [], f"Code {code!r} wrongly flagged as unknown"


# ═══════════════════════════════════════════════════════════════════════════
# Exit reasons
# ═══════════════════════════════════════════════════════════════════════════


class TestExitReasons:
    def test_exit_reason_by_code(self, with_absences_text: str) -> None:
        out = _extract_fixture(with_absences_text)
        # MARTIN exits with rupture code '059' (demission)
        assert out.establishments[0].counts.exit_reasons_by_code == {"059": 1}

    def test_exit_reason_by_label(self, with_absences_text: str) -> None:
        out = _extract_fixture(with_absences_text)
        assert out.establishments[0].counts.exit_reasons_by_label == {"demission": 1}

    def test_unknown_exit_reason_preserved(
        self, with_unknown_exit_and_absence_codes_text: str
    ) -> None:
        out = _extract_fixture(with_unknown_exit_and_absence_codes_text)
        assert "999" in out.establishments[0].counts.exit_reasons_by_code
        assert any(
            "Unknown contract end reason code: '999'" in w
            for w in out.global_quality.warnings
        )

    def test_no_exit_reason_empty_dict(self) -> None:
        text = (
            MINIMAL_HEADER + MINIMAL_ESTABLISHMENT
            + _make_employee()
            + FOOTER
        )
        out = _extract_fixture(text)
        assert out.establishments[0].counts.exit_reasons_by_code == {}
        assert out.establishments[0].counts.exit_reasons_by_label == {}

    def test_exit_099_still_counted_in_reasons(self) -> None:
        """Rupture code 099 is excluded from exiting_employees but included in exit_reasons."""
        text = (
            MINIMAL_HEADER + MINIMAL_ESTABLISHMENT
            + _make_employee(contract_end="15012025", rupture="099")
            + FOOTER
        )
        out = _extract_fixture(text)
        assert out.establishments[0].counts.exiting_employees_in_month == 0
        assert out.establishments[0].counts.exit_reasons_by_code == {"099": 1}

    def test_all_enum_exit_codes_no_unknown_warning(self) -> None:
        from dsn_extractor.enums import CONTRACT_END_REASON_LABELS

        for code in CONTRACT_END_REASON_LABELS:
            text = (
                MINIMAL_HEADER + MINIMAL_ESTABLISHMENT
                + _make_employee(contract_end="15012025", rupture=code)
                + FOOTER
            )
            out = _extract_fixture(text)
            reason_warnings = [
                w for w in out.global_quality.warnings if "Unknown contract end reason" in w
            ]
            assert reason_warnings == [], f"Code {code!r} wrongly flagged as unknown"


# ═══════════════════════════════════════════════════════════════════════════
# Absences
# ═══════════════════════════════════════════════════════════════════════════


class TestAbsences:
    def test_absences_events_count(self, with_absences_text: str) -> None:
        out = _extract_fixture(with_absences_text)
        # DUPONT: 2 absences (01, 03), MARTIN: 1 absence (05)
        assert out.establishments[0].counts.absences_events_count == 3

    def test_absences_employees_count(self, with_absences_text: str) -> None:
        out = _extract_fixture(with_absences_text)
        assert out.establishments[0].counts.absences_employees_count == 2

    def test_absences_by_code(self, with_absences_text: str) -> None:
        out = _extract_fixture(with_absences_text)
        assert out.establishments[0].counts.absences_by_code == {
            "01": 1,
            "03": 1,
            "05": 1,
        }

    def test_no_absences_zero_counts(self, single_establishment_text: str) -> None:
        out = _extract_fixture(single_establishment_text)
        assert out.establishments[0].counts.absences_events_count == 0
        assert out.establishments[0].counts.absences_employees_count == 0
        assert out.establishments[0].counts.absences_by_code == {}

    def test_multi_absence_per_employee(self) -> None:
        text = (
            MINIMAL_HEADER + MINIMAL_ESTABLISHMENT
            + _make_employee(name="A", absences=["01", "01", "03"])
            + FOOTER
        )
        out = _extract_fixture(text)
        assert out.establishments[0].counts.absences_events_count == 3
        assert out.establishments[0].counts.absences_employees_count == 1
        assert out.establishments[0].counts.absences_by_code == {"01": 2, "03": 1}

    def test_unknown_absence_code_preserved(
        self, with_unknown_exit_and_absence_codes_text: str
    ) -> None:
        out = _extract_fixture(with_unknown_exit_and_absence_codes_text)
        assert "88" in out.establishments[0].counts.absences_by_code
        assert any(
            "Unknown absence motif code: '88'" in w
            for w in out.global_quality.warnings
        )

    def test_all_enum_absence_codes_no_unknown_warning(self) -> None:
        from dsn_extractor.enums import ABSENCE_MOTIF_LABELS

        for code in ABSENCE_MOTIF_LABELS:
            text = (
                MINIMAL_HEADER + MINIMAL_ESTABLISHMENT
                + _make_employee(absences=[code])
                + FOOTER
            )
            out = _extract_fixture(text)
            absence_warnings = [
                w for w in out.global_quality.warnings if "Unknown absence motif" in w
            ]
            assert absence_warnings == [], f"Code {code!r} wrongly flagged as unknown"


# ═══════════════════════════════════════════════════════════════════════════
# Social analysis composition
# ═══════════════════════════════════════════════════════════════════════════


class TestSocialAnalysis:
    def test_effectif(self, with_absences_text: str) -> None:
        out = _extract_fixture(with_absences_text)
        sa = out.establishments[0].social_analysis
        assert sa.effectif == out.establishments[0].counts.employee_blocks_count

    def test_entrees(self, with_absences_text: str) -> None:
        out = _extract_fixture(with_absences_text)
        sa = out.establishments[0].social_analysis
        assert sa.entrees == out.establishments[0].counts.new_employees_in_month

    def test_sorties(self, with_absences_text: str) -> None:
        out = _extract_fixture(with_absences_text)
        sa = out.establishments[0].social_analysis
        assert sa.sorties == out.establishments[0].counts.exiting_employees_in_month

    def test_cadre_count(self) -> None:
        text = (
            MINIMAL_HEADER + MINIMAL_ESTABLISHMENT
            + _make_employee(name="A", ret_cat="01")
            + _make_employee(name="B", ret_cat="02")  # extension_cadre
            + _make_employee(name="C", ret_cat="04")  # non_cadre
            + FOOTER
        )
        out = _extract_fixture(text)
        sa = out.establishments[0].social_analysis
        assert sa.cadre_count == 2  # cadre + extension_cadre
        assert sa.non_cadre_count == 1

    def test_contracts_by_code_and_label(self, with_absences_text: str) -> None:
        out = _extract_fixture(with_absences_text)
        sa = out.establishments[0].social_analysis
        assert sa.contracts_by_code == out.establishments[0].counts.employees_by_contract_nature_code
        assert sa.contracts_by_label == out.establishments[0].counts.employees_by_contract_nature_label

    def test_absences_surfaced(self, with_absences_text: str) -> None:
        out = _extract_fixture(with_absences_text)
        sa = out.establishments[0].social_analysis
        assert sa.absences_events_count == 3
        assert sa.absences_employees_count == 2
        assert sa.absences_by_code == {"01": 1, "03": 1, "05": 1}

    def test_net_verse_net_fiscal_pas(self, with_absences_text: str) -> None:
        out = _extract_fixture(with_absences_text)
        sa = out.establishments[0].social_analysis
        extras = out.establishments[0].extras
        assert sa.net_verse_total == extras.net_paid_sum
        assert sa.net_fiscal_total == extras.net_fiscal_sum
        assert sa.pas_total == extras.pas_sum

    def test_quality_alerts(self, with_absences_text: str) -> None:
        out = _extract_fixture(with_absences_text)
        sa = out.establishments[0].social_analysis
        assert sa.quality_alerts_count == len(out.establishments[0].quality.warnings)
        assert sa.quality_alerts == out.establishments[0].quality.warnings

    def test_global_social_analysis_effectif(self, multi_establishment_text: str) -> None:
        out = _extract_fixture(multi_establishment_text)
        gsa = out.global_social_analysis
        assert gsa.effectif == out.global_counts.employee_blocks_count

    def test_global_numeric_fields_sum_of_establishments(
        self, multi_establishment_text: str
    ) -> None:
        out = _extract_fixture(multi_establishment_text)
        gsa = out.global_social_analysis
        assert gsa.effectif == sum(e.social_analysis.effectif for e in out.establishments)
        assert gsa.entrees == sum(e.social_analysis.entrees for e in out.establishments)
        assert gsa.sorties == sum(e.social_analysis.sorties for e in out.establishments)
        assert gsa.stagiaires == sum(e.social_analysis.stagiaires for e in out.establishments)
        assert gsa.absences_events_count == sum(
            e.social_analysis.absences_events_count for e in out.establishments
        )
        assert gsa.absences_employees_count == sum(
            e.social_analysis.absences_employees_count for e in out.establishments
        )

    def test_global_quality_alerts_gte_sum_of_establishment_alerts(
        self, multi_establishment_text: str
    ) -> None:
        out = _extract_fixture(multi_establishment_text)
        gsa = out.global_social_analysis
        est_sum = sum(e.social_analysis.quality_alerts_count for e in out.establishments)
        assert gsa.quality_alerts_count >= est_sum


# ═══════════════════════════════════════════════════════════════════════════
# Payroll tracking composition
# ═══════════════════════════════════════════════════════════════════════════


class TestPayrollTracking:
    def test_bulletins(self, with_absences_text: str) -> None:
        out = _extract_fixture(with_absences_text)
        pt = out.establishments[0].payroll_tracking
        assert pt.bulletins == out.establishments[0].counts.employee_blocks_count

    def test_billable_entries_exits(self, with_absences_text: str) -> None:
        out = _extract_fixture(with_absences_text)
        pt = out.establishments[0].payroll_tracking
        c = out.establishments[0].counts
        assert pt.billable_entries == c.new_employees_in_month
        assert pt.billable_exits == c.exiting_employees_in_month

    def test_billable_absence_events(self, with_absences_text: str) -> None:
        out = _extract_fixture(with_absences_text)
        pt = out.establishments[0].payroll_tracking
        assert pt.billable_absence_events == 3

    def test_exceptional_events_count(self, with_absences_text: str) -> None:
        out = _extract_fixture(with_absences_text)
        pt = out.establishments[0].payroll_tracking
        # exceptional = exits + absence_events
        c = out.establishments[0].counts
        assert pt.exceptional_events_count == c.exiting_employees_in_month + c.absences_events_count

    def test_dsn_anomalies_count(self, with_absences_text: str) -> None:
        out = _extract_fixture(with_absences_text)
        pt = out.establishments[0].payroll_tracking
        assert pt.dsn_anomalies_count == len(out.establishments[0].quality.warnings)

    def test_complexity_score_deterministic(self, with_absences_text: str) -> None:
        out1 = _extract_fixture(with_absences_text)
        out2 = _extract_fixture(with_absences_text)
        assert out1.establishments[0].payroll_tracking.complexity_score == (
            out2.establishments[0].payroll_tracking.complexity_score
        )

    def test_complexity_score_formula(self, with_absences_text: str) -> None:
        out = _extract_fixture(with_absences_text)
        pt = out.establishments[0].payroll_tracking
        inputs = pt.complexity_inputs
        expected = (
            1 * inputs["bulletins"]
            + 3 * inputs["entries"]
            + 3 * inputs["exits"]
            + 2 * inputs["absence_events"]
            + 5 * inputs["dsn_anomalies"]
        )
        assert pt.complexity_score == expected

    def test_complexity_inputs_transparency(self, with_absences_text: str) -> None:
        out = _extract_fixture(with_absences_text)
        pt = out.establishments[0].payroll_tracking
        assert pt.complexity_inputs["bulletins"] == pt.bulletins
        assert pt.complexity_inputs["entries"] == pt.billable_entries
        assert pt.complexity_inputs["exits"] == pt.billable_exits
        assert pt.complexity_inputs["absence_events"] == pt.billable_absence_events
        assert pt.complexity_inputs["dsn_anomalies"] == pt.dsn_anomalies_count

    def test_global_complexity_score_from_global_inputs(
        self, multi_establishment_text: str
    ) -> None:
        out = _extract_fixture(multi_establishment_text)
        gpt = out.global_payroll_tracking
        inputs = gpt.complexity_inputs
        expected = (
            1 * inputs["bulletins"]
            + 3 * inputs["entries"]
            + 3 * inputs["exits"]
            + 2 * inputs["absence_events"]
            + 5 * inputs["dsn_anomalies"]
        )
        assert gpt.complexity_score == expected

    def test_global_score_gt_sum_when_global_only_warnings(
        self, multi_establishment_text: str
    ) -> None:
        """Multi-establishment emits 'Multiple establishments detected' at orchestrator level.
        This warning is in global_quality but not in any per-establishment quality,
        so global anomalies > sum(est anomalies) and global score > sum(est scores)."""
        out = _extract_fixture(multi_establishment_text)
        gpt = out.global_payroll_tracking
        est_score_sum = sum(e.payroll_tracking.complexity_score for e in out.establishments)
        assert gpt.complexity_score > est_score_sum

    def test_global_score_eq_sum_when_no_global_only_warnings(self) -> None:
        """Single establishment with no parser-level warnings:
        global score == establishment score."""
        text = (
            MINIMAL_HEADER + MINIMAL_ESTABLISHMENT
            + _make_employee(absences=["01"])
            + "S21.G00.54.001,'17'\nS21.G00.54.002,'100.00'\n"
            + FOOTER
        )
        out = _extract_fixture(text)
        gpt = out.global_payroll_tracking
        est_score = out.establishments[0].payroll_tracking.complexity_score
        assert gpt.complexity_score == est_score


# ═══════════════════════════════════════════════════════════════════════════
# Enum warning consistency
# ═══════════════════════════════════════════════════════════════════════════


class TestEnumWarningConsistency:
    def test_known_contract_code_80_no_warning(self) -> None:
        """Code 80 (mandat_social) must produce a label and no unknown warning."""
        text = (
            MINIMAL_HEADER + MINIMAL_ESTABLISHMENT
            + _make_employee(nature="80")
            + FOOTER
        )
        out = _extract_fixture(text)
        assert "mandat_social" in out.establishments[0].counts.employees_by_contract_nature_label
        contract_warnings = [
            w for w in out.global_quality.warnings if "Unknown contract nature" in w
        ]
        assert contract_warnings == []

    def test_known_exit_reason_035_no_warning(self) -> None:
        """Code 035 (fin_periode_essai_initiative_salarie) must produce label, no warning."""
        text = (
            MINIMAL_HEADER + MINIMAL_ESTABLISHMENT
            + _make_employee(contract_end="15012025", rupture="035")
            + FOOTER
        )
        out = _extract_fixture(text)
        assert out.establishments[0].counts.exit_reasons_by_label == {
            "fin_periode_essai_initiative_salarie": 1,
        }
        reason_warnings = [
            w for w in out.global_quality.warnings if "Unknown contract end reason" in w
        ]
        assert reason_warnings == []

    def test_known_absence_code_501_no_warning(self) -> None:
        """Code 501 (conge_divers_non_remunere) must produce label, no warning."""
        text = (
            MINIMAL_HEADER + MINIMAL_ESTABLISHMENT
            + _make_employee(absences=["501"])
            + FOOTER
        )
        out = _extract_fixture(text)
        assert out.establishments[0].counts.absences_by_code == {"501": 1}
        absence_warnings = [
            w for w in out.global_quality.warnings if "Unknown absence motif" in w
        ]
        assert absence_warnings == []

    def test_repeated_absence_501_no_warnings(self) -> None:
        """Multiple occurrences of code 501 must not emit any unknown warnings."""
        text = (
            MINIMAL_HEADER + MINIMAL_ESTABLISHMENT
            + _make_employee(name="A", absences=["501", "501"])
            + _make_employee(name="B", absences=["501"])
            + FOOTER
        )
        out = _extract_fixture(text)
        assert out.establishments[0].counts.absences_by_code == {"501": 3}
        absence_warnings = [
            w for w in out.global_quality.warnings if "Unknown absence motif" in w
        ]
        assert absence_warnings == []

    def test_known_retirement_codes_no_warning(self) -> None:
        from dsn_extractor.enums import RETIREMENT_CATEGORY_LABELS

        for code in RETIREMENT_CATEGORY_LABELS:
            text = (
                MINIMAL_HEADER + MINIMAL_ESTABLISHMENT
                + _make_employee(ret_cat=code)
                + FOOTER
            )
            out = _extract_fixture(text)
            ret_warnings = [
                w for w in out.global_quality.warnings if "Unknown retirement" in w
            ]
            assert ret_warnings == [], f"Code {code!r} wrongly flagged as unknown"


# ═══════════════════════════════════════════════════════════════════════════
# Idempotency + no-aliasing
# ═══════════════════════════════════════════════════════════════════════════


class TestExtractorIdempotency:
    def test_repeated_extraction_identical(self, with_absences_text: str) -> None:
        parsed = parse(with_absences_text)
        out1 = extract(parsed, "test.dsn")
        out2 = extract(parsed, "test.dsn")
        assert out1.model_dump() == out2.model_dump()

    def test_parsed_warnings_not_mutated(self, with_absences_text: str) -> None:
        parsed = parse(with_absences_text)
        original = list(parsed.warnings)
        extract(parsed, "test.dsn")
        assert parsed.warnings == original

    def test_parsed_records_not_mutated(self, with_absences_text: str) -> None:
        parsed = parse(with_absences_text)
        count_before = len(parsed.all_records)
        extract(parsed, "test.dsn")
        assert len(parsed.all_records) == count_before

    def test_parsed_establishment_blocks_not_mutated(self, with_absences_text: str) -> None:
        parsed = parse(with_absences_text)
        snapshots = [
            (len(est.records), len(est.employee_blocks))
            for est in parsed.establishments
        ]
        extract(parsed, "test.dsn")
        for i, est in enumerate(parsed.establishments):
            assert (len(est.records), len(est.employee_blocks)) == snapshots[i]


class TestNoAliasing:
    def test_social_analysis_to_counts(self, with_absences_text: str) -> None:
        out = _extract_fixture(with_absences_text)
        est = out.establishments[0]
        original_contracts = dict(est.counts.employees_by_contract_nature_code)
        original_warnings = list(est.quality.warnings)

        est.social_analysis.contracts_by_code["XX"] = 99
        est.social_analysis.absences_by_code["XX"] = 1
        est.social_analysis.exit_reasons_by_code["XX"] = 1
        est.social_analysis.quality_alerts.append("bogus")

        assert est.counts.employees_by_contract_nature_code == original_contracts
        assert est.counts.absences_by_code != {"XX": 1}  # XX was not in original
        assert "XX" not in est.counts.absences_by_code
        assert "XX" not in est.counts.exit_reasons_by_code
        assert est.quality.warnings == original_warnings

    def test_payroll_tracking_to_counts(self, with_absences_text: str) -> None:
        out = _extract_fixture(with_absences_text)
        est = out.establishments[0]
        original_warnings = list(est.quality.warnings)

        est.payroll_tracking.complexity_inputs["XX"] = 99

        assert "XX" not in est.counts.__dict__.get("_unused", {})
        assert est.quality.warnings == original_warnings

    def test_establishment_to_global(self, multi_establishment_text: str) -> None:
        out = _extract_fixture(multi_establishment_text)
        global_contracts = dict(out.global_social_analysis.contracts_by_code)
        global_alerts = list(out.global_social_analysis.quality_alerts)
        global_inputs = dict(out.global_payroll_tracking.complexity_inputs)

        out.establishments[0].social_analysis.contracts_by_code["XX"] = 99
        out.establishments[0].social_analysis.quality_alerts.append("bogus")
        out.establishments[0].payroll_tracking.complexity_inputs["XX"] = 99

        assert out.global_social_analysis.contracts_by_code == global_contracts
        assert out.global_social_analysis.quality_alerts == global_alerts
        assert out.global_payroll_tracking.complexity_inputs == global_inputs

    def test_global_sections_to_global_counts(self, with_absences_text: str) -> None:
        out = _extract_fixture(with_absences_text)
        original_code = dict(out.global_counts.employees_by_contract_nature_code)

        out.global_social_analysis.contracts_by_code["XX"] = 99
        out.global_payroll_tracking.complexity_inputs["XX"] = 99

        assert out.global_counts.employees_by_contract_nature_code == original_code

    def test_sibling_establishments(self, multi_establishment_text: str) -> None:
        out = _extract_fixture(multi_establishment_text)
        est1_contracts = dict(out.establishments[1].social_analysis.contracts_by_code)

        out.establishments[0].social_analysis.contracts_by_code["XX"] = 99

        assert out.establishments[1].social_analysis.contracts_by_code == est1_contracts


# ═══════════════════════════════════════════════════════════════════════════
# Model defaults / schema validation
# ═══════════════════════════════════════════════════════════════════════════


class TestModelDefaults:
    def test_social_analysis_default(self) -> None:
        from dsn_extractor.models import SocialAnalysis

        sa = SocialAnalysis()
        assert sa.effectif == 0
        assert sa.contracts_by_code == {}
        assert sa.quality_alerts == []
        assert sa.net_verse_total is None

    def test_payroll_tracking_default(self) -> None:
        from dsn_extractor.models import PayrollTracking

        pt = PayrollTracking()
        assert pt.bulletins == 0
        assert pt.complexity_score == 0
        assert pt.complexity_inputs == {}

    def test_establishment_counts_new_fields_default(self) -> None:
        from dsn_extractor.models import EstablishmentCounts

        c = EstablishmentCounts()
        assert c.employees_by_contract_nature_label == {}
        assert c.exit_reasons_by_code == {}
        assert c.exit_reasons_by_label == {}
        assert c.absences_employees_count == 0
        assert c.absences_events_count == 0
        assert c.absences_by_code == {}

    def test_dsn_output_default_includes_new_sections(self) -> None:
        out = DSNOutput()
        assert isinstance(out.global_social_analysis, SocialAnalysis)
        assert isinstance(out.global_payroll_tracking, PayrollTracking)

    def test_establishment_default_includes_new_sections(self) -> None:
        from dsn_extractor.models import Establishment

        est = Establishment()
        assert isinstance(est.social_analysis, SocialAnalysis)
        assert isinstance(est.payroll_tracking, PayrollTracking)

    def test_social_analysis_forbids_extra_fields(self) -> None:
        from dsn_extractor.models import SocialAnalysis
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            SocialAnalysis(bogus=1)  # type: ignore[call-arg]

    def test_payroll_tracking_forbids_extra_fields(self) -> None:
        from dsn_extractor.models import PayrollTracking
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            PayrollTracking(bogus=1)  # type: ignore[call-arg]

    def test_payroll_tracking_name_list_defaults(self) -> None:
        pt = PayrollTracking()
        assert pt.billable_entry_names == []
        assert pt.billable_exit_names == []
        assert pt.billable_absence_details == []

    def test_establishment_counts_name_list_defaults(self) -> None:
        from dsn_extractor.models import EstablishmentCounts

        c = EstablishmentCounts()
        assert c.entry_employee_names == []
        assert c.exit_employee_names == []
        assert c.absence_event_details == []


# ═══════════════════════════════════════════════════════════════════════════
# Employee name lists
# ═══════════════════════════════════════════════════════════════════════════


class TestEmployeeNameLists:
    def test_entry_names_from_fixture(self, with_absences_text: str) -> None:
        out = _extract_fixture(with_absences_text)
        # MARTIN starts 15/01/2025 (in period)
        assert out.establishments[0].counts.entry_employee_names == ["MARTIN SOPHIE"]

    def test_exit_names_from_fixture(self, with_absences_text: str) -> None:
        out = _extract_fixture(with_absences_text)
        # MARTIN exits 31/01/2025 with rupture 059
        assert out.establishments[0].counts.exit_employee_names == ["MARTIN SOPHIE"]

    def test_absence_details_from_fixture(self, with_absences_text: str) -> None:
        out = _extract_fixture(with_absences_text)
        details = out.establishments[0].counts.absence_event_details
        # DUPONT: 2 events (01, 03), MARTIN: 1 event (05) — one per event, DSN order
        assert len(details) == 3
        assert details[0].employee_name == "DUPONT JEAN"
        assert details[0].motif_code == "01"
        assert details[0].motif_label == "maladie"
        assert details[1].employee_name == "DUPONT JEAN"
        assert details[1].motif_code == "03"
        assert details[1].motif_label == "accident_travail"
        assert details[2].employee_name == "MARTIN SOPHIE"
        assert details[2].motif_code == "05"
        assert details[2].motif_label == "maternite"

    def test_absence_details_one_per_event(self) -> None:
        """3 absence events on one employee → 3 detail entries (not deduplicated)."""
        text = (
            MINIMAL_HEADER + MINIMAL_ESTABLISHMENT
            + _make_employee(name="DOE", first="JOHN", absences=["01", "01", "03"])
            + FOOTER
        )
        out = _extract_fixture(text)
        details = out.establishments[0].counts.absence_event_details
        assert len(details) == 3
        assert all(d.employee_name == "DOE JOHN" for d in details)

    def test_entry_names_empty_when_no_entries(self) -> None:
        text = (
            MINIMAL_HEADER + MINIMAL_ESTABLISHMENT
            + _make_employee(contract_start="01032020")  # outside Jan 2025
            + FOOTER
        )
        out = _extract_fixture(text)
        assert out.establishments[0].counts.entry_employee_names == []

    def test_missing_prenom_fallback(self) -> None:
        emp = (
            "S21.G00.30.001,'X'\n"
            "S21.G00.30.002,'DURAND'\n"
            "S21.G00.30.006,'1'\n"
            "S21.G00.40.001,'15012025'\n"
            "S21.G00.40.002,'04'\n"
            "S21.G00.40.003,'01'\n"
            "S21.G00.40.007,'01'\n"
            "S21.G00.50.002,'2000.00'\n"
            "S21.G00.50.004,'1800.00'\n"
            "S21.G00.50.009,'200.00'\n"
        )
        text = MINIMAL_HEADER + MINIMAL_ESTABLISHMENT + emp + FOOTER
        out = _extract_fixture(text)
        assert out.establishments[0].counts.entry_employee_names == ["DURAND"]

    def test_missing_nom_fallback(self) -> None:
        emp = (
            "S21.G00.30.001,'X'\n"
            "S21.G00.30.004,'Marie'\n"
            "S21.G00.30.006,'2'\n"
            "S21.G00.40.001,'15012025'\n"
            "S21.G00.40.002,'04'\n"
            "S21.G00.40.003,'01'\n"
            "S21.G00.40.007,'01'\n"
            "S21.G00.50.002,'2000.00'\n"
            "S21.G00.50.004,'1800.00'\n"
            "S21.G00.50.009,'200.00'\n"
        )
        text = MINIMAL_HEADER + MINIMAL_ESTABLISHMENT + emp + FOOTER
        out = _extract_fixture(text)
        assert out.establishments[0].counts.entry_employee_names == ["Marie"]

    def test_both_missing_fallback(self) -> None:
        emp = (
            "S21.G00.30.001,'X'\n"
            "S21.G00.30.006,'1'\n"
            "S21.G00.40.001,'15012025'\n"
            "S21.G00.40.002,'04'\n"
            "S21.G00.40.003,'01'\n"
            "S21.G00.40.007,'01'\n"
            "S21.G00.50.002,'2000.00'\n"
            "S21.G00.50.004,'1800.00'\n"
            "S21.G00.50.009,'200.00'\n"
        )
        text = MINIMAL_HEADER + MINIMAL_ESTABLISHMENT + emp + FOOTER
        out = _extract_fixture(text)
        assert out.establishments[0].counts.entry_employee_names == ["?"]

    def test_names_order_is_dsn_file_order(self) -> None:
        text = (
            MINIMAL_HEADER + MINIMAL_ESTABLISHMENT
            + _make_employee(name="CHARLIE", first="C", contract_start="10012025")
            + _make_employee(name="ALPHA", first="A", contract_start="05012025")
            + _make_employee(name="BRAVO", first="B", contract_start="20012025")
            + FOOTER
        )
        out = _extract_fixture(text)
        assert out.establishments[0].counts.entry_employee_names == [
            "CHARLIE C",
            "ALPHA A",
            "BRAVO B",
        ]

    def test_global_names_concatenation(self, multi_establishment_text: str) -> None:
        out = _extract_fixture(multi_establishment_text)
        global_entries = out.global_counts.entry_employee_names
        expected = []
        for e in out.establishments:
            expected += e.counts.entry_employee_names
        assert global_entries == expected

    def test_len_entry_names_equals_metric(self, with_absences_text: str) -> None:
        out = _extract_fixture(with_absences_text)
        pt = out.establishments[0].payroll_tracking
        assert len(pt.billable_entry_names) == pt.billable_entries

    def test_len_exit_names_equals_metric(self, with_absences_text: str) -> None:
        out = _extract_fixture(with_absences_text)
        pt = out.establishments[0].payroll_tracking
        assert len(pt.billable_exit_names) == pt.billable_exits

    def test_len_absence_details_equals_metric(self, with_absences_text: str) -> None:
        out = _extract_fixture(with_absences_text)
        pt = out.establishments[0].payroll_tracking
        assert len(pt.billable_absence_details) == pt.billable_absence_events


class TestEmployeeNameAliasing:
    def test_no_aliasing_names_tracking_to_counts(self, with_absences_text: str) -> None:
        out = _extract_fixture(with_absences_text)
        est = out.establishments[0]
        original = list(est.counts.entry_employee_names)
        est.payroll_tracking.billable_entry_names.append("BOGUS")
        assert est.counts.entry_employee_names == original

    def test_no_aliasing_names_est_to_global(self, multi_establishment_text: str) -> None:
        out = _extract_fixture(multi_establishment_text)
        original = list(out.global_payroll_tracking.billable_entry_names)
        out.establishments[0].payroll_tracking.billable_entry_names.append("BOGUS")
        assert out.global_payroll_tracking.billable_entry_names == original

    def test_no_aliasing_absence_detail_tracking_to_counts(
        self, with_absences_text: str
    ) -> None:
        out = _extract_fixture(with_absences_text)
        est = out.establishments[0]
        original_name = est.counts.absence_event_details[0].employee_name
        est.payroll_tracking.billable_absence_details[0].employee_name = "BOGUS"
        assert est.counts.absence_event_details[0].employee_name == original_name

    def test_no_aliasing_absence_detail_est_to_global(
        self, with_absences_text: str
    ) -> None:
        out = _extract_fixture(with_absences_text)
        original_name = out.global_payroll_tracking.billable_absence_details[0].employee_name
        out.establishments[0].payroll_tracking.billable_absence_details[0].employee_name = "BOGUS"
        assert out.global_payroll_tracking.billable_absence_details[0].employee_name == original_name

    def test_no_aliasing_absence_detail_global_counts_to_global_tracking(
        self, with_absences_text: str
    ) -> None:
        out = _extract_fixture(with_absences_text)
        original_name = out.global_payroll_tracking.billable_absence_details[0].employee_name
        out.global_counts.absence_event_details[0].employee_name = "BOGUS"
        assert out.global_payroll_tracking.billable_absence_details[0].employee_name == original_name

    def test_no_aliasing_absence_detail_est_counts_to_global_counts(
        self, with_absences_text: str
    ) -> None:
        out = _extract_fixture(with_absences_text)
        original_name = out.global_counts.absence_event_details[0].employee_name
        out.establishments[0].counts.absence_event_details[0].employee_name = "BOGUS"
        assert out.global_counts.absence_event_details[0].employee_name == original_name


# ═══════════════════════════════════════════════════════════════════════════
# Absence detail model + sensitive data
# ═══════════════════════════════════════════════════════════════════════════


class TestAbsenceDetailModel:
    def test_absence_detail_has_all_fields(self, with_absences_text: str) -> None:
        out = _extract_fixture(with_absences_text)
        d = out.establishments[0].counts.absence_event_details[0]
        assert hasattr(d, "employee_name")
        assert hasattr(d, "motif_code")
        assert hasattr(d, "motif_label")

    def test_absence_detail_unknown_motif_uses_raw_code(
        self, with_unknown_exit_and_absence_codes_text: str
    ) -> None:
        out = _extract_fixture(with_unknown_exit_and_absence_codes_text)
        details = out.establishments[0].counts.absence_event_details
        assert any(d.motif_code == "88" and d.motif_label == "88" for d in details)

    def test_absence_detail_forbids_extra_fields(self) -> None:
        from dsn_extractor.models import AbsenceDetail
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            AbsenceDetail(employee_name="X", motif_code="01", motif_label="m", bogus="x")  # type: ignore[call-arg]


class TestSensitiveDataExclusion:
    """Ensure NIR, NTT, and birth dates never appear in serialized output."""

    def test_no_nir_in_output(self) -> None:
        import json

        nir = "1234567890123"
        text = (
            MINIMAL_HEADER + MINIMAL_ESTABLISHMENT
            + f"S21.G00.30.001,'{nir}'\n"
            + "S21.G00.30.002,'DUPONT'\n"
            + f"S21.G00.30.003,'{nir}'\n"
            + "S21.G00.30.004,'JEAN'\n"
            + "S21.G00.30.006,'1'\n"
            + "S21.G00.40.001,'15012025'\n"
            + "S21.G00.40.002,'04'\n"
            + "S21.G00.40.003,'01'\n"
            + "S21.G00.40.007,'01'\n"
            + "S21.G00.50.002,'2000.00'\n"
            + "S21.G00.50.004,'1800.00'\n"
            + "S21.G00.50.009,'200.00'\n"
            + "S21.G00.65.001,'01'\n"
            + "S21.G00.65.002,'10012025'\n"
            + "S21.G00.65.003,'15012025'\n"
            + FOOTER
        )
        out = _extract_fixture(text)
        serialized = json.dumps(out.model_dump(mode="json"))
        assert nir not in serialized

    def test_no_ntt_in_output(self) -> None:
        import json

        ntt = "2987654321098"
        text = (
            MINIMAL_HEADER + MINIMAL_ESTABLISHMENT
            + "S21.G00.30.001,'X'\n"
            + "S21.G00.30.002,'MARTIN'\n"
            + "S21.G00.30.004,'SOPHIE'\n"
            + f"S21.G00.30.018,'{ntt}'\n"
            + "S21.G00.30.006,'2'\n"
            + "S21.G00.40.001,'15012025'\n"
            + "S21.G00.40.002,'04'\n"
            + "S21.G00.40.003,'01'\n"
            + "S21.G00.40.007,'01'\n"
            + "S21.G00.50.002,'2000.00'\n"
            + "S21.G00.50.004,'1800.00'\n"
            + "S21.G00.50.009,'200.00'\n"
            + FOOTER
        )
        out = _extract_fixture(text)
        serialized = json.dumps(out.model_dump(mode="json"))
        assert ntt not in serialized

    def test_no_nir_in_server_response(self) -> None:
        from starlette.testclient import TestClient
        from server.app import app

        nir = "1234567890123"
        dsn = (
            MINIMAL_HEADER + MINIMAL_ESTABLISHMENT
            + f"S21.G00.30.001,'{nir}'\n"
            + "S21.G00.30.002,'TEST'\n"
            + f"S21.G00.30.003,'{nir}'\n"
            + "S21.G00.30.004,'USER'\n"
            + "S21.G00.30.006,'1'\n"
            + "S21.G00.40.001,'15012025'\n"
            + "S21.G00.40.002,'04'\n"
            + "S21.G00.40.003,'01'\n"
            + "S21.G00.40.007,'01'\n"
            + "S21.G00.50.002,'2000.00'\n"
            + "S21.G00.50.004,'1800.00'\n"
            + "S21.G00.50.009,'200.00'\n"
            + FOOTER
        )
        client = TestClient(app)
        r = client.post(
            "/api/extract",
            files={"file": ("test.dsn", dsn.encode("utf-8"), "application/octet-stream")},
        )
        assert r.status_code == 200
        assert nir not in r.text
