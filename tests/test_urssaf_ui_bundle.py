"""Static regression guards for the URSSAF UI cleanup pass.

These are cheap string/regex checks against the shipped frontend bundles.
They don't exercise JS at runtime — they exist so an accidental revert of
the URSSAF UX cleanup (NC token unification, collapsed-row noise removal,
header rename, pill variants, OK-with-warnings branch) is caught in CI
instead of reaching users.

By design these guards are brittle: if someone renames one of these
classes or strings deliberately, the test fails and they should re-read
the intent in this file before adjusting the assertion.
"""

from __future__ import annotations

import re
from pathlib import Path

APP_JS = Path(__file__).parent.parent / "server" / "static" / "app.js"
STYLE_CSS = Path(__file__).parent.parent / "server" / "static" / "style.css"


def _app_js() -> str:
    return APP_JS.read_text(encoding="utf-8")


def _style_css() -> str:
    return STYLE_CSS.read_text(encoding="utf-8")


def test_nc_short_form_removed_from_app_js():
    """`N.C.` is no longer emitted anywhere in the shipped bundle."""
    text = _app_js()
    assert "N.C." not in text, (
        "The short `N.C.` token must not appear in app.js — we unified on "
        "a single em-dash (`—`) with a `title=\"Non calculable\"` tooltip."
    )
    assert re.search(r"['\">]NC[<'\"]", text) is None, (
        "A bare `NC` string literal was found in app.js — replace it with "
        "a `<span class=\"cell-na\" title=\"Non calculable\">—</span>` chip."
    )


def test_non_calculable_uses_em_dash_cell_na_pattern():
    """Non-calculable cells render as a muted em-dash with the full meaning
    preserved in the `title` tooltip — no more loud `Non calculable` chips
    repeated across every empty cell."""
    text = _app_js()
    # The `cell-na` class carries the em-dash + tooltip pattern. We expect
    # it at the three formerly-divergent cell sites (assiette delta, CTP
    # delta, detail status cell) plus the AT-rate-only declared cell.
    occurrences = text.count('class="cell-na"')
    assert occurrences >= 4, (
        "Expected at least 4 `cell-na` spans in app.js (formatDetailStatus, "
        "assiette delta, CTP delta, AT-rate-only declared); "
        f"found {occurrences}."
    )
    # The meaning must still be conveyed via the tooltip.
    assert 'title="Non calculable"' in text, (
        "At least one `cell-na` em-dash must carry `title=\"Non calculable\"` "
        "so the meaning is accessible on hover."
    )
    # The old loud `<span class="cell-info">Non calculable</span>` chip
    # pattern must not survive anywhere.
    assert 'class="cell-info">Non calculable</span>' not in text, (
        "Found leftover `cell-info` chip with literal `Non calculable` body "
        "— should be replaced with the `cell-na` em-dash pattern."
    )


def test_collapsed_row_warning_markup_moved_to_expansion():
    """The full-sentence warning row is gone from the collapsed state,
    replaced by the `urssaf-expansion-warnings` container that lives inside
    `urssaf-ctp-expansion__content`."""
    text = _app_js()
    assert "urssaf-ctp-warning-row" not in text, (
        "`urssaf-ctp-warning-row` class (the collapsed-state full-sentence "
        "warning row) must be removed — the warning sentence now lives "
        "inside the expanded state via `urssaf-expansion-warnings`."
    )
    assert "urssaf-expansion-warnings" in text, (
        "`urssaf-expansion-warnings` container must exist — it replaces "
        "the old inline warning row in the expanded state."
    )
    assert "urssaf-ctp-row--has-warnings" in text, (
        "`urssaf-ctp-row--has-warnings` modifier must be applied on rows "
        "with warnings — it drives the subtle left-accent stripe that is "
        "the only collapsed-state signal for row-level warnings."
    )


def test_all_four_urssaf_status_pill_variants_present():
    """Every URSSAF status variant must still be emitted somewhere in
    app.js — guards against a regression that drops one of them."""
    text = _app_js()
    for variant in (
        "status-badge--ok",
        "status-badge--ecart",
        "status-badge--manquant_individuel",
        "status-badge--non_rattache",
    ):
        assert variant in text, f"Missing URSSAF status pill variant: {variant}"


