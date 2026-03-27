"""Contribution reconciliation logic for DSN files.

Compares aggregate (S21.G00.20), detailed (S21.G00.22/23/55), and individual
(S21.G00.50/78/81) amounts across 5 families: PAS, URSSAF, prévoyance,
mutuelle, retraite.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

from dsn_extractor.block_groups import (
    BlockGroup,
    EstablishmentBlockGroups,
    EmployeeBlockGroups,
    group_employee_blocks,
    group_establishment_blocks,
)
from dsn_extractor.models import (
    ContributionComparisonDetail,
    ContributionComparisonItem,
    ContributionComparisons,
)
from dsn_extractor.normalize import normalize_decimal
from dsn_extractor.organisms import (
    ORGANISM_REGISTRY,
    CTP_LABELS,
    lookup_complementary_family_override,
    lookup_organism,
    lookup_ctp,
)
from dsn_extractor.parser import DSNRecord, EmployeeBlock, EstablishmentBlock


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _find_value(records: list[DSNRecord], code: str) -> str | None:
    for r in records:
        if r.code == code:
            return r.raw_value
    return None


def _find_all_values(records: list[DSNRecord], code: str) -> list[str]:
    return [r.raw_value for r in records if r.code == code]


def _find_all_records(records: list[DSNRecord], code: str) -> list[DSNRecord]:
    return [r for r in records if r.code == code]


def _record_lines(records: list[DSNRecord]) -> list[int]:
    return [r.line_number for r in records]


def _dec(raw: str | None) -> Decimal | None:
    if raw is None:
        return None
    return normalize_decimal(raw)


def _within_tolerance(a: Decimal | None, b: Decimal | None, tol: Decimal) -> bool:
    if a is None or b is None:
        return False
    return abs(a - b) <= tol


REGULARIZATION_WARNING = (
    "Des régularisations DSN ont été détectées. Les éléments régularisés "
    "sur des mois précédents ne sont pas pris en compte correctement par "
    "cet outil en V1."
)

_TOL_001 = Decimal("0.01")


def _employee_display_name(emp: EmployeeBlock) -> str:
    nom = (_find_value(emp.records, "S21.G00.30.002") or "").strip()
    prenom = (_find_value(emp.records, "S21.G00.30.004") or "").strip()
    if nom and prenom:
        return f"{nom} {prenom}"
    return nom or prenom or "?"


# ---------------------------------------------------------------------------
# Classification (rules 1→2→3→3b→4→5)
# ---------------------------------------------------------------------------


def _classify_s20(
    organism_id: str,
    s22_organism_ids: set[str],
    s15_organism_ids: set[str],
) -> str:
    """Return family string for an S20 block's organism_id."""
    # Rule 1: structural literal
    if organism_id == "DGFIP":
        return "pas"
    # Rule 2: structural S22 linkage
    if organism_id in s22_organism_ids:
        return "urssaf"
    # Rule 3: structural S15 linkage → complementary universe.
    # The business split mutuelle vs prevoyance is resolved later at the
    # contract level, not guessed here from the organism alone.
    if organism_id in s15_organism_ids:
        return "complementary"
    # Rule 4: registry fallback — only retraite (no structural aggregate path
    # exists for retraite complémentaire in the DSN data model)
    _, _, family = lookup_organism(organism_id)
    if family == "retraite":
        return "retraite"
    # Rule 5: unclassified — registry-only urssaf/pas/prevoyance/mutuelle
    # without their structural link (S22/S15/DGFIP) must NOT be classified
    return "unclassified"


# ---------------------------------------------------------------------------
# Regularization detection
# ---------------------------------------------------------------------------


def _check_regularization(block: BlockGroup) -> bool:
    """Check if a block contains a regularization marker."""
    for r in block.records:
        if r.code in ("S21.G00.20.013", "S21.G00.22.006", "S21.G00.55.005"):
            if r.raw_value and r.raw_value.strip():
                return True
    for child in block.children:
        if _check_regularization(child):
            return True
    return False


# ---------------------------------------------------------------------------
# PAS reconciliation
# ---------------------------------------------------------------------------


