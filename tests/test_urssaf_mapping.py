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
        assert len(rules) == 23
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

    def test_ctp_027_is_enabled(self):
        rule = get_rule("027")
        assert rule is not None
        assert rule.product_status == "enabled"
        assert rule.individual_codes_s81 == ("100",)
        assert rule.base_codes_s78 == frozenset({"03"})

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
        rule = get_rule("900")
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

    def test_027_mappable_enabled(self):
        assert is_urssaf_code_mappable("027") is True

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

    def test_get_individual_code_for_027_returns_100(self):
        assert get_individual_code_for_ctp("027") == "100"

    def test_get_individual_code_for_inactive_returns_none(self):
        assert get_individual_code_for_ctp("900") is None

    def test_non_rattache_is_recognized_status(self):
        assert "non_rattache" in URSSAF_DETAIL_STATUSES

    def test_load_mapping_returns_active_1_to_1_only(self):
        mapping = load_mapping()
        assert isinstance(mapping, dict)
        for row in mapping.values():
            assert isinstance(row, UrssafIndividualMapping)
        # Active 1:1 rules (no components): 003, 004, 027, 236, 332, 423, 635,
        # 668, 669, 772, 937, 959, 983, 987, 992, 993
        # Excluded: 100, 726, 863 (1:N with components), 260 (1:N flat),
        # 900, 901, 971 (expert_pending)
        assert len(mapping) == 16
        assert "100" not in mapping  # 1:N
        assert "726" not in mapping  # 1:N
        assert "863" not in mapping  # 1:N
        assert "260" not in mapping  # 1:N
        assert "900" not in mapping  # expert_pending
        assert "027" in mapping
        assert "959" in mapping

    def test_260_not_mappable_1_to_n_flat(self):
        """CTP 260 is active 1:N without components — not representable in legacy API."""
        assert is_urssaf_code_mappable("260") is False
        assert get_individual_code_for_ctp("260") is None


# ---------------------------------------------------------------------------
# New validated mapping rules tests
# ---------------------------------------------------------------------------


