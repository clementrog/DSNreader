"""Pydantic output models for DSN extraction."""

from __future__ import annotations

import datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class Declaration(BaseModel):
    norm_version: str | None = None
    declaration_nature_code: str | None = None
    declaration_kind_code: str | None = None
    declaration_rank_code: str | None = None
    period_start: datetime.date | None = None
    period_end: datetime.date | None = None
    month: str | None = None  # YYYY-MM derived from period_start
    dsn_id: str | None = None


class Company(BaseModel):
    siren: str | None = None
    nic: str | None = None
    siret: str | None = None  # siren + nic, computed by extractor
    name: str | None = None
    address: str | None = None
    postal_code: str | None = None
    city: str | None = None
    country_code: str | None = None


class EstablishmentIdentity(BaseModel):
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
    employee_blocks_count: int = 0
    stagiaires: int = 0
    employees_by_retirement_category_code: dict[str, int] = Field(default_factory=dict)
    employees_by_retirement_category_label: dict[str, int] = Field(default_factory=dict)
    employees_by_conventional_status_code: dict[str, int] = Field(default_factory=dict)
    employees_by_contract_nature_code: dict[str, int] = Field(default_factory=dict)
    new_employees_in_month: int = 0
    exiting_employees_in_month: int = 0


class EstablishmentAmounts(BaseModel):
    tickets_restaurant_employer_contribution_total: Decimal | None = None
    transport_public_total: Decimal | None = None
    transport_personal_total: Decimal | None = None


class EstablishmentExtras(BaseModel):
    net_fiscal_sum: Decimal | None = None
    net_paid_sum: Decimal | None = None
    pas_sum: Decimal | None = None
    gross_sum_from_salary_bases: Decimal | None = None


class Quality(BaseModel):
    warnings: list[str] = Field(default_factory=list)


class Establishment(BaseModel):
    identity: EstablishmentIdentity = Field(default_factory=EstablishmentIdentity)
    counts: EstablishmentCounts = Field(default_factory=EstablishmentCounts)
    amounts: EstablishmentAmounts = Field(default_factory=EstablishmentAmounts)
    extras: EstablishmentExtras = Field(default_factory=EstablishmentExtras)
    quality: Quality = Field(default_factory=Quality)


class DSNOutput(BaseModel):
    source_file: str = ""
    declaration: Declaration = Field(default_factory=Declaration)
    company: Company = Field(default_factory=Company)
    establishments: list[Establishment] = Field(default_factory=list)
    global_counts: EstablishmentCounts = Field(default_factory=EstablishmentCounts)
    global_amounts: EstablishmentAmounts = Field(default_factory=EstablishmentAmounts)
    global_extras: EstablishmentExtras = Field(default_factory=EstablishmentExtras)
    global_quality: Quality = Field(default_factory=Quality)