def _compute_pas(
    dgfip_s20_blocks: list[BlockGroup],
    employee_blocks: list[EmployeeBlock],
) -> ContributionComparisonItem:
    warnings: list[str] = []

    if len(dgfip_s20_blocks) > 1:
        warnings.append("multiple_dgfip_blocks")

    # Aggregate amount
    aggregate = Decimal(0)
    agg_lines: list[int] = []
    has_regularization = False
    for s20 in dgfip_s20_blocks:
        amt = _dec(_find_value(s20.records, "S21.G00.20.005"))
        if amt is not None:
            aggregate += amt
        agg_lines.extend(_record_lines(s20.records))
        if _check_regularization(s20):
            has_regularization = True

    # Individual amount: sum ALL S21.G00.50.009 across ALL employees
    individual = Decimal(0)
    details: list[ContributionComparisonDetail] = []
    has_individual = False
    for emp in employee_blocks:
        pas_records = _find_all_records(emp.records, "S21.G00.50.009")
        emp_total = Decimal(0)
        for rec in pas_records:
            val = _dec(rec.raw_value)
            if val is not None:
                emp_total += val
                has_individual = True
        if emp_total != 0:
            name = _employee_display_name(emp)
            details.append(ContributionComparisonDetail(
                key=name,
                label="PAS individuel",
                declared_amount=emp_total,
                status="ok",
                record_lines=[r.line_number for r in pas_records],
            ))
            individual += emp_total

    # Status
    aggregate_amount = aggregate if dgfip_s20_blocks else None
    individual_amount = individual if has_individual else None

    if aggregate_amount is None:
        status = "manquant_agrege"
    elif individual_amount is None:
        status = "manquant_individuel"
    elif _within_tolerance(aggregate_amount, individual_amount, _TOL_001):
        status = "ok"
    else:
        status = "ecart"

    delta = None
    if aggregate_amount is not None and individual_amount is not None:
        delta = aggregate_amount - individual_amount

    if has_regularization:
        warnings.append(REGULARIZATION_WARNING)

    return ContributionComparisonItem(
        family="pas",
        organism_id="DGFIP",
        organism_label="DGFIP",
        aggregate_amount=aggregate_amount,
        individual_amount=individual_amount,
        aggregate_vs_individual_delta=delta,
        status=status,
        details=details,
        warnings=warnings,
    )


# ---------------------------------------------------------------------------
# URSSAF reconciliation
# ---------------------------------------------------------------------------


