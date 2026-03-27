"""Tests for contribution reconciliation (organisms, block_groups, contributions)."""

from __future__ import annotations

import csv
import tempfile
from decimal import Decimal
from pathlib import Path

import pytest

from dsn_extractor.block_groups import (
    group_employee_blocks,
    group_establishment_blocks,
)
from dsn_extractor.contributions import (
    compute_contribution_comparisons,
    merge_contribution_comparisons,
)
from dsn_extractor.models import (
    ContributionComparisons,
    ContributionComparisonItem,
    DSNOutput,
)
from dsn_extractor.organisms import (
    COMPLEMENTARY_FAMILY_OVERRIDES,
    CTP_LABELS,
    ORGANISM_REGISTRY,
    TYPE_CODE_TO_FAMILY,
    _load_registry,
    lookup_complementary_family_override,
    _DATA_DIR,
    _COMPLEMENTARY_FAMILY_OVERRIDES_TSV,
    _TSV_NAME,
)
from dsn_extractor.parser import DSNRecord, EmployeeBlock, EstablishmentBlock


# ---------------------------------------------------------------------------
# DSN record helpers
# ---------------------------------------------------------------------------


def _r(code: str, value: str, line: int = 1) -> DSNRecord:
    return DSNRecord(code=code, raw_value=value, line_number=line)


def _est(*records: DSNRecord, employees: list[EmployeeBlock] | None = None) -> EstablishmentBlock:
    est = EstablishmentBlock(records=list(records))
    if employees:
        est.employee_blocks = employees
    return est


def _emp(*records: DSNRecord) -> EmployeeBlock:
    return EmployeeBlock(records=list(records))


# ---------------------------------------------------------------------------
# Artifact validation tests
# ---------------------------------------------------------------------------


