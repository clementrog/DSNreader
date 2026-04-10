"""URSSAF CTP → individual-contribution mapping rules (V1 rule engine).

Canonical source of truth for which URSSAF CTP codes (``S21.G00.23.001``)
can be linked to employee-level individual contribution blocks
(``S21.G00.81.001``), under which conditions.

Replaces the former flat TSV lookup (``data/urssaf_individual_mapping.tsv``)
with a rule engine supporting:
- 1:N CTP-to-S81 mappings
- Component-scoped matching (qualifier → base code → S81 codes)
- Activation statuses (enabled, guarded, expert_pending, excluded)

The backward-compatible API is provided by
``dsn_extractor.urssaf_individual_mapping`` which delegates to this module.
"""

from __future__ import annotations

from dataclasses import dataclass


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class UrssafMappingComponent:
    """One qualifier-scoped matching slice within a 1:N CTP rule.

    Binds a set of assiette qualifiers to the allowed S78 base codes
    and the S81 individual codes that may be matched under those bases.
    """

    assiette_qualifiers_s23: frozenset[str]
    base_codes_s78: frozenset[str]
    individual_codes_s81: tuple[str, ...]


@dataclass(frozen=True)
class UrssafMappingConditions:
    """Top-level conditions that gate whether the rule is evaluable at all."""

    requires_insee_commune: bool = False
    threshold_rule: str | None = None
    notes: str | None = None


@dataclass(frozen=True)
class UrssafMappingRule:
    """One CTP mapping rule with optional component-scoped matching."""

    ctp_code: str
    ctp_label: str
    cardinality: str  # "1:1" or "1:N"
    individual_codes_s81: tuple[str, ...]
    components: tuple[UrssafMappingComponent, ...] | None = None
    conditions: UrssafMappingConditions = UrssafMappingConditions()
    ops_rule: str = "urssaf_siret"
    confidence: str = "high"
    product_status: str = "enabled"  # enabled | guarded | expert_pending | excluded
    source_refs: tuple[str, ...] = ()


# ---------------------------------------------------------------------------
# Allowed values
# ---------------------------------------------------------------------------

_VALID_PRODUCT_STATUSES = frozenset({"enabled", "guarded", "expert_pending", "excluded"})
_VALID_CARDINALITIES = frozenset({"1:1", "1:N"})
_ACTIVE_STATUSES = frozenset({"enabled", "guarded"})


# ---------------------------------------------------------------------------
# V1 Rule data
# ---------------------------------------------------------------------------

_RULES: dict[str, UrssafMappingRule] = {
    # ---- CTP 100: Cotisations sociales RG (1:N, component-scoped) --------
    "100": UrssafMappingRule(
        ctp_code="100",
        ctp_label="RG CAS GENERAL",
        cardinality="1:N",
        individual_codes_s81=("045", "068", "074", "075", "076"),
        components=(
            UrssafMappingComponent(
                assiette_qualifiers_s23=frozenset({"920"}),
                base_codes_s78=frozenset({"03"}),
                individual_codes_s81=("045", "068", "074", "075", "076"),
            ),
            UrssafMappingComponent(
                assiette_qualifiers_s23=frozenset({"921"}),
                base_codes_s78=frozenset({"02"}),
                individual_codes_s81=("076",),
            ),
        ),
        confidence="high",
        product_status="enabled",
        source_refs=(
            "publicodes 13.1 L7-247 (base 03)",
            "publicodes 13.1 L402-480 (base 02)",
        ),
    ),
    # ---- CTP 959: Contribution formation professionnelle (1:1) -----------
    "959": UrssafMappingRule(
        ctp_code="959",
        ctp_label="CFP ENTREPRISE < 11 SALARIES",
        cardinality="1:1",
        individual_codes_s81=("128",),
        confidence="high",
        product_status="enabled",
        source_refs=("publicodes 13.1",),
    ),
    # ---- CTP 983: CFP intermittents du spectacle (1:1) -------------------
    "983": UrssafMappingRule(
        ctp_code="983",
        ctp_label="CFP INTERMITTENTS DU SPECTACLE",
        cardinality="1:1",
        individual_codes_s81=("128",),
        confidence="high",
        product_status="enabled",
        source_refs=("publicodes 13.1",),
    ),
    # ---- CTP 987: Contribution CPF CDD (1:1) ----------------------------
    "987": UrssafMappingRule(
        ctp_code="987",
        ctp_label="CONTRIBUTION CPF CDD",
        cardinality="1:1",
        individual_codes_s81=("129",),
        confidence="high",
        product_status="enabled",
        source_refs=("publicodes 13.1",),
    ),
    # ---- CTP 992: TA principale hors Alsace-Moselle (1:1) ----------------
    "992": UrssafMappingRule(
        ctp_code="992",
        ctp_label="TA PRINCIPALE HORS ALSACE MOSELLE",
        cardinality="1:1",
        individual_codes_s81=("130",),
        confidence="high",
        product_status="enabled",
        source_refs=("publicodes 13.1",),
    ),
    # ---- CTP 993: TA Alsace-Moselle (1:1) ---------------------------------
    "993": UrssafMappingRule(
        ctp_code="993",
        ctp_label="TA ALSACE MOSELLE",
        cardinality="1:1",
        individual_codes_s81=("130",),
        confidence="high",
        product_status="enabled",
        source_refs=("publicodes 13.1",),
    ),
    # ---- CTP 027: Dialogue social — expert_pending -----------------------
    "027": UrssafMappingRule(
        ctp_code="027",
        ctp_label="CONTRIBUTION AU DIALOGUE SOCIAL",
        cardinality="1:1",
        individual_codes_s81=("100",),
        confidence="high",
        product_status="expert_pending",
        source_refs=("publicodes 13.1 L235-247",),
    ),
    # ---- CTP 900: Versement mobilité — expert_pending --------------------
    "900": UrssafMappingRule(
        ctp_code="900",
        ctp_label="VERSEMENT MOBILITE",
        cardinality="1:1",
        individual_codes_s81=("081",),
        conditions=UrssafMappingConditions(
            requires_insee_commune=True,
            notes="Requires commune-scoped matching not available in V1.",
        ),
        confidence="high",
        product_status="expert_pending",
        source_refs=("publicodes 13.1",),
    ),
    # ---- CTP 901: Versement mobilité additionnel — expert_pending --------
    "901": UrssafMappingRule(
        ctp_code="901",
        ctp_label="VERSEMENT MOBILITE ADDITIONNEL",
        cardinality="1:1",
        individual_codes_s81=("082",),
        conditions=UrssafMappingConditions(
            requires_insee_commune=True,
            notes="Requires commune-scoped matching not available in V1.",
        ),
        confidence="high",
        product_status="expert_pending",
        source_refs=("publicodes 13.1",),
    ),
    # ---- CTP 971: CFP entreprise >= 11 salariés — expert_pending ----------
    "971": UrssafMappingRule(
        ctp_code="971",
        ctp_label="CFP ENTREPRISE >= 11 SALARIES",
        cardinality="1:1",
        individual_codes_s81=("128",),
        conditions=UrssafMappingConditions(
            threshold_rule="smic_threshold",
            notes="Threshold logic not implementable in V1.",
        ),
        confidence="high",
        product_status="expert_pending",
        source_refs=("publicodes 13.1",),
    ),
}


