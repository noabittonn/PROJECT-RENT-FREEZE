"""Étape 1 — Télécharger les données (équivalent du `make download` de fitnr/acris-download).

Usage :
    python 01_download.py            # télécharge tout ce qui manque
    python 01_download.py --force    # retélécharge tout

Prévoir ~10-15 Go de disque et du temps (ACRIS Parties est le plus gros fichier).
Si tu as déjà lancé `make download` avec le repo du prof, copie simplement ses CSV
dans data/raw/ sous les noms acris_master.csv, acris_legals.csv, acris_parties.csv.
"""
import sys
import urllib.request
from config import RAW, SOURCES, EXPORT_URL

RAW.mkdir(parents=True, exist_ok=True)
force = "--force" in sys.argv


def progress(blocks, block_size, total):
    done = blocks * block_size / 1e6
    print(f"\r   {done:,.0f} Mo téléchargés", end="", flush=True)


from common import REPO_NAMES

for name, (dataset_id, label) in SOURCES.items():
    dest = RAW / f"{name}.csv"
    repo_files = [RAW / f"{n}.csv" for n in REPO_NAMES.get(name, [])]
    if not force and any(p.exists() for p in repo_files):
        print(f"✓ {name} : fichier du repo fitnr déjà présent")
        continue
    if dest.exists() and not force:
        print(f"✓ {name}.csv déjà présent ({dest.stat().st_size/1e6:,.0f} Mo)")
        continue
    url = EXPORT_URL.format(id=dataset_id)
    print(f"↓ {label}\n   {url}")
    tmp = dest.with_suffix(".part")
    urllib.request.urlretrieve(url, tmp, reporthook=progress)
    tmp.rename(dest)
    print(f"\n✓ {name}.csv ({dest.stat().st_size/1e6:,.0f} Mo)")

print("\nTerminé. Étape suivante : python 02_build_transactions.py")
