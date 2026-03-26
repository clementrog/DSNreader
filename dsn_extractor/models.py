"""Pydantic output models for DSN extraction."""

from __future__ import annotations

import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class Declaration(BaseModel):
    model_config = ConfigDict(extra="forbid")

    norm_version: str | None = None
    declaration_nature_code: str | None = None
    declaration_kind_code: str | None = None
    declaration_rank_code: str | None = None
    period_start: datetime.date | None = None
    period_end: datetime.date | None = None
    month: str | None = None  # YYYY-MM derived from period_start
    dsn_id: str | None = None

    @field_validator("month")
    @classmethod
    def _month_must_be_yyyy_mm(cls, v: str | None) -> str | None:
        if v is None:
            return None
        if not isinstance(v, str):
            raise ValueError("month must be a string in YYYY-MM format")
        import re
        if not re.fullmatch(r"\d{4}-(0[1-9]|1[0-2])", v):
            raise ValueError(f"month must match YYYY-MM format, got {v!r}")
        return v


class Company(BaseModel):
    model_config = ConfigDict(extra="forbid")

    siren: str | None = None
    nic: str | None = None
    siret: str | None = None  # siren + nic, computed by extractor
    name: str | None = None
    address: str | None = None
    postal_code: str | None = None
    city: str | None = None
    country_code: str | None = None


class EstablishmentIdentity(BaseModel):
    model_config = ConfigDict(extra="forbid")

    nic: str | None = None
    siret: str | None = None  # company siren + establishment nic
    name: str | None = None
    naf_code: str | None = None
    ccn_code: str | None = None
    address: str | None = None
    postal_code: str | None = None
    city: str | None = None
    employee_band_code: str | None = None


class EstablishmentCounts(BaseModel):
    model_config = ConfigDict(extra="forbid")

    employee_blocks_count: int = 0
    stagiaires: int = 0
    employees_by_retirement_category_code: dict[str, int] = Field(default_factory=dict)
    employees_by_retirement_category_label: dict[str, int] = Field(default_factory=dict)
    employees_by_conventional_status_code: dict[str, int] = Field(default_factory=dict)
    employees_by_contract_nature_code: dict[str, int] = Field(default_factory=dict)
    employees_by_contract_nature_label: dict[str, int] = Field(default_factory=dict)
    new_employees_in_month: int = 0
    exiting_employees_in_month: int = 0
    exit_reasons_by_code: dict[str, int] = Field(default_factory=dict)
    exit_reasons_by_label: dict[str, int] = Field(default_factory=dict)
    absences_employees_count: int = 0
    absences_events_count: int = 0
    absences_by_code: dict[str, int] = Field(default_factory=dict)
    entry_employee_names: list[str] = Field(default_factory=list)
    exit_employee_names: list[str] = Field(default_factory=list)
    absence_employee_names: list[str] = Field(default_factory=list)


class EstablishmentAmounts(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tickets_restaurant_employer_contribution_total: Decimal | None = None
    transport_public_total: Decimal | None = None
    transport_personal_total: Decimal | None = None


class EstablishmentExtras(BaseModel):
    model_config = ConfigDict(extra="forbid")

    net_fiscal_sum: Decimal | None = None
    net_paid_sum: Decimal | None = None
    pas_sum: Decimal | None = None
    gross_sum_from_salary_bases: Decimal | None = None


class Quality(BaseModel):
    model_config = ConfigDict(extra="forbid")

    warnings: list[str] = Field(default_factory=list)


class SocialAnalysis(BaseModel):
    model_config = ConfigDict(extra="forbid")

    effectif: int = 0
    entrees: int = 0
    sorties: int = 0
    stagiaires: int = 0
    cadre_count: int = 0
    non_cadre_count: int = 0
    contracts_by_code: dict[str, int] = Field(default_factory=dict)
    contracts_by_label: dict[str, int] = Field(default_factory=dict)
    exit_reasons_by_code: dict[str, int] = Field(default_factory=dict)
    exit_reasons_by_label: dict[str, int] = Field(default_factory=dict)
    absences_employees_count: int = 0
    absences_events_count: int = 0
    absences_by_code: dict[str, int] = Field(default_factory=dict)
    net_verse_total: Decimal | None = None
    net_fiscal_total: Decimal | None = None
    pas_total: Decimal | None = None
    quality_alerts_count: int = 0
    quality_alerts: list[str] = Field(default_factory=list)


class PayrollTracking(BaseModel):
    model_config = ConfigDict(extra="forbid")

    bulletins: int = 0
    billable_entries: int = 0
    billable_exits: int = 0
    billable_absence_events: int = 0
    exceptional_events_count: int = 0
    dsn_anomalies_count: int = 0
    complexity_score: int = 0
    complexity_inputs: dict[str, int] = Field(default_factory=dict)
    billable_entry_names: list[str] = Field(default_factory=list)
    billable_exit_names: list[str] = Field(default_factory=list)
    billable_absence_names: list[str] = Field(default_factory=list)


class Establishment(BaseModel):
    model_config = ConfigDict(extra="forbid")

    identity: EstablishmentIdentity = Field(default_factory=EstablishmentIdentity)
    counts: EstablishmentCounts = Field(default_factory=EstablishmentCounts)
    amounts: EstablishmentAmounts = Field(default_factory=EstablishmentAmounts)
    extras: EstablishmentExtras = Field(default_factory=EstablishmentExtras)
    quality: Quality = Field(default_factory=Quality)
    social_analysis: SocialAnalysis = Field(default_factory=SocialAnalysis)
    payroll_tracking: PayrollTracking = Field(default_factory=PayrollTracking)


class DSNOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_file: str = ""
    declaration: Declaration = Field(default_factory=Declaration)
    company: Company = Field(default_factory=Company)
    establishments: list[Establishment] = Field(default_factory=list)
    global_counts: EstablishmentCounts = Field(default_factory=EstablishmentCounts)
    global_amounts: EstablishmentAmounts = Field(default_factory=EstablishmentAmounts)
    global_extras: EstablishmentExtras = Field(default_factory=EstablishmentExtras)
    global_quality: Quality = Field(default_factory=Quality)
    global_social_analysis: SocialAnalysis = Field(default_factory=SocialAnalysis)
    global_payroll_tracking: PayrollTracking = Field(default_factory=PayrollTracking)
