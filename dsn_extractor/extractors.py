"""Metric extraction functions for DSN files."""

from __future__ import annotations

import datetime
from decimal import Decimal

from dsn_extractor.enums import CONTRACT_NATURE_LABELS, RETIREMENT_CATEGORY_LABELS
from dsn_extractor.models import (
    Company,
    Declaration,
    DSNOutput,
    Establishment,
    EstablishmentAmounts,
    EstablishmentCounts,
    EstablishmentExtras,
    EstablishmentIdentity,
    Quality,
)
from dsn_extractor.normalize import lookup_enum_label, normalize_date, normalize_decimal, normalize_empty
from dsn_extractor.parser import DSNRecord, EmployeeBlock, EstablishmentBlock, ParsedDSN


# ---------------------------------------------------------------------------
# Record lookup helpers
# ---------------------------------------------------------------------------


def _find_value(records: list[DSNRecord], code: str) -> str | None:
    """Return the raw_value of the first record matching *code*, or None."""
    for r in records:
        if r.code == code:
            return r.raw_value
    return None


def _find_all_values(records: list[DSNRecord], code: str) -> list[str]:
    """Return all raw_values for records matching *code*."""
    return [r.raw_value for r in records if r.code == code]


# ---------------------------------------------------------------------------
# Null-safe decimal helpers
# ---------------------------------------------------------------------------


def _sum_decimal(a: Decimal | None, b: Decimal | None) -> Decimal | None:
    if a is None and b is None:
        return None
    return (a or Decimal(0)) + (b or Decimal(0))


# ---------------------------------------------------------------------------
# Extraction functions
# ---------------------------------------------------------------------------


def _extract_declaration(file_level_records: list[DSNRecord]) -> Declaration:
    period_start = normalize_date(_find_value(file_level_records, "S20.G00.05.005") or "")
    period_end = normalize_date(_find_value(file_level_records, "S20.G00.05.007") or "")
    month = period_start.strftime("%Y-%m") if period_start else None

    return Declaration(
        norm_version=normalize_empty(_find_value(file_level_records, "S10.G00.00.001") or ""),
        declaration_nature_code=normalize_empty(_find_value(file_level_records, "S20.G00.05.001") or ""),
        declaration_kind_code=normalize_empty(_find_value(file_level_records, "S20.G00.05.002") or ""),
        declaration_rank_code=normalize_empty(_find_value(file_level_records, "S20.G00.05.003") or ""),
        period_start=period_start,
        period_end=period_end,
        month=month,
        dsn_id=normalize_empty(_find_value(file_level_records, "S20.G00.05.009") or ""),
    )


def _extract_company(file_level_records: list[DSNRecord]) -> Company:
    siren = normalize_empty(_find_value(file_level_records, "S10.G00.01.001") or "")
    nic = normalize_empty(_find_value(file_level_records, "S10.G00.01.002") or "")
    siret = siren + nic if (siren and nic) else None

    return Company(
        siren=siren,
        nic=nic,
        siret=siret,
        name=normalize_empty(_find_value(file_level_records, "S10.G00.01.003") or ""),
        address=normalize_empty(_find_value(file_level_records, "S10.G00.01.004") or ""),
        postal_code=normalize_empty(_find_value(file_level_records, "S10.G00.01.005") or ""),
        city=normalize_empty(_find_value(file_level_records, "S10.G00.01.006") or ""),
        country_code=normalize_empty(_find_value(file_level_records, "S10.G00.01.007") or ""),
    )


def _extract_establishment_identity(
    est: EstablishmentBlock,
    company_siren: str | None,
    employee_blocks: list[EmployeeBlock],
    warnings: list[str],
) -> EstablishmentIdentity:
    has_s11 = any(r.code == "S21.G00.11.001" for r in est.records)

    if has_s11:
        nic = normalize_empty(_find_value(est.records, "S21.G00.11.001") or "")
        naf_code = normalize_empty(_find_value(est.records, "S21.G00.11.002") or "")
        address = normalize_empty(_find_value(est.records, "S21.G00.11.003") or "")
        postal_code = normalize_empty(_find_value(est.records, "S21.G00.11.004") or "")
        city = normalize_empty(_find_value(est.records, "S21.G00.11.005") or "")
        name = normalize_empty(_find_value(est.records, "S21.G00.11.008") or "")
        ccn_code = normalize_empty(_find_value(est.records, "S21.G00.11.022") or "")
    else:
        nic = normalize_empty(_find_value(est.records, "S21.G00.06.001") or "")
        naf_code = None
        address = None
        postal_code = None
        city = None
        name = None
        ccn_code = None
        warnings.append("Establishment missing S21.G00.11 block, falling back to S21.G00.06")

    # CCN fallback from employee-level S21.G00.40.017
    if ccn_code is None:
        employee_ccns: set[str] = set()
        for emp in employee_blocks:
            val = _find_value(emp.records, "S21.G00.40.017")
            if val and val.strip():
                employee_ccns.add(val)
        if len(employee_ccns) == 1:
            ccn_code = employee_ccns.pop()
        elif len(employee_ccns) > 1:
            warnings.append(
                f"Conflicting employee CCN values: {sorted(employee_ccns)}"
            )

    siret = company_siren + nic if (company_siren and nic) else None

    return EstablishmentIdentity(
        nic=nic,
        siret=siret,
        name=name,
        naf_code=naf_code,
        ccn_code=ccn_code,
        address=address,
        postal_code=postal_code,
        city=city,
    )


