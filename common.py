"""Petits utilitaires partagés."""
import re
import duckdb
from config import RAW

# Noms des fichiers produits par le repo fitnr/acris-download (dossier data/)
REPO_NAMES = {
    "acris_master":  ["real_property_master"],
    "acris_legals":  ["real_property_legals"],
    "acris_parties": ["real_property_parties"],
}


def norm_col(s: str) -> str:
    """'DOC. TYPE' -> 'doc_type' ; 'RECORDED / FILED' -> 'recorded_filed'."""
    return re.sub(r"[^a-z0-9]+", "_", s.strip().lower()).strip("_")


def csv_view(con: duckdb.DuckDBPyConnection, name: str, aliases: dict) -> None:
    """Crée une vue DuckDB `name` sur data/raw/{name}.csv avec des noms de colonnes
    stables, que le CSV vienne de l'export web (en-têtes 'DOC. TYPE') ou de l'API
    ('doc_type'). `aliases` = {nom_voulu: [variantes possibles]}."""
    candidates = [RAW / f"{n}.csv" for n in [name, *REPO_NAMES.get(name, [])]]
    path = next((p for p in candidates if p.exists()), None)
    if path is None:
        raise FileNotFoundError(f"{candidates[0]} introuvable — lance d'abord 01_download.py "
                                f"ou copie ici les CSV du repo fitnr/acris-download")
    with open(path, encoding="utf-8", errors="replace") as f:
        header = f.readline().rstrip("\n\r")
    raw_cols = [c.strip().strip('"') for c in header.split(",")]
    # 'DOC. TYPE', 'doc_type' et 'doctype' (format du repo fitnr) sont reconnus pareil
    by_norm = {norm_col(c).replace("_", ""): c for c in raw_cols}
    select = []
    for want, variants in aliases.items():
        found = next((by_norm[v.replace("_", "")] for v in [want, *variants]
                      if v.replace("_", "") in by_norm), None)
        if found is None:
            raise KeyError(f"{name}.csv : colonne '{want}' introuvable. "
                           f"Colonnes présentes : {sorted(by_norm)}")
        select.append(f'"{found}" AS {want}')
    con.execute(f"""
        CREATE OR REPLACE VIEW {name} AS
        SELECT {', '.join(select)}
        FROM read_csv('{path.as_posix()}', header=true, all_varchar=true,
                      ignore_errors=true, parallel=true)
    """)


NAME_CLEAN_SQL = """
    trim(regexp_replace(regexp_replace(upper(coalesce({col}, '')),
        '[^A-Z0-9& ]', ' ', 'g'), '\\s+', ' ', 'g'))
"""
