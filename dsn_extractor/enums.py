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
    "03": "ctt_interim",
    "07": "cdi_intermittent",
    "08": "cdd_usage",
    "09": "cdd_senior",
    "10": "cdd_objet_defini",
    "29": "convention_stage",
    "32": "cdd_remplacement",
    "50": "cdi_chantier",
    "60": "cdi_operationnel",
    "70": "cdi_interimaire",
    "80": "mandat_social",
    "81": "mandat_electif",
    "82": "contrat_appui",
    "89": "volontariat_service_civique",
    "90": "autre_contrat",
    "91": "contrat_engagement_educatif",
    "92": "cdd_tremplin",
    "93": "dispositif_academie_leaders",
}