def _extract_counts(
    employee_blocks: list[EmployeeBlock],
    period_start: datetime.date | None,
    period_end: datetime.date | None,
    warnings: list[str],
) -> EstablishmentCounts:
    by_retirement_code: dict[str, int] = {}
    by_retirement_label: dict[str, int] = {}
    by_conventional_status: dict[str, int] = {}
    by_contract_nature: dict[str, int] = {}
    stagiaires = 0
    new_employees = 0
    exiting_employees = 0

    for emp in employee_blocks:
        # Contract nature
        nature_raw = _find_value(emp.records, "S21.G00.40.007")
        if nature_raw:
            by_contract_nature[nature_raw] = by_contract_nature.get(nature_raw, 0) + 1
            if nature_raw == "29":
                stagiaires += 1
            _, was_known = lookup_enum_label(nature_raw, CONTRACT_NATURE_LABELS)
            if not was_known:
                warnings.append(f"Unknown contract nature code: {nature_raw!r}")

        # Retirement category
        ret_raw = _find_value(emp.records, "S21.G00.40.003")
        if ret_raw:
            by_retirement_code[ret_raw] = by_retirement_code.get(ret_raw, 0) + 1
            label, was_known = lookup_enum_label(ret_raw, RETIREMENT_CATEGORY_LABELS)
            by_retirement_label[label] = by_retirement_label.get(label, 0) + 1
            if not was_known:
                warnings.append(f"Unknown retirement category code: {ret_raw!r}")

        # Conventional status
        conv_raw = _find_value(emp.records, "S21.G00.40.002")
        if conv_raw:
            by_conventional_status[conv_raw] = by_conventional_status.get(conv_raw, 0) + 1

        # New employees
        contract_start_raw = _find_value(emp.records, "S21.G00.40.001")
        if contract_start_raw:
            contract_start = normalize_date(contract_start_raw)
            if contract_start and period_start and period_end:
                if period_start <= contract_start <= period_end:
                    new_employees += 1
        else:
            warnings.append("Employee block missing contract start date (S21.G00.40.001)")

        # Exiting employees
        end_date_raw = _find_value(emp.records, "S21.G00.62.001")
        if end_date_raw:
            end_date = normalize_date(end_date_raw)
            rupture_code = _find_value(emp.records, "S21.G00.62.002")
            if rupture_code is None:
                warnings.append(
                    "Contract end block (S21.G00.62) missing rupture code (S21.G00.62.002)"
                )
            if end_date and period_start and period_end:
                if period_start <= end_date <= period_end:
                    if rupture_code != "099":
                        exiting_employees += 1

    return EstablishmentCounts(
        employee_blocks_count=len(employee_blocks),
        stagiaires=stagiaires,
        employees_by_retirement_category_code=by_retirement_code,
        employees_by_retirement_category_label=by_retirement_label,
        employees_by_conventional_status_code=by_conventional_status,
        employees_by_contract_nature_code=by_contract_nature,
        new_employees_in_month=new_employees,
        exiting_employees_in_month=exiting_employees,
    )


def _extract_amounts(
    s54_blocks: list[list[DSNRecord]],
    warnings: list[str],
) -> EstablishmentAmounts:
    if not s54_blocks:
        warnings.append("No S21.G00.54 block family present in establishment")
        return EstablishmentAmounts()

    type_17: Decimal | None = None
    type_18: Decimal | None = None
    type_19: Decimal | None = None

    for group in s54_blocks:
        s54_type = _find_value(group, "S21.G00.54.001")
        amount = normalize_decimal(_find_value(group, "S21.G00.54.002") or "")
        if amount is None:
            continue
        if s54_type == "17":
            type_17 = (type_17 or Decimal(0)) + amount
        elif s54_type == "18":
            type_18 = (type_18 or Decimal(0)) + amount
        elif s54_type == "19":
            type_19 = (type_19 or Decimal(0)) + amount

    return EstablishmentAmounts(
        tickets_restaurant_employer_contribution_total=type_17,
        transport_public_total=type_18,
        transport_personal_total=type_19,
    )


def _extract_extras(employee_blocks: list[EmployeeBlock]) -> EstablishmentExtras:
    net_fiscal: Decimal | None = None
    net_paid: Decimal | None = None
    pas: Decimal | None = None

    for emp in employee_blocks:
        nf = normalize_decimal(_find_value(emp.records, "S21.G00.50.002") or "")
        if nf is not None:
            net_fiscal = (net_fiscal or Decimal(0)) + nf

        np_ = normalize_decimal(_find_value(emp.records, "S21.G00.50.004") or "")
        if np_ is not None:
            net_paid = (net_paid or Decimal(0)) + np_

        ps = normalize_decimal(_find_value(emp.records, "S21.G00.50.009") or "")
        if ps is not None:
            pas = (pas or Decimal(0)) + ps

    return EstablishmentExtras(
        net_fiscal_sum=net_fiscal,
        net_paid_sum=net_paid,
        pas_sum=pas,
    )


