"""Tests for normalization, enums, and output models."""

from __future__ import annotations

import datetime
import json
from decimal import Decimal

import pytest
from pydantic import ValidationError

from dsn_extractor.enums import CONTRACT_NATURE_LABELS, RETIREMENT_CATEGORY_LABELS
from dsn_extractor.models import (
    Company,
    Declaration,
    DSNOutput,
    Establishment,
    EstablishmentAmounts,
    EstablishmentCounts,
    EstablishmentExtras,
    EstablishmentIdentity,
    Quality,
)
from dsn_extractor.normalize import (
    lookup_enum_label,
    normalize_date,
    normalize_decimal,
    normalize_empty,
)


# ---------------------------------------------------------------------------
# normalize_date
# ---------------------------------------------------------------------------


class TestNormalizeDate:
    def test_valid_first_of_month(self):
        assert normalize_date("01012025") == datetime.date(2025, 1, 1)

    def test_valid_end_of_month(self):
        assert normalize_date("31012025") == datetime.date(2025, 1, 31)

    def test_valid_mid_month(self):
        assert normalize_date("15062023") == datetime.date(2023, 6, 15)

    def test_empty_string_returns_none(self):
        assert normalize_date("") is None

    def test_whitespace_only_returns_none(self):
        assert normalize_date("   ") is None

    def test_invalid_format_returns_none(self):
        assert normalize_date("not-a-date") is None

    def test_short_string_returns_none(self):
        assert normalize_date("0101") is None

    def test_invalid_day_returns_none(self):
        assert normalize_date("32012025") is None

    def test_invalid_month_returns_none(self):
        assert normalize_date("01132025") is None

    def test_strips_whitespace(self):
        assert normalize_date(" 01012025 ") == datetime.date(2025, 1, 1)

    # -- DSN date format contract (DDMMYYYY) --

    def test_fixture_period_start(self):
        """Fixture single_establishment.dsn: S20.G00.05.005,'01012025' = Jan 1."""
        assert normalize_date("01012025") == datetime.date(2025, 1, 1)

    def test_fixture_period_end(self):
        """Fixture single_establishment.dsn: S20.G00.05.007,'31012025' = Jan 31."""
        assert normalize_date("31012025") == datetime.date(2025, 1, 31)

    def test_fixture_contract_start_mid_month(self):
        """Fixture single_establishment.dsn: S21.G00.40.001,'15012025' = Jan 15."""
        assert normalize_date("15012025") == datetime.date(2025, 1, 15)

    def test_fixture_february_period(self):
        """Fixture no_s54_blocks.dsn: period '01022025'-'28022025' = Feb 2025."""
        assert normalize_date("01022025") == datetime.date(2025, 2, 1)
        assert normalize_date("28022025") == datetime.date(2025, 2, 28)

    def test_yyyymmdd_input_rejected_when_ambiguous(self):
        """'20250101' interpreted as DDMMYYYY would be day=20, month=25 -> invalid."""
        assert normalize_date("20250101") is None

    def test_yyyymmdd_input_misinterpreted_when_plausible(self):
        """'20251201' as DDMMYYYY = day=20, month=25 -> invalid. Not Dec 1 2025."""
        assert normalize_date("20251201") is None

    def test_iso_dash_format_rejected(self):
        assert normalize_date("2025-01-01") is None

    def test_slash_format_rejected(self):
        assert normalize_date("01/01/2025") is None


# ---------------------------------------------------------------------------
# normalize_decimal
# ---------------------------------------------------------------------------


class TestNormalizeDecimal:
    def test_valid_decimal(self):
        assert normalize_decimal("2500.00") == Decimal("2500.00")

    def test_integer_string(self):
        assert normalize_decimal("100") == Decimal("100")

    def test_negative_value(self):
        assert normalize_decimal("-50.25") == Decimal("-50.25")

    def test_empty_string_returns_none(self):
        assert normalize_decimal("") is None

    def test_whitespace_only_returns_none(self):
        assert normalize_decimal("  ") is None

    def test_invalid_string_returns_none(self):
        assert normalize_decimal("abc") is None

    def test_zero(self):
        assert normalize_decimal("0.00") == Decimal("0.00")

    def test_strips_whitespace(self):
        assert normalize_decimal(" 42.50 ") == Decimal("42.50")

    # -- Non-finite rejection --

    def test_nan_returns_none(self):
        assert normalize_decimal("NaN") is None

    def test_snan_returns_none(self):
        assert normalize_decimal("sNaN") is None

    def test_infinity_returns_none(self):
        assert normalize_decimal("Infinity") is None

    def test_negative_infinity_returns_none(self):
        assert normalize_decimal("-Infinity") is None

    def test_inf_shorthand_returns_none(self):
        assert normalize_decimal("Inf") is None