def _compute_urssaf(
    organism_id: str,
    s20_blocks: list[BlockGroup],
    s22_blocks: list[BlockGroup],
    est_groups: EstablishmentBlockGroups,
) -> ContributionComparisonItem:
    label, _, _ = lookup_organism(organism_id)
    warnings: list[str] = []
    has_regularization = False

    # Aggregate amount — sum across all S20 blocks for this organism
    agg_total = Decimal(0)
    has_agg = False
    for s20 in s20_blocks:
        amt = _dec(_find_value(s20.records, "S21.G00.20.005"))
        if amt is not None:
            agg_total += amt
            has_agg = True
        if _check_regularization(s20):
            has_regularization = True
    aggregate_amount = agg_total if has_agg else None

    # Find ALL matching S22 bordereaux for this organism
    matching_s22_blocks: list[BlockGroup] = []
    for s22 in s22_blocks:
        s22_org = _find_value(s22.records, "S21.G00.22.001")
        if s22_org and s22_org.strip() == organism_id:
            matching_s22_blocks.append(s22)

    if len(matching_s22_blocks) > 1:
        warnings.append("multiple_s22_bordereaux")

    bordereau_amount: Decimal | None = None
    bord_total = Decimal(0)
    has_bord = False
    all_s23_children: list[BlockGroup] = []
    for s22 in matching_s22_blocks:
        amt = _dec(_find_value(s22.records, "S21.G00.22.005"))
        if amt is not None:
            bord_total += amt
            has_bord = True
        if _check_regularization(s22):
            has_regularization = True
        all_s23_children.extend(s22.children)
    bordereau_amount = bord_total if has_bord else None

    # CTP detail from S23 children of ALL matching S22 blocks
    details: list[ContributionComparisonDetail] = []
    component_total = Decimal(0)
    n_recalculated_ctps = 0
    has_ctp = False
    non_calculable_ctp_count = 0

    if matching_s22_blocks:
        for s23 in all_s23_children:
            ctp_code = _find_value(s23.records, "S21.G00.23.001") or ""
            assiette_qual = _find_value(s23.records, "S21.G00.23.002") or ""
            insee_code = _find_value(s23.records, "S21.G00.23.006") or ""
            key = f"{ctp_code}/{assiette_qual}/{insee_code}".rstrip("/")

            declared_raw = _find_value(s23.records, "S21.G00.23.005")
            rate_raw = _find_value(s23.records, "S21.G00.23.003")
            base_raw = _find_value(s23.records, "S21.G00.23.004")

            declared = _dec(declared_raw) if declared_raw and declared_raw.strip() else None
            rate = _dec(rate_raw) if rate_raw and rate_raw.strip() else None
            base = _dec(base_raw) if base_raw and base_raw.strip() else None

            recomputed: Decimal | None = None
            if base is not None and rate is not None:
                recomputed = (base * rate / Decimal(100)).quantize(
                    Decimal("0.01"), rounding=ROUND_HALF_UP
                )
                n_recalculated_ctps += 1

            # Amount to use for this CTP
            if declared is not None:
                ctp_amount = declared
            elif recomputed is not None:
                ctp_amount = recomputed
            else:
                ctp_amount = None

            # Detail status
            ctp_status = "ok"
            ctp_delta: Decimal | None = None
            ctp_warnings: list[str] = []

            if ctp_amount is None:
                ctp_status = "non_calculable"
                non_calculable_ctp_count += 1
            elif declared is not None and recomputed is not None:
                ctp_delta = declared - recomputed
                if not _within_tolerance(declared, recomputed, _TOL_001):
                    ctp_status = "ecart"
                    ctp_warnings.append(
                        f"CTP {ctp_code}: déclaré {declared} ≠ recalculé {recomputed}"
                    )

            if ctp_amount is not None:
                component_total += ctp_amount
                has_ctp = True

            details.append(ContributionComparisonDetail(
                key=key,
                label=lookup_ctp(ctp_code) or ctp_code,
                declared_amount=declared,
                computed_amount=recomputed,
                delta=ctp_delta,
                status=ctp_status,
                record_lines=_record_lines(s23.records),
                warnings=ctp_warnings,
            ))

    component_amount = component_total if has_ctp else None
    component_comparison_complete = has_ctp and non_calculable_ctp_count == 0
    if has_ctp and non_calculable_ctp_count > 0:
        warnings.append(
            f"partial_ctp_recalculation: {non_calculable_ctp_count} lignes non calculables"
        )
        # Keep line-level details, but do not present a partial subtotal as the
        # full detailed amount in the top-level card.
        component_amount = None

    # Deltas
    agg_vs_bord_delta: Decimal | None = None
    bord_vs_comp_delta: Decimal | None = None

    if aggregate_amount is not None and bordereau_amount is not None:
        agg_vs_bord_delta = aggregate_amount - bordereau_amount

    if bordereau_amount is not None and component_amount is not None:
        bord_vs_comp_delta = bordereau_amount - component_amount

    # Status determination
    if aggregate_amount is None:
        status = "manquant_agrege"
    elif not matching_s22_blocks:
        status = "manquant_bordereau"
    elif not has_ctp:
        status = "manquant_detail"
    else:
        # Control 1: versement vs bordereau
        ctrl1_ok = bordereau_amount is not None and _within_tolerance(
            aggregate_amount, bordereau_amount, _TOL_001
        )
        if not component_comparison_complete:
            status = "ok" if ctrl1_ok else "ecart"
        else:
            # Control 2: bordereau vs sum(CTP) — dynamic tolerance
            dynamic_tol = max(_TOL_001, _TOL_001 * n_recalculated_ctps)
            ctrl2_ok = bordereau_amount is not None and component_amount is not None and _within_tolerance(
                bordereau_amount, component_amount, dynamic_tol
            )
            if ctrl1_ok and ctrl2_ok:
                status = "ok"
            else:
                status = "ecart"

    if has_regularization:
        warnings.append(REGULARIZATION_WARNING)

    return ContributionComparisonItem(
        family="urssaf",
        organism_id=organism_id,
        organism_label=label,
        aggregate_amount=aggregate_amount,
        bordereau_amount=bordereau_amount,
        component_amount=component_amount,
        aggregate_vs_bordereau_delta=agg_vs_bord_delta,
        bordereau_vs_component_delta=bord_vs_comp_delta,
        status=status,
        details=details,
        warnings=warnings,
    )


