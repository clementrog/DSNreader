"""Wiring guards for the « Démo publique de Linc » toast.

The toast logic is plain JS with no JS test runner in this repo; its runtime
behaviour (date label, show/hide, dismiss) is checked in a browser before the
PR. These cheap checks keep the wiring from silently breaking: the markup is
served hidden, the script is loaded and cache-busted, and it only ever reads
www.linc.fr and sends visitors to the tagged sign-up page.
"""

from __future__ import annotations

from pathlib import Path

from starlette.testclient import TestClient

from server.app import _asset_version, app

STATIC = Path(__file__).parent.parent / "server" / "static"
client = TestClient(app)


def test_toast_markup_is_served_hidden():
    html = client.get("/").text
    assert '<aside id="demo-live-toast" class="demo-toast" aria-label="D&#233;mo publique de Linc" hidden>' in html
    assert 'aria-label="Fermer"' in html
    assert "Le logiciel de paie des cabinets exigeants" in html


def test_toast_links_to_the_tagged_signup_page_in_a_new_tab():
    html = client.get("/").text
    assert (
        'href="https://www.linc.fr/demo-live?utm_source=controle-dsn&amp;utm_medium=toast&amp;utm_campaign=demo-live"'
        ' target="_blank" rel="noopener">M\'inscrire</a>'
    ) in html


def test_toast_script_is_loaded_and_served():
    html = client.get("/").text
    assert "/static/demo-live-toast.js?v=" in html
    r = client.get("/static/demo-live-toast.js")
    assert r.status_code == 200
    assert "javascript" in r.headers["content-type"]


def test_toast_script_reads_only_linc_and_remembers_the_session():
    js = (STATIC / "demo-live-toast.js").read_text(encoding="utf-8")
    assert '"https://www.linc.fr/api/demo-live"' in js
    assert 'body.status !== "open"' in js
    assert '"linc-demo-live-toast"' in js
    assert "·" not in js


def test_toast_uses_a_non_reserved_ga4_parameter():
    # `session_id` is GA4's own browsing-session id; overwriting it corrupts later events.
    js = (STATIC / "demo-live-toast.js").read_text(encoding="utf-8")
    assert "demo_session_id: demoSessionId" in js
    assert "session_id:" not in js.replace("demo_session_id:", "")


def test_toast_never_shows_on_phones():
    js = (STATIC / "demo-live-toast.js").read_text(encoding="utf-8")
    css = (STATIC / "style.css").read_text(encoding="utf-8")
    assert '"(max-width: 767px)"' in js
    assert "@media (max-width: 767px) {\n  .demo-toast {\n    display: none;" in css
    assert "width: auto;" not in css.split("/* ── Démo publique de Linc (toast)")[1]


def test_asset_version_follows_the_toast_script():
    toast = STATIC / "demo-live-toast.js"
    assert int(_asset_version()) >= int(toast.stat().st_mtime)