class TestNewValidatedRules:
    """Tests for the validated CTP→S81 mappings added in V1.1."""

    # ---- CTP 332 → 049 (02) -----------------------------------------------

    def test_ctp_332_maps_to_049_base_02(self):
        rule = get_rule("332")
        assert rule is not None
        assert rule.product_status == "enabled"
        assert rule.individual_codes_s81 == ("049",)
        assert rule.base_codes_s78 == frozenset({"02"})

    # ---- CTP 236 → 049 (02) -----------------------------------------------

    def test_ctp_236_maps_to_049_base_02(self):
        rule = get_rule("236")
        assert rule is not None
        assert rule.product_status == "enabled"
        assert rule.individual_codes_s81 == ("049",)
        assert rule.base_codes_s78 == frozenset({"02"})

    # ---- CTP 260 → 072 + 079 (04) -----------------------------------------

    def test_ctp_260_maps_to_072_079_base_04(self):
        rule = get_rule("260")
        assert rule is not None
        assert rule.product_status == "enabled"
        assert rule.cardinality == "1:N"
        assert set(rule.individual_codes_s81) == {"072", "079"}
        assert rule.base_codes_s78 == frozenset({"04"})
        assert rule.components is None  # flat 1:N, no qualifier split

    # ---- CTP 423 → 040 (07) if apprentice ----------------------------------

    def test_ctp_423_apprentice_only(self):
        rule = get_rule("423")
        assert rule is not None
        assert rule.product_status == "enabled"
        assert rule.individual_codes_s81 == ("040",)
        assert rule.base_codes_s78 == frozenset({"07"})
        assert rule.conditions.requires_contract_nature == frozenset({"02"})

    # ---- CTP 772 → 040 (07) if NOT apprentice ------------------------------

    def test_ctp_772_non_apprentice_only(self):
        rule = get_rule("772")
        assert rule is not None
        assert rule.product_status == "enabled"
        assert rule.individual_codes_s81 == ("040",)
        assert rule.base_codes_s78 == frozenset({"07"})
        assert rule.conditions.excludes_contract_nature == frozenset({"02"})

    # ---- CTP 726 D/P → apprentice-only split --------------------------------

    def test_ctp_726_apprentice_split(self):
        rule = get_rule("726")
        assert rule is not None
        assert rule.product_status == "enabled"
        assert rule.cardinality == "1:N"
        assert rule.conditions.requires_contract_nature == frozenset({"02"})
        assert rule.components is not None
        assert len(rule.components) == 2
        # D (920/base03)
        comp_d = rule.components[0]
        assert comp_d.assiette_qualifiers_s23 == frozenset({"920"})
        assert comp_d.base_codes_s78 == frozenset({"03"})
        assert comp_d.individual_codes_s81 == ("045", "068", "074", "075", "076")
        # P (921/base02)
        comp_p = rule.components[1]
        assert comp_p.assiette_qualifiers_s23 == frozenset({"921"})
        assert comp_p.base_codes_s78 == frozenset({"02"})
        assert comp_p.individual_codes_s81 == ("076",)

    # ---- CTP 863 D/P → mandataire-only split --------------------------------

    def test_ctp_863_mandataire_split(self):
        rule = get_rule("863")
        assert rule is not None
        assert rule.product_status == "enabled"
        assert rule.cardinality == "1:N"
        assert rule.conditions.requires_contract_nature == frozenset({"80"})
        assert rule.components is not None
        assert len(rule.components) == 2

    # ---- CTP 100 → excludes mandataire only -----------------------------------

    def test_ctp_100_excludes_mandataire_only(self):
        rule = get_rule("100")
        assert rule.conditions.excludes_contract_nature == frozenset({"80"})

    # ---- CTP 635 → 907 (03) -----------------------------------------------

    def test_ctp_635_maps_to_907_base_03(self):
        rule = get_rule("635")
        assert rule is not None
        assert rule.product_status == "enabled"
        assert rule.individual_codes_s81 == ("907",)
        assert rule.base_codes_s78 == frozenset({"03"})

    # ---- CTP 937 → 048 (07) -----------------------------------------------

    def test_ctp_937_maps_to_048_base_07(self):
        rule = get_rule("937")
        assert rule is not None
        assert rule.product_status == "enabled"
        assert rule.individual_codes_s81 == ("048",)
        assert rule.base_codes_s78 == frozenset({"07"})

    # ---- CTP 003 → 114 (03) -----------------------------------------------

    def test_ctp_003_maps_to_114_base_03(self):
        rule = get_rule("003")
        assert rule is not None
        assert rule.product_status == "enabled"
        assert rule.individual_codes_s81 == ("114",)
        assert rule.base_codes_s78 == frozenset({"03"})

    # ---- CTP 004 → 021 (03) -----------------------------------------------

    def test_ctp_004_maps_to_021_base_03(self):
        rule = get_rule("004")
        assert rule is not None
        assert rule.product_status == "enabled"
        assert rule.individual_codes_s81 == ("021",)
        assert rule.base_codes_s78 == frozenset({"03"})

    # ---- CTP 668 → 018 (03) sign=negative ----------------------------------

    def test_ctp_668_negative_sign_gating(self):
        rule = get_rule("668")
        assert rule is not None
        assert rule.product_status == "enabled"
        assert rule.individual_codes_s81 == ("018",)
        assert rule.base_codes_s78 == frozenset({"03"})
        assert rule.conditions.sign_condition == "negative"

    # ---- CTP 669 → 018 (03) sign=positive ----------------------------------

    def test_ctp_669_positive_sign_gating(self):
        rule = get_rule("669")
        assert rule is not None
        assert rule.product_status == "enabled"
        assert rule.individual_codes_s81 == ("018",)
        assert rule.base_codes_s78 == frozenset({"03"})
        assert rule.conditions.sign_condition == "positive"

    # ---- CTP 900 regression: still blocked ----------------------------------

    def test_ctp_900_still_expert_pending(self):
        """CTP 900 requires commune-scoped matching — must NOT be activated."""
        rule = get_rule("900")
        assert rule is not None
        assert rule.product_status == "expert_pending"
        assert rule.conditions.requires_insee_commune is True
        assert is_rule_active(rule) is False

    # ---- Status detection uses correct DSN field ----------------------------

    def test_apprentice_status_uses_S40_007_02(self):
        """All apprentice-gated rules reference S21.G00.40.007 value '02'."""
        for ctp_code in ("423", "726"):
            rule = get_rule(ctp_code)
            assert "02" in rule.conditions.requires_contract_nature
        # Non-apprentice excludes 02
        rule_772 = get_rule("772")
        assert "02" in rule_772.conditions.excludes_contract_nature

    def test_mandataire_status_uses_S40_007_80(self):
        """Mandataire-gated rules reference S21.G00.40.007 value '80'."""
        rule = get_rule("863")
        assert "80" in rule.conditions.requires_contract_nature
        # CTP 100 excludes mandataire
        rule_100 = get_rule("100")
        assert "80" in rule_100.conditions.excludes_contract_nature