# ---------------------------------------------------------------------------
# Prévoyance / Mutuelle reconciliation
# ---------------------------------------------------------------------------


@dataclass
class S15Entry:
    """One parsed S21.G00.15 adhesion block."""

    contract_ref: str
    organism_id: str
    adhesion_id: str


def _build_s15_entries(
    s15_blocks: list[BlockGroup],
) -> tuple[list[S15Entry], list[str]]:
    """Extract all S15 entries preserving the full business key.

    Returns (entries, warnings).  Same contract_ref pointing to different
    organisms is ambiguous.  Same contract_ref + same organism + different
    adhesion_id produces distinct entries (not ambiguous — two adhesions).
    """
    entries: list[S15Entry] = []
    warnings: list[str] = []
    # Track contract_ref → set of organism_ids to detect cross-organism ambiguity
    orgs_by_cref: dict[str, set[str]] = {}
    # Deduplicate by full key so repeated identical S15 blocks don't double-count
    seen_keys: set[tuple[str, str, str]] = set()

    for s15 in s15_blocks:
        contract_ref = (_find_value(s15.records, "S21.G00.15.001") or "").strip()
        organism_id = (_find_value(s15.records, "S21.G00.15.002") or "").strip()
        adhesion_id = (_find_value(s15.records, "S21.G00.15.005") or "").strip()

        if not contract_ref:
            continue

        orgs_by_cref.setdefault(contract_ref, set()).add(organism_id)

        key = (contract_ref, organism_id, adhesion_id)
        if key not in seen_keys:
            seen_keys.add(key)
            entries.append(S15Entry(
                contract_ref=contract_ref,
                organism_id=organism_id,
                adhesion_id=adhesion_id,
            ))

    for cref, org_ids in orgs_by_cref.items():
        if len(org_ids) > 1:
            warnings.append(f"ambiguous_s15_mapping: contract_ref '{cref}'")

    return entries, warnings


def _build_s70_map(
    employee_blocks: list[EmployeeBlock],
) -> tuple[dict[str, str], list[str]]:
    """Build affiliation_id → adhesion_id map from S70 blocks across employees.

    Returns (map, warnings).
    """
    result: dict[str, str] = {}
    ambiguous: set[str] = set()
    warnings: list[str] = []

    for emp in employee_blocks:
        emp_groups = group_employee_blocks(emp)
        for s70 in emp_groups.s70_blocks:
            affil_id = (_find_value(s70.records, "S21.G00.70.012") or "").strip()
            adhes_id = (_find_value(s70.records, "S21.G00.70.013") or "").strip()
            if not affil_id:
                continue
            if affil_id in result and result[affil_id] != adhes_id:
                ambiguous.add(affil_id)
            else:
                result[affil_id] = adhes_id

    for affil in ambiguous:
        warnings.append(f"ambiguous_s70_mapping: affiliation_id '{affil}'")

    return result, warnings