# ---------------------------------------------------------------------------
# Aggregation helpers
# ---------------------------------------------------------------------------


def _merge_counts(counts_list: list[EstablishmentCounts]) -> EstablishmentCounts:
    total = EstablishmentCounts()
    for c in counts_list:
        total.employee_blocks_count += c.employee_blocks_count
        total.stagiaires += c.stagiaires
        total.new_employees_in_month += c.new_employees_in_month
        total.exiting_employees_in_month += c.exiting_employees_in_month
        for k, v in c.employees_by_retirement_category_code.items():
            total.employees_by_retirement_category_code[k] = (
                total.employees_by_retirement_category_code.get(k, 0) + v
            )
        for k, v in c.employees_by_retirement_category_label.items():
            total.employees_by_retirement_category_label[k] = (
                total.employees_by_retirement_category_label.get(k, 0) + v
            )
        for k, v in c.employees_by_conventional_status_code.items():
            total.employees_by_conventional_status_code[k] = (
                total.employees_by_conventional_status_code.get(k, 0) + v
            )
        for k, v in c.employees_by_contract_nature_code.items():
            total.employees_by_contract_nature_code[k] = (
                total.employees_by_contract_nature_code.get(k, 0) + v
            )
    return total


def _merge_amounts(amounts_list: list[EstablishmentAmounts]) -> EstablishmentAmounts:
    total = EstablishmentAmounts()
    for a in amounts_list:
        total.tickets_restaurant_employer_contribution_total = _sum_decimal(
            total.tickets_restaurant_employer_contribution_total,
            a.tickets_restaurant_employer_contribution_total,
        )
        total.transport_public_total = _sum_decimal(
            total.transport_public_total, a.transport_public_total
        )
        total.transport_personal_total = _sum_decimal(
            total.transport_personal_total, a.transport_personal_total
        )
    return total


def _merge_extras(extras_list: list[EstablishmentExtras]) -> EstablishmentExtras:
    total = EstablishmentExtras()
    for e in extras_list:
        total.net_fiscal_sum = _sum_decimal(total.net_fiscal_sum, e.net_fiscal_sum)
        total.net_paid_sum = _sum_decimal(total.net_paid_sum, e.net_paid_sum)
        total.pas_sum = _sum_decimal(total.pas_sum, e.pas_sum)
        total.gross_sum_from_salary_bases = _sum_decimal(
            total.gross_sum_from_salary_bases, e.gross_sum_from_salary_bases
        )
    return total


# ---------------------------------------------------------------------------
# Public orchestrator
# ---------------------------------------------------------------------------


def extract(parsed: ParsedDSN, source_file: str = "") -> DSNOutput:
    """Extract structured metrics from a parsed DSN file."""
    global_warnings: list[str] = []

    # 1. Declaration
    declaration = _extract_declaration(parsed.file_level_records)
    period_start = declaration.period_start
    period_end = declaration.period_end

    if period_start is None:
        global_warnings.append("Missing or invalid period start date (S20.G00.05.005)")
    if period_end is None:
        global_warnings.append("Missing or invalid period end date (S20.G00.05.007)")

    # 2. Company
    company = _extract_company(parsed.file_level_records)

    # 3. Multiple establishments warning
    if len(parsed.establishments) > 1:
        global_warnings.append("Multiple establishments detected in file")

    # 4. Per-establishment extraction
    establishments: list[Establishment] = []
    all_counts: list[EstablishmentCounts] = []
    all_amounts: list[EstablishmentAmounts] = []
    all_extras: list[EstablishmentExtras] = []

    for est_block in parsed.establishments:
        est_warnings: list[str] = []

        identity = _extract_establishment_identity(
            est_block, company.siren, est_block.employee_blocks, est_warnings
        )
        counts = _extract_counts(
            est_block.employee_blocks, period_start, period_end, est_warnings
        )
        amounts = _extract_amounts(est_block.s54_blocks, est_warnings)
        extras = _extract_extras(est_block.employee_blocks)

        est = Establishment(
            identity=identity,
            counts=counts,
            amounts=amounts,
            extras=extras,
            quality=Quality(warnings=est_warnings),
        )
        establishments.append(est)
        all_counts.append(counts)
        all_amounts.append(amounts)
        all_extras.append(extras)

    # 5. Global aggregation
    global_counts = _merge_counts(all_counts)
    global_amounts = _merge_amounts(all_amounts)
    global_extras = _merge_extras(all_extras)

    # 6. Global quality: parser warnings + orchestrator warnings + per-establishment warnings
    all_warnings = list(parsed.warnings) + global_warnings
    for est in establishments:
        all_warnings.extend(est.quality.warnings)

    return DSNOutput(
        source_file=source_file,
        declaration=declaration,
        company=company,
        establishments=establishments,
        global_counts=global_counts,
        global_amounts=global_amounts,
        global_extras=global_extras,
        global_quality=Quality(warnings=all_warnings),
    )