def test_delta_header_renamed():
    """`Delta code` / `DELTA CODE` header literal is gone; `Delta` is the
    canonical header for the per-CTP delta column."""
    text = _app_js()
    assert "Delta code" not in text, (
        "Header `Delta code` was renamed to `Delta` — the column sits "
        "between `Déclaré` and `Individuel`, so `code` was redundant and "
        "made the uppercase-transformed header wrap awkwardly."
    )
    assert "DELTA CODE" not in text, (
        "Found literal `DELTA CODE` in app.js — this should never appear; "
        "the uppercase form is produced by CSS text-transform."
    )
    assert re.search(r"<th[^>]*>Delta</th>", text) is not None, (
        "Expected `<th class=\"col-num\">Delta</th>` header on the URSSAF "
        "CTP table."
    )


def test_ok_with_warnings_card_header_branch():
    """When aggregate status is OK but row-level warnings exist, the card
    header must render the muted sub-line instead of the loud OK pill."""
    text = _app_js()
    assert "contrib-summary__ok-with-warnings" in text, (
        "`contrib-summary__ok-with-warnings` span must be emitted in the "
        "`item.status === 'ok' && allWarnings.length > 0` branch."
    )
    assert "point(s) de vigilance" in text, (
        "Expected user-facing copy 'point(s) de vigilance' on the muted "
        "OK-with-warnings sub-line."
    )
    # The branch guard on the OK pill must actually suppress it.
    assert "showOkBadge" in text, (
        "`showOkBadge` control variable must exist — it suppresses the "
        "status-badge--ok pill when warnings exist."
    )


def test_col_num_alignment_class_applied():
    """Numeric columns carry `col-num` so the collapsed, assiette, and
    employee tables line up vertically on amounts/rates."""
    text = _app_js()
    count = text.count("col-num")
    assert count >= 8, (
        "Expected `col-num` class on numeric headers/cells across the "
        "URSSAF CTP table and assiette sub-table; "
        f"found only {count} occurrences."
    )
    assert ".col-num" in _style_css(), (
        "`.col-num` CSS rule must exist in style.css (right-align + "
        "tabular-nums)."
    )


def test_hidden_ok_hint_present_at_bottom():
    """When the default `écarts only` filter is active and OK rows are
    hidden, the URSSAF table footer must surface a muted clickable hint."""
    text = _app_js()
    assert 'data-action="toggle-ecarts-filter-off"' in text, (
        "Expected a `toggle-ecarts-filter-off` action wired from the "
        "bottom hint button so one click flips the filter off."
    )
    assert "urssaf-hidden-ok-hint" in text, (
        "Expected a `urssaf-hidden-ok-hint` button rendered below the "
        "URSSAF table when reconciled rows are hidden."
    )
    # The source file stores accented characters as escape sequences
    # (`\u00e9` etc.), so we match against the escaped form.
    assert "r\\u00e9concili\\u00e9" in text, (
        "Expected user-facing French copy 'réconcilié' on the bottom "
        "hint (e.g. 'N code(s) réconcilié(s) masqué(s)')."
    )


def test_compact_expansion_warning_replaces_banner():
    """The row-level warning in the expanded state is a compact one-liner
    with a tooltip, not the former full-width banner."""
    text = _app_js()
    assert "urssaf-expansion-warning__text" in text, (
        "Expected compact warning markup `urssaf-expansion-warning__text` "
        "(single-line, ellipsis-clipped) inside the expansion."
    )
    # The old full-banner pattern used `.inline-warning` divs inside the
    # `urssaf-expansion-warnings` container. We want the compact class
    # instead — check the compact class lives inside that container.
    assert "urssaf-expansion-warning " in text or 'urssaf-expansion-warning"' in text, (
        "Expected `urssaf-expansion-warning` compact row inside the "
        "expansion warnings container."
    )


def test_reconstructed_declared_amount_uses_subtle_origin_line():
    """Rebuilt D rows keep the provenance cue, but as a low-noise origin
    line rather than a colored pill badge in the collapsed amount cell."""
    text = _app_js()
    assert "Reconstitué" in text, (
        "Expected `Reconstitué` copy in app.js for reconstructed "
        "URSSAF declared amounts."
    )
    assert "amount_source === 'reconstructed'" in text, (
        "The URSSAF bundle must branch on `amount_source === 'reconstructed'` "
        "to render reconstructed declared amounts distinctly."
    )
    assert "amount-origin" in text, (
        "Expected the collapsed amount cell to use the subtle `amount-origin` "
        "meta line for reconstructed or mixed provenance."
    )


