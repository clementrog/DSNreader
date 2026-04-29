"""Static regression guards for the URSSAF UI cleanup pass.

These are cheap string/regex checks against the shipped frontend bundles.
They don't exercise JS at runtime — they exist so an accidental revert of
the URSSAF UX cleanup (NC token unification, collapsed-row noise removal,
header rename, pill variants, warning removal) is caught in CI instead of
reaching users.

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


def test_warning_markup_removed_from_urssaf_rows():
    """Warning-specific row markup is gone from the URSSAF bundle."""
    text = _app_js()
    assert "urssaf-ctp-warning-row" not in text, (
        "`urssaf-ctp-warning-row` must stay removed."
    )
    assert "urssaf-expansion-warnings" not in text, (
        "The URSSAF expansion should no longer render warning containers."
    )
    assert "urssaf-ctp-row--has-warnings" not in text, (
        "The collapsed URSSAF row should no longer carry warning-only "
        "styling."
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


def test_urssaf_ctp_issue_drives_family_and_card_status():
    """A top-level URSSAF item can be `ok` while one CTP drill-down has a
    material delta. The UI status must use the CTP-level issue so the family
    pill/card badge turns red instead of staying green."""
    text = _app_js()
    assert "function hasMaterialUrssafCtpIssue" in text
    assert 'item.family !== "urssaf"' in text
    assert 'b.mapping_status !== "rattachable"' in text
    assert "b.delta_within_unit" in text
    assert 'if (hasMaterialUrssafCtpIssue(item)) return "ecart";' in text
    assert 'getContributionDisplayStatus(item) === "ecart"' in text
    assert 'getStatusBadgeClass(displayStatus)' in text


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


def test_warning_header_branch_removed():
    """Contribution cards no longer show warning-specific header states."""
    text = _app_js()
    assert "contrib-summary__ok-with-warnings" not in text, (
        "The contribution header should no longer render the old OK-with-"
        "warnings sub-line."
    )
    assert "point(s) de vigilance" not in text, (
        "Warning-count copy should no longer appear in contribution headers."
    )
    assert "showOkBadge" not in text, (
        "The old warning-specific badge suppression branch should be gone."
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


def test_employee_breakdown_starts_under_parent_individual_column():
    """Expanded salarié rows reuse the parent grid so the child `Individuel`
    header and amounts sit on the same vertical rail as the parent CTP
    `Individuel` header and amounts."""
    text = _app_js()
    css = _style_css()
    assert "'<td></td>'" in text
    assert "'<td colspan=\"2\" class=\"urssaf-employee-name\">'" in text
    assert "'<td class=\"col-num\"><span class=\"urssaf-employee-amount\">'" in text
    assert "urssaf-employee-amount__value" in text
    assert "'<th colspan=\"2\">Salari\\u00e9</th>'" in text
    assert "'<th class=\"col-num\">Individuel</th>'" in text
    assert '"Libellé" + "Déclaré"' in text
    assert ".urssaf-employees-table" in css
    assert ".urssaf-employee-name" in css
    assert ".urssaf-employee-amount__value" in css
    assert "text-overflow: ellipsis;" in css
    assert '.urssaf-ctp-expansion > td[colspan="7"]' in css


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


def test_expanded_warning_markup_removed():
    """The expanded URSSAF view should no longer render warning-specific UI."""
    text = _app_js()
    assert "urssaf-expansion-warning__text" not in text, (
        "Expanded URSSAF warnings should not render dedicated warning rows."
    )
    assert "inline-warning" not in text, (
        "Legacy inline warning markup should stay removed."
    )


def test_reconstructed_declared_amount_no_longer_shows_inline_origin_label():
    """Rebuilt D rows stay visually quiet in the collapsed state: no
    `Reconstitué` or `Mixte` micro-label repeated on each amount cell."""
    text = _app_js()
    assert "amount_source === 'reconstructed'" not in text, (
        "The frontend should no longer branch on `amount_source === "
        "'reconstructed'` now that reconstructed rows do not display a "
        "special inline provenance marker."
    )
    assert "Reconstitué" not in text, (
        "The collapsed URSSAF amount cell should no longer repeat a "
        "`Reconstitué` label on every reconstructed row."
    )
    assert "Mixte" not in text, (
        "The collapsed URSSAF amount cell should no longer repeat a "
        "`Mixte` label on every partially reconstructed row."
    )


def test_informational_partial_rows_are_driven_by_comparison_mode():
    """URSSAF informational-partial presentation must key off the backend
    `comparison_mode` contract, not off any warning-specific markup."""
    text = _app_js()
    assert "comparison_mode === 'informational_partial'" in text, (
        "Expected explicit frontend branch on `comparison_mode === "
        "'informational_partial'` so informational rows do not depend on "
        "warning-related UI."
    )
    assert "_isInformationalPartialComparison" in text, (
        "Expected dedicated helper for informational-partial rows so the UI "
        "can still react to the backend contract where needed."
    )
    assert re.search(
        r"if \(_isInformationalPartialComparison\(breakdown\)\)\s*\{\s*return true;\s*\}",
        text,
    ) is None, (
        "Informational-partial rows should no longer be forced into the "
        "`écarts` bucket just because the comparison mode is partial."
    )
    assert "cell-info-state" not in text, (
        "Informational-partial rows should no longer render a dedicated "
        "visible `Partiel` delta state."
    )
    assert "Rattaché · Partiel" not in text, (
        "Collapsed informational rows should no longer say "
        "`Rattaché · Partiel`."
    )
    assert "Delta non affiché : montant URSSAF complet vs total salarié partiel" in text, (
        "Expected explicit delta tooltip for informational-partial rows."
    )
    assert ">OK</span>" in text, (
        "Expected collapsed rattachable rows to use the simpler visible "
        "`OK` label."
    )


def test_informational_partial_note_removed_from_urssaf_expansion():
    """Informational-partial rows keep their dedicated status/delta UI, but
    the long explanatory note is no longer repeated inline in the expansion."""
    text = _app_js()
    assert "Comparaison informative uniquement." not in text, (
        "The expanded URSSAF row should not repeat the informational-"
        "partial explanation inline."
    )
    assert "Le delta CTP est donc volontairement masqué." not in text, (
        "The expanded URSSAF row should not repeat the masked-delta "
        "explanation inline."
    )


def test_mixed_declared_amount_no_longer_has_frontend_specific_branch():
    """Mixed declared+reconstructed rows no longer render a dedicated
    frontend badge or note, so the old UI-specific branch should be gone."""
    text = _app_js()
    assert "amount_source === 'mixed'" not in text, (
        "The frontend should no longer branch on `amount_source === 'mixed'` "
        "now that the inline mixed-origin cue has been removed."
    )
    assert "Montant URSSAF reconstitué pour la comparaison." not in text, (
        "The expanded URSSAF row should not repeat the reconstructed-origin "
        "explanation inline."
    )


def test_warning_counts_removed_from_trust_banner_and_cards():
    """Warnings no longer affect the trust banner or contribution headers."""
    text = _app_js()
    assert "countComparisonWarnings" not in text, (
        "The frontend should no longer compute warning counts for the "
        "contribution trust banner."
    )
    assert "collectComparisonWarnings" not in text, (
        "The frontend should no longer aggregate warning lists for "
        "contribution cards."
    )
    assert "avert." not in text, (
        "Warning-count shorthand should no longer appear in the shipped UI."
    )
    assert "trust-count--warning" not in text, (
        "The trust banner should no longer render a warning count column."
    )


def test_collapsible_headers_use_compact_horizontal_layout():
    """Collapsible header rows keep a horizontal structure with compact
    amount cells and inline identity metadata."""
    app = _app_js()
    css = _style_css()
    assert "contrib-summary__identity" in app, (
        "Top-level contribution headers should render title and metadata "
        "inside a dedicated inline identity wrapper."
    )
    assert ".contrib-summary__identity" in css, (
        "Expected CSS for the inline contribution identity wrapper."
    )
    assert "amount-stack--compact" in app, (
        "Collapsed amount cells should use the compact stack variant when "
        "no second-line provenance label is rendered."
    )
    assert ".amount-stack--compact" in css, (
        "Expected CSS for the compact one-line amount stack."
    )


def test_employee_details_hide_inline_dsn_columns_and_use_info_icon():
    """Employee drill-down should keep the amount column aligned while
    moving S81/DSN context behind a compact info icon."""
    app = _app_js()
    css = _style_css()
    assert "<th>Code S81</th>" not in app, (
        "The employee drill-down should no longer render a visible "
        "`Code S81` column."
    )
    assert "<th>Lignes DSN</th>" not in app, (
        "The employee drill-down should no longer render a visible "
        "`Lignes DSN` column."
    )
    assert "urssaf-inline-info" in app, (
        "Expected a compact inline info icon next to employee amounts."
    )
    assert "data-tooltip=" in app, (
        "Expected the inline info icon to expose an explicit tooltip payload, "
        "not only a browser-native title attribute."
    )
    assert "Codes S81" in app and "Lignes DSN" in app, (
        "The info icon tooltip should still carry S81 and DSN-line context."
    )
    assert 'colspan="2" class="urssaf-employee-name"' in app and "urssaf-employee-amount__value" in app, (
        "The employee drill-down should reuse the parent grid so the "
        "salarié amount stays under the parent `Individuel` column."
    )
    assert ".urssaf-employee-amount" in css and ".urssaf-inline-info" in css, (
        "Expected dedicated CSS for the inline amount + info icon layout."
    )
    assert ".urssaf-inline-info::after" in css, (
        "Expected an explicit hover tooltip style for the inline info icon."
    )
    assert "z-index: 2147483647;" in css and ":has(.urssaf-inline-info:hover)" in css, (
        "Employee tooltips must rise above sticky headers/subheaders; the "
        "tooltip alone is not enough because table ancestors can still stack "
        "below those headers."
    )
    assert ".urssaf-inline-info:hover,\n.urssaf-inline-info:focus-visible {\n  z-index: 2147483646;\n}" in css, (
        "Hover must not change the info icon's positioning; changing it from "
        "absolute to relative makes the icon move under the cursor and causes "
        "tooltip flicker."
    )
    assert ".contrib-item--expanded" in css and "overflow: visible;" in css, (
        "Expanded contribution cards must allow tooltip overflow."
    )
    assert ".urssaf-employees-table td,\n.urssaf-employees-table th" in css, (
        "Employee detail table cells must allow tooltip overflow."
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