# ---------------------------------------------------------------------------
# normalize_empty
# ---------------------------------------------------------------------------


class TestNormalizeEmpty:
    def test_empty_string_returns_none(self):
        assert normalize_empty("") is None

    def test_non_empty_string_preserved(self):
        assert normalize_empty("hello") == "hello"

    def test_whitespace_preserved(self):
        assert normalize_empty("  ") == "  "

    def test_numeric_string_preserved(self):
        assert normalize_empty("01") == "01"


# ---------------------------------------------------------------------------
# lookup_enum_label
# ---------------------------------------------------------------------------


class TestLookupEnumLabel:
    def test_known_retirement_code(self):
        assert lookup_enum_label("01", RETIREMENT_CATEGORY_LABELS) == ("cadre", True)

    def test_known_retirement_code_04(self):
        assert lookup_enum_label("04", RETIREMENT_CATEGORY_LABELS) == ("non_cadre", True)

    def test_unknown_retirement_code(self):
        assert lookup_enum_label("03", RETIREMENT_CATEGORY_LABELS) == ("03", False)

    def test_known_contract_nature(self):
        assert lookup_enum_label("29", CONTRACT_NATURE_LABELS) == ("convention_stage", True)

    def test_unknown_contract_nature(self):
        assert lookup_enum_label("50", CONTRACT_NATURE_LABELS) == ("50", False)

    def test_empty_string(self):
        assert lookup_enum_label("", RETIREMENT_CATEGORY_LABELS) == ("", False)

    def test_all_retirement_codes_known(self):
        for code in RETIREMENT_CATEGORY_LABELS:
            _, was_known = lookup_enum_label(code, RETIREMENT_CATEGORY_LABELS)
            assert was_known, f"Code {code!r} should be known"

    def test_all_contract_nature_codes_known(self):
        for code in CONTRACT_NATURE_LABELS:
            _, was_known = lookup_enum_label(code, CONTRACT_NATURE_LABELS)
            assert was_known, f"Code {code!r} should be known"


# ---------------------------------------------------------------------------
# Enum maps
# ---------------------------------------------------------------------------


class TestEnumMaps:
    def test_retirement_category_keys(self):
        assert set(RETIREMENT_CATEGORY_LABELS.keys()) == {"01", "02", "04", "98", "99"}

    def test_contract_nature_keys(self):
        assert set(CONTRACT_NATURE_LABELS.keys()) == {"01", "02", "29"}

    def test_retirement_values_unique(self):
        values = list(RETIREMENT_CATEGORY_LABELS.values())
        assert len(values) == len(set(values))

    def test_contract_nature_values_unique(self):
        values = list(CONTRACT_NATURE_LABELS.values())
        assert len(values) == len(set(values))


# ---------------------------------------------------------------------------
# Model instantiation and serialization
# ---------------------------------------------------------------------------


class TestModelInstantiation:
    def test_declaration_defaults(self):
        d = Declaration()
        assert d.norm_version is None
        assert d.period_start is None
        assert d.month is None

    def test_company_defaults(self):
        c = Company()
        assert c.siren is None
        assert c.siret is None

    def test_establishment_counts_defaults(self):
        c = EstablishmentCounts()
        assert c.employee_blocks_count == 0
        assert c.stagiaires == 0
        assert c.employees_by_retirement_category_code == {}
        assert c.new_employees_in_month == 0

    def test_dsn_output_defaults(self):
        out = DSNOutput()
        assert out.source_file == ""
        assert out.establishments == []
        assert out.global_counts.employee_blocks_count == 0

    def test_dsn_output_json_round_trip(self):
        out = DSNOutput(
            source_file="test.dsn",
            declaration=Declaration(
                period_start=datetime.date(2025, 1, 1),
                month="2025-01",
            ),
            global_counts=EstablishmentCounts(
                employee_blocks_count=5,
                employees_by_retirement_category_code={"01": 3, "04": 2},
            ),
            global_amounts=EstablishmentAmounts(
                tickets_restaurant_employer_contribution_total=Decimal("150.00"),
            ),
        )
        data = out.model_dump(mode="json")
        assert data["source_file"] == "test.dsn"
        assert data["declaration"]["period_start"] == "2025-01-01"
        assert data["declaration"]["month"] == "2025-01"
        assert data["global_counts"]["employee_blocks_count"] == 5
        assert data["global_counts"]["employees_by_retirement_category_code"] == {"01": 3, "04": 2}

    def test_decimal_json_serialization(self):
        a = EstablishmentAmounts(
            tickets_restaurant_employer_contribution_total=Decimal("2500.00"),
        )
        data = a.model_dump(mode="json")
        # Pydantic v2 serializes Decimal as string by default
        assert data["tickets_restaurant_employer_contribution_total"] == "2500.00"

    def test_date_json_serialization(self):
        d = Declaration(period_start=datetime.date(2025, 1, 1))
        data = d.model_dump(mode="json")
        assert data["period_start"] == "2025-01-01"

    def test_establishment_mutable_defaults_independent(self):
        e1 = Establishment()
        e2 = Establishment()
        e1.counts.employees_by_retirement_category_code["01"] = 5
        assert e2.counts.employees_by_retirement_category_code == {}

    def test_dsn_output_mutable_defaults_independent(self):
        o1 = DSNOutput()
        o2 = DSNOutput()
        o1.establishments.append(Establishment())
        assert o2.establishments == []

    def test_quality_mutable_defaults_independent(self):
        q1 = Quality()
        q2 = Quality()
        q1.warnings.append("test warning")
        assert q2.warnings == []


