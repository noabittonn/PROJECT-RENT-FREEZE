"""Paramètres du projet. Tout ce qu'on peut vouloir changer est ici."""
import os
from pathlib import Path

ROOT = Path(__file__).parent
DATA = Path(os.environ.get("RFL_DATA", ROOT / "data"))  # RFL_DATA=tests/data pour le test
RAW = DATA / "raw"      # CSV bruts (ACRIS, PLUTO, HPD)
OUT = DATA / "out"      # tables produites
PROMPTS = ROOT / "prompts"

# --- Fichiers bruts (exports CSV complets de NYC Open Data) ---------------
# Mêmes jeux de données que le repo fitnr/acris-download.
SOURCES = {
    "acris_master":  ("bnx9-e6tj", "ACRIS Real Property Master"),
    "acris_legals":  ("8h5j-fqxa", "ACRIS Real Property Legals"),
    "acris_parties": ("636b-3b5g", "ACRIS Real Property Parties"),
    "pluto":         ("64uk-42ks", "Primary Land Use Tax Lot Output (PLUTO)"),
    "hpd_reg":       ("tesw-yqqr", "HPD Multiple Dwelling Registrations"),
    "hpd_contacts":  ("feu5-w2e2", "HPD Registration Contacts"),
}
EXPORT_URL = "https://data.cityofnewyork.us/api/views/{id}/rows.csv?accessType=DOWNLOAD"

# --- Filtres de l'échantillon ----------------------------------------------
START_DATE = "2010-01-01"
DEED_TYPES = ("DEED", "DEEDO")     # deeds ; exclut mortgages, satisfactions, etc.
MIN_AMOUNT = 250_000                # enlève les transferts nominaux (0 $, 10 $...)
MIN_RES_UNITS = 6                   # seuil de la rent stabilization (6+ logements)
BLDG_CLASS_PREFIXES = ("C", "D")    # walk-ups (C) et elevator buildings (D)

# --- Sélection des "big players" (étapes 2-3 du prof) ----------------------
N_PLAYERS = 100

# Acteurs non marchands ou intermédiaires à exclure du ranking
EXCLUDE_PATTERNS = [
    r"\bBANK\b", r"\bN\.?A\.?$", r"FEDERAL NATIONAL", r"FEDERAL HOME LOAN",
    r"\bREFEREE\b", r"\bSHERIFF\b", r"CITY OF NEW YORK", r"\bNYC\b",
    r"HOUSING PRESERVATION", r"HOUSING DEVELOPMENT CORP", r"\bHDFC\b",
    r"\bHPD\b", r"PUBLIC ADMINISTRATOR", r"ESTATE OF", r"\bEXECUTOR",
    r"MORTGAGE", r"SAVINGS", r"TITLE INSURANCE", r"UNKNOWN",
]

# --- Ranking LLM (étape 4) --------------------------------------------------
LLM_MODEL = "claude-sonnet-5-5"
PROMPT_FILE = PROMPTS / "ranking_v1.md"
PROMPT_VERSION = "ranking_v1"

# --- Repères du graphique (étape 5) — dates à revérifier avant diffusion ---
EVENTS = [
    ("2013-11-05", "de Blasio elected", "election"),
    ("2015-06-29", "Freeze 2015", "freeze"),
    ("2016-06-27", "Freeze 2016", "freeze"),
    ("2017-11-07", "de Blasio re-elected", "election"),
    ("2019-06-14", "HSTPA", "law"),
    ("2020-06-17", "Freeze 2020", "freeze"),
    ("2021-11-02", "Adams elected", "election"),
    ("2025-11-04", "Mamdani elected", "election"),
    ("2026-06-25", "Freeze 2026", "freeze"),
]
