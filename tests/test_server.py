"""Tests for the FastAPI web API (Slice 6)."""

from __future__ import annotations

import pathlib

import pytest
from starlette.testclient import TestClient

from dsn_extractor.extractors import extract
from dsn_extractor.models import DSNOutput
from dsn_extractor.parser import parse
import server.app as server_app
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
                     "global_counts", "global_amounts", "global_extras", "global_quality",
                     "global_social_analysis", "global_payroll_tracking"):
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
            files={"file": ("data.csv", fixture.read_bytes(), "application/octet-stream")},
        )
        assert r.status_code == 422
        body = r.json()
        assert "extension" in body["detail"].lower()
        assert isinstance(body["warnings"], list)

    def test_txt_extension_accepted(self):
        fixture = FIXTURES / "single_establishment.dsn"
        r = client.post(
            "/api/extract",
            files={"file": ("data.txt", fixture.read_bytes(), "application/octet-stream")},
        )
        assert r.status_code == 200

    def test_edi_extension_accepted(self):
        fixture = FIXTURES / "single_establishment.dsn"
        r = client.post(
            "/api/extract",
            files={"file": ("data.edi", fixture.read_bytes(), "application/octet-stream")},
        )
        assert r.status_code == 200

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

    def test_non_utf8_falls_back_to_latin1(self):
        """Non-UTF-8 bytes are decoded via Latin-1 fallback (no 422)."""
        r = client.post(
            "/api/extract",
            files={"file": ("bad.dsn", b"\x80\x81\x82\xff", "application/octet-stream")},
        )
        # Decodes as Latin-1 but contains no valid DSN lines → 400
        assert r.status_code == 400
        assert isinstance(r.json()["warnings"], list)


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


# ── Frontend wiring (Slice 7) ──────────────────────────────


class TestFrontendWiring:
    def test_index_references_static_assets(self):
        """Root HTML must reference /static/style.css and /static/app.js."""
        r = client.get("/")
        assert r.status_code == 200
        html = r.text
        assert "/static/style.css" in html
        assert "/static/app.js" in html

    def test_index_contains_beta_heading_and_footer(self):
        r = client.get("/")
        assert r.status_code == 200
        html = r.text
        assert "Contr&#244;le DSN" in html
        assert "logo-linc.svg" in html
        assert 'id="feedback-btn-results"' in html
        assert 'id="feedback-btn-error"' in html

    def test_static_css_served(self):
        r = client.get("/static/style.css")
        assert r.status_code == 200
        assert "text/css" in r.headers["content-type"]

    def test_static_js_served(self):
        r = client.get("/static/app.js")
        assert r.status_code == 200
        assert "javascript" in r.headers["content-type"]

    def test_health_not_shadowed_by_static_mount(self):
        r = client.get("/health")
        assert r.status_code == 200
        assert r.json() == {"status": "ok"}

    def test_api_extract_not_shadowed_by_static_mount(self):
        """POST /api/extract still works after static mount."""
        r = _upload("single_establishment.dsn")
        assert r.status_code == 200
        assert "source_file" in r.json()

    def test_wrong_extension_rejected_by_server(self):
        """Server returns 422 for non-.dsn/.txt files (defence-in-depth for client-side gate)."""
        r = client.post(
            "/api/extract",
            files={"file": ("data.csv", b"content", "text/plain")},
        )
        assert r.status_code == 422


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


# ── Response schema (new sections) ────────────────────────────


class TestResponseSchema:
    def test_response_contains_new_top_level_keys(self):
        r = _upload("single_establishment.dsn")
        body = r.json()
        assert "global_social_analysis" in body
        assert "global_payroll_tracking" in body

    def test_response_establishment_contains_new_keys(self):
        r = _upload("single_establishment.dsn")
        body = r.json()
        for est in body["establishments"]:
            assert "social_analysis" in est
            assert "payroll_tracking" in est

    def test_response_social_analysis_shape(self):
        r = _upload("single_establishment.dsn")
        sa = r.json()["global_social_analysis"]
        assert isinstance(sa["effectif"], int)
        assert isinstance(sa["entrees"], int)
        assert isinstance(sa["sorties"], int)
        assert isinstance(sa["stagiaires"], int)
        assert isinstance(sa["cadre_count"], int)
        assert isinstance(sa["non_cadre_count"], int)
        assert isinstance(sa["contracts_by_code"], dict)
        assert isinstance(sa["contracts_by_label"], dict)
        assert isinstance(sa["exit_reasons_by_code"], dict)
        assert isinstance(sa["exit_reasons_by_label"], dict)
        assert isinstance(sa["absences_by_code"], dict)
        assert isinstance(sa["quality_alerts"], list)
        assert isinstance(sa["quality_alerts_count"], int)
        # Decimal fields serialized as strings or null
        for field in ("net_verse_total", "net_fiscal_total", "pas_total"):
            assert sa[field] is None or isinstance(sa[field], str)

    def test_response_payroll_tracking_shape(self):
        r = _upload("single_establishment.dsn")
        pt = r.json()["global_payroll_tracking"]
        assert isinstance(pt["bulletins"], int)
        assert isinstance(pt["billable_entries"], int)
        assert isinstance(pt["billable_exits"], int)
        assert isinstance(pt["billable_absence_events"], int)
        assert isinstance(pt["exceptional_events_count"], int)
        assert isinstance(pt["dsn_anomalies_count"], int)
        assert isinstance(pt["complexity_score"], int)
        assert isinstance(pt["complexity_inputs"], dict)
        assert isinstance(pt["billable_entry_names"], list)
        assert isinstance(pt["billable_exit_names"], list)
        assert isinstance(pt["billable_absence_details"], list)

    def test_response_validates_against_model(self):
        """Full API response round-trips through DSNOutput model validation."""
        r = _upload("single_establishment.dsn")
        assert r.status_code == 200
        # This will raise ValidationError if schema doesn't match
        DSNOutput.model_validate(r.json())