# ---------------------------------------------------------------------------
# Extra fields rejected (extra="forbid")
# ---------------------------------------------------------------------------


class TestExtraFieldsRejected:
    def test_declaration_rejects_extra(self):
        with pytest.raises(ValidationError):
            Declaration(norm_version="P25V01", bogus="x")

    def test_company_rejects_extra(self):
        with pytest.raises(ValidationError):
            Company(siren="123456789", extra_field=1)

    def test_establishment_identity_rejects_extra(self):
        with pytest.raises(ValidationError):
            EstablishmentIdentity(nic="00011", foo="bar")

    def test_establishment_counts_rejects_extra(self):
        with pytest.raises(ValidationError):
            EstablishmentCounts(employee_blocks_count=3, unknown=True)

    def test_establishment_amounts_rejects_extra(self):
        with pytest.raises(ValidationError):
            EstablishmentAmounts(bonus=Decimal("100"))

    def test_establishment_extras_rejects_extra(self):
        with pytest.raises(ValidationError):
            EstablishmentExtras(mystery="value")

    def test_quality_rejects_extra(self):
        with pytest.raises(ValidationError):
            Quality(warnings=[], severity="high")

    def test_establishment_rejects_extra(self):
        with pytest.raises(ValidationError):
            Establishment(label="test")

    def test_dsn_output_rejects_extra(self):
        with pytest.raises(ValidationError):
            DSNOutput(source_file="test.dsn", version=2)

    def test_nested_extra_rejected_via_dict(self):
        """Extra field in a nested model provided as dict is also rejected."""
        with pytest.raises(ValidationError):
            DSNOutput(declaration={"norm_version": "P25V01", "bogus": "x"})


# ---------------------------------------------------------------------------
# Validation-path tests (model_validate / model_validate_json)
# ---------------------------------------------------------------------------


class TestModelValidation:
    def test_declaration_validate_from_dict(self):
        d = Declaration.model_validate({
            "norm_version": "P25V01",
            "period_start": "2025-01-01",
            "month": "2025-01",
        })
        assert d.norm_version == "P25V01"
        assert d.period_start == datetime.date(2025, 1, 1)
        assert d.month == "2025-01"

    def test_company_validate_from_dict(self):
        c = Company.model_validate({
            "siren": "123456789",
            "nic": "00011",
            "siret": "12345678900011",
        })
        assert c.siret == "12345678900011"

    def test_establishment_counts_validate_from_dict(self):
        c = EstablishmentCounts.model_validate({
            "employee_blocks_count": 3,
            "employees_by_retirement_category_code": {"01": 2, "04": 1},
        })
        assert c.employee_blocks_count == 3
        assert c.employees_by_retirement_category_code == {"01": 2, "04": 1}
        # Unset fields get defaults
        assert c.stagiaires == 0

    def test_establishment_amounts_validate_from_dict(self):
        a = EstablishmentAmounts.model_validate({
            "tickets_restaurant_employer_contribution_total": "150.00",
        })
        assert a.tickets_restaurant_employer_contribution_total == Decimal("150.00")
        assert a.transport_public_total is None

    def test_dsn_output_validate_from_nested_dict(self):
        out = DSNOutput.model_validate({
            "source_file": "test.dsn",
            "declaration": {"month": "2025-01", "period_start": "2025-01-01"},
            "company": {"siren": "123456789"},
            "establishments": [{
                "identity": {"nic": "00011"},
                "counts": {"employee_blocks_count": 5},
            }],
        })
        assert out.source_file == "test.dsn"
        assert out.declaration.month == "2025-01"
        assert out.company.siren == "123456789"
        assert len(out.establishments) == 1
        assert out.establishments[0].identity.nic == "00011"
        assert out.establishments[0].counts.employee_blocks_count == 5

    def test_declaration_validate_json(self):
        payload = json.dumps({
            "norm_version": "P25V01",
            "period_start": "2025-01-01",
            "period_end": "2025-01-31",
            "month": "2025-01",
        })
        d = Declaration.model_validate_json(payload)
        assert d.period_start == datetime.date(2025, 1, 1)
        assert d.period_end == datetime.date(2025, 1, 31)

    def test_dsn_output_validate_json(self):
        payload = json.dumps({
            "source_file": "janvier.dsn",
            "declaration": {"month": "2025-01"},
            "company": {"siren": "123456789", "name": "ACME"},
            "global_counts": {
                "employee_blocks_count": 10,
                "employees_by_retirement_category_code": {"01": 6, "04": 4},
            },
            "global_amounts": {
                "tickets_restaurant_employer_contribution_total": "300.00",
            },
        })
        out = DSNOutput.model_validate_json(payload)
        assert out.source_file == "janvier.dsn"
        assert out.company.name == "ACME"
        assert out.global_counts.employee_blocks_count == 10
        assert out.global_amounts.tickets_restaurant_employer_contribution_total == Decimal("300.00")

    def test_validate_rejects_extra_field_in_json(self):
        payload = json.dumps({"siren": "123", "bogus": "x"})
        with pytest.raises(ValidationError):
            Company.model_validate_json(payload)

    def test_validate_rejects_wrong_type(self):
        with pytest.raises(ValidationError):
            EstablishmentCounts.model_validate({"employee_blocks_count": "not_an_int"})


