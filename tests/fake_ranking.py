"""Génère un ranking ALÉATOIRE pour tester 05_plot.py (aucune valeur réelle)."""
import json, random, sys
from pathlib import Path
import pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from config import OUT
random.seed(2)
p = pd.read_csv(OUT / "players_top.csv")
res = [{"player_key": k, "identified_as": "simulated",
        "score": None if random.random() < 0.3 else random.randint(1, 5),
        "confidence": "low", "note": "simulated"} for k in p.player_key]
json.dump(res, open(OUT / "fake_ranking.json", "w"))
print("fake_ranking.json écrit")