def _compute_complementary(
    organism_id: str,
    s20_blocks: list[BlockGroup],
    est_groups: EstablishmentBlockGroups,
    employee_blocks: list[EmployeeBlock],
    s15_entries: list[S15Entry],
    s15_warnings: list[str],
    s70_map: dict[str, str],
    s70_warnings: list[str],
) -> list[ContributionComparisonItem]:
    """Compute reconciliation for a complementary organism.

    Accepts all S20 blocks for this organism. Merges aggregate amounts and S55
    children across blocks, then emits one item per unique
    (organism_id, contract_ref, adhesion_id) key from S15.
    """
    label, _, registry_family = lookup_organism(organism_id)
    has_regularization = False

    # Bridge-link validation
    s15_present = len(est_groups.s15_blocks) > 0
    s70_present = len(s70_map) > 0
    s15_ambiguous = len(s15_warnings) > 0
    s70_ambiguous = len(s70_warnings) > 0

    base_warnings: list[str] = []
    if not s15_present:
        base_warnings.append("missing_structuring_block_s15")
    if not s70_present:
        base_warnings.append("missing_structuring_block_s70")
    base_warnings.extend(s15_warnings)
    base_warnings.extend(s70_warnings)

    s70_valid = s70_present and not s70_ambiguous
    bridge_valid = s15_present and not s15_ambiguous and s70_valid

    # Aggregate amount — sum across ALL S20 blocks for this organism
    agg_total = Decimal(0)
    has_agg = False
    for s20 in s20_blocks:
        amt = _dec(_find_value(s20.records, "S21.G00.20.005"))
        if amt is not None:
            agg_total += amt
            has_agg = True
        if _check_regularization(s20):
            has_regularization = True
    aggregate_amount = agg_total if has_agg else None

    # Collect S55 children across ALL S20 blocks, indexed by contract_ref
    s55_by_contract: dict[str, list[BlockGroup]] = {}
    for s20 in s20_blocks:
        for s55 in s20.children:
            cref = (_find_value(s55.records, "S21.G00.55.003") or "").strip()
            s55_by_contract.setdefault(cref, []).append(s55)
            if _check_regularization(s55):
                has_regularization = True

    # Collect contracts for this organism from S15 entries — full business key
    # Each unique (contract_ref, adhesion_id) for this organism gets its own item.
    org_contracts: list[tuple[str, str]] = []
    for entry in s15_entries:
        if entry.organism_id == organism_id:
            pair = (entry.contract_ref, entry.adhesion_id)
            if pair not in org_contracts:
                org_contracts.append(pair)

    # If no S15 contracts found, produce a single non-split item
    if not org_contracts:
        fallback_family = registry_family if registry_family in ("prevoyance", "mutuelle") else "unclassified"
        warnings = list(base_warnings)
        comp_total = Decimal(0)
        has_comp = False
        for s55_list in s55_by_contract.values():
            for s55 in s55_list:
                amt = _dec(_find_value(s55.records, "S21.G00.55.001"))
                if amt is not None:
                    comp_total += amt
                    has_comp = True
        component_amount = comp_total if has_comp else None

        if has_regularization:
            warnings.append(REGULARIZATION_WARNING)

        return [ContributionComparisonItem(
            family=fallback_family,
            organism_id=organism_id,
            organism_label=label,
            aggregate_amount=aggregate_amount,
            component_amount=component_amount,
            status="non_rattache",
            warnings=warnings,
        )]

    # Detect contract_refs shared by multiple adhesions — S55 has no adhesion
    # discriminator so component amounts cannot be split across adhesions.
    adhesions_per_cref: dict[str, list[str]] = {}
    for cref, adhes in org_contracts:
        adhesions_per_cref.setdefault(cref, []).append(adhes)
    shared_crefs: set[str] = {
        cref for cref, adhes_list in adhesions_per_cref.items()
        if len(adhes_list) > 1
    }

    # Precompute component totals per contract_ref (once, not per adhesion)
    comp_by_cref: dict[str, Decimal | None] = {}
    for cref in {c for c, _ in org_contracts}:
        total = Decimal(0)
        found = False
        for s55 in s55_by_contract.get(cref, []):
            amt = _dec(_find_value(s55.records, "S21.G00.55.001"))
            if amt is not None:
                total += amt
                found = True
        # Include S55 with empty contract_ref if only one contract_ref
        if len(adhesions_per_cref) == 1:
            for s55 in s55_by_contract.get("", []):
                amt = _dec(_find_value(s55.records, "S21.G00.55.001"))
                if amt is not None:
                    total += amt
                    found = True
        comp_by_cref[cref] = total if found else None

    # One item per unique (contract_ref, adhesion_id)
    items: list[ContributionComparisonItem] = []
    for contract_ref, adhesion_id in org_contracts:
        item_family = lookup_complementary_family_override(organism_id, contract_ref)
        if item_family is None:
            item_family = registry_family if registry_family in ("prevoyance", "mutuelle") else "unclassified"
        warnings = list(base_warnings)
        cref_shared = contract_ref in shared_crefs

        # Component amount: only assignable when adhesion is sole owner of the cref.
        # When multiple adhesions share a cref, the S55 amount cannot be split —
        # set to None and downgrade instead of duplicating.
        if cref_shared:
            component_amount: Decimal | None = None
            warnings.append(
                f"component_not_allocable_across_adhesions: contract_ref "
                f"'{contract_ref}' shared by adhesions "
                f"{', '.join(adhesions_per_cref[contract_ref])}"
            )
        else:
            component_amount = comp_by_cref.get(contract_ref)

        # Individual amount from S78(31)/S81 linked through S70→adhesion_id
        ind_total = Decimal(0)
        has_ind = False
        details: list[ContributionComparisonDetail] = []

        if bridge_valid and adhesion_id:
            for emp in employee_blocks:
                emp_groups = group_employee_blocks(emp)
                emp_name = _employee_display_name(emp)

                for s78 in emp_groups.s78_blocks:
                    base_code = (_find_value(s78.records, "S21.G00.78.001") or "").strip()
                    if base_code != "31":
                        continue
                    affil_id = (_find_value(s78.records, "S21.G00.78.005") or "").strip()
                    linked_adhesion = s70_map.get(affil_id, "")
                    if linked_adhesion != adhesion_id:
                        continue

                    for s81 in s78.children:
                        amt = _dec(_find_value(s81.records, "S21.G00.81.004"))
                        if amt is not None:
                            ind_total += amt
                            has_ind = True
                            details.append(ContributionComparisonDetail(
                                key=emp_name,
                                label=f"S81 base 31 contrat {contract_ref}",
                                declared_amount=amt,
                                status="ok",
                                record_lines=_record_lines(s81.records),
                            ))

        individual_amount = ind_total if has_ind else None

        # Deltas and status
        agg_vs_comp = None
        agg_vs_ind = None

        if cref_shared:
            # Component not allocable per adhesion → non_calculable.
            # Raw individual still visible.
            status = "non_calculable"
        elif not bridge_valid:
            status = "non_rattache"
        elif component_amount is None and individual_amount is None:
            status = "manquant_detail"
        else:
            if component_amount is not None and individual_amount is not None:
                agg_vs_ind = component_amount - individual_amount
            if len(org_contracts) == 1:
                if aggregate_amount is not None and component_amount is not None:
                    agg_vs_comp = aggregate_amount - component_amount
                if aggregate_amount is not None and individual_amount is not None:
                    agg_vs_ind = aggregate_amount - individual_amount

            all_ok = True
            if len(org_contracts) == 1:
                if component_amount is not None and aggregate_amount is not None:
                    if not _within_tolerance(aggregate_amount, component_amount, _TOL_001):
                        all_ok = False
                if individual_amount is not None and aggregate_amount is not None:
                    if not _within_tolerance(aggregate_amount, individual_amount, _TOL_001):
                        all_ok = False
            else:
                if component_amount is not None and individual_amount is not None:
                    if not _within_tolerance(component_amount, individual_amount, _TOL_001):
                        all_ok = False
                elif component_amount is None and individual_amount is None:
                    all_ok = False
            status = "ok" if all_ok else "ecart"

        if has_regularization:
            warnings.append(REGULARIZATION_WARNING)

        items.append(ContributionComparisonItem(
            family=item_family,
            organism_id=organism_id,
            organism_label=label,
            aggregate_amount=aggregate_amount if len(org_contracts) == 1 else None,
            component_amount=component_amount,
            individual_amount=individual_amount,
            aggregate_vs_component_delta=agg_vs_comp,
            aggregate_vs_individual_delta=agg_vs_ind,
            status=status,
            details=details,
            warnings=warnings,
            adhesion_id=adhesion_id or None,
            contract_ref=contract_ref or None,
        ))

    return items


