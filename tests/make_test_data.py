"""Crée de FAUSSES données au format des exports NYC Open Data, pour vérifier que
toute la chaîne tourne (sans rien télécharger). Aucune valeur n'est réelle.

    RFL_DATA=tests/data python tests/make_test_data.py
    RFL_DATA=tests/data python 02_build_transactions.py
    RFL_DATA=tests/data python 03_select_players.py
    RFL_DATA=tests/data python tests/fake_ranking.py
    RFL_DATA=tests/data python 04_rank_players.py --import tests/data/out/fake_ranking.json
    RFL_DATA=tests/data python 05_plot.py --demo
"""
import json, os, random, sys
from pathlib import Path
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from config import RAW, OUT

random.seed(1)
RAW.mkdir(parents=True, exist_ok=True); OUT.mkdir(parents=True, exist_ok=True)

lots = [(b, random.randint(1, 3000), random.randint(1, 80)) for b in range(1, 6) for _ in range(800)]
lots = list(dict.fromkeys(lots))
pluto = pd.DataFrame({
    "borough": [["MN","BX","BK","QN","SI"][b-1] for b,_,_ in lots],
    "block": [k for _,k,_ in lots], "lot": [l for _,_,l in lots],
    "bbl": [f"{b*1_000_000_000 + k*10_000 + l}.00000000" for b,k,l in lots],
    "bldgclass": random.choices(["C1","C4","D1","D7","A1","R4"], k=len(lots)),
    "unitsres": [random.randint(2, 120) for _ in lots],
    "yearbuilt": [random.randint(1900, 2010) for _ in lots],
    "address": [f"{random.randint(1,999)} FAKE STREET" for _ in lots],
})
pluto.to_csv(RAW / "pluto.csv", index=False)

operators = [f"OPERATOR {i:03d}" for i in range(250)]
op_weight = [1 / (i + 1) ** 0.9 for i in range(250)]        # quelques gros, beaucoup de petits
op_addr = {o: (f"{random.randint(1,999)} BROADWAY", f"{random.randint(10001,11699)}") for o in operators}
llc_of = {o: [f"{random.randint(1,999)} {o.split()[1]} REALTY LLC {j}" for j in range(6)] for o in operators}

master, legals, parties = [], [], []
for i in range(9000):
    doc = f"FT_{i:010d}"
    d = pd.Timestamp("2010-01-01") + pd.Timedelta(days=random.randint(0, 6100))
    b, k, l = random.choice(lots)
    master.append({"DOCUMENT ID": doc, "RECORD TYPE": "A", "CRFN": i,
                   "RECORDED BOROUGH": b,
                   "DOC. TYPE": random.choices(["DEED", "MTGE", "DEEDO", "SAT"], [5, 3, 1, 2])[0],
                   "DOCUMENT DATE": d.strftime("%m/%d/%Y"),
                   "DOCUMENT AMT": random.choice([0, 10, random.randint(500_000, 40_000_000)]),
                   "RECORDED / FILED": (d + pd.Timedelta(days=20)).strftime("%m/%d/%Y 12:00:00 AM")})
    legals.append({"DOCUMENT ID": doc, "RECORD TYPE": "L", "BOROUGH": b, "BLOCK": k, "LOT": l,
                   "PROPERTY TYPE": "AP", "STREET NUMBER": "1", "STREET NAME": "FAKE ST"})
    seller, buyer = random.choices(operators, op_weight, k=2)
    for side, op in (("1", seller), ("2", buyer)):
        addr, z = op_addr[op]
        parties.append({"DOCUMENT ID": doc, "RECORD TYPE": "P", "PARTY TYPE": side,
                        "NAME": random.choice(llc_of[op]), "ADDRESS 1": addr,
                        "ADDRESS 2": "", "COUNTRY": "US", "CITY": "NEW YORK",
                        "STATE": "NY", "ZIP": z})
parties.append({"DOCUMENT ID": "FT_0000000001", "RECORD TYPE": "P", "PARTY TYPE": "2",
                "NAME": "BIG BANK N.A.", "ADDRESS 1": "1 WALL ST", "ZIP": "10005"})
pd.DataFrame(master).to_csv(RAW / "acris_master.csv", index=False)
pd.DataFrame(legals).to_csv(RAW / "acris_legals.csv", index=False)
pd.DataFrame(parties).to_csv(RAW / "acris_parties.csv", index=False)

contacts = []
for n, o in enumerate(operators[:60]):           # 60 opérateurs retrouvés dans HPD
    for j, llc in enumerate(llc_of[o]):
        rid = n * 10 + j
        contacts += [
            {"RegistrationContactID": len(contacts), "RegistrationID": rid, "Type": "CorporateOwner",
             "CorporationName": llc, "FirstName": "", "LastName": ""},
            {"RegistrationContactID": len(contacts)+1, "RegistrationID": rid, "Type": "HeadOfficer",
             "CorporationName": "", "FirstName": "JOHN", "LastName": f"DOE{n:03d}"},
            {"RegistrationContactID": len(contacts)+2, "RegistrationID": rid, "Type": "Agent",
             "CorporationName": f"{o} MGMT CORP", "FirstName": "", "LastName": ""}]
pd.DataFrame(contacts).to_csv(RAW / "hpd_contacts.csv", index=False)
print("Fausses données écrites dans", RAW)
