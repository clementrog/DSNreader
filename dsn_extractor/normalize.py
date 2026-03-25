"""Date, decimal, and enum normalization."""

from __future__ import annotations

import datetime
from decimal import Decimal, InvalidOperation


def normalize_date(raw: str) -> datetime.date | None:
    """Parse a DSN date string (DDMMYYYY) into a date, or None if empty/invalid."""
    if not raw or not raw.strip():
        return None
    stripped = raw.strip()
    if len(stripped) != 8:
        return None
    try:
        return datetime.datetime.strptime(stripped, "%d%m%Y").date()
    except ValueError:
        return None


def normalize_decimal(raw: str) -> Decimal | None:
    """Parse a numeric string into Decimal, or None if empty/invalid."""
    if not raw or not raw.strip():
        return None
    try:
        return Decimal(raw.strip())
    except InvalidOperation:
        return None


def normalize_empty(raw: str) -> str | None:
    """Return None if raw is the empty string, otherwise return raw as-is."""
    if raw == "":
        return None
    return raw


def lookup_enum_label(raw: str, label_map: dict[str, str]) -> tuple[str, bool]:
    """Look up a label for a raw DSN code.

    Returns (label, was_known). Unknown codes pass through as their raw value.
    """
    return label_map.get(raw, raw), raw in label_map
