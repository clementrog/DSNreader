"""Tests for CTP rate reference loading, validation, and lookup."""

from __future__ import annotations

import datetime as dt
from decimal import Decimal
from pathlib import Path

import pytest

from dsn_extractor.ctp_rates import (
    CTP_RATE_REFERENCE,
    CTPRateReference,
    _load_ctp_rate_reference,
    lookup_ctp_reference,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_VALID_ROW = "999\tTEST LABEL\tTEST\tE\t\t1.00\t\t01/01/2024"


def _write_tsv(tmp_path: Path, *lines: str) -> Path:
    tsv = tmp_path / "ctp_rate_reference.tsv"
    tsv.write_text("\n".join(lines), encoding="utf-8")
    return tsv


# ---------------------------------------------------------------------------
# TestCTPRateArtifact — acceptance checks on the checked-in TSV artifact
# ---------------------------------------------------------------------------


class TestCTPRateArtifact:
    """Validate the production TSV dataset loaded at import time."""

    def test_tsv_loaded(self) -> None:
        assert isinstance(CTP_RATE_REFERENCE, dict)
        assert len(CTP_RATE_REFERENCE) > 0

    def test_minimum_row_count(self) -> None:
        total = sum(len(v) for v in CTP_RATE_REFERENCE.values())
        assert total >= 500

    def test_entries_sorted_by_date(self) -> None:
        for code, entries in CTP_RATE_REFERENCE.items():
            dates = [e.effective_date for e in entries]
            assert dates == sorted(dates), f"CTP {code} entries not sorted by date"

    def test_no_duplicate_effective_dates(self) -> None:
        for code, entries in CTP_RATE_REFERENCE.items():
            dates = [e.effective_date for e in entries]
            assert len(dates) == len(set(dates)), (
                f"CTP {code} has duplicate effective_date values"
            )

    def test_known_code_100_date_boundaries(self) -> None:
        entries = CTP_RATE_REFERENCE["100"]
        by_date = {e.effective_date: e for e in entries}

        entry_2024 = by_date[dt.date(2024, 1, 1)]
        assert entry_2024.rate_deplafonne == Decimal("13.17")

        entry_2026 = by_date[dt.date(2026, 1, 1)]
        assert entry_2026.rate_deplafonne == Decimal("13.26")

    def test_known_code_772_date_boundaries(self) -> None:
        entries = CTP_RATE_REFERENCE["772"]
        by_date = {e.effective_date: e for e in entries}

        entry_2019 = by_date[dt.date(2019, 1, 1)]
        assert entry_2019.rate_deplafonne == Decimal("4.05")

        entry_2025 = by_date[dt.date(2025, 5, 1)]
        assert entry_2025.rate_deplafonne == Decimal("4.00")

    def test_required_codes_present(self) -> None:
        required = {"100", "260", "332", "430", "635", "668", "726", "772", "937"}
        assert required.issubset(CTP_RATE_REFERENCE.keys())


# ---------------------------------------------------------------------------
# TestCTPRateLoaderErrors — fail-fast on malformed artifacts
# ---------------------------------------------------------------------------


class TestCTPRateLoaderErrors:
    """Each test writes a temp TSV and expects a RuntimeError."""

    def test_missing_file(self, tmp_path: Path) -> None:
        with pytest.raises(RuntimeError):
            _load_ctp_rate_reference(tmp_path / "does_not_exist.tsv")

    def test_empty_file(self, tmp_path: Path) -> None:
        tsv = _write_tsv(tmp_path)  # no lines
        with pytest.raises(RuntimeError):
            _load_ctp_rate_reference(tsv)

    def test_wrong_column_count(self, tmp_path: Path) -> None:
        tsv = _write_tsv(tmp_path, "999\tLABEL\tSHORT\tE\t1.00")
        with pytest.raises(RuntimeError):
            _load_ctp_rate_reference(tsv)

    def test_missing_ctp_code(self, tmp_path: Path) -> None:
        tsv = _write_tsv(tmp_path, "\tTEST LABEL\tTEST\tE\t\t1.00\t\t01/01/2024")
        with pytest.raises(RuntimeError):
            _load_ctp_rate_reference(tsv)

    def test_invalid_date(self, tmp_path: Path) -> None:
        tsv = _write_tsv(tmp_path, "999\tTEST LABEL\tTEST\tE\t\t1.00\t\t99/99/9999")
        with pytest.raises(RuntimeError):
            _load_ctp_rate_reference(tsv)

    def test_duplicate_effective_date(self, tmp_path: Path) -> None:
        row1 = "999\tTEST LABEL\tTEST\tE\t\t1.00\t\t01/01/2024"
        row2 = "999\tTEST LABEL\tTEST\tE\t\t2.00\t\t01/01/2024"
        tsv = _write_tsv(tmp_path, row1, row2)
        with pytest.raises(RuntimeError):
            _load_ctp_rate_reference(tsv)

    def test_header_row_rejected(self, tmp_path: Path) -> None:
        tsv = _write_tsv(
            tmp_path,
            "Code\tLibelle\tShort\tFmt\tPlaf\tDeplaf\tAT\tDate",
        )
        with pytest.raises(RuntimeError):
            _load_ctp_rate_reference(tsv)


# ---------------------------------------------------------------------------
# TestCTPRateLookup — date selection logic
# ---------------------------------------------------------------------------


class TestCTPRateLookup:
    """Test lookup_ctp_reference against the live CTP_RATE_REFERENCE."""

    def test_unknown_code_returns_none(self) -> None:
        assert lookup_ctp_reference("ZZZZZ", dt.date(2025, 1, 1)) is None

    def test_none_date_returns_none(self) -> None:
        assert lookup_ctp_reference("100", reference_date=None) is None

    def test_selects_latest_applicable_date(self) -> None:
        result = lookup_ctp_reference("100", dt.date(2025, 6, 1))
        assert result is not None
        assert result.rate_deplafonne == Decimal("13.17")
        assert result.effective_date == dt.date(2024, 1, 1)

    def test_exact_boundary_date(self) -> None:
        result = lookup_ctp_reference("100", dt.date(2026, 1, 1))
        assert result is not None
        assert result.rate_deplafonne == Decimal("13.26")
        assert result.effective_date == dt.date(2026, 1, 1)

    def test_before_all_dates_returns_first(self) -> None:
        result = lookup_ctp_reference("100", dt.date(2020, 1, 1))
        assert result is None
