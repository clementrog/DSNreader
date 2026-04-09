"""URSSAF CTP → individual-contribution mapping (Slice B discovery gate).

Locks the product rule about which URSSAF CTP codes (``S21.G00.23.001``) can
be reliably linked down to employee-level individual contribution blocks
(``S21.G00.81.001``).

The rule is default-deny: a CTP code is only "rattachable" when the DSN norm
(``docs/13. DSN/13.1-cotisations-dsn.publicodes``) explicitly associates it
with a single individual code and an URSSAF-scoped OPS. Codes absent from the
mapping table are treated as ``non_rattache`` by the consumer.

This module is documentation + scaffolding only. It is NOT wired into
``dsn_extractor.contributions._compute_urssaf`` — Slice C is responsible for
that. The module exists so the spec, the data, and the tests land together
before any engine change.

The canonical source of truth is ``data/urssaf_individual_mapping.tsv``,
loaded at import time with strict fail-fast validation (same pattern as
``organisms.py`` and ``ctp_rates.py``).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


# ---------------------------------------------------------------------------
# Recognized URSSAF detail statuses
# ---------------------------------------------------------------------------

# Slice B adds ``non_rattache`` to the set of statuses the URSSAF detail layer
# is allowed to carry. The pydantic field is a free ``str`` today (see
# ``ContributionComparisonDetail.status``) so no schema migration is required;
# this constant is the single source of truth for "allowed" values.
URSSAF_DETAIL_STATUSES: tuple[str, ...] = (
    "ok",
    "ecart",
    "non_calculable",
    "non_rattache",
    "declared_only",
    "computed_only",
)


# ---------------------------------------------------------------------------
# Mapping row
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class UrssafIndividualMapping:
    """One verified CTP → individual-code row."""

    ctp_code: str
    ctp_label: str
    individual_code_s81: str
    ops_rule: str
    source_ref: str


# ---------------------------------------------------------------------------
# TSV loader with fail-fast validation
# ---------------------------------------------------------------------------

_DATA_DIR = Path(__file__).parent / "data"
_TSV_NAME = "urssaf_individual_mapping.tsv"
_EXPECTED_COLUMNS = 5


def _load_mapping(tsv_path: Path) -> dict[str, UrssafIndividualMapping]:
    if not tsv_path.is_file():
        raise RuntimeError(f"{_TSV_NAME} not found at {tsv_path}")

    lines = tsv_path.read_text(encoding="utf-8").splitlines()
    if not lines:
        raise RuntimeError(f"{_TSV_NAME} is empty")

    mapping: dict[str, UrssafIndividualMapping] = {}
    for line_num, raw_line in enumerate(lines, start=1):
        if not raw_line.strip():
            continue

        cols = raw_line.split("\t")
        if len(cols) != _EXPECTED_COLUMNS:
            raise RuntimeError(
                f"{_TSV_NAME} line {line_num}: expected "
                f"{_EXPECTED_COLUMNS} columns, got {len(cols)}"
            )

        ctp_code = cols[0].strip()
        ctp_label = cols[1].strip()
        individual_code_s81 = cols[2].strip()
        ops_rule = cols[3].strip()
        source_ref = cols[4].strip()

        if ctp_code.lower().startswith(("ctp", "code")):
            raise RuntimeError(
                f"{_TSV_NAME} line {line_num}: contains header row — remove it"
            )

        if not ctp_code or not individual_code_s81:
            raise RuntimeError(
                f"{_TSV_NAME} line {line_num}: missing ctp_code or "
                f"individual_code_s81"
            )

        if ctp_code in mapping:
            raise RuntimeError(
                f"{_TSV_NAME} line {line_num}: duplicate ctp_code {ctp_code!r}"
            )

        mapping[ctp_code] = UrssafIndividualMapping(
            ctp_code=ctp_code,
            ctp_label=ctp_label,
            individual_code_s81=individual_code_s81,
            ops_rule=ops_rule,
            source_ref=source_ref,
        )

    return mapping


# Loaded once at import time. Fail fast if the TSV is broken.
_MAPPING: dict[str, UrssafIndividualMapping] = _load_mapping(_DATA_DIR / _TSV_NAME)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def load_mapping() -> dict[str, UrssafIndividualMapping]:
    """Return a copy of the loaded mapping (ctp_code → row)."""
    return dict(_MAPPING)


def is_urssaf_code_mappable(ctp_code: str | None) -> bool:
    """Return True if the CTP code has an explicit, verified individual link.

    Default-deny: empty, None, or unknown codes return False.
    """
    if not ctp_code:
        return False
    return ctp_code in _MAPPING


def get_individual_code_for_ctp(ctp_code: str | None) -> str | None:
    """Return the ``S21.G00.81.001`` individual code for a mappable CTP.

    Returns ``None`` for empty, None, or unmappable codes.
    """
    if not ctp_code:
        return None
    row = _MAPPING.get(ctp_code)
    return row.individual_code_s81 if row is not None else None