# ---------------------------------------------------------------------------
# Declaration.month YYYY-MM validation
# ---------------------------------------------------------------------------


class TestDeclarationMonth:
    # -- Valid values --

    def test_none_accepted(self):
        d = Declaration(month=None)
        assert d.month is None

    def test_default_is_none(self):
        d = Declaration()
        assert d.month is None

    def test_valid_january(self):
        d = Declaration(month="2025-01")
        assert d.month == "2025-01"

    def test_valid_december(self):
        d = Declaration(month="2025-12")
        assert d.month == "2025-12"

    def test_valid_via_model_validate(self):
        d = Declaration.model_validate({"month": "2023-06"})
        assert d.month == "2023-06"

    def test_valid_via_model_validate_json(self):
        d = Declaration.model_validate_json('{"month": "2025-01"}')
        assert d.month == "2025-01"

    # -- Rejected values --

    def test_rejects_bare_year(self):
        with pytest.raises(ValidationError):
            Declaration(month="2025")

    def test_rejects_full_date(self):
        with pytest.raises(ValidationError):
            Declaration(month="2025-01-15")

    def test_rejects_month_zero(self):
        with pytest.raises(ValidationError):
            Declaration(month="2025-00")

    def test_rejects_month_thirteen(self):
        with pytest.raises(ValidationError):
            Declaration(month="2025-13")

    def test_rejects_no_dash(self):
        with pytest.raises(ValidationError):
            Declaration(month="202501")

    def test_rejects_slash_separator(self):
        with pytest.raises(ValidationError):
            Declaration(month="2025/01")

    def test_rejects_empty_string(self):
        with pytest.raises(ValidationError):
            Declaration(month="")

    def test_rejects_garbage(self):
        with pytest.raises(ValidationError):
            Declaration(month="janvier")

    def test_rejected_via_model_validate(self):
        with pytest.raises(ValidationError):
            Declaration.model_validate({"month": "2025-13"})

    def test_rejected_via_model_validate_json(self):
        with pytest.raises(ValidationError):
            Declaration.model_validate_json('{"month": "not-valid"}')

    # -- Whitespace and non-string edge cases --

    def test_rejects_leading_whitespace(self):
        with pytest.raises(ValidationError):
            Declaration(month=" 2025-01")

    def test_rejects_trailing_whitespace(self):
        with pytest.raises(ValidationError):
            Declaration(month="2025-01 ")

    def test_rejects_integer(self):
        with pytest.raises(ValidationError):
            Declaration.model_validate({"month": 202501})

    # -- Nested round-trip --

    def test_month_survives_dsn_output_round_trip(self):
        """month value survives DSNOutput -> model_dump(mode='json') -> model_validate."""
        original = DSNOutput(
            source_file="test.dsn",
            declaration=Declaration(month="2025-01"),
        )
        data = original.model_dump(mode="json")
        restored = DSNOutput.model_validate(data)
        assert restored.declaration.month == "2025-01"

        json_str = json.dumps(data)
        restored_json = DSNOutput.model_validate_json(json_str)
        assert restored_json.declaration.month == "2025-01"
