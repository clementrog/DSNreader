"""Tests for the URSSAF CTP → individual-code mapping gate (Slice B).

The slice is documentation + scaffolding only. These tests lock the product
rule ("default-deny, explicit mapping table only") and protect the TSV
against accidental regression. No DSN fixture is required — the mapping is
pure data + pure functions.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from dsn_extractor.urssaf_individual_mapping import (
    URSSAF_DETAIL_STATUSES,
    UrssafIndividualMapping,
    get_individual_code_for_ctp,
    is_urssaf_code_mappable,
    load_mapping,
)


def test_mapping_loads():
    """The TSV file exists and loads into a non-empty dict."""
    mapping = load_mapping()
    assert isinstance(mapping, dict)
    assert len(mapping) >= 1
    for row in mapping.values():
        assert isinstance(row, UrssafIndividualMapping)


def test_ctp_027_is_mappable():
    """CTP 027 (Contribution au dialogue social) is the first locked row.

    Source: publicodes 13.1 L235-247 (DIALOGUE SOCIAL 100 → URSSAF SIRET).
    """
    assert is_urssaf_code_mappable("027") is True


def test_ctp_027_maps_to_individual_code_100():
    """CTP 027 drills down to S21.G00.81.001 individual code '100'."""
    assert get_individual_code_for_ctp("027") == "100"


def test_unknown_ctp_is_not_mappable():
    """Default-deny: unknown codes return False / None."""
    assert is_urssaf_code_mappable("9999") is False
    assert is_urssaf_code_mappable("0000") is False
    assert get_individual_code_for_ctp("9999") is None


def test_empty_and_none_are_not_mappable():
    """Defensive: empty and None inputs return False / None, never raise."""
    assert is_urssaf_code_mappable("") is False
    assert is_urssaf_code_mappable(None) is False
    assert get_individual_code_for_ctp("") is None
    assert get_individual_code_for_ctp(None) is None


def test_non_rattache_is_recognized_status():
    """'non_rattache' is part of the URSSAF detail status vocabulary."""
    assert "non_rattache" in URSSAF_DETAIL_STATUSES


def test_mapping_table_has_no_duplicate_ctp():
    """The TSV loader fails fast on duplicate ctp_code rows.

    Protects the data file against accidental double-rows in future edits.
    """
    tsv_path = (
        Path(__file__).parent.parent
        / "dsn_extractor"
        / "data"
        / "urssaf_individual_mapping.tsv"
    )
    raw_lines = [
        line for line in tsv_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    ctp_codes = [line.split("\t")[0].strip() for line in raw_lines]
    assert len(ctp_codes) == len(set(ctp_codes)), (
        f"Duplicate ctp_code in urssaf_individual_mapping.tsv: {ctp_codes}"
    )