class TestFeedbackAPI:
    def test_feedback_rejects_non_json_body(self):
        r = client.post(
            "/api/feedback",
            content="not json",
            headers={"Content-Type": "text/plain"},
        )
        assert r.status_code == 400

    def test_feedback_rejects_invalid_category(self):
        r = client.post(
            "/api/feedback",
            json={
                "category": "bogus",
                "message": "Ajouter un raccourci",
                "email": "person@example.com",
                "phone": "0601020304",
                "consent": True,
                "context": {},
            },
        )
        assert r.status_code == 400
        assert "invalide" in r.json()["detail"].lower()

    def test_feedback_rejects_missing_fields(self):
        r = client.post(
            "/api/feedback",
            json={
                "category": "issue",
                "message": "",
                "email": "person@example.com",
                "phone": "",
                "consent": True,
                "context": {},
            },
        )
        assert r.status_code == 400
        assert "message" in r.json()["detail"].lower() or "téléphone" in r.json()["detail"].lower()

    def test_feedback_rejects_missing_consent(self):
        r = client.post(
            "/api/feedback",
            json={
                "category": "issue",
                "message": "Une erreur est visible",
                "email": "person@example.com",
                "phone": "0601020304",
                "consent": False,
                "context": {},
            },
        )
        assert r.status_code == 400
        assert "consentement" in r.json()["detail"].lower()

    def test_feedback_rejects_invalid_email(self):
        r = client.post(
            "/api/feedback",
            json={
                "category": "improvement",
                "message": "Ajouter un raccourci",
                "email": "not-an-email",
                "phone": "0601020304",
                "consent": True,
                "context": {},
            },
        )
        assert r.status_code == 400
        assert "email valide" in r.json()["detail"].lower()

    def test_feedback_returns_config_error_when_resend_key_missing(self, monkeypatch):
        monkeypatch.delenv("RESEND_API_KEY", raising=False)

        r = client.post(
            "/api/feedback",
            json={
                "category": "issue",
                "message": "Le calcul plante après chargement.",
                "email": "person@example.com",
                "phone": "0601020304",
                "consent": True,
                "context": {"phase": "error"},
            },
        )

        assert r.status_code == 500
        assert "configuré" in r.json()["detail"].lower()

    def test_feedback_sends_email_with_sanitized_context(self, monkeypatch):
        captured: dict[str, object] = {}

        def fake_send_feedback_email(**kwargs):
            captured.update(kwargs)
            return {"id": "email_123"}

        monkeypatch.setattr(server_app, "_send_feedback_email", fake_send_feedback_email)

        r = client.post(
            "/api/feedback",
            json={
                "category": "issue",
                "message": "Le calcul plante après chargement.",
                "email": "person@example.com",
                "phone": "0601020304",
                "consent": True,
                "context": {
                    "timestamp": "2026-04-08T10:30:00Z",
                    "phase": "results",
                    "filename": "/tmp/private-folder/client-a.dsn",
                    "active_page": "controle",
                    "scope": "global",
                    "active_contribution_family": "urssaf",
                    "browser": "Mozilla/5.0",
                    "language": "fr-FR",
                    "theme": "light",
                    "error_detail": None,
                    "visible_warning_count": 2,
                    "comparison_ok_count": 18,
                    "comparison_mismatch_count": 3,
                    "comparison_warning_count": 1,
                    "raw_dsn": "S10.G00.00.001,'P24V01'",
                    "full_payload": {"employees": ["Alice Martin"]},
                },
            },
        )

        assert r.status_code == 200
        assert r.json()["status"] == "ok"
        assert captured["category"] == "issue"
        assert captured["email"] == "person@example.com"
        assert captured["phone"] == "0601020304"

        context = captured["context"]
        assert context["filename"] == "client-a.dsn"
        assert context["comparison_mismatch_count"] == 3
        assert "raw_dsn" not in context
        assert "full_payload" not in context

    def test_feedback_returns_clean_error_on_send_failure(self, monkeypatch):
        def fake_send_feedback_email(**kwargs):
            raise RuntimeError("L'envoi du retour a échoué.")

        monkeypatch.setattr(server_app, "_send_feedback_email", fake_send_feedback_email)

        r = client.post(
            "/api/feedback",
            json={
                "category": "issue",
                "message": "Le calcul plante après chargement.",
                "email": "person@example.com",
                "phone": "0601020304",
                "consent": True,
                "context": {"phase": "error"},
            },
        )

        assert r.status_code == 500
        assert "échoué" in r.json()["detail"].lower()
