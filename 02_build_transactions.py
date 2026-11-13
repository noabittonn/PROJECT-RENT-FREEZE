"""Étape 1 bis — Construire la table des ventes d'immeubles résidentiels multifamily.

Filtres : deeds seulement, depuis START_DATE, montant > MIN_AMOUNT,
lot PLUTO en classe C/D avec au moins MIN_RES_UNITS logements.

Sorties :
    data/out/transactions.parquet   une ligne par (document, BBL)
    data/out/parties.parquet        une ligne par partie (buyer/seller) de ces documents
"""
import duckdb
from config import (OUT, START_DATE, DEED_TYPES, MIN_AMOUNT, MIN_RES_UNITS,
                    BLDG_CLASS_PREFIXES)
from common import csv_view, NAME_CLEAN_SQL

OUT.mkdir(parents=True, exist_ok=True)
con = duckdb.connect()

csv_view(con, "acris_master", {
    "document_id": [], "doc_type": [],
    "document_date": ["doc_date"], "document_amt": ["doc_amount"],
    "recorded_datetime": ["recorded_filed"],
})
csv_view(con, "acris_legals", {
    "document_id": [], "borough": [], "block": [], "lot": [],
    "street_number": [], "street_name": [],
})
csv_view(con, "acris_parties", {
    "document_id": [], "party_type": [], "name": [],
    "address_1": [], "city": [], "state": [], "zip": [],
})
csv_view(con, "pluto", {
    "bbl": [], "bldgclass": ["bldg_class"], "unitsres": ["units_res", "resunits"],
    "yearbuilt": ["year_built"], "address": [],
})

deed_list = ", ".join(f"'{d}'" for d in DEED_TYPES)
class_cond = " OR ".join(f"bldgclass LIKE '{p}%'" for p in BLDG_CLASS_PREFIXES)

# Dates ACRIS : '01/31/2015 12:00:00 AM' (export web) ou ISO (API) -> on gère les deux.
date_sql = """coalesce(
    try_strptime(substr({c}, 1, 10), '%m/%d/%Y'),
    try_cast(substr({c}, 1, 10) AS TIMESTAMP))::DATE"""

con.execute(f"""
CREATE OR REPLACE TABLE pluto_mf AS
SELECT try_cast(try_cast(bbl AS DOUBLE) AS BIGINT) AS bbl,
       bldgclass, try_cast(unitsres AS INTEGER) AS units_res,
       try_cast(yearbuilt AS INTEGER) AS year_built, address
FROM pluto
WHERE ({class_cond}) AND try_cast(unitsres AS INTEGER) >= {MIN_RES_UNITS}
""")

con.execute(f"""
CREATE OR REPLACE TABLE deeds AS
SELECT document_id,
       doc_type,
       {date_sql.format(c='document_date')}      AS doc_date,
       {date_sql.format(c='recorded_datetime')}  AS recorded_date,
       try_cast(document_amt AS DOUBLE)          AS amount
FROM acris_master
WHERE doc_type IN ({deed_list})
""")
con.execute(f"""
CREATE OR REPLACE TABLE deeds AS
SELECT *, coalesce(doc_date, recorded_date) AS sale_date
FROM deeds
WHERE coalesce(doc_date, recorded_date) >= DATE '{START_DATE}'
  AND amount >= {MIN_AMOUNT}
""")

con.execute("""
CREATE OR REPLACE TABLE transactions AS
SELECT d.document_id, d.doc_type, d.sale_date, d.amount,
       l.bbl, p.bldgclass, p.units_res, p.year_built, p.address,
       count(*) OVER (PARTITION BY d.document_id) AS n_lots_in_doc
FROM deeds d
JOIN (SELECT DISTINCT document_id,
             try_cast(borough AS BIGINT) * 1000000000
           + try_cast(block AS BIGINT) * 10000
           + try_cast(lot AS BIGINT) AS bbl
      FROM acris_legals) l USING (document_id)
JOIN pluto_mf p USING (bbl)
""")

# party_type : 1 = grantor (vendeur), 2 = grantee (acheteur)
con.execute(f"""
CREATE OR REPLACE TABLE parties AS
SELECT DISTINCT pa.document_id,
       CASE pa.party_type WHEN '1' THEN 'seller' WHEN '2' THEN 'buyer' END AS side,
       {NAME_CLEAN_SQL.format(col='pa.name')}     AS name_clean,
       pa.name                                    AS name_raw,
       {NAME_CLEAN_SQL.format(col='pa.address_1')} AS address_clean,
       left(coalesce(pa.zip, ''), 5)              AS zip
FROM acris_parties pa
WHERE pa.document_id IN (SELECT document_id FROM transactions)
  AND pa.party_type IN ('1', '2')
""")

con.execute(f"COPY transactions TO '{(OUT/'transactions.parquet').as_posix()}' (FORMAT parquet)")
con.execute(f"COPY parties TO '{(OUT/'parties.parquet').as_posix()}' (FORMAT parquet)")
# Versions CSV pour Excel / R sans arrow
con.execute(f"COPY transactions TO '{(OUT/'transactions.csv').as_posix()}' (HEADER)")

print(con.execute("""
SELECT year(sale_date) AS annee,
       count(DISTINCT document_id) AS ventes,
       count(DISTINCT bbl)         AS immeubles,
       round(median(amount)/1e6, 2) AS prix_median_M
FROM transactions GROUP BY 1 ORDER BY 1
""").df().to_string(index=False))
print("\nÉtape suivante : python 03_select_players.py")
