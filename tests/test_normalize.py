"""Tests for normalization, enums, and output models."""

from __future__ import annotations

import datetime
from decimal import Decimal

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