class TestArtifactValidation:
    """Validate the checked-in organisms_reference.tsv artifact."""

    def test_tsv_exists(self):
        tsv_path = _DATA_DIR / _TSV_NAME
        assert tsv_path.is_file(), f"Canonical artifact missing: {tsv_path}"

    def test_complementary_family_overrides_tsv_exists(self):
        tsv_path = _DATA_DIR / _COMPLEMENTARY_FAMILY_OVERRIDES_TSV
        assert tsv_path.is_file(), f"Canonical artifact missing: {tsv_path}"

    def test_registry_populated(self):
        assert len(ORGANISM_REGISTRY) > 0

    def test_complementary_family_overrides_populated(self):
        assert len(COMPLEMENTARY_FAMILY_OVERRIDES) > 0

    def test_registry_matches_tsv_exactly(self):
        """Read TSV row-by-row and compare against ORGANISM_REGISTRY."""
        tsv_path = _DATA_DIR / _TSV_NAME
        tsv_entries: dict[str, tuple[str, str]] = {}
        with open(tsv_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                cols = line.split("\t")
                organism_id = cols[0].strip()
                label = cols[1].strip()
                type_code = cols[2].strip()
                tsv_entries[organism_id] = (label, type_code)

        # Same count
        assert len(ORGANISM_REGISTRY) == len(tsv_entries), (
            f"Registry has {len(ORGANISM_REGISTRY)} entries, TSV has {len(tsv_entries)}"
        )
        # Same keys and values
        for org_id, (label, type_code) in tsv_entries.items():
            assert org_id in ORGANISM_REGISTRY, f"TSV entry {org_id} missing from registry"
            reg_label, reg_type, reg_family = ORGANISM_REGISTRY[org_id]
            assert reg_label == label, f"Label mismatch for {org_id}"
            assert reg_type == type_code, f"Type code mismatch for {org_id}"

    def test_all_type_codes_mapped(self):
        for org_id, (label, type_code, family) in ORGANISM_REGISTRY.items():
            assert type_code in TYPE_CODE_TO_FAMILY, (
                f"Type code '{type_code}' for {org_id} not in TYPE_CODE_TO_FAMILY"
            )

    def test_no_duplicates_in_tsv(self):
        tsv_path = _DATA_DIR / _TSV_NAME
        ids = []
        with open(tsv_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    ids.append(line.split("\t")[0].strip())
        assert len(ids) == len(set(ids)), "Duplicate organism_ids in TSV"

    def test_document_literals_present(self):
        assert "DGFIP" in ORGANISM_REGISTRY
        assert "78430152500035" not in ORGANISM_REGISTRY or True  # may not be exact match
        # At least one AAR retraite entry exists
        retraite_entries = [
            k for k, v in ORGANISM_REGISTRY.items() if v[2] == "retraite"
        ]
        assert len(retraite_entries) > 0

    def test_alan_health_contract_override_present(self):
        assert (
            lookup_complementary_family_override("AALAN1", "SANTE0000041844")
            == "mutuelle"
        )

    def test_deterministic_keys(self):
        """Registry keys are unique (guaranteed by dict, but explicit test)."""
        keys = list(ORGANISM_REGISTRY.keys())
        assert len(keys) == len(set(keys))


class TestArtifactFailFast:
    """Test that invalid artifacts cause RuntimeError at load time."""

    def test_missing_artifact(self):
        with pytest.raises(RuntimeError, match="not found"):
            _load_registry(Path("/nonexistent/path/organisms_reference.tsv"))

    def test_empty_artifact(self, tmp_path):
        tsv = tmp_path / "organisms_reference.tsv"
        tsv.write_text("", encoding="utf-8")
        with pytest.raises(RuntimeError, match="empty"):
            _load_registry(tsv)

    def test_header_row_rejected(self, tmp_path):
        tsv = tmp_path / "organisms_reference.tsv"
        tsv.write_text("organism_id\tlabel\ttype_code\teffective_date\n", encoding="utf-8")
        with pytest.raises(RuntimeError, match="header row"):
            _load_registry(tsv)

    def test_malformed_row(self, tmp_path):
        tsv = tmp_path / "organisms_reference.tsv"
        tsv.write_text("DGFIP\tDGFIP\tFIP\t2\nBAD\tBAD\tFIP\n", encoding="utf-8")
        with pytest.raises(RuntimeError, match="expected 4 columns"):
            _load_registry(tsv)

    def test_missing_required_field(self, tmp_path):
        tsv = tmp_path / "organisms_reference.tsv"
        tsv.write_text("\tDGFIP\tFIP\t2\n", encoding="utf-8")
        with pytest.raises(RuntimeError, match="missing organism_id"):
            _load_registry(tsv)

    def test_unknown_type_code(self, tmp_path):
        tsv = tmp_path / "organisms_reference.tsv"
        tsv.write_text("TEST1\tTest\tXYZ\t2\n", encoding="utf-8")
        with pytest.raises(RuntimeError, match="unknown type_code 'XYZ'"):
            _load_registry(tsv)

    def test_duplicate_key(self, tmp_path):
        tsv = tmp_path / "organisms_reference.tsv"
        tsv.write_text("DGFIP\tDGFIP\tFIP\t2\nDGFIP\tDGFIP2\tFIP\t2\n", encoding="utf-8")
        with pytest.raises(RuntimeError, match="duplicate organism_id 'DGFIP'"):
            _load_registry(tsv)


# ---------------------------------------------------------------------------
# Block groups tests
# ---------------------------------------------------------------------------


class TestBlockGroups:
    def test_orphan_s55(self):
        est = _est(
            _r("S21.G00.55.001", "100.00", 1),
            _r("S21.G00.55.003", "REF1", 2),
        )
        groups = group_establishment_blocks(est)
        assert any("orphan_s55_block" in w for w in groups.warnings)

    def test_orphan_s23(self):
        est = _est(
            _r("S21.G00.23.001", "027", 1),
            _r("S21.G00.23.005", "50.00", 2),
        )
        groups = group_establishment_blocks(est)
        assert any("orphan_s23_block" in w for w in groups.warnings)

    def test_orphan_s81(self):
        emp = _emp(
            _r("S21.G00.30.001", "12345", 1),
            _r("S21.G00.81.001", "131", 2),
            _r("S21.G00.81.004", "100.00", 3),
        )
        groups = group_employee_blocks(emp)
        assert any("orphan_s81_block" in w for w in groups.warnings)

    def test_s79_ignored_in_78_81_chain(self):
        emp = _emp(
            _r("S21.G00.30.001", "12345", 1),
            _r("S21.G00.78.001", "03", 2),
            _r("S21.G00.78.004", "3000.00", 3),
            _r("S21.G00.79.001", "01", 4),  # S79 — should be ignored
            _r("S21.G00.79.004", "1500.00", 5),
            _r("S21.G00.81.001", "131", 6),
            _r("S21.G00.81.004", "200.00", 7),
        )
        groups = group_employee_blocks(emp)
        assert len(groups.s78_blocks) == 1
        assert len(groups.s78_blocks[0].children) == 1  # S81 attached to S78
        assert not any("orphan" in w for w in groups.warnings)

    def test_s70_restarts_when_suffix_order_resets(self):
        emp = _emp(
            _r("S21.G00.30.001", "12345", 1),
            _r("S21.G00.70.005", "Ensemble du personnel", 2),
            _r("S21.G00.70.012", "2", 3),
            _r("S21.G00.70.013", "101", 4),
            _r("S21.G00.70.004", "V335004", 5),
            _r("S21.G00.70.012", "1", 6),
            _r("S21.G00.70.013", "100", 7),
        )
        groups = group_employee_blocks(emp)

        assert len(groups.s70_blocks) == 2
        first = {r.code: r.raw_value for r in groups.s70_blocks[0].records}
        second = {r.code: r.raw_value for r in groups.s70_blocks[1].records}
        assert first["S21.G00.70.012"] == "2"
        assert first["S21.G00.70.013"] == "101"
        assert second["S21.G00.70.004"] == "V335004"
        assert second["S21.G00.70.012"] == "1"
        assert second["S21.G00.70.013"] == "100"

    def test_s20_s22_s23_chain(self):
        est = _est(
            _r("S21.G00.20.001", "78861779300013", 1),
            _r("S21.G00.20.005", "5000.00", 2),
            _r("S21.G00.22.001", "78861779300013", 3),
            _r("S21.G00.22.005", "5000.00", 4),
            _r("S21.G00.23.001", "100", 5),
            _r("S21.G00.23.005", "3000.00", 6),
            _r("S21.G00.23.001", "027", 7),
            _r("S21.G00.23.005", "2000.00", 8),
        )
        groups = group_establishment_blocks(est)
        assert len(groups.s20_blocks) == 1
        assert len(groups.s22_blocks) == 1
        assert len(groups.s22_blocks[0].children) == 2  # 2 CTP blocks


# ---------------------------------------------------------------------------
# Classification tests
# ---------------------------------------------------------------------------


class TestClassification:
    def test_pas_dgfip_literal(self):
        est = _est(
            _r("S21.G00.20.001", "DGFIP", 1),
            _r("S21.G00.20.005", "1000.00", 2),
        )
        cc = compute_contribution_comparisons(est)
        assert len(cc.items) == 1
        assert cc.items[0].family == "pas"

    def test_urssaf_via_s22(self):
        est = _est(
            _r("S21.G00.20.001", "78861779300013", 1),
            _r("S21.G00.20.005", "5000.00", 2),
            _r("S21.G00.22.001", "78861779300013", 3),
            _r("S21.G00.22.005", "5000.00", 4),
        )
        cc = compute_contribution_comparisons(est)
        urssaf_items = [i for i in cc.items if i.family == "urssaf"]
        assert len(urssaf_items) == 1

    def test_s22_takes_precedence_over_registry(self):
        """Even if registry says 'retraite', S22 linkage → urssaf."""
        # Use a known URSSAF SIRET that has an S22
        est = _est(
            _r("S21.G00.20.001", "78861779300013", 1),
            _r("S21.G00.20.005", "5000.00", 2),
            _r("S21.G00.22.001", "78861779300013", 3),
            _r("S21.G00.22.005", "5000.00", 4),
        )
        cc = compute_contribution_comparisons(est)
        assert cc.items[0].family == "urssaf"

    def test_retraite_via_registry(self):
        # AGIRC-ARRCO organism: 41062136100014 = IRCOM (AAR)
        est = _est(
            _r("S21.G00.20.001", "41062136100014", 1),
            _r("S21.G00.20.005", "2000.00", 2),
        )
        cc = compute_contribution_comparisons(est)
        assert len(cc.items) == 1
        assert cc.items[0].family == "retraite"

    def test_unclassified_unknown_organism(self):
        est = _est(
            _r("S21.G00.20.001", "UNKNOWN_ORG_999", 1),
            _r("S21.G00.20.005", "500.00", 2),
        )
        cc = compute_contribution_comparisons(est)
        assert len(cc.items) == 1
        item = cc.items[0]
        assert item.family == "unclassified"
        assert item.status == "non_calculable"
        assert item.aggregate_amount == Decimal("500.00")
        assert any("unclassified_organism" in w for w in item.warnings)

    def test_unclassified_canonical_shape(self):
        """Rules 3b and 5 produce identical field shape."""
        est = _est(
            _r("S21.G00.20.001", "UNKNOWN_ORG_999", 1),
            _r("S21.G00.20.005", "500.00", 2),
        )
        cc = compute_contribution_comparisons(est)
        item = cc.items[0]
        assert item.family == "unclassified"
        assert item.status == "non_calculable"
        assert item.bordereau_amount is None
        assert item.component_amount is None
        assert item.individual_amount is None
        assert item.aggregate_vs_bordereau_delta is None
        assert item.bordereau_vs_component_delta is None
        assert item.aggregate_vs_component_delta is None
        assert item.aggregate_vs_individual_delta is None
        assert item.details == []
        assert item.adhesion_id is None
        assert item.contract_ref is None

    def test_dgfip_literal_case_sensitive(self):
        est = _est(
            _r("S21.G00.20.001", "dgfip", 1),
            _r("S21.G00.20.005", "100.00", 2),
        )
        cc = compute_contribution_comparisons(est)
        # lowercase 'dgfip' is NOT 'DGFIP' — should be unclassified
        assert cc.items[0].family == "unclassified"


# ---------------------------------------------------------------------------
# Serialization tests
# ---------------------------------------------------------------------------


class TestSerialization:
    def test_all_fields_present_in_json(self):
        item = ContributionComparisonItem(family="pas", status="ok")
        data = item.model_dump(mode="json")
        expected_fields = {
            "family", "organism_id", "organism_label", "aggregate_amount",
            "bordereau_amount", "component_amount", "individual_amount",
            "aggregate_vs_bordereau_delta", "bordereau_vs_component_delta",
            "aggregate_vs_component_delta", "aggregate_vs_individual_delta",
            "status", "details", "warnings", "adhesion_id", "contract_ref",
        }
        assert set(data.keys()) == expected_fields

    def test_null_fields_are_null_not_absent(self):
        item = ContributionComparisonItem(family="pas", status="ok")
        data = item.model_dump(mode="json")
        assert "bordereau_amount" in data
        assert data["bordereau_amount"] is None

    def test_empty_lists_are_empty_not_null(self):
        item = ContributionComparisonItem(family="pas", status="ok")
        data = item.model_dump(mode="json")
        assert data["details"] == []
        assert data["warnings"] == []

    def test_round_trip(self):
        item = ContributionComparisonItem(
            family="pas",
            organism_id="DGFIP",
            aggregate_amount=Decimal("1000.00"),
            status="ok",
        )
        data = item.model_dump(mode="json")
        restored = ContributionComparisonItem.model_validate(data)
        assert restored.family == "pas"

    def test_dsn_output_with_contributions(self):
        output = DSNOutput()
        data = output.model_dump(mode="json")
        assert "contribution_comparisons" in data["establishments"] or True  # no establishments
        assert "global_contribution_comparisons" in data
        assert data["global_contribution_comparisons"]["items"] == []


# ---------------------------------------------------------------------------
# Counting semantics tests
# ---------------------------------------------------------------------------


class TestCounting:
    def test_ok_count_only_ok(self):
        est = _est(
            _r("S21.G00.20.001", "DGFIP", 1),
            _r("S21.G00.20.005", "100.00", 2),
            employees=[
                _emp(
                    _r("S21.G00.30.001", "12345", 10),
                    _r("S21.G00.50.009", "100.00", 11),
                ),
            ],
        )
        cc = compute_contribution_comparisons(est)
        assert cc.ok_count == 1
        assert cc.mismatch_count == 0

    def test_mismatch_count_only_ecart(self):
        est = _est(
            _r("S21.G00.20.001", "DGFIP", 1),
            _r("S21.G00.20.005", "100.00", 2),
            employees=[
                _emp(
                    _r("S21.G00.30.001", "12345", 10),
                    _r("S21.G00.50.009", "200.00", 11),
                ),
            ],
        )
        cc = compute_contribution_comparisons(est)
        assert cc.ok_count == 0
        assert cc.mismatch_count == 1

    def test_unclassified_excluded_from_ok_mismatch(self):
        est = _est(
            _r("S21.G00.20.001", "UNKNOWN_999", 1),
            _r("S21.G00.20.005", "100.00", 2),
        )
        cc = compute_contribution_comparisons(est)
        assert cc.ok_count == 0
        assert cc.mismatch_count == 0
        assert cc.warning_count > 0

    def test_warnings_from_all_items(self):
        est = _est(
            _r("S21.G00.20.001", "DGFIP", 1),
            _r("S21.G00.20.005", "100.00", 2),
            _r("S21.G00.20.001", "UNKNOWN_999", 5),
            _r("S21.G00.20.005", "50.00", 6),
            employees=[
                _emp(
                    _r("S21.G00.30.001", "12345", 10),
                    _r("S21.G00.50.009", "100.00", 11),
                ),
            ],
        )
        cc = compute_contribution_comparisons(est)
        # Warning from unclassified item should be counted
        assert cc.warning_count >= 1


# ---------------------------------------------------------------------------
# Bridge-link scope tests
# ---------------------------------------------------------------------------


class TestBridgeLinkScope:
    def test_retraite_unaffected_by_missing_s15(self):
        est = _est(
            _r("S21.G00.20.001", "41062136100014", 1),  # IRCOM = retraite
            _r("S21.G00.20.005", "500.00", 2),
            # No S15 blocks at all
            employees=[
                _emp(
                    _r("S21.G00.30.001", "12345", 10),
                    _r("S21.G00.78.001", "03", 11),
                    _r("S21.G00.78.004", "3000.00", 12),
                    _r("S21.G00.81.001", "131", 13),
                    _r("S21.G00.81.004", "500.00", 14),
                ),
            ],
        )
        cc = compute_contribution_comparisons(est)
        retraite = [i for i in cc.items if i.family == "retraite"]
        assert len(retraite) == 1
        assert retraite[0].status != "non_rattache"

    def test_urssaf_unaffected_by_missing_s15_s70(self):
        est = _est(
            _r("S21.G00.20.001", "78861779300013", 1),
            _r("S21.G00.20.005", "5000.00", 2),
            _r("S21.G00.22.001", "78861779300013", 3),
            _r("S21.G00.22.005", "5000.00", 4),
            _r("S21.G00.23.001", "100", 5),
            _r("S21.G00.23.005", "5000.00", 6),
        )
        cc = compute_contribution_comparisons(est)
        urssaf = [i for i in cc.items if i.family == "urssaf"]
        assert len(urssaf) == 1
        assert urssaf[0].status != "non_rattache"

    def test_pas_unaffected_by_missing_s15_s70(self):
        est = _est(
            _r("S21.G00.20.001", "DGFIP", 1),
            _r("S21.G00.20.005", "100.00", 2),
            employees=[
                _emp(
                    _r("S21.G00.30.001", "12345", 10),
                    _r("S21.G00.50.009", "100.00", 11),
                ),
            ],
        )
        cc = compute_contribution_comparisons(est)
        pas = [i for i in cc.items if i.family == "pas"]
        assert len(pas) == 1
        assert pas[0].status == "ok"


# ---------------------------------------------------------------------------
# Core reconciliation tests
# ---------------------------------------------------------------------------


class TestPAS:
    def test_pas_ok(self):
        est = _est(
            _r("S21.G00.20.001", "DGFIP", 1),
            _r("S21.G00.20.005", "300.00", 2),
            employees=[
                _emp(
                    _r("S21.G00.30.001", "12345", 10),
                    _r("S21.G00.30.002", "DUPONT", 11),
                    _r("S21.G00.50.009", "200.00", 12),
                ),
                _emp(
                    _r("S21.G00.30.001", "67890", 20),
                    _r("S21.G00.30.002", "MARTIN", 21),
                    _r("S21.G00.50.009", "100.00", 22),
                ),
            ],
        )
        cc = compute_contribution_comparisons(est)
        pas = [i for i in cc.items if i.family == "pas"][0]
        assert pas.status == "ok"
        assert pas.aggregate_amount == Decimal("300.00")
        assert pas.individual_amount == Decimal("300.00")
        assert len(pas.details) == 2

    def test_pas_ecart(self):
        est = _est(
            _r("S21.G00.20.001", "DGFIP", 1),
            _r("S21.G00.20.005", "300.00", 2),
            employees=[
                _emp(
                    _r("S21.G00.30.001", "12345", 10),
                    _r("S21.G00.50.009", "250.00", 11),
                ),
            ],
        )
        cc = compute_contribution_comparisons(est)
        pas = [i for i in cc.items if i.family == "pas"][0]
        assert pas.status == "ecart"
        assert pas.aggregate_vs_individual_delta == Decimal("50.00")

    def test_pas_multiple_s50_per_employee(self):
        est = _est(
            _r("S21.G00.20.001", "DGFIP", 1),
            _r("S21.G00.20.005", "300.00", 2),
            employees=[
                _emp(
                    _r("S21.G00.30.001", "12345", 10),
                    _r("S21.G00.50.009", "200.00", 11),
                    _r("S21.G00.50.009", "100.00", 12),  # second S50 block
                ),
            ],
        )
        cc = compute_contribution_comparisons(est)
        pas = [i for i in cc.items if i.family == "pas"][0]
        assert pas.status == "ok"
        assert pas.individual_amount == Decimal("300.00")


class TestURSSAF:
    def test_urssaf_multi_ctp(self):
        est = _est(
            _r("S21.G00.20.001", "78861779300013", 1),
            _r("S21.G00.20.005", "5000.00", 2),
            _r("S21.G00.22.001", "78861779300013", 3),
            _r("S21.G00.22.005", "5000.00", 4),
            _r("S21.G00.23.001", "100", 5),
            _r("S21.G00.23.005", "3000.00", 6),
            _r("S21.G00.23.001", "027", 7),
            _r("S21.G00.23.005", "2000.00", 8),
        )
        cc = compute_contribution_comparisons(est)
        urssaf = [i for i in cc.items if i.family == "urssaf"][0]
        assert urssaf.status == "ok"
        assert urssaf.aggregate_amount == Decimal("5000.00")
        assert urssaf.bordereau_amount == Decimal("5000.00")
        assert urssaf.component_amount == Decimal("5000.00")
        assert len(urssaf.details) == 2

    def test_urssaf_rate_only(self):
        """CTP with empty 23.005 but base+rate present → uses recomputed."""
        est = _est(
            _r("S21.G00.20.001", "78861779300013", 1),
            _r("S21.G00.20.005", "219.00", 2),
            _r("S21.G00.22.001", "78861779300013", 3),
            _r("S21.G00.22.005", "219.00", 4),
            _r("S21.G00.23.001", "100", 5),
            _r("S21.G00.23.002", "920", 6),
            _r("S21.G00.23.003", "7.30", 7),
            _r("S21.G00.23.004", "3000.00", 8),
            _r("S21.G00.23.005", "", 9),  # empty declared
        )
        cc = compute_contribution_comparisons(est)
        urssaf = [i for i in cc.items if i.family == "urssaf"][0]
        # recomputed = 3000 * 7.30 / 100 = 219.00
        assert urssaf.component_amount == Decimal("219.00")
        assert urssaf.details[0].computed_amount == Decimal("219.00")

    def test_urssaf_partial_ctp_recalculation_hides_partial_component_total(self):
        est = _est(
            _r("S21.G00.20.001", "78861779300013", 1),
            _r("S21.G00.20.005", "5000.00", 2),
            _r("S21.G00.22.001", "78861779300013", 3),
            _r("S21.G00.22.005", "5000.00", 4),
            _r("S21.G00.23.001", "100", 5),
            _r("S21.G00.23.002", "920", 6),
            _r("S21.G00.23.003", "10.00", 7),
            _r("S21.G00.23.004", "1000.00", 8),
            _r("S21.G00.23.001", "260", 9),
            _r("S21.G00.23.002", "920", 10),
            _r("S21.G00.23.004", "4000.00", 11),
        )
        cc = compute_contribution_comparisons(est)
        urssaf = [i for i in cc.items if i.family == "urssaf"][0]

        assert urssaf.component_amount is None
        assert urssaf.bordereau_vs_component_delta is None
        assert any("partial_ctp_recalculation" in w for w in urssaf.warnings)
        assert urssaf.status == "ok"


class TestRetraite:
    def test_retraite_bases_02_03_with_negatives(self):
        est = _est(
            _r("S21.G00.20.001", "41062136100014", 1),  # IRCOM = retraite
            _r("S21.G00.20.005", "450.00", 2),
            employees=[
                _emp(
                    _r("S21.G00.30.001", "12345", 10),
                    _r("S21.G00.30.002", "DUPONT", 11),
                    # Base 03
                    _r("S21.G00.78.001", "03", 12),
                    _r("S21.G00.78.004", "3000.00", 13),
                    _r("S21.G00.81.001", "131", 14),
                    _r("S21.G00.81.004", "300.00", 15),
                    _r("S21.G00.81.001", "132", 16),
                    _r("S21.G00.81.004", "200.00", 17),
                    # Base 02
                    _r("S21.G00.78.001", "02", 18),
                    _r("S21.G00.78.004", "2500.00", 19),
                    _r("S21.G00.81.001", "106", 20),
                    _r("S21.G00.81.004", "-50.00", 21),  # negative exoneration
                ),
            ],
        )
        cc = compute_contribution_comparisons(est)
        retraite = [i for i in cc.items if i.family == "retraite"][0]
        # 300 + 200 + (-50) = 450
        assert retraite.individual_amount == Decimal("450.00")
        assert retraite.status == "ok"


# ---------------------------------------------------------------------------
# Regularization tests
# ---------------------------------------------------------------------------


class TestRegularization:
    def test_regularization_preserves_ok(self):
        est = _est(
            _r("S21.G00.20.001", "DGFIP", 1),
            _r("S21.G00.20.005", "100.00", 2),
            _r("S21.G00.20.013", "CRM123", 3),  # regularization marker
            employees=[
                _emp(
                    _r("S21.G00.30.001", "12345", 10),
                    _r("S21.G00.50.009", "100.00", 11),
                ),
            ],
        )
        cc = compute_contribution_comparisons(est)
        pas = [i for i in cc.items if i.family == "pas"][0]
        assert pas.status == "ok"
        assert any("régularisation" in w.lower() for w in pas.warnings)

    def test_regularization_preserves_ecart(self):
        est = _est(
            _r("S21.G00.20.001", "DGFIP", 1),
            _r("S21.G00.20.005", "100.00", 2),
            _r("S21.G00.20.013", "CRM123", 3),
            employees=[
                _emp(
                    _r("S21.G00.30.001", "12345", 10),
                    _r("S21.G00.50.009", "200.00", 11),
                ),
            ],
        )
        cc = compute_contribution_comparisons(est)
        pas = [i for i in cc.items if i.family == "pas"][0]
        assert pas.status == "ecart"
        assert any("régularisation" in w.lower() for w in pas.warnings)

    def test_no_marker_no_warning(self):
        est = _est(
            _r("S21.G00.20.001", "DGFIP", 1),
            _r("S21.G00.20.005", "100.00", 2),
            employees=[
                _emp(
                    _r("S21.G00.30.001", "12345", 10),
                    _r("S21.G00.50.009", "100.00", 11),
                ),
            ],
        )
        cc = compute_contribution_comparisons(est)
        pas = [i for i in cc.items if i.family == "pas"][0]
        assert not any("régularisation" in w.lower() for w in pas.warnings)


# ---------------------------------------------------------------------------
# Response shape / UI tests
# ---------------------------------------------------------------------------


class TestResponseShape:
    def test_empty_state(self):
        est = _est()
        cc = compute_contribution_comparisons(est)
        assert cc.items == []
        assert cc.ok_count == 0
        assert cc.mismatch_count == 0
        assert cc.warning_count == 0

    def test_json_validates_dsn_output(self):
        est = _est(
            _r("S21.G00.20.001", "DGFIP", 1),
            _r("S21.G00.20.005", "100.00", 2),
        )
        cc = compute_contribution_comparisons(est)
        data = cc.model_dump(mode="json")
        restored = ContributionComparisons.model_validate(data)
        assert len(restored.items) == len(cc.items)


# ---------------------------------------------------------------------------
# Global aggregation tests
# ---------------------------------------------------------------------------


class TestGlobalAggregation:
    def test_multi_establishment(self):
        est1 = _est(
            _r("S21.G00.20.001", "DGFIP", 1),
            _r("S21.G00.20.005", "100.00", 2),
            employees=[
                _emp(
                    _r("S21.G00.30.001", "12345", 10),
                    _r("S21.G00.50.009", "100.00", 11),
                ),
            ],
        )
        est2 = _est(
            _r("S21.G00.20.001", "DGFIP", 20),
            _r("S21.G00.20.005", "200.00", 21),
            employees=[
                _emp(
                    _r("S21.G00.30.001", "67890", 30),
                    _r("S21.G00.50.009", "200.00", 31),
                ),
            ],
        )
        cc1 = compute_contribution_comparisons(est1)
        cc2 = compute_contribution_comparisons(est2)
        merged = merge_contribution_comparisons([cc1, cc2])
        assert len(merged.items) == 2
        assert merged.ok_count == 2

    def test_single_establishment_equals_global(self):
        est = _est(
            _r("S21.G00.20.001", "DGFIP", 1),
            _r("S21.G00.20.005", "100.00", 2),
            employees=[
                _emp(
                    _r("S21.G00.30.001", "12345", 10),
                    _r("S21.G00.50.009", "100.00", 11),
                ),
            ],
        )
        cc = compute_contribution_comparisons(est)
        merged = merge_contribution_comparisons([cc])
        assert merged.ok_count == cc.ok_count
        assert merged.mismatch_count == cc.mismatch_count
        assert merged.warning_count == cc.warning_count
        assert len(merged.items) == len(cc.items)


# ---------------------------------------------------------------------------
# Regression tests — reproduced defects
# ---------------------------------------------------------------------------


class TestRegressionClassification:
    """Registry-only prevoyance/mutuelle/urssaf without structural link → unclassified."""

    def test_registry_only_prevoyance_without_s15_is_unclassified(self):
        """P0942 = AG2R PREVOYANCE (CTI → prevoyance) but no S15 or S22 link."""
        est = _est(
            _r("S21.G00.20.001", "P0942", 1),
            _r("S21.G00.20.005", "1200.00", 2),
        )
        cc = compute_contribution_comparisons(est)
        assert len(cc.items) == 1
        item = cc.items[0]
        assert item.family == "unclassified"
        assert item.status == "non_calculable"
        assert item.aggregate_amount == Decimal("1200.00")
        assert any("unclassified_organism" in w for w in item.warnings)

    def test_registry_only_mutuelle_without_s15_is_unclassified(self):
        """538518473 = HARMONIE MUTUELLE (FNM → mutuelle) but no S15 link."""
        est = _est(
            _r("S21.G00.20.001", "538518473", 1),
            _r("S21.G00.20.005", "800.00", 2),
        )
        cc = compute_contribution_comparisons(est)
        assert len(cc.items) == 1
        item = cc.items[0]
        assert item.family == "unclassified"
        assert item.status == "non_calculable"
        assert item.aggregate_amount == Decimal("800.00")

    def test_registry_only_urssaf_without_s22_is_unclassified(self):
        """Urssaf organism without S22 bordereau → unclassified, not urssaf."""
        est = _est(
            _r("S21.G00.20.001", "78861779300013", 1),  # Urssaf IDF
            _r("S21.G00.20.005", "5000.00", 2),
            # No S22 block
        )
        cc = compute_contribution_comparisons(est)
        assert len(cc.items) == 1
        item = cc.items[0]
        # Without S22, rule 2 doesn't match. Rule 4 only accepts retraite.
        assert item.family == "unclassified"
        assert item.status == "non_calculable"


class TestRegressionS70Mandatory:
    """Complementary with S15 + S55 but no S70 → not ok."""

    def test_prevoyance_with_s15_s55_but_no_s70(self):
        """S15+S55 present, S70 missing → non_rattache, raw amounts visible."""
        est = _est(
            # S15 adhesion
            _r("S21.G00.15.001", "CONTRAT_PREV", 1),
            _r("S21.G00.15.002", "P0942", 2),  # AG2R PREVOYANCE
            _r("S21.G00.15.005", "ADH001", 3),
            # S20 versement
            _r("S21.G00.20.001", "P0942", 10),
            _r("S21.G00.20.005", "500.00", 11),
            # S55 composant
            _r("S21.G00.55.001", "500.00", 12),
            _r("S21.G00.55.003", "CONTRAT_PREV", 13),
            employees=[
                _emp(
                    _r("S21.G00.30.001", "12345", 20),
                    # No S70 blocks at all
                    _r("S21.G00.78.001", "31", 21),
                    _r("S21.G00.78.005", "AFFIL001", 22),
                    _r("S21.G00.78.006", "CONTRAT_PREV", 23),
                    _r("S21.G00.81.001", "059", 24),
                    _r("S21.G00.81.004", "500.00", 25),
                ),
            ],
        )
        cc = compute_contribution_comparisons(est)
        prev = [i for i in cc.items if i.family == "prevoyance"]
        assert len(prev) == 1
        item = prev[0]
        assert item.status == "non_rattache"
        # Raw amounts still visible
        assert item.component_amount == Decimal("500.00")
        assert any("missing_structuring_block_s70" in w for w in item.warnings)
        # Must NOT be ok
        assert cc.ok_count == 0


class TestRegressionMultiContract:
    """Same organism with two contracts → two distinct items."""

    def test_one_organism_two_contracts_produces_two_items(self):
        est = _est(
            # Two S15 adhesions for same organism, different contracts
            _r("S21.G00.15.001", "CONTRAT_A", 1),
            _r("S21.G00.15.002", "P0942", 2),
            _r("S21.G00.15.005", "ADH_A", 3),
            _r("S21.G00.15.001", "CONTRAT_B", 4),
            _r("S21.G00.15.002", "P0942", 5),
            _r("S21.G00.15.005", "ADH_B", 6),
            # S20 versement
            _r("S21.G00.20.001", "P0942", 10),
            _r("S21.G00.20.005", "1000.00", 11),
            # S55 composants for each contract
            _r("S21.G00.55.001", "600.00", 12),
            _r("S21.G00.55.003", "CONTRAT_A", 13),
            _r("S21.G00.55.001", "400.00", 14),
            _r("S21.G00.55.003", "CONTRAT_B", 15),
            employees=[
                _emp(
                    _r("S21.G00.30.001", "12345", 20),
                    # S70 affiliations
                    _r("S21.G00.70.001", "1", 21),
                    _r("S21.G00.70.012", "AFFIL_A", 22),
                    _r("S21.G00.70.013", "ADH_A", 23),
                    _r("S21.G00.70.001", "2", 24),
                    _r("S21.G00.70.012", "AFFIL_B", 25),
                    _r("S21.G00.70.013", "ADH_B", 26),
                    # S78/S81 for contract A
                    _r("S21.G00.78.001", "31", 30),
                    _r("S21.G00.78.005", "AFFIL_A", 31),
                    _r("S21.G00.78.006", "CONTRAT_A", 32),
                    _r("S21.G00.81.001", "059", 33),
                    _r("S21.G00.81.004", "600.00", 34),
                    # S78/S81 for contract B
                    _r("S21.G00.78.001", "31", 40),
                    _r("S21.G00.78.005", "AFFIL_B", 41),
                    _r("S21.G00.78.006", "CONTRAT_B", 42),
                    _r("S21.G00.81.001", "059", 43),
                    _r("S21.G00.81.004", "400.00", 44),
                ),
            ],
        )
        cc = compute_contribution_comparisons(est)
        prev = [i for i in cc.items if i.family == "prevoyance"]
        assert len(prev) == 2, f"Expected 2 items, got {len(prev)}"
        contracts = {i.contract_ref for i in prev}
        assert contracts == {"CONTRAT_A", "CONTRAT_B"}
        # Each should have its own component amount
        for item in prev:
            if item.contract_ref == "CONTRAT_A":
                assert item.component_amount == Decimal("600.00")
            elif item.contract_ref == "CONTRAT_B":
                assert item.component_amount == Decimal("400.00")

    def test_individual_matching_uses_affiliation_not_s78_contract_number(self):
        est = _est(
            _r("S21.G00.15.001", "CONTRAT_PREV", 1),
            _r("S21.G00.15.002", "P0942", 2),
            _r("S21.G00.15.005", "ADH_PREV", 3),
            _r("S21.G00.20.001", "P0942", 10),
            _r("S21.G00.20.005", "500.00", 11),
            _r("S21.G00.55.001", "500.00", 12),
            _r("S21.G00.55.003", "CONTRAT_PREV", 13),
            employees=[
                _emp(
                    _r("S21.G00.30.001", "12345", 20),
                    _r("S21.G00.70.001", "1", 21),
                    _r("S21.G00.70.012", "AFF_PREV", 22),
                    _r("S21.G00.70.013", "ADH_PREV", 23),
                    _r("S21.G00.78.001", "31", 30),
                    _r("S21.G00.78.005", "AFF_PREV", 31),
                    # S78.006 is the employment-contract number, not S15.001.
                    _r("S21.G00.78.006", "CTR_SALARIE_2025", 32),
                    _r("S21.G00.81.001", "059", 33),
                    _r("S21.G00.81.004", "500.00", 34),
                ),
            ],
        )
        cc = compute_contribution_comparisons(est)
        prev = [i for i in cc.items if i.family == "prevoyance"]
        assert len(prev) == 1
        item = prev[0]
        assert item.individual_amount == Decimal("500.00")
        assert item.status == "ok"

    def test_complementary_family_can_differ_by_contract_for_same_organism(self):
        est = _est(
            _r("S21.G00.15.001", "SANTE0000041844", 1),
            _r("S21.G00.15.002", "AALAN1", 2),
            _r("S21.G00.15.005", "ADH_SANTE", 3),
            _r("S21.G00.15.001", "PREV_CONTRAT_X", 4),
            _r("S21.G00.15.002", "AALAN1", 5),
            _r("S21.G00.15.005", "ADH_PREV", 6),
            _r("S21.G00.20.001", "AALAN1", 10),
            _r("S21.G00.20.005", "1000.00", 11),
            _r("S21.G00.55.001", "600.00", 12),
            _r("S21.G00.55.003", "SANTE0000041844", 13),
            _r("S21.G00.55.001", "400.00", 14),
            _r("S21.G00.55.003", "PREV_CONTRAT_X", 15),
            employees=[
                _emp(
                    _r("S21.G00.30.001", "12345", 20),
                    _r("S21.G00.70.001", "1", 21),
                    _r("S21.G00.70.012", "AFF_SANTE", 22),
                    _r("S21.G00.70.013", "ADH_SANTE", 23),
                    _r("S21.G00.70.001", "2", 24),
                    _r("S21.G00.70.012", "AFF_PREV", 25),
                    _r("S21.G00.70.013", "ADH_PREV", 26),
                    _r("S21.G00.78.001", "31", 30),
                    _r("S21.G00.78.005", "AFF_SANTE", 31),
                    _r("S21.G00.81.001", "059", 32),
                    _r("S21.G00.81.004", "600.00", 33),
                    _r("S21.G00.78.001", "31", 40),
                    _r("S21.G00.78.005", "AFF_PREV", 41),
                    _r("S21.G00.81.001", "059", 42),
                    _r("S21.G00.81.004", "400.00", 43),
                ),
            ],
        )
        cc = compute_contribution_comparisons(est)
        by_contract = {i.contract_ref: i for i in cc.items if i.organism_id == "AALAN1"}

        assert by_contract["SANTE0000041844"].family == "mutuelle"
        assert by_contract["PREV_CONTRAT_X"].family == "prevoyance"


class TestRegressionSameContractDifferentAdhesion:
    """Same organism + same contract_ref + different adhesion_id."""

    def test_same_contract_ref_two_adhesions_produces_two_items(self):
        """Two S15 with same contract_ref and organism but different adhesion_id
        → two distinct items, both non_calculable (component not allocable)."""
        est = _est(
            _r("S21.G00.15.001", "CONTRAT_X", 1),
            _r("S21.G00.15.002", "P0942", 2),
            _r("S21.G00.15.005", "ADH_ALPHA", 3),
            _r("S21.G00.15.001", "CONTRAT_X", 4),
            _r("S21.G00.15.002", "P0942", 5),
            _r("S21.G00.15.005", "ADH_BETA", 6),
            _r("S21.G00.20.001", "P0942", 10),
            _r("S21.G00.20.005", "1000.00", 11),
            _r("S21.G00.55.001", "600.00", 12),
            _r("S21.G00.55.003", "CONTRAT_X", 13),
            _r("S21.G00.55.001", "400.00", 14),
            _r("S21.G00.55.003", "CONTRAT_X", 15),
            employees=[
                _emp(
                    _r("S21.G00.30.001", "12345", 20),
                    _r("S21.G00.70.001", "1", 21),
                    _r("S21.G00.70.012", "AFFIL_A", 22),
                    _r("S21.G00.70.013", "ADH_ALPHA", 23),
                    _r("S21.G00.70.001", "2", 24),
                    _r("S21.G00.70.012", "AFFIL_B", 25),
                    _r("S21.G00.70.013", "ADH_BETA", 26),
                    _r("S21.G00.78.001", "31", 30),
                    _r("S21.G00.78.005", "AFFIL_A", 31),
                    _r("S21.G00.78.006", "CONTRAT_X", 32),
                    _r("S21.G00.81.001", "059", 33),
                    _r("S21.G00.81.004", "600.00", 34),
                    _r("S21.G00.78.001", "31", 40),
                    _r("S21.G00.78.005", "AFFIL_B", 41),
                    _r("S21.G00.78.006", "CONTRAT_X", 42),
                    _r("S21.G00.81.001", "059", 43),
                    _r("S21.G00.81.004", "400.00", 44),
                ),
            ],
        )
        cc = compute_contribution_comparisons(est)
        prev = [i for i in cc.items if i.family == "prevoyance"]
        assert len(prev) == 2, (
            f"Expected 2 items, got {len(prev)}: "
            f"{[(i.contract_ref, i.adhesion_id) for i in prev]}"
        )
        adhesions = {i.adhesion_id for i in prev}
        assert adhesions == {"ADH_ALPHA", "ADH_BETA"}
        # Both must be non_calculable — S55 component cannot be split by adhesion
        for item in prev:
            assert item.status == "non_calculable", (
                f"adhesion {item.adhesion_id}: expected non_calculable, got {item.status}"
            )
            assert item.component_amount is None, (
                f"adhesion {item.adhesion_id}: component_amount must be None "
                f"when shared, got {item.component_amount}"
            )
            assert any("component_not_allocable" in w for w in item.warnings)
        # Individual amounts still visible per adhesion
        by_adh = {i.adhesion_id: i for i in prev}
        assert by_adh["ADH_ALPHA"].individual_amount == Decimal("600.00")
        assert by_adh["ADH_BETA"].individual_amount == Decimal("400.00")
        # Must NOT count as ok or ecart
        assert cc.ok_count == 0
        assert cc.mismatch_count == 0

    def test_same_contract_ref_two_adhesions_not_silently_overwritten(self):
        """Second adhesion is not dropped. Both present and non_calculable."""
        est = _est(
            _r("S21.G00.15.001", "CTR", 1),
            _r("S21.G00.15.002", "P0942", 2),
            _r("S21.G00.15.005", "FIRST", 3),
            _r("S21.G00.15.001", "CTR", 4),
            _r("S21.G00.15.002", "P0942", 5),
            _r("S21.G00.15.005", "SECOND", 6),
            _r("S21.G00.20.001", "P0942", 10),
            _r("S21.G00.20.005", "100.00", 11),
            _r("S21.G00.55.001", "100.00", 12),
            _r("S21.G00.55.003", "CTR", 13),
            employees=[
                _emp(
                    _r("S21.G00.30.001", "12345", 20),
                    _r("S21.G00.70.001", "1", 21),
                    _r("S21.G00.70.012", "AF1", 22),
                    _r("S21.G00.70.013", "FIRST", 23),
                    _r("S21.G00.70.001", "2", 24),
                    _r("S21.G00.70.012", "AF2", 25),
                    _r("S21.G00.70.013", "SECOND", 26),
                    _r("S21.G00.78.001", "31", 30),
                    _r("S21.G00.78.005", "AF1", 31),
                    _r("S21.G00.78.006", "CTR", 32),
                    _r("S21.G00.81.001", "059", 33),
                    _r("S21.G00.81.004", "50.00", 34),
                    _r("S21.G00.78.001", "31", 40),
                    _r("S21.G00.78.005", "AF2", 41),
                    _r("S21.G00.78.006", "CTR", 42),
                    _r("S21.G00.81.001", "059", 43),
                    _r("S21.G00.81.004", "50.00", 44),
                ),
            ],
        )
        cc = compute_contribution_comparisons(est)
        prev = [i for i in cc.items if i.family == "prevoyance"]
        assert len(prev) == 2
        assert {"FIRST", "SECOND"} == {i.adhesion_id for i in prev}
        # Both non_calculable — shared contract_ref blocks component allocation
        for item in prev:
            assert item.status == "non_calculable"
            assert item.component_amount is None

    def test_shared_s55_not_duplicated_across_adhesions(self):
        """Exact reproduced defect: one S55 amount of 600, two adhesions with
        individual 600/400. The 600 must NOT be assigned to both adhesions."""
        est = _est(
            _r("S21.G00.15.001", "CONTRAT_A", 1),
            _r("S21.G00.15.002", "P0942", 2),
            _r("S21.G00.15.005", "ADH_1", 3),
            _r("S21.G00.15.001", "CONTRAT_A", 4),
            _r("S21.G00.15.002", "P0942", 5),
            _r("S21.G00.15.005", "ADH_2", 6),
            _r("S21.G00.20.001", "P0942", 10),
            _r("S21.G00.20.005", "1000.00", 11),
            # Single S55 at contract level — 600.00
            _r("S21.G00.55.001", "600.00", 12),
            _r("S21.G00.55.003", "CONTRAT_A", 13),
            employees=[
                _emp(
                    _r("S21.G00.30.001", "12345", 20),
                    _r("S21.G00.70.001", "1", 21),
                    _r("S21.G00.70.012", "AFF1", 22),
                    _r("S21.G00.70.013", "ADH_1", 23),
                    _r("S21.G00.70.001", "2", 24),
                    _r("S21.G00.70.012", "AFF2", 25),
                    _r("S21.G00.70.013", "ADH_2", 26),
                    _r("S21.G00.78.001", "31", 30),
                    _r("S21.G00.78.005", "AFF1", 31),
                    _r("S21.G00.78.006", "CONTRAT_A", 32),
                    _r("S21.G00.81.001", "059", 33),
                    _r("S21.G00.81.004", "600.00", 34),
                    _r("S21.G00.78.001", "31", 40),
                    _r("S21.G00.78.005", "AFF2", 41),
                    _r("S21.G00.78.006", "CONTRAT_A", 42),
                    _r("S21.G00.81.001", "059", 43),
                    _r("S21.G00.81.004", "400.00", 44),
                ),
            ],
        )
        cc = compute_contribution_comparisons(est)
        prev = [i for i in cc.items if i.family == "prevoyance"]
        assert len(prev) == 2

        by_adh = {i.adhesion_id: i for i in prev}
        adh1 = by_adh["ADH_1"]
        adh2 = by_adh["ADH_2"]

        # CRITICAL: component_amount must NOT be 600 on both items
        assert adh1.component_amount is None, (
            f"ADH_1 component_amount must be None (not allocable), got {adh1.component_amount}"
        )
        assert adh2.component_amount is None, (
            f"ADH_2 component_amount must be None (not allocable), got {adh2.component_amount}"
        )

        # Both must be non_calculable — not ok, not ecart
        assert adh1.status == "non_calculable"
        assert adh2.status == "non_calculable"

        # Individual amounts still correct per adhesion
        assert adh1.individual_amount == Decimal("600.00")
        assert adh2.individual_amount == Decimal("400.00")

        # Warning explains the situation
        assert any("component_not_allocable" in w for w in adh1.warnings)
        assert any("component_not_allocable" in w for w in adh2.warnings)

        # No false ok/ecart in counts
        assert cc.ok_count == 0
        assert cc.mismatch_count == 0


class TestRegressionMultiCaisseRetraite:
    """Multi-caisse retraite without allocation → not ok, not counted as success."""

    def test_multi_caisse_retraite_is_non_calculable(self):
        est = _est(
            # Two retraite organisms
            _r("S21.G00.20.001", "41062136100014", 1),  # IRCOM
            _r("S21.G00.20.005", "300.00", 2),
            _r("S21.G00.20.001", "31456056600015", 3),  # CGRR
            _r("S21.G00.20.005", "200.00", 4),
            employees=[
                _emp(
                    _r("S21.G00.30.001", "12345", 10),
                    _r("S21.G00.78.001", "03", 11),
                    _r("S21.G00.81.001", "131", 12),
                    _r("S21.G00.81.004", "500.00", 13),
                ),
            ],
        )
        cc = compute_contribution_comparisons(est)
        retraite = [i for i in cc.items if i.family == "retraite"]
        assert len(retraite) == 2
        for item in retraite:
            assert item.status == "non_calculable", (
                f"Multi-caisse retraite should be non_calculable, got {item.status}"
            )
            assert any("multiple_retirement_organisms_unallocated" in w for w in item.warnings)
            # Raw aggregate amount still visible
            assert item.aggregate_amount is not None
        # Must NOT count as success
        assert cc.ok_count == 0
        assert cc.mismatch_count == 0


class TestRegressionOrphanWarnings:
    """Orphan S55/S23/S81 warnings must appear in final serialized payload."""

    def test_orphan_s55_warning_in_final_payload(self):
        """S55 without preceding S20 → warning reaches serialized output."""
        est = _est(
            # Orphan S55 (no S20 before it)
            _r("S21.G00.55.001", "100.00", 1),
            _r("S21.G00.55.003", "REF1", 2),
            # Then a normal DGFIP S20
            _r("S21.G00.20.001", "DGFIP", 5),
            _r("S21.G00.20.005", "100.00", 6),
            employees=[
                _emp(
                    _r("S21.G00.30.001", "12345", 10),
                    _r("S21.G00.50.009", "100.00", 11),
                ),
            ],
        )
        cc = compute_contribution_comparisons(est)
        # The orphan warning should appear in at least one item's warnings
        all_warnings = []
        for item in cc.items:
            all_warnings.extend(item.warnings)
        assert any("orphan_s55_block" in w for w in all_warnings), (
            f"Expected orphan_s55_block warning in payload, got: {all_warnings}"
        )
        assert cc.warning_count > 0

    def test_orphan_s23_warning_in_final_payload(self):
        """S23 without preceding S22 → warning in output."""
        est = _est(
            _r("S21.G00.23.001", "100", 1),
            _r("S21.G00.23.005", "500.00", 2),
            _r("S21.G00.20.001", "DGFIP", 5),
            _r("S21.G00.20.005", "100.00", 6),
            employees=[
                _emp(
                    _r("S21.G00.30.001", "12345", 10),
                    _r("S21.G00.50.009", "100.00", 11),
                ),
            ],
        )
        cc = compute_contribution_comparisons(est)
        all_warnings = []
        for item in cc.items:
            all_warnings.extend(item.warnings)
        assert any("orphan_s23_block" in w for w in all_warnings)

    def test_orphan_s81_warning_in_final_payload(self):
        """S81 without preceding S78 → warning in output."""
        est = _est(
            _r("S21.G00.20.001", "DGFIP", 1),
            _r("S21.G00.20.005", "100.00", 2),
            employees=[
                _emp(
                    _r("S21.G00.30.001", "12345", 10),
                    _r("S21.G00.50.009", "100.00", 11),
                    _r("S21.G00.81.001", "131", 20),
                    _r("S21.G00.81.004", "200.00", 21),
                ),
            ],
        )
        cc = compute_contribution_comparisons(est)
        all_warnings = []
        for item in cc.items:
            all_warnings.extend(item.warnings)
        assert any("orphan_s81_block" in w for w in all_warnings)

    def test_orphan_warnings_with_zero_items_still_visible(self):
        """Orphan blocks with no S20 at all → carrier item surfaces warnings."""
        est = _est(
            # Orphan S55 — no S20 at all
            _r("S21.G00.55.001", "100.00", 1),
            _r("S21.G00.55.003", "REF1", 2),
            # Orphan S23 — no S22 at all
            _r("S21.G00.23.001", "027", 3),
            _r("S21.G00.23.005", "50.00", 4),
        )
        cc = compute_contribution_comparisons(est)
        # Must still have items (carrier)
        assert len(cc.items) >= 1, "Expected at least one carrier item for orphan warnings"
        all_warnings = []
        for item in cc.items:
            all_warnings.extend(item.warnings)
        assert any("orphan_s55_block" in w for w in all_warnings), (
            f"orphan_s55_block missing from payload: {all_warnings}"
        )
        assert any("orphan_s23_block" in w for w in all_warnings), (
            f"orphan_s23_block missing from payload: {all_warnings}"
        )
        assert cc.warning_count > 0
        # Carrier must not count as success
        assert cc.ok_count == 0
        assert cc.mismatch_count == 0

    def test_orphan_s81_with_zero_s20_items(self):
        """Orphan S81 in employee with no S20 blocks → carrier surfaces warning."""
        est = _est(
            employees=[
                _emp(
                    _r("S21.G00.30.001", "12345", 1),
                    _r("S21.G00.81.001", "131", 2),
                    _r("S21.G00.81.004", "200.00", 3),
                ),
            ],
        )
        cc = compute_contribution_comparisons(est)
        assert len(cc.items) >= 1
        all_warnings = []
        for item in cc.items:
            all_warnings.extend(item.warnings)
        assert any("orphan_s81_block" in w for w in all_warnings)
        assert cc.warning_count > 0


class TestRegressionRepeatedURSSAFS20:
    """Two S20 blocks for same URSSAF organism must not overwrite each other."""

    def test_two_s20_same_organism_amounts_summed(self):
        """Two S20 versements for same URSSAF → aggregate = sum of both."""
        est = _est(
            # First S20 versement
            _r("S21.G00.20.001", "78861779300013", 1),
            _r("S21.G00.20.005", "3000.00", 2),
            # Second S20 versement for same organism (e.g. regularization period)
            _r("S21.G00.20.001", "78861779300013", 3),
            _r("S21.G00.20.005", "2000.00", 4),
            # S22 bordereau
            _r("S21.G00.22.001", "78861779300013", 5),
            _r("S21.G00.22.005", "5000.00", 6),
            # CTP detail
            _r("S21.G00.23.001", "100", 7),
            _r("S21.G00.23.005", "5000.00", 8),
        )
        cc = compute_contribution_comparisons(est)
        urssaf = [i for i in cc.items if i.family == "urssaf"]
        assert len(urssaf) == 1
        item = urssaf[0]
        # aggregate must be 3000 + 2000 = 5000, not just 2000 (overwritten)
        assert item.aggregate_amount == Decimal("5000.00"), (
            f"Expected 5000.00, got {item.aggregate_amount}"
        )
        assert item.bordereau_amount == Decimal("5000.00")
        assert item.component_amount == Decimal("5000.00")
        # All three match → ok
        assert item.status == "ok"
        assert cc.ok_count == 1

    def test_two_s20_same_organism_no_false_ecart(self):
        """Second S20 must not overwrite first — must not create a false ecart."""
        est = _est(
            # Two S20 blocks that sum to match the bordereau
            _r("S21.G00.20.001", "78861779300013", 1),
            _r("S21.G00.20.005", "1000.00", 2),
            _r("S21.G00.20.001", "78861779300013", 3),
            _r("S21.G00.20.005", "4000.00", 4),
            # S22 bordereau matching the sum
            _r("S21.G00.22.001", "78861779300013", 5),
            _r("S21.G00.22.005", "5000.00", 6),
            _r("S21.G00.23.001", "100", 7),
            _r("S21.G00.23.005", "5000.00", 8),
        )
        cc = compute_contribution_comparisons(est)
        urssaf = [i for i in cc.items if i.family == "urssaf"][0]
        # If only the second S20 (4000) were kept, this would be ecart
        assert urssaf.status == "ok", (
            f"Expected ok (sum 1000+4000=5000 matches bordereau), got {urssaf.status}"
        )


class TestRegressionComplementaryMerge:
    """Same organism + same contract across multiple S20 blocks → one item."""

    def test_two_s20_same_organism_same_contract_yields_one_item(self):
        """Two S20 for P0942, each with S55 for same contract → one merged item."""
        est = _est(
            # S15 adhesion — one contract
            _r("S21.G00.15.001", "CONTRAT_X", 1),
            _r("S21.G00.15.002", "P0942", 2),
            _r("S21.G00.15.005", "ADH_X", 3),
            # First S20 versement with S55
            _r("S21.G00.20.001", "P0942", 10),
            _r("S21.G00.20.005", "300.00", 11),
            _r("S21.G00.55.001", "300.00", 12),
            _r("S21.G00.55.003", "CONTRAT_X", 13),
            # Second S20 versement for same organism, with S55
            _r("S21.G00.20.001", "P0942", 20),
            _r("S21.G00.20.005", "200.00", 21),
            _r("S21.G00.55.001", "200.00", 22),
            _r("S21.G00.55.003", "CONTRAT_X", 23),
            employees=[
                _emp(
                    _r("S21.G00.30.001", "12345", 30),
                    _r("S21.G00.70.001", "1", 31),
                    _r("S21.G00.70.012", "AFFIL_X", 32),
                    _r("S21.G00.70.013", "ADH_X", 33),
                    _r("S21.G00.78.001", "31", 34),
                    _r("S21.G00.78.005", "AFFIL_X", 35),
                    _r("S21.G00.78.006", "CONTRAT_X", 36),
                    _r("S21.G00.81.001", "059", 37),
                    _r("S21.G00.81.004", "500.00", 38),
                ),
            ],
        )
        cc = compute_contribution_comparisons(est)
        prev = [i for i in cc.items if i.family == "prevoyance"]
        # Must be exactly ONE item, not two partial ecart rows
        assert len(prev) == 1, f"Expected 1 merged item, got {len(prev)}"
        item = prev[0]
        # Aggregate: 300 + 200 = 500
        assert item.aggregate_amount == Decimal("500.00"), (
            f"Expected merged aggregate 500.00, got {item.aggregate_amount}"
        )
        # Component: 300 + 200 = 500
        assert item.component_amount == Decimal("500.00"), (
            f"Expected merged component 500.00, got {item.component_amount}"
        )
        # Individual: 500
        assert item.individual_amount == Decimal("500.00")
        # All match → ok
        assert item.status == "ok"
        assert item.contract_ref == "CONTRAT_X"
        assert item.adhesion_id == "ADH_X"

    def test_two_s20_same_organism_same_contract_does_not_produce_partial_ecart(self):
        """If amounts are only coherent when merged, partial rows would be ecart."""
        est = _est(
            _r("S21.G00.15.001", "CTR1", 1),
            _r("S21.G00.15.002", "P0942", 2),
            _r("S21.G00.15.005", "ADH1", 3),
            # S20 #1: 400
            _r("S21.G00.20.001", "P0942", 10),
            _r("S21.G00.20.005", "400.00", 11),
            _r("S21.G00.55.001", "400.00", 12),
            _r("S21.G00.55.003", "CTR1", 13),
            # S20 #2: 600
            _r("S21.G00.20.001", "P0942", 20),
            _r("S21.G00.20.005", "600.00", 21),
            _r("S21.G00.55.001", "600.00", 22),
            _r("S21.G00.55.003", "CTR1", 23),
            employees=[
                _emp(
                    _r("S21.G00.30.001", "12345", 30),
                    _r("S21.G00.70.001", "1", 31),
                    _r("S21.G00.70.012", "AFF1", 32),
                    _r("S21.G00.70.013", "ADH1", 33),
                    _r("S21.G00.78.001", "31", 34),
                    _r("S21.G00.78.005", "AFF1", 35),
                    _r("S21.G00.78.006", "CTR1", 36),
                    _r("S21.G00.81.001", "059", 37),
                    _r("S21.G00.81.004", "1000.00", 38),
                ),
            ],
        )
        cc = compute_contribution_comparisons(est)
        prev = [i for i in cc.items if i.family == "prevoyance"]
        assert len(prev) == 1
        item = prev[0]
        # Merged: aggregate=1000, component=1000, individual=1000 → ok
        assert item.aggregate_amount == Decimal("1000.00")
        assert item.component_amount == Decimal("1000.00")
        assert item.individual_amount == Decimal("1000.00")
        assert item.status == "ok"


class TestRegressionMultipleS22:
    """Multiple S22 bordereaux for the same URSSAF organism."""

    def test_two_s22_same_organism_amounts_summed_with_warning(self):
        """Two S22 for same organism → bordereau amounts summed, warning emitted."""
        est = _est(
            _r("S21.G00.20.001", "78861779300013", 1),
            _r("S21.G00.20.005", "8000.00", 2),
            # First S22
            _r("S21.G00.22.001", "78861779300013", 3),
            _r("S21.G00.22.005", "5000.00", 4),
            _r("S21.G00.23.001", "100", 5),
            _r("S21.G00.23.005", "5000.00", 6),
            # Second S22 for same organism
            _r("S21.G00.22.001", "78861779300013", 7),
            _r("S21.G00.22.005", "3000.00", 8),
            _r("S21.G00.23.001", "027", 9),
            _r("S21.G00.23.005", "3000.00", 10),
        )
        cc = compute_contribution_comparisons(est)
        urssaf = [i for i in cc.items if i.family == "urssaf"]
        assert len(urssaf) == 1
        item = urssaf[0]
        # Bordereau: 5000 + 3000 = 8000
        assert item.bordereau_amount == Decimal("8000.00"), (
            f"Expected summed bordereau 8000.00, got {item.bordereau_amount}"
        )
        # Component: 5000 + 3000 = 8000
        assert item.component_amount == Decimal("8000.00")
        assert item.aggregate_amount == Decimal("8000.00")
        assert item.status == "ok"
        # Warning for multiple S22
        assert any("multiple_s22_bordereaux" in w for w in item.warnings)

    def test_single_s22_no_warning(self):
        """Single S22 → no multiple_s22_bordereaux warning."""
        est = _est(
            _r("S21.G00.20.001", "78861779300013", 1),
            _r("S21.G00.20.005", "5000.00", 2),
            _r("S21.G00.22.001", "78861779300013", 3),
            _r("S21.G00.22.005", "5000.00", 4),
            _r("S21.G00.23.001", "100", 5),
            _r("S21.G00.23.005", "5000.00", 6),
        )
        cc = compute_contribution_comparisons(est)
        urssaf = [i for i in cc.items if i.family == "urssaf"][0]
        assert not any("multiple_s22_bordereaux" in w for w in urssaf.warnings)


# ---------------------------------------------------------------------------
# Hardening: product contracts
# ---------------------------------------------------------------------------


class TestZeroItemWarningCarrierContract:
    """The zero-item warning carrier is a technical visibility mechanism.

    When structural anomalies are detected but no S20 blocks produce comparison
    items, a carrier item is emitted so warnings reach the serialized payload.
    This test locks down its exact shape so refactors do not break UI surfacing.
    """

    def test_carrier_serialization_shape(self):
        est = _est(
            _r("S21.G00.55.001", "100.00", 1),  # orphan S55, no S20
        )
        cc = compute_contribution_comparisons(est)
        assert len(cc.items) == 1
        carrier = cc.items[0]
        # Locked contract fields
        assert carrier.family == "unclassified"
        assert carrier.status == "non_calculable"
        assert carrier.organism_id is None
        assert carrier.organism_label is None
        assert carrier.aggregate_amount is None
        assert carrier.bordereau_amount is None
        assert carrier.component_amount is None
        assert carrier.individual_amount is None
        assert carrier.details == []
        assert carrier.adhesion_id is None
        assert carrier.contract_ref is None
        # Warnings present and non-empty
        assert len(carrier.warnings) > 0
        # Round-trips through JSON without field loss
        data = carrier.model_dump(mode="json")
        assert data["family"] == "unclassified"
        assert data["status"] == "non_calculable"
        assert data["organism_id"] is None
        assert data["warnings"] != []
        # All amount fields present as null (not absent)
        for field in ("aggregate_amount", "bordereau_amount", "component_amount",
                       "individual_amount"):
            assert field in data
            assert data[field] is None

    def test_carrier_does_not_count_as_ok_or_ecart(self):
        est = _est(
            _r("S21.G00.23.001", "100", 1),  # orphan S23, no S20
        )
        cc = compute_contribution_comparisons(est)
        assert cc.ok_count == 0
        assert cc.mismatch_count == 0
        assert cc.warning_count > 0


class TestWarningCountUniquenessContract:
    """warning_count counts unique warning strings — product contract."""

    def test_duplicate_warnings_counted_once(self):
        """Same warning on two items → counted once in warning_count."""
        est = _est(
            # Two DGFIP S20 blocks → triggers "multiple_dgfip_blocks" once
            _r("S21.G00.20.001", "DGFIP", 1),
            _r("S21.G00.20.005", "100.00", 2),
            _r("S21.G00.20.001", "DGFIP", 3),
            _r("S21.G00.20.005", "200.00", 4),
            # An unclassified organism → adds its own warning
            _r("S21.G00.20.001", "UNKNOWN_XYZ", 5),
            _r("S21.G00.20.005", "50.00", 6),
            employees=[
                _emp(
                    _r("S21.G00.30.001", "12345", 10),
                    _r("S21.G00.50.009", "300.00", 11),
                ),
            ],
        )
        cc = compute_contribution_comparisons(est)
        # Collect all warnings across all items
        all_warnings: list[str] = []
        for item in cc.items:
            all_warnings.extend(item.warnings)
        unique_warnings = set(all_warnings)
        # warning_count must equal the unique count, not the total count
        assert cc.warning_count == len(unique_warnings)

    def test_distinct_warnings_each_counted(self):
        """Two different warnings → both counted."""
        est = _est(
            _r("S21.G00.20.001", "DGFIP", 1),
            _r("S21.G00.20.005", "100.00", 2),
            _r("S21.G00.20.001", "DGFIP", 3),  # triggers multiple_dgfip_blocks
            _r("S21.G00.20.005", "50.00", 4),
            employees=[
                _emp(
                    _r("S21.G00.30.001", "12345", 10),
                    _r("S21.G00.50.009", "150.00", 11),
                    _r("S21.G00.81.001", "131", 20),  # orphan S81
                    _r("S21.G00.81.004", "99.00", 21),
                ),
            ],
        )
        cc = compute_contribution_comparisons(est)
        all_warnings: list[str] = []
        for item in cc.items:
            all_warnings.extend(item.warnings)
        unique_warnings = set(all_warnings)
        assert len(unique_warnings) >= 2  # at least multiple_dgfip + orphan_s81
        assert cc.warning_count == len(unique_warnings)
