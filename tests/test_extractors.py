"""Tests for Slice 3 — Extractors."""

from __future__ import annotations

import copy
import datetime
from decimal import Decimal

import pytest

from dsn_extractor.extractors import _sum_decimal, extract
from dsn_extractor.models import DSNOutput
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
) -> str:
    lines = [
        f"S21.G00.30.001,'{name}'",
        f"S21.G00.30.002,'{first}'",
        f"S21.G00.30.004,'{birth}'",
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