# ---------------------------------------------------------------------------
# Retraite reconciliation
# ---------------------------------------------------------------------------


def _compute_retraite(
    retraite_s20_blocks: list[tuple[str, BlockGroup]],
    employee_blocks: list[EmployeeBlock],
) -> list[ContributionComparisonItem]:
    """Compute retraite reconciliation for one or more retraite organisms."""
    if not retraite_s20_blocks:
        return []

    items: list[ContributionComparisonItem] = []

    # Compute individual total from S78{02,03}/S81{131,132,106,109}
    individual_total = Decimal(0)
    has_individual = False
    ind_details: list[ContributionComparisonDetail] = []

    for emp in employee_blocks:
        emp_groups = group_employee_blocks(emp)
        emp_name = _employee_display_name(emp)

        for s78 in emp_groups.s78_blocks:
            base_code = (_find_value(s78.records, "S21.G00.78.001") or "").strip()
            if base_code not in ("02", "03"):
                continue

            for s81 in s78.children:
                code_81 = (_find_value(s81.records, "S21.G00.81.001") or "").strip()
                if code_81 not in ("131", "132", "106", "109"):
                    continue

                amt = _dec(_find_value(s81.records, "S21.G00.81.004"))
                if amt is not None:
                    individual_total += amt
                    has_individual = True
                    ind_details.append(ContributionComparisonDetail(
                        key=f"{emp_name}/{code_81}",
                        label=f"S81 code {code_81} base {base_code}",
                        declared_amount=amt,
                        status="ok",
                        record_lines=_record_lines(s81.records),
                    ))

    individual_amount = individual_total if has_individual else None

    multi_caisse = len(retraite_s20_blocks) > 1

    for organism_id, s20 in retraite_s20_blocks:
        label, _, _ = lookup_organism(organism_id)
        warnings: list[str] = []
        has_regularization = _check_regularization(s20)

        aggregate_amount = _dec(_find_value(s20.records, "S21.G00.20.005"))

        if multi_caisse:
            warnings.append("multiple_retirement_organisms_unallocated")

        delta: Decimal | None = None
        if aggregate_amount is not None and individual_amount is not None:
            if not multi_caisse:
                delta = aggregate_amount - individual_amount

        # Status
        if aggregate_amount is None:
            status = "manquant_agrege"
        elif individual_amount is None:
            status = "manquant_individuel"
        elif multi_caisse:
            # Cannot compare per-caisse — no allocation key available.
            # Must not return ok/ecart since no comparison was performed.
            status = "non_calculable"
        elif _within_tolerance(aggregate_amount, individual_amount, _TOL_001):
            status = "ok"
        else:
            status = "ecart"

        if has_regularization:
            warnings.append(REGULARIZATION_WARNING)

        items.append(ContributionComparisonItem(
            family="retraite",
            organism_id=organism_id,
            organism_label=label,
            aggregate_amount=aggregate_amount,
            individual_amount=individual_amount if not multi_caisse else None,
            aggregate_vs_individual_delta=delta,
            status=status,
            details=ind_details if not multi_caisse else [],
            warnings=warnings,
        ))

    return items


