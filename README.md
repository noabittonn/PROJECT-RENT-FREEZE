# Rent freeze — qualité des acheteurs vs vendeurs (plan du Prof. Cohen)

Ce dossier implémente les 5 étapes dictées par le prof :

| Étape du prof | Script | Sortie |
|---|---|---|
| 1-3. Cloner fitnr/acris-download, lire le README, télécharger les données | repo du prof (`make download`) ; `01_download.py` complète avec PLUTO et HPD | CSV dans `data/raw/` |
| 4. Caractériser les données, format facile pour Python/R | `00_describe_data.py`, `02_build_transactions.py` | `ACRIS_characterization.md`, `transactions.parquet` / `.csv` |
| Graphique — sous-échantillon des gros acteurs, quelques dizaines à 100 max | `03_select_players.py` | `players_top.csv` |
| Graphique — Claude classe les acteurs (jugement + mémoire) avec une note | `04_rank_players.py` + `prompts/ranking_v1.md` | `players_ranked.csv` |
| Graphique — série temporelle qualité moyenne buyer / seller depuis 2010, avec élections et freezes | `05_plot.py` | `buyer_seller_quality.png` |

## Installation

```bash
pip install duckdb pandas matplotlib anthropic tabulate
```

## Lancer

```bash
# Dans le dossier acris-download (repo du prof) :
make download                  # garde les CSV ; long (plusieurs heures)
# copier data/real_property_*.csv et data/document_control_codes.csv
# du repo vers rent_freeze_landlords/data/raw/, puis ici :
python 01_download.py          # ne télécharge que ce qui manque (PLUTO, HPD)
python 00_describe_data.py     # caractérisation des données (étape 4 du prof)
python 02_build_transactions.py
python 03_select_players.py
#   -> relire data/out/players_top.csv (voir plus bas)
python 04_rank_players.py      # avec ANTHROPIC_API_KEY
#   ou sans clé API : python 04_rank_players.py --manual  (puis --import)
python 05_plot.py              # options : --freq half  --weight units
```

**Sur Windows**, `make` n'existe pas par défaut : saute la ligne `make download` et lance
seulement `python 01_download.py`, qui télécharge exactement les mêmes fichiers (mêmes
adresses que le Makefile du repo).

Attention : utilise `make download` et pas seulement `make sqlite` : le Makefile
considère les CSV comme intermédiaires et peut les effacer après chargement dans la base.

Si tu as déjà téléchargé les données avec le repo fitnr (`make download`), copie simplement
ses CSV `real_property_master.csv`, `real_property_legals.csv`, `real_property_parties.csv`
dans `data/raw/` : les scripts reconnaissent ses noms de fichiers et de colonnes.
(Sinon, `01_download.py` les télécharge sous les noms
`acris_master.csv`, `acris_legals.csv`, `acris_parties.csv`.)

**Avec Claude Code** (comme le prof l'a suggéré) : ouvre Claude Code dans ce dossier et
demande « lance le pipeline étape par étape et montre-moi les sorties ».

## Choix faits (et pourquoi)

- **Échantillon** : deeds (`DEED`, `DEEDO`) depuis 2010, montant ≥ 250 000 $ pour enlever
  les transferts nominaux, lots PLUTO en classe C ou D avec ≥ 6 logements (seuil de la
  rent stabilization). Tout est réglable dans `config.py`.
- **Regroupement des LLC** : c'est le vrai piège. Les noms ACRIS sont des LLC, donc on
  regroupe (1) via le head officer HPD de la LLC, sinon (2) via l'adresse postale commune
  dans ACRIS, sinon (3) le nom. Banques, referees, ville, HDFC, successions sont exclus.
- **Ranking** : le prompt impose `score: null` si Claude ne reconnaît pas l'acteur, une
  confiance, une note explicative, et ne note jamais à partir d'un nom de LLC.
- **Graphique** : moyenne des scores des acheteurs et des vendeurs notés, par année,
  pondérée par nombre de ventes (ou d'unités). Le panneau du bas montre combien de
  ventes ont un acheteur / vendeur noté : si c'est faible une année, le point est fragile.

## Relecture manuelle de `players_top.csv` (1-2 h, indispensable)

- Corriger `label` quand tu reconnais l'opérateur (ça aide beaucoup le ranking).
- Les lignes `review_flag` « adresse partagée » peuvent être un cabinet d'avocats qui
  regroupe des propriétaires sans lien : les supprimer ou les scinder.
- Supprimer ce qui n'est pas un landlord (promoteurs condo purs, institutions).

## Limites à dire au prof

1. Le score est **statique** : la réputation actuelle est appliquée à toute la période,
   donc la courbe ne bouge que par **changement de composition** des acheteurs/vendeurs.
2. **Biais de notoriété** : Claude connaît mieux les mauvais landlords (presse), donc les
   « unknown » ne sont pas aléatoires.
3. HPD registrations = situation **actuelle** : des vendeurs sortis du marché depuis
   longtemps ne sont pas retrouvés et passent par le regroupement par adresse.
4. 2026 est une **année partielle**.

Prochaine étape naturelle : valider le ranking en le comparant aux violations HPD par
unité des immeubles de chaque acteur et à la liste « Worst Landlords » du Public Advocate.

## Tester sans données réelles

```bash
export RFL_DATA=tests/data
python tests/make_test_data.py
python 02_build_transactions.py && python 03_select_players.py
python tests/fake_ranking.py && python 04_rank_players.py --import tests/data/out/fake_ranking.json
python 05_plot.py --demo
```
Les données de test sont **fictives** : elles servent uniquement à vérifier que le code tourne.