def test_informational_partial_rows_are_driven_by_comparison_mode():
    """URSSAF informational-partial presentation must key off the backend
    `comparison_mode` contract, not off a French warning sentence."""
    text = _app_js()
    assert "comparison_mode === 'informational_partial'" in text, (
        "Expected explicit frontend branch on `comparison_mode === "
        "'informational_partial'` so informational rows do not depend on "
        "warning text parsing."
    )
    assert "_isInformationalPartialComparison" in text, (
        "Expected dedicated helper for informational-partial rows so the "
        "filter, stripe, and note share the same machine-readable contract."
    )
    assert "cell-info-state" in text, (
        "Expected a dedicated informational delta state instead of the "
        "generic non-calculable em-dash."
    )
    assert "Rattaché · Partiel" in text, (
        "Expected collapsed informational rows to say `Rattaché · Partiel` "
        "rather than plain `Rattaché`."
    )
    assert "Delta non affiché : montant URSSAF complet vs total salarié partiel" in text, (
        "Expected explicit delta tooltip for informational-partial rows."
    )
    assert "Partiel" in text, (
        "Expected the collapsed delta cell to render a dedicated "
        "`Partiel` state."
    )


def test_informational_partial_note_present_in_urssaf_expansion():
    """Expanded URSSAF rows should explain informational-partial semantics
    from the backend flag, independently of row warning copy."""
    text = _app_js()
    assert "Le delta CTP est donc volontairement masqué." in text, (
        "Expected explicit explanatory note in the URSSAF expansion for "
        "comparison_mode=informational_partial rows."
    )


def test_mixed_declared_amount_badge_present():
    """Mixed declared+reconstructed rows surface an explicit cue instead of
    inheriting the last processed detail source."""
    text = _app_js()
    assert "amount_source === 'mixed'" in text, (
        "The URSSAF bundle must branch on `amount_source === 'mixed'` so "
        "mixed rows do not pretend to be fully reconstructed or fully literal."
    )
    assert "Mixte" in text, (
        "Expected `Mixte` copy in app.js for partially reconstructed URSSAF "
        "declared amounts."
    )


def test_default_filter_shows_all_rows():
    """The URSSAF 'écarts only' filter defaults to OFF so a fresh DSN upload
    starts from the neutral full-list view. Default lives in initial state
    and in the state.reset path."""
    text = _app_js()
    # Both the initial declaration and the reset path must default to false.
    matches = re.findall(r"contribFilterEcartsOnly:\s*false", text)
    assert len(matches) >= 2, (
        "`contribFilterEcartsOnly` must default to `false` in both the "
        "initial state declaration and the state-reset path; "
        f"found {len(matches)} `: false` occurrences."
    )


def test_initial_contribution_tab_forces_urssaf():
    """A fresh DSN upload must land on the URSSAF tab, even if another
    family currently carries the worst status."""
    text = _app_js()
    assert re.search(
        r'function getInitialContributionTab\(data\)\s*\{\s*return "urssaf";\s*\}',
        text,
    ) is not None, (
        "`getInitialContributionTab()` must force `urssaf` so users land on "
        "the primary reconciliation tab right after upload."
    )


def test_top_level_contribution_sections_stay_open_by_default():
    """Top-level organism cards stay open on a fresh render so users keep
    context on each organism while only the inner URSSAF rows are collapsed."""
    text = _app_js()
    assert re.search(
        r"function getItemDefaultExpanded\(item\)\s*\{\s*return true;\s*\}",
        text,
    ) is not None, (
        "`getItemDefaultExpanded()` must return `true` so top-level "
        "organism sections stay open after a new upload."
    )


def test_urssaf_subsections_collapsed_by_default():
    """URSSAF CTP sub-sections start collapsed, even when they contain an
    issue, so the initial view stays readable without hiding the organism."""
    text = _app_js()
    assert re.search(
        r"function _isUrssafCtpExpanded\(item, ctpCode, hasIssueDefault\)\s*\{[\s\S]*?return false;\s*\}",
        text,
    ) is not None, (
        "`_isUrssafCtpExpanded()` must default to `false` so only the "
        "sub-sections are collapsed on a fresh upload."
    )


def test_pill_sizing_tightened():
    """The shared `.status-badge` block now reads as a calm text status,
    not a filled pill: no uppercase shouting, no tinted background, no
    large legacy padding."""
    css = _style_css()
    badge_block = re.search(
        r"\.status-badge\s*\{[^}]*\}", css, flags=re.DOTALL
    )
    assert badge_block is not None, "Could not locate `.status-badge` CSS block."
    body = badge_block.group(0)
    assert "padding: 5px 12px" not in body, (
        "Old pill padding `5px 12px` still present — the cleanup pass "
        "should not render a legacy filled-chip footprint anymore."
    )
    assert "text-transform: uppercase" not in body, (
        "Status badges should no longer shout in uppercase after the "
        "UI refinement pass."
    )
    assert "background: transparent" in body, (
        "Status badges should now render as lightweight text markers, not "
        "tinted pills with filled backgrounds."
    )
