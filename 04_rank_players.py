"""Étape 4 — Faire classer les players par Claude (jugement + mémoire), avec une note.

Deux façons de faire :
  A) Automatique (clé API Anthropic dans ANTHROPIC_API_KEY) :
        python 04_rank_players.py
  B) À la main / Claude Code (pas de clé API) :
        python 04_rank_players.py --manual
     -> écrit data/out/ranking_prompt_filled.md ; colle-le dans Claude, puis
        enregistre la réponse JSON dans data/out/ranking_response.json et lance
        python 04_rank_players.py --import data/out/ranking_response.json

Sortie : data/out/players_ranked.csv (score 1-5 ou vide si inconnu, + note).
"""
import json
import re
import sys
from datetime import datetime
import pandas as pd
from config import OUT, PROMPT_FILE, PROMPT_VERSION, LLM_MODEL

BATCH = 25
players = pd.read_csv(OUT / "players_top.csv")
template = PROMPT_FILE.read_text(encoding="utf-8")

FIELDS = ["player_key", "label", "sample_names", "main_address", "managing_agent",
          "n_deals", "n_buys", "n_sells", "n_buildings", "boroughs",
          "first_year", "last_year"]


def fill(df: pd.DataFrame) -> str:
    rows = df[[c for c in FIELDS if c in df.columns]].fillna("").to_dict("records")
    return template.replace("{{PLAYERS}}", json.dumps(rows, ensure_ascii=False, indent=1))


def parse(text: str) -> list:
    text = re.sub(r"```(json)?", "", text).strip()
    start, end = text.find("["), text.rfind("]")
    return json.loads(text[start:end + 1])


def save(results: list, source: str) -> None:
    res = pd.DataFrame(results)
    res["score"] = pd.to_numeric(res.get("score"), errors="coerce")
    out = players.merge(res, on="player_key", how="left")
    out["prompt_version"], out["model"] = PROMPT_VERSION, source
    out["ranked_at"] = datetime.now().isoformat(timespec="seconds")
    out.to_csv(OUT / "players_ranked.csv", index=False)
    known = out.score.notna().sum()
    print(f"✓ players_ranked.csv : {known}/{len(out)} players notés, "
          f"{len(out)-known} 'unknown'.")
    print(out.loc[out.score.notna(), ["label", "identified_as", "score", "confidence"]]
          .sort_values("score").to_string(index=False))
    print("\nÉtape suivante : python 05_plot.py")


if "--manual" in sys.argv:
    path = OUT / "ranking_prompt_filled.md"
    path.write_text(fill(players), encoding="utf-8")
    print(f"Prompt écrit dans {path}. Colle-le dans Claude, enregistre la réponse "
          f"dans {OUT/'ranking_response.json'}, puis :\n"
          f"python 04_rank_players.py --import {OUT/'ranking_response.json'}")
elif "--import" in sys.argv:
    f = sys.argv[sys.argv.index("--import") + 1]
    save(parse(open(f, encoding="utf-8").read()), source="manual")
else:
    import anthropic
    client = anthropic.Anthropic()
    results = []
    for i in range(0, len(players), BATCH):
        batch = players.iloc[i:i + BATCH]
        msg = client.messages.create(
            model=LLM_MODEL, max_tokens=8000, temperature=0,
            messages=[{"role": "user", "content": fill(batch)}])
        text = "".join(b.text for b in msg.content if b.type == "text")
        results += parse(text)
        print(f"  lot {i//BATCH + 1} : {len(batch)} players "
              f"({msg.usage.input_tokens} in / {msg.usage.output_tokens} out tokens)")
    (OUT / "ranking_raw.json").write_text(json.dumps(results, ensure_ascii=False, indent=1))
    save(results, source=LLM_MODEL)
