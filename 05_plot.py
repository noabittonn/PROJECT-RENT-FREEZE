"""Étape 5 — Qualité moyenne des acheteurs et des vendeurs, 2010 → aujourd'hui,
avec les élections, les rent freezes et HSTPA en repères.

Usage :
    python 05_plot.py                    # par année, pondéré par nombre de ventes
    python 05_plot.py --freq half        # par semestre
    python 05_plot.py --weight units     # pondéré par nombre de logements

Sorties : data/out/buyer_seller_quality.png / .csv
"""
import sys
import duckdb
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from config import OUT, EVENTS

freq = sys.argv[sys.argv.index("--freq") + 1] if "--freq" in sys.argv else "year"
weight = sys.argv[sys.argv.index("--weight") + 1] if "--weight" in sys.argv else "deals"
demo = "--demo" in sys.argv

con = duckdb.connect()
con.execute(f"CREATE TABLE tx AS SELECT * FROM '{(OUT/'transactions.parquet').as_posix()}'")
con.execute(f"CREATE TABLE pm AS SELECT * FROM '{(OUT/'party_player_map.parquet').as_posix()}'")
con.register("ranked", pd.read_csv(OUT / "players_ranked.csv")[["player_key", "score"]])

# Une ligne par vente : score moyen des acheteurs notés, des vendeurs notés.
deals = con.execute("""
WITH d AS (
    SELECT document_id, min(sale_date) AS sale_date, sum(units_res) AS units
    FROM tx GROUP BY 1),
s AS (
    SELECT pm.document_id, pm.side, avg(r.score) AS score
    FROM (SELECT DISTINCT document_id, side, player_key FROM pm) pm
    JOIN ranked r USING (player_key)
    WHERE r.score IS NOT NULL
    GROUP BY 1, 2)
SELECT d.*,
       max(s.score) FILTER (WHERE s.side = 'buyer')  AS buyer_score,
       max(s.score) FILTER (WHERE s.side = 'seller') AS seller_score
FROM d LEFT JOIN s USING (document_id)
GROUP BY ALL
""").df()

deals["sale_date"] = pd.to_datetime(deals.sale_date)
deals["period"] = (deals.sale_date.dt.to_period("Y") if freq == "year" else
                   deals.sale_date.dt.to_period("Q").map(
                       lambda p: pd.Period(f"{p.year}-{1 if p.quarter <= 2 else 7:02d}", "M")))
deals["w"] = deals.units.fillna(1) if weight == "units" else 1.0


def wmean(g, col):
    m = g[col].notna()
    return (g.loc[m, col] * g.loc[m, "w"]).sum() / g.loc[m, "w"].sum() if m.any() else float("nan")


series = deals.groupby("period").apply(lambda g: pd.Series({
    "buyer_quality":  wmean(g, "buyer_score"),
    "seller_quality": wmean(g, "seller_score"),
    "n_deals": len(g),
    "n_buyer_rated":  g.buyer_score.notna().sum(),
    "n_seller_rated": g.seller_score.notna().sum(),
}), include_groups=False).reset_index()
series["date"] = series.period.dt.to_timestamp(how="start") + (
    pd.DateOffset(months=6) if freq == "year" else pd.DateOffset(months=3))
series.drop(columns="date").assign(period=series.period.astype(str)).to_csv(
    OUT / "buyer_seller_quality.csv", index=False)

# ---------------------------------------------------------------- figure
fig, (ax, axn) = plt.subplots(2, 1, figsize=(12, 7), sharex=True,
                              gridspec_kw={"height_ratios": [3, 1]})
ax.plot(series.date, series.buyer_quality, "o-", color="#1f6f8b", lw=2, label="Buyers")
ax.plot(series.date, series.seller_quality, "s--", color="#c0392b", lw=2, label="Sellers")
ax.set_ylabel("Average landlord quality\n(1 = worst, 5 = best)")
ax.set_ylim(1, 5)
ax.grid(alpha=0.3)

style = {"election": ("#7f8c8d", ":"), "freeze": ("#27ae60", "-"), "law": ("#8e44ad", "-.")}
for i, (d, label, kind) in enumerate(EVENTS):
    color, ls = style[kind]
    for a in (ax, axn):
        a.axvline(pd.Timestamp(d), color=color, ls=ls, lw=1.2, alpha=0.8)
    ax.text(pd.Timestamp(d), 4.95 - 0.28 * (i % 3), " " + label, rotation=0,
            fontsize=8, color=color, va="top")

axn.bar(series.date, series.n_buyer_rated, width=120 if freq == "year" else 60,
        color="#1f6f8b", alpha=0.6, label="Rated buyers")
axn.bar(series.date, series.n_seller_rated, width=120 if freq == "year" else 60,
        bottom=series.n_buyer_rated, color="#c0392b", alpha=0.5, label="Rated sellers")
axn.set_ylabel("Rated deals")
axn.legend(loc="upper left", fontsize=8, frameon=False)
axn.xaxis.set_major_locator(mdates.YearLocator())
axn.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))

from matplotlib.lines import Line2D
handles = ax.get_legend_handles_labels()[0] + [
    Line2D([], [], color=style["freeze"][0], ls="-", label="Rent freeze (RGB vote)"),
    Line2D([], [], color=style["election"][0], ls=":", label="Mayoral election"),
    Line2D([], [], color=style["law"][0], ls="-.", label="HSTPA 2019")]
ax.legend(handles=handles, loc="lower left", fontsize=8, ncol=5, frameon=False)
w = "units" if weight == "units" else "number of sales"
ax.set_title("NYC multifamily sales: average landlord quality of buyers vs. sellers"
             f"\nTop players by activity, rated by LLM; weighted by {w}", fontsize=12)
if demo:
    fig.text(0.5, 0.55, "SIMULATED DATA — CODE TEST ONLY", ha="center", va="center",
             fontsize=34, color="red", alpha=0.25, rotation=20, weight="bold")
fig.tight_layout()
fig.savefig(OUT / "buyer_seller_quality.png", dpi=200)
print(series[["period", "buyer_quality", "seller_quality", "n_deals",
              "n_buyer_rated", "n_seller_rated"]].assign(period=series.period.astype(str))
      .round(2).to_string(index=False))
print(f"\n✓ {OUT/'buyer_seller_quality.png'}")