# ---------------------------------------------------------------------------
# Unclassified outcome
# ---------------------------------------------------------------------------


def _make_unclassified(
    organism_id: str,
    s20_block: BlockGroup,
    warning_key: str,
) -> ContributionComparisonItem:
    label, _, _ = lookup_organism(organism_id)
    aggregate_amount = _dec(_find_value(s20_block.records, "S21.G00.20.005"))

    return ContributionComparisonItem(
        family="unclassified",
        organism_id=organism_id,
        organism_label=label,
        aggregate_amount=aggregate_amount,
        status="non_calculable",
        warnings=[warning_key],
    )


# ---------------------------------------------------------------------------
# Count computation
# ---------------------------------------------------------------------------


def _compute_counts(items: list[ContributionComparisonItem]) -> tuple[int, int, int]:
    """Compute (ok_count, mismatch_count, warning_count).

    warning_count is the number of **unique warning strings** across all items
    and their details.  This is a product contract: the same warning text
    appearing on multiple items is counted once.  Duplicates are deduplicated
    by exact string equality.
    """
    ok = sum(1 for i in items if i.status == "ok")
    ecart = sum(1 for i in items if i.status == "ecart")
    seen: set[str] = set()
    for item in items:
        for w in item.warnings:
            seen.add(w)
        for detail in item.details:
            for w in detail.warnings:
                seen.add(w)
    return ok, ecart, len(seen)


# ---------------------------------------------------------------------------
# Public orchestrator
# ---------------------------------------------------------------------------


