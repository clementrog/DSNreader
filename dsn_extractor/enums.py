"""DSN enumeration label maps."""

from __future__ import annotations

# S21.G00.40.003 — Code statut categoriel Retraite Complementaire obligatoire
RETIREMENT_CATEGORY_LABELS: dict[str, str] = {
    "01": "cadre",
    "02": "extension_cadre",
    "04": "non_cadre",
    "98": "other_no_cadre_split",
    "99": "no_complementary_retirement",
}

# S21.G00.40.007 — Nature du contrat
CONTRACT_NATURE_LABELS: dict[str, str] = {
    "01": "cdi_prive",
    "02": "cdd_prive",
    "29": "convention_stage",
}
