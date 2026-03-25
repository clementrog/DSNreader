"""Tests for Slice 5 — CLI entry point."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures"


def run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "dsn_extractor", *args],
        capture_output=True,
        text=True,
    )


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


class TestHappyPath:
    def test_basic_invocation(self) -> None:
        r = run_cli(str(FIXTURES / "single_establishment.dsn"))
        assert r.returncode == 0
        data = json.loads(r.stdout)
        assert "establishments" in data
        assert data["source_file"] == "single_establishment.dsn"

    def test_pretty_output(self) -> None:
        r = run_cli(str(FIXTURES / "single_establishment.dsn"), "--pretty")
        assert r.returncode == 0
        # Pretty output has indented lines
        assert "\n  " in r.stdout
        json.loads(r.stdout)  # still valid JSON

    def test_per_establishment_explicit(self) -> None:
        r = run_cli(str(FIXTURES / "single_establishment.dsn"), "--per-establishment")
        assert r.returncode == 0
        data = json.loads(r.stdout)
        assert "establishments" in data

    def test_global_only(self) -> None:
        r = run_cli(str(FIXTURES / "single_establishment.dsn"), "--global-only")
        assert r.returncode == 0
        data = json.loads(r.stdout)
        assert "establishments" not in data
        assert "global_counts" in data
        assert "global_amounts" in data

    def test_multi_establishment(self) -> None:
        r = run_cli(str(FIXTURES / "multi_establishment.dsn"))
        assert r.returncode == 0
        data = json.loads(r.stdout)
        assert len(data["establishments"]) == 2


# ---------------------------------------------------------------------------
# Mutual exclusion
# ---------------------------------------------------------------------------


class TestMutualExclusion:
    def test_both_flags_rejected(self) -> None:
        r = run_cli(
            str(FIXTURES / "single_establishment.dsn"),
            "--per-establishment",
            "--global-only",
        )
        assert r.returncode == 2
        assert r.stderr  # argparse prints error


# ---------------------------------------------------------------------------
# Failure contract (exit 1)
# ---------------------------------------------------------------------------


class TestFailureContract:
    def test_nonexistent_file(self) -> None:
        r = run_cli("/tmp/nonexistent_file_dsn_test.dsn")
        assert r.returncode == 1
        assert "Error" in r.stderr

    def test_zero_valid_dsn_lines(self, tmp_path: Path) -> None:
        bad_file = tmp_path / "garbage.dsn"
        bad_file.write_text("this is not a DSN file\njust plain text\n")
        r = run_cli(str(bad_file))
        assert r.returncode == 1
        assert "no valid DSN lines" in r.stderr

    def test_skipped_lines_tolerated(self, tmp_path: Path) -> None:
        """A file with some garbage lines but valid DSN content still succeeds."""
        content = (
            "ENVELOPE HEADER\n"
            "S10.G00.00.001,'P24V01'\n"
            "S10.G00.01.001,'123456789'\n"
            "S90.G00.90.001,'0'\n"
        )
        mixed_file = tmp_path / "mixed.dsn"
        mixed_file.write_text(content)
        r = run_cli(str(mixed_file))
        assert r.returncode == 0
        json.loads(r.stdout)

    def test_empty_file(self, tmp_path: Path) -> None:
        empty = tmp_path / "empty.dsn"
        empty.write_text("")
        r = run_cli(str(empty))
        assert r.returncode == 1
        assert "no valid DSN lines" in r.stderr


# ---------------------------------------------------------------------------
# Other
# ---------------------------------------------------------------------------


class TestOther:
    def test_help(self) -> None:
        r = run_cli("--help")
        assert r.returncode == 0
        assert "dsn_extractor" in r.stdout