def compute_contribution_comparisons(
    est_block: EstablishmentBlock,
) -> ContributionComparisons:
    """Compute all contribution comparisons for one establishment."""
    est_groups = group_establishment_blocks(est_block)
    structural_warnings: list[str] = list(est_groups.warnings)

    # Collect employee-level grouping warnings
    for emp in est_block.employee_blocks:
        emp_grp = group_employee_blocks(emp)
        structural_warnings.extend(emp_grp.warnings)

    # Collect organism IDs from structural linkage blocks
    s22_organism_ids: set[str] = set()
    for s22 in est_groups.s22_blocks:
        org_id = (_find_value(s22.records, "S21.G00.22.001") or "").strip()
        if org_id:
            s22_organism_ids.add(org_id)

    s15_organism_ids: set[str] = set()
    for s15 in est_groups.s15_blocks:
        org_id = (_find_value(s15.records, "S21.G00.15.002") or "").strip()
        if org_id:
            s15_organism_ids.add(org_id)

    # Build S15 entries and S70 map (shared across all prevoyance/mutuelle)
    s15_entries, s15_warnings = _build_s15_entries(est_groups.s15_blocks)
    s70_map, s70_warnings = _build_s70_map(est_block.employee_blocks)

    # Classify each S20 block
    items: list[ContributionComparisonItem] = []
    dgfip_s20_blocks: list[BlockGroup] = []
    urssaf_s20_by_org: dict[str, list[BlockGroup]] = {}
    complementary_s20_by_org: dict[str, list[BlockGroup]] = {}
    retraite_s20: list[tuple[str, BlockGroup]] = []

    for s20 in est_groups.s20_blocks:
        organism_id = (_find_value(s20.records, "S21.G00.20.001") or "").strip()
        if not organism_id:
            continue

        family = _classify_s20(organism_id, s22_organism_ids, s15_organism_ids)

        if family == "pas":
            dgfip_s20_blocks.append(s20)
        elif family == "urssaf":
            urssaf_s20_by_org.setdefault(organism_id, []).append(s20)
        elif family == "complementary":
            complementary_s20_by_org.setdefault(organism_id, []).append(s20)
        elif family == "retraite":
            retraite_s20.append((organism_id, s20))
        else:
            # Determine warning type
            if organism_id in s15_organism_ids:
                warning = (
                    f"s15_linked_unknown_subtype: organism {organism_id} is linked "
                    "via S15 but registry does not resolve to prevoyance or mutuelle"
                )
            else:
                warning = f"unclassified_organism: {organism_id}"
            items.append(_make_unclassified(organism_id, s20, warning))

    # PAS
    if dgfip_s20_blocks:
        items.append(_compute_pas(dgfip_s20_blocks, est_block.employee_blocks))

    # URSSAF
    for org_id, s20_list in urssaf_s20_by_org.items():
        items.append(_compute_urssaf(org_id, s20_list, est_groups.s22_blocks, est_groups))

    # Complementary (family resolved per contract)
    for org_id, s20_list in complementary_s20_by_org.items():
        items.extend(_compute_complementary(
            org_id, s20_list, est_groups, est_block.employee_blocks,
            s15_entries, s15_warnings, s70_map, s70_warnings,
        ))

    # Retraite
    items.extend(_compute_retraite(retraite_s20, est_block.employee_blocks))

    # Propagate structural orphan warnings so they always reach the payload.
    if structural_warnings:
        if items:
            # Distribute to each item so they surface in context
            for item in items:
                for w in structural_warnings:
                    if w not in item.warnings:
                        item.warnings.append(w)
        else:
            # No comparison items — create a carrier so warnings are not lost.
            # This is a technical visibility mechanism, not a real organism
            # record.  It exists solely to surface structural anomaly warnings
            # (orphan blocks, etc.) in the serialized payload and warning_count
            # when no S20 versement blocks produced comparison items.
            # Contract: family="unclassified", status="non_calculable",
            # organism_id=None, all amounts None.
            items.append(ContributionComparisonItem(
                family="unclassified",
                status="non_calculable",
                warnings=list(structural_warnings),
            ))

    # Counts
    ok_count, mismatch_count, warning_count = _compute_counts(items)

    return ContributionComparisons(
        items=items,
        ok_count=ok_count,
        mismatch_count=mismatch_count,
        warning_count=warning_count,
    )


def merge_contribution_comparisons(
    comparisons_list: list[ContributionComparisons],
) -> ContributionComparisons:
    """Merge contribution comparisons from multiple establishments."""
    all_items: list[ContributionComparisonItem] = []
    for cc in comparisons_list:
        all_items.extend(cc.items)

    ok_count, mismatch_count, warning_count = _compute_counts(all_items)

    return ContributionComparisons(
        items=all_items,
        ok_count=ok_count,
        mismatch_count=mismatch_count,
        warning_count=warning_count,
    )
