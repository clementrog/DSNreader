"""Tests for the FastAPI web API (Slice 6)."""

from __future__ import annotations

import pathlib

import pytest
from starlette.testclient import TestClient

from dsn_extractor.extractors import extract
from dsn_extractor.parser import parse
from server.app import app

FIXTURES = pathlib.Path(__file__).resolve().parent / "fixtures"

client = TestClient(app)


def _upload(fixture_name: str, *, filename: str | None = None, headers: dict[str, str] | None = None):
    """POST a fixture file to /api/extract."""
    path = FIXTURES / fixture_name
    fname = filename or fixture_name
    return client.post(
        "/api/extract",
        files={"file": (fname, path.read_bytes(), "application/octet-stream")},
        headers=headers,
    )


# ── Success tests ──────────────────────────────────────────────


class TestExtractSuccess:
    def test_single_establishment(self):
        r = _upload("single_establishment.dsn")
        assert r.status_code == 200
        body = r.json()
        for key in ("source_file", "declaration", "company", "establishments",
                     "global_counts", "global_amounts", "global_extras", "global_quality"):
            assert key in body

    def test_multi_establishment(self):
        r = _upload("multi_establishment.dsn")
        assert r.status_code == 200
        body = r.json()
        assert len(body["establishments"]) >= 2

    def test_payload_matches_library(self):
        """API response must exactly match direct library extraction."""
        fixture = FIXTURES / "single_establishment.dsn"
        text = fixture.read_text(encoding="utf-8")
        expected = extract(parse(text), source_file="single_establishment.dsn").model_dump(mode="json")

        r = _upload("single_establishment.dsn")
        assert r.status_code == 200
        assert r.json() == expected


# ── Parse tolerance ────────────────────────────────────────────


class TestParseTolerance:
    def test_skipped_lines_accepted(self):
        """File with valid DSN lines mixed with garbage returns 200, not 400."""
        mixed = (
            "GARBAGE LINE ONE\n"
            "S10.G00.00.001,'P24V01'\n"
            "NOT A DSN LINE\n"
            "S10.G00.01.001,'123456789'\n"
            "S20.G00.05.005,'01012025'\n"
        )
        r = client.post(
            "/api/extract",
            files={"file": ("test.dsn", mixed.encode("utf-8"), "application/octet-stream")},
        )
        assert r.status_code == 200
        body = r.json()
        assert body["declaration"]["period_start"] == "2025-01-01"


# ── Error tests ────────────────────────────────────────────────


class TestErrors:
    def test_empty_file(self):
        r = client.post(
            "/api/extract",
            files={"file": ("empty.dsn", b"", "application/octet-stream")},
        )
        assert r.status_code == 400
        body = r.json()
        assert "detail" in body
        assert isinstance(body["warnings"], list)

    def test_no_valid_records(self):
        content = b"this is not a dsn file\njust random text\n"
        r = client.post(
            "/api/extract",
            files={"file": ("bad.dsn", content, "application/octet-stream")},
        )
        assert r.status_code == 400
        body = r.json()
        assert "no valid DSN lines" in body["detail"]
        assert isinstance(body["warnings"], list)

    def test_invalid_extension(self):
        fixture = FIXTURES / "single_establishment.dsn"
        r = client.post(
            "/api/extract",
            files={"file": ("data.txt", fixture.read_bytes(), "application/octet-stream")},
        )
        assert r.status_code == 422
        body = r.json()
        assert "extension" in body["detail"].lower()
        assert isinstance(body["warnings"], list)

    def test_oversized_file(self):
        # 10 MB + 1 byte
        big = b"x" * (10 * 1024 * 1024 + 1)
        r = client.post(
            "/api/extract",
            files={"file": ("huge.dsn", big, "application/octet-stream")},
        )
        assert r.status_code == 413
        body = r.json()
        assert "too large" in body["detail"].lower()
        assert isinstance(body["warnings"], list)

    def test_non_utf8(self):
        r = client.post(
            "/api/extract",
            files={"file": ("bad.dsn", b"\x80\x81\x82\xff", "application/octet-stream")},
        )
        assert r.status_code == 422
        body = r.json()
        assert "utf-8" in body["detail"].lower()
        assert isinstance(body["warnings"], list)


# ── Infrastructure ─────────────────────────────────────────────


class TestInfrastructure:
    def test_health(self):
        r = client.get("/health")
        assert r.status_code == 200
        assert r.json() == {"status": "ok"}

    def test_static_index(self):
        r = client.get("/")
        assert r.status_code == 200
        assert "text/html" in r.headers["content-type"]


# ── CORS ───────────────────────────────────────────────────────


class TestCORS:
    def test_cors_simple_request(self):
        """Response to a request with Origin header includes CORS allow header."""
        r = _upload("single_establishment.dsn", headers={"Origin": "http://example.com"})
        assert r.status_code == 200
        assert r.headers.get("access-control-allow-origin") == "*"

    def test_cors_preflight(self):
        """OPTIONS preflight returns correct CORS headers."""
        r = client.options(
            "/api/extract",
            headers={
                "Origin": "http://example.com",
                "Access-Control-Request-Method": "POST",
            },
        )
        assert r.status_code == 200
        assert r.headers.get("access-control-allow-origin") == "*"
        assert "POST" in r.headers.get("access-control-allow-methods", "").upper()
