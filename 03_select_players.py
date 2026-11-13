"""Étapes 2-3 — Regrouper les LLC en "players" et garder les ~100 plus actifs.

Problème : dans ACRIS, acheteurs et vendeurs sont des LLC ("123 EAST 116 LLC").
Compter les noms bruts ne fait pas apparaître les vrais opérateurs.
Regroupement simple, par ordre de priorité :
  1. Nom de la LLC retrouvé comme CorporateOwner dans les HPD registrations
     -> on prend le Head Officer de cet enregistrement (souvent le vrai principal).
  2. Sinon, adresse postale de la partie dans ACRIS (adresse + zip) :
     des LLC qui partagent une adresse appartiennent souvent au même opérateur.
  3. Sinon, le nom nettoyé.
C'est volontairement simple : la liste finale (~100 lignes) doit être relue à la
main (1-2 h). La colonne `review_flag` signale les groupes suspects.

Sorties :
    data/out/party_player_map.parquet
    data/out/players_top.csv       <- à relire, puis à classer à l'étape 4
"""
import re
import duckdb
from config import OUT, N_PLAYERS, EXCLUDE_PATTERNS
from common import csv_view, NAME_CLEAN_SQL

con = duckdb.connect()
con.execute(f"CREATE TABLE tx AS SELECT * FROM '{(OUT/'transactions.parquet').as_posix()}'")
con.execute(f"CREATE TABLE parties AS SELECT * FROM '{(OUT/'parties.parquet').as_posix()}'")

# ---------- 1. Correspondance LLC -> head officer via HPD -------------------
try:
    csv_view(con, "hpd_contacts", {
        "registrationid": [], "type": [], "corporationname": [],
        "firstname": [], "lastname": [],
    })
    con.execute(f"""
    CREATE TABLE hpd_map AS
    WITH c AS (
        SELECT registrationid, type,
               {NAME_CLEAN_SQL.format(col='corporationname')} AS corp,
               trim(upper(coalesce(firstname,'') || ' ' || coalesce(lastname,''))) AS person
        FROM hpd_contacts),
    owners AS (SELECT registrationid, corp FROM c
               WHERE type = 'CorporateOwner' AND corp <> ''),
    heads  AS (SELECT registrationid, person FROM c
               WHERE type = 'HeadOfficer' AND person <> ''),
    agents AS (SELECT registrationid, corp AS agent FROM c
               WHERE type = 'Agent' AND corp <> '')
    SELECT o.corp AS name_clean,
           mode(h.person) AS head_officer,
           mode(a.agent)  AS managing_agent
    FROM owners o
    LEFT JOIN heads  h USING (registrationid)
    LEFT JOIN agents a USING (registrationid)
    GROUP BY 1
    """)
    print(f"HPD : {con.execute('SELECT count(*) FROM hpd_map').fetchone()[0]:,} LLC reliées à un head officer / agent")
except FileNotFoundError:
    print("⚠ hpd_contacts.csv absent : regroupement par adresse/nom uniquement")
    con.execute("CREATE TABLE hpd_map (name_clean VARCHAR, head_officer VARCHAR, managing_agent VARCHAR)")

# ---------- 2. Clé "player" pour chaque partie -------------------------------
exclude_re = "|".join(f"({p})" for p in EXCLUDE_PATTERNS).replace("'", "''")
con.execute(f"""
CREATE TABLE party_map AS
SELECT p.*, h.head_officer, h.managing_agent,
       CASE
         WHEN h.head_officer IS NOT NULL AND h.head_officer <> ''
              THEN 'HPD:' || h.head_officer
         WHEN length(p.address_clean) >= 6
              THEN 'ADDR:' || p.address_clean || ' ' || p.zip
         ELSE 'NAME:' || p.name_clean
       END AS player_key,
       regexp_matches(p.name_clean, '{exclude_re}') AS excluded
FROM parties p
LEFT JOIN hpd_map h USING (name_clean)
""")
con.execute(f"COPY party_map TO '{(OUT/'party_player_map.parquet').as_posix()}' (FORMAT parquet)")

# ---------- 3. Activité par player, top N -----------------------------------
players = con.execute(f"""
WITH act AS (
    SELECT pm.player_key, pm.side, pm.document_id, pm.name_clean,
           pm.address_clean, pm.zip, pm.managing_agent,
           t.bbl, t.sale_date, t.units_res
    FROM party_map pm JOIN tx t USING (document_id)
    WHERE NOT pm.excluded),
agg AS (
SELECT player_key,
       count(DISTINCT document_id)                                   AS n_deals,
       count(DISTINCT document_id) FILTER (WHERE side = 'buyer')     AS n_buys,
       count(DISTINCT document_id) FILTER (WHERE side = 'seller')    AS n_sells,
       count(DISTINCT bbl)                                           AS n_buildings,
       string_agg(DISTINCT CASE bbl // 1000000000
            WHEN 1 THEN 'MN' WHEN 2 THEN 'BX' WHEN 3 THEN 'BK'
            WHEN 4 THEN 'QN' WHEN 5 THEN 'SI' END, ',')              AS boroughs,
       min(year(sale_date)) AS first_year, max(year(sale_date)) AS last_year,
       count(DISTINCT name_clean)                                    AS n_entity_names,
       array_to_string(list_slice(list(DISTINCT name_clean), 1, 8), ' | ') AS sample_names,
       mode(address_clean || ' ' || zip)                            AS main_address,
       mode(managing_agent)                                         AS managing_agent
FROM act
GROUP BY player_key
),
units AS (
    SELECT player_key, sum(units_res) AS approx_units
    FROM (SELECT DISTINCT player_key, bbl, units_res FROM act) GROUP BY 1)
SELECT agg.*, units.approx_units
FROM agg JOIN units USING (player_key)
ORDER BY n_deals DESC
LIMIT {N_PLAYERS}
""").df()

players.insert(1, "label", players.player_key.str.split(":", n=1).str[1])
players.insert(2, "grouping", players.player_key.str.split(":", n=1).str[0])
# Groupe par adresse avec beaucoup de noms différents = possible cabinet d'avocats
players["review_flag"] = ""
players.loc[(players.grouping == "ADDR") & (players.n_entity_names > 15),
            "review_flag"] = "adresse partagée par beaucoup d'entités : cabinet / registered agent ?"
players.loc[players.n_buys + players.n_sells > players.n_deals,
            "review_flag"] += " acheteur ET vendeur dans un même deal (transfert interne ?)"
players.to_csv(OUT / "players_top.csv", index=False)

total = con.execute("SELECT count(DISTINCT document_id) FROM tx").fetchone()[0]
keys = "', '".join(k.replace("'", "''") for k in players.player_key)
covered = con.execute(f"""
    SELECT count(DISTINCT document_id) FROM party_map
    WHERE player_key IN ('{keys}')""").fetchone()[0]
print(f"\nTop {len(players)} players : présents dans {covered:,} / {total:,} ventes "
      f"({covered/total:.0%}).")
print(players[["label", "grouping", "n_deals", "n_buys", "n_sells", "n_buildings"]]
      .head(15).to_string(index=False))
print("\n→ Ouvre data/out/players_top.csv, corrige les regroupements évidents"
      "\n  (colonne `label` : mets le vrai nom de l'opérateur si tu le connais),"
      "\n  supprime les lignes non pertinentes, puis : python 04_rank_players.py")
