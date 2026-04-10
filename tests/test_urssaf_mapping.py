"""Tests for the URSSAF CTP → individual-code mapping rules (V1).

Tests both the canonical rule module (``urssaf_mapping_rules``) and the
backward-compatible shim (``urssaf_individual_mapping``).
"""

from __future__ import annotations

import pytest

from dsn_extractor.urssaf_mapping_rules import (
    UrssafMappingRule,
    all_rules,
    get_rule,
    is_rule_active,
)
from dsn_extractor.urssaf_individual_mapping import (
    URSSAF_DETAIL_STATUSES,
    UrssafIndividualMapping,
    get_individual_code_for_ctp,
    is_urssaf_code_mappable,
    load_mapping,
)


# ---------------------------------------------------------------------------
# Canonical rule module tests
# ---------------------------------------------------------------------------


class TestUrssafMappingRules:

    def test_all_rules_load(self):
        rules = all_rules()
        assert isinstance(rules, dict)
        assert len(rules) == 10
        for rule in rules.values():
            assert isinstance(rule, UrssafMappingRule)

    def test_ctp_100_enabled_1_to_n_with_2_components(self):
        rule = get_rule("100")
        assert rule is not None
        assert rule.product_status == "enabled"
        assert rule.cardinality == "1:N"
        assert rule.components is not None
        assert len(rule.components) == 2

    def test_ctp_100_component_a_920_base_03(self):
        rule = get_rule("100")
        comp_a = rule.components[0]
        assert comp_a.assiette_qualifiers_s23 == frozenset({"920"})
        assert comp_a.base_codes_s78 == frozenset({"03"})
        assert comp_a.individual_codes_s81 == ("045", "068", "074", "075", "076")

    def test_ctp_100_component_b_921_base_02(self):
        rule = get_rule("100")
        comp_b = rule.components[1]
        assert comp_b.assiette_qualifiers_s23 == frozenset({"921"})
        assert comp_b.base_codes_s78 == frozenset({"02"})
        assert comp_b.individual_codes_s81 == ("076",)

    def test_ctp_100_individual_codes_is_union_of_components(self):
        rule = get_rule("100")
        component_union = set()
        for comp in rule.components:
            component_union.update(comp.individual_codes_s81)
        assert set(rule.individual_codes_s81) == component_union

    def test_ctp_027_is_expert_pending(self):
        rule = get_rule("027")
        assert rule is not None
        assert rule.product_status == "expert_pending"

    def test_ctp_900_is_expert_pending(self):
        rule = get_rule("900")
        assert rule is not None
        assert rule.product_status == "expert_pending"

    def test_ctp_901_is_expert_pending(self):
        rule = get_rule("901")
        assert rule is not None
        assert rule.product_status == "expert_pending"

    def test_ctp_971_is_expert_pending(self):
        rule = get_rule("971")
        assert rule is not None
        assert rule.product_status == "expert_pending"

    def test_is_rule_active_true_for_enabled(self):
        rule = get_rule("959")
        assert is_rule_active(rule) is True

    def test_is_rule_active_false_for_expert_pending(self):
        rule = get_rule("027")
        assert is_rule_active(rule) is False

    def test_is_rule_active_true_for_guarded_forward_compat(self):
        """guarded is active by design (no guarded rules in V1)."""
        fake = UrssafMappingRule(
            ctp_code="TEST",
            ctp_label="TEST",
            cardinality="1:1",
            individual_codes_s81=("999",),
            product_status="guarded",
        )
        assert is_rule_active(fake) is True

    def test_no_duplicate_ctp_codes(self):
        rules = all_rules()
        assert len(rules) == len(set(rules.keys()))

    def test_get_rule_returns_none_for_unknown(self):
        assert get_rule("9999") is None
        assert get_rule("") is None
        assert get_rule(None) is None


# ---------------------------------------------------------------------------
# Backward-compat shim tests
# ---------------------------------------------------------------------------


class TestUrssafIndividualMappingShim:

    def test_959_is_mappable(self):
        assert is_urssaf_code_mappable("959") is True

    def test_100_not_mappable_1_to_n(self):
        """CTP 100 is active but 1:N — not representable in legacy API."""
        assert is_urssaf_code_mappable("100") is False

    def test_900_not_mappable_expert_pending(self):
        assert is_urssaf_code_mappable("900") is False

    def test_027_not_mappable_expert_pending(self):
        assert is_urssaf_code_mappable("027") is False

    def test_unknown_not_mappable(self):
        assert is_urssaf_code_mappable("9999") is False

    def test_empty_and_none_not_mappable(self):
        assert is_urssaf_code_mappable("") is False
        assert is_urssaf_code_mappable(None) is False

    def test_get_individual_code_for_959(self):
        assert get_individual_code_for_ctp("959") == "128"

    def test_get_individual_code_for_100_returns_none_1_to_n(self):
        """CTP 100 is 1:N with components — cannot be flattened to one code."""
        assert get_individual_code_for_ctp("100") is None

    def test_get_individual_code_for_inactive_returns_none(self):
        assert get_individual_code_for_ctp("027") is None

    def test_non_rattache_is_recognized_status(self):
        assert "non_rattache" in URSSAF_DETAIL_STATUSES

    def test_load_mapping_returns_active_1_to_1_only(self):
        mapping = load_mapping()
        assert isinstance(mapping, dict)
        for row in mapping.values():
            assert isinstance(row, UrssafIndividualMapping)
        # Active 1:1 rules: 959, 983, 987, 992, 993 (100 excluded — 1:N)
        assert len(mapping) == 5
        assert "100" not in mapping
        assert "027" not in mapping
        assert "900" not in mapping
        assert "959" in mapping
