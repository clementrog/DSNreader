from __future__ import annotations

from decimal import Decimal
from pathlib import Path

from dsn_extractor.extractors import extract
from dsn_extractor.parser import parse


def test_demo_fixture_keeps_expected_light_failures():
    fixture = Path(__file__).parent.parent / "demo" / "ben-consulting-services-2026-04-demo-light-errors.dsn"

    result = extract(parse(fixture.read_text(encoding="utf-8")), source_file=fixture.name)

    assert result.global_counts.employee_blocks_count == 7
    assert result.global_counts.new_employees_in_month == 0
    assert result.global_counts.exiting_employees_in_month == 1
    assert result.global_counts.exit_reasons_by_code == {"034": 1}
    assert result.global_quality.warnings == []

    items = result.global_contribution_comparisons.items
    pas = next(item for item in items if item.family == "pas")
    assert pas.status == "ecart"
    assert pas.aggregate_amount == Decimal("2851.00")
    assert pas.individual_amount == Decimal("2841.21")
    assert pas.aggregate_vs_individual_delta == Decimal("9.79")

    urssaf = next(item for item in items if item.family == "urssaf")
    assert urssaf.status == "ok"
    assert [row.mapped_code for row in urssaf.urssaf_code_breakdowns] == [
        "027D",
        "100D",
        "100P",
        "260D",
        "332P",
        "423D",
        "430D",
        "635D",
        "726D",
        "726P",
        "772D",
        "937D",
        "959D",
        "992D",
        "668P",
        "669P",
    ]
    ctp260 = next(row for row in urssaf.urssaf_code_breakdowns if row.ctp_code == "260")
    assert ctp260.delta == Decimal("0.04")
    assert ctp260.delta_within_unit is True
    ctp772 = next(row for row in urssaf.urssaf_code_breakdowns if row.ctp_code == "772")
    assert ctp772.delta == Decimal("0.02")
    assert ctp772.delta_within_unit is True
    ctp959 = next(row for row in urssaf.urssaf_code_breakdowns if row.ctp_code == "959")
    assert ctp959.mapping_status == "rattachable"
    assert ctp959.declared_amount == Decimal("178.08")
    assert ctp959.individual_amount == Decimal("172.07")
    assert ctp959.delta == Decimal("6.01")
    assert ctp959.delta_within_unit is False

    retraite = next(item for item in items if item.family == "retraite")
    assert retraite.status == "ok"
    assert retraite.aggregate_amount == Decimal("4320.18")
    assert retraite.individual_amount == Decimal("4320.18")