# ---------------------------------------------------------------------------
# Import-time validation
# ---------------------------------------------------------------------------

def _validate_rules(rules: dict[str, UrssafMappingRule]) -> None:
    """Fail fast on invalid rule data."""
    for key, rule in rules.items():
        if key != rule.ctp_code:
            raise RuntimeError(
                f"Rule key {key!r} != rule.ctp_code {rule.ctp_code!r}"
            )
        if not rule.ctp_code:
            raise RuntimeError("Empty ctp_code in rule")
        if not rule.individual_codes_s81:
            raise RuntimeError(
                f"Rule {rule.ctp_code}: empty individual_codes_s81"
            )
        if rule.product_status not in _VALID_PRODUCT_STATUSES:
            raise RuntimeError(
                f"Rule {rule.ctp_code}: invalid product_status "
                f"{rule.product_status!r}"
            )
        if rule.cardinality not in _VALID_CARDINALITIES:
            raise RuntimeError(
                f"Rule {rule.ctp_code}: invalid cardinality "
                f"{rule.cardinality!r}"
            )
        if rule.product_status == "guarded":
            has_condition = (
                rule.conditions.requires_insee_commune
                or rule.conditions.threshold_rule is not None
            )
            if not has_condition:
                raise RuntimeError(
                    f"Rule {rule.ctp_code}: guarded status requires "
                    f"at least one non-trivial condition"
                )
        if rule.components is not None:
            component_codes: set[str] = set()
            for comp in rule.components:
                if not comp.assiette_qualifiers_s23:
                    raise RuntimeError(
                        f"Rule {rule.ctp_code}: component has empty "
                        f"assiette_qualifiers_s23"
                    )
                if not comp.base_codes_s78:
                    raise RuntimeError(
                        f"Rule {rule.ctp_code}: component has empty "
                        f"base_codes_s78"
                    )
                if not comp.individual_codes_s81:
                    raise RuntimeError(
                        f"Rule {rule.ctp_code}: component has empty "
                        f"individual_codes_s81"
                    )
                component_codes.update(comp.individual_codes_s81)
            rule_codes = set(rule.individual_codes_s81)
            if component_codes != rule_codes:
                raise RuntimeError(
                    f"Rule {rule.ctp_code}: individual_codes_s81 "
                    f"{rule_codes} != union of component codes "
                    f"{component_codes}"
                )


_validate_rules(_RULES)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_rule(ctp_code: str | None) -> UrssafMappingRule | None:
    """Return the mapping rule for a CTP code, or None.

    Returns rules of any ``product_status``. The caller decides how
    to handle inactive rules.
    """
    if not ctp_code:
        return None
    return _RULES.get(ctp_code)


def is_rule_active(rule: UrssafMappingRule) -> bool:
    """Return True if the rule's product_status is active (enabled or guarded)."""
    return rule.product_status in _ACTIVE_STATUSES


def all_rules() -> dict[str, UrssafMappingRule]:
    """Return a copy of all declared rules (any status)."""
    return dict(_RULES)
