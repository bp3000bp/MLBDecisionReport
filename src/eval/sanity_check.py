"""
Sanity check for the send/hold grading model. Two checks:

1. EXTERNAL (if data/reference/br_baserunning_xbt.csv exists):
   Spearman rho between our team send_rate and BR's XBT% (extra bases taken %).
   Positive rho = our aggressive teams match BR's aggressive teams.

2. INTERNAL — year-over-year send_rate stability:
   If send_rate reflects real coaching philosophy (not noise), a team's send_rate
   in year Y should predict year Y+1 (coaches don't change philosophy overnight).
   Tests consecutive year pairs: 2020-21, 2021-22, 2022-23, 2023-24.
   Expected rho: 0.3-0.6 if metric is stable; near-zero would indicate noise.

3. INTERNAL — safe_rate vs send_rate (structural check):
   Conservative coaches hold except in obvious situations -> slightly higher safe_rate.
   Aggressive coaches send in marginal situations -> slightly lower safe_rate.
   Expected rho: slightly negative. Near-zero also acceptable (all situations viable).

Prints all results. Saves joined correlation table if external data available.

External data: data/reference/br_baserunning_xbt.csv
  Columns: team_br (full BR name), game_year (int), xbt_pct (float 0-1)
  Can be built by the agent that fetches BR team baserunning stats.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

ROOT = Path(__file__).resolve().parents[2]
PROC = ROOT / "data" / "processed"
REF  = ROOT / "data" / "reference"

LOW_SAMPLE = 100   # flag team-years with fewer than this many opportunities

# Full BR team name -> Statcast 3-letter code
BR_NAME_TO_CODE = {
    "Arizona Diamondbacks":   "AZ",
    "Atlanta Braves":         "ATL",
    "Baltimore Orioles":      "BAL",
    "Boston Red Sox":         "BOS",
    "Chicago Cubs":           "CHC",
    "Chicago White Sox":      "CWS",
    "Cincinnati Reds":        "CIN",
    "Cleveland Guardians":    "CLE",
    "Cleveland Indians":      "CLE",
    "Colorado Rockies":       "COL",
    "Detroit Tigers":         "DET",
    "Houston Astros":         "HOU",
    "Kansas City Royals":     "KC",
    "Los Angeles Angels":     "LAA",
    "Los Angeles Dodgers":    "LAD",
    "Miami Marlins":          "MIA",
    "Milwaukee Brewers":      "MIL",
    "Minnesota Twins":        "MIN",
    "New York Mets":          "NYM",
    "New York Yankees":       "NYY",
    "Oakland Athletics":      "ATH",
    "Athletics":              "ATH",
    "Philadelphia Phillies":  "PHI",
    "Pittsburgh Pirates":     "PIT",
    "San Diego Padres":       "SD",
    "Seattle Mariners":       "SEA",
    "San Francisco Giants":   "SF",
    "St. Louis Cardinals":    "STL",
    "Tampa Bay Rays":         "TB",
    "Texas Rangers":          "TEX",
    "Toronto Blue Jays":      "TOR",
    "Washington Nationals":   "WSH",
}


def _rho(a: pd.Series, b: pd.Series, label: str) -> float:
    rho, p = spearmanr(a, b)
    stars = "***" if p < 0.001 else ("**" if p < 0.01 else ("*" if p < 0.05 else ""))
    print(f"  {label:55s}  rho={rho:+.3f}  p={p:.4f} {stars}")
    return rho


def check_external(lb: pd.DataFrame) -> None:
    xbt_path = REF / "br_baserunning_xbt.csv"
    if not xbt_path.exists():
        print("  [SKIP] data/reference/br_baserunning_xbt.csv not found.")
        print("         Build it from Baseball Reference team baserunning pages (XBT% column).")
        print("         Format: team_br,game_year,xbt_pct")
        return

    xbt = pd.read_csv(xbt_path)
    xbt["team"] = xbt["team_br"].map(BR_NAME_TO_CODE)
    missing = xbt[xbt["team"].isna()]["team_br"].unique()
    if len(missing):
        print(f"  WARN: unmapped BR names: {missing}")
        xbt = xbt.dropna(subset=["team"])

    joined = lb.merge(xbt[["team", "game_year", "xbt_pct"]],
                      left_on=["batting_team", "game_year"],
                      right_on=["team", "game_year"],
                      how="inner")

    # Exclude small samples before correlating
    full = joined[joined["n_opportunities"] >= LOW_SAMPLE]
    print(f"\n  {len(full)} team-years (>= {LOW_SAMPLE} opp) joined to BR XBT%")

    _rho(full["send_rate"],           full["xbt_pct"], "send_rate vs XBT%")
    _rho(full["bad_hold_runs_per100"], full["xbt_pct"], "bad_hold_runs_per100 vs XBT%")

    # Rank comparison: top/bottom 10 by our metric vs their XBT rank
    full = full.copy()
    full["our_rank"] = full["send_rate"].rank(ascending=False).astype(int)
    full["xbt_rank"] = full["xbt_pct"].rank(ascending=False).astype(int)
    full["rank_diff"] = (full["our_rank"] - full["xbt_rank"]).abs()
    full = full.sort_values("send_rate", ascending=False)

    print("\n  Top 15 by our send_rate vs XBT% rank:")
    cols = ["batting_team", "game_year", "send_rate", "our_rank", "xbt_pct", "xbt_rank", "rank_diff"]
    print(full.head(15)[cols].to_string(index=False))
    print("\n  Bottom 10 (most conservative) vs XBT% rank:")
    print(full.tail(10)[cols].to_string(index=False))

    gaps = full[full["rank_diff"] > 30]
    if len(gaps):
        print(f"\n  {len(gaps)} outliers (rank gap > 30) — review these:")
        print(gaps[cols].to_string(index=False))

    full.to_csv(PROC / "sanity_external.csv", index=False)
    print(f"\n  Saved joined table -> data/processed/sanity_external.csv")


def check_yoy_stability(lb: pd.DataFrame) -> None:
    """Year-over-year send_rate Spearman correlation (same team, consecutive seasons)."""
    pairs = [(2020, 2021), (2021, 2022), (2022, 2023), (2023, 2024)]
    rhos = []
    for y1, y2 in pairs:
        a = lb[lb["game_year"] == y1][["batting_team", "send_rate"]].rename(
            columns={"send_rate": "sr_y1"})
        b = lb[lb["game_year"] == y2][["batting_team", "send_rate"]].rename(
            columns={"send_rate": "sr_y2"})
        merged = a.merge(b, on="batting_team")
        if len(merged) < 5:
            print(f"  {y1}-{y2}: only {len(merged)} matched teams, skipping")
            continue
        rho = _rho(merged["sr_y1"], merged["sr_y2"],
                   f"send_rate {y1} vs {y2}  (n={len(merged)})")
        rhos.append(rho)

    if rhos:
        print(f"\n  Mean year-over-year rho: {np.mean(rhos):+.3f}")
        print("  Interpretation: >0.35 = stable metric (real coaching signal); "
              "near-zero = mostly noise")


def check_send_vs_safe(lb: pd.DataFrame) -> None:
    """
    Correlate send_rate vs safe_rate.
    Conservative coaches select only obvious sends -> slightly higher safe_rate.
    Aggressive coaches send in marginal situations -> slightly lower safe_rate.
    Structural finding: all bins have P(safe) >= 0.947, so we expect weak negative rho.
    """
    full = lb[lb["n_opportunities"] >= LOW_SAMPLE]
    _rho(full["send_rate"], full["safe_rate"],
         f"send_rate vs safe_rate  (n={len(full)})")
    print("  Expected: slight negative (aggressive = slightly lower actual safe rate).")
    print("  Near-zero also ok — all bins are high P(safe) regardless.")


def run() -> None:
    lb = pd.read_csv(PROC / "leaderboard_team.csv")

    print(f"\n{'='*68}")
    print("SANITY CHECK 1 — External: send_rate vs Baseball Reference XBT%")
    print(f"{'='*68}")
    check_external(lb)

    print(f"\n{'='*68}")
    print("SANITY CHECK 2 — Internal: year-over-year send_rate stability")
    print(f"{'='*68}")
    print("  If send_rate reflects coaching philosophy, it should be consistent")
    print("  year-over-year for the same team (same coach = same tendency).")
    check_yoy_stability(lb)

    print(f"\n{'='*68}")
    print("SANITY CHECK 3 — Structural: send_rate vs actual safe_rate")
    print(f"{'='*68}")
    check_send_vs_safe(lb)

    print(f"\n{'='*68}")
    print("NOTABLE CASES — spot checks against known teams")
    print(f"{'='*68}")
    cases = {
        "COL": "Coors Field -> expect low bad_hold_runs_per100 (most aggressive)",
        "SEA": "Expected over-holder based on leaderboard (2022+2023 top 10)",
        "ATL": "Snitker-era Braves known for aggressive running (2022-2024)",
    }
    for team, note in cases.items():
        rows = lb[lb["batting_team"] == team][
            ["batting_team", "game_year", "send_rate", "bad_hold_runs_per100", "n_opportunities"]
        ].sort_values("game_year")
        print(f"\n  {team} — {note}")
        print(rows.to_string(index=False))


if __name__ == "__main__":
    sys.path.insert(0, str(ROOT))
    run()
