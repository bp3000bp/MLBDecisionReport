"""
Pinch Hit Grader — leaderboards.

Aggregates graded pinch hit appearances to:
  - Team × season leaderboard: n_ph, good_ph_rate, avg_woba_gain, run_value_per100

Primary metric: run_value_per100 — expected run value per 100 pinch hit appearances.

Low-sample flag: < 20 pinch hit appearances in a team-season.

Run:
    python -m src.eval.pinch_hit_leaderboards
"""

from pathlib import Path

import pandas as pd
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
PROC = ROOT / "data" / "processed"


def build_leaderboards() -> pd.DataFrame:
    dec_path = PROC / "pinch_hit_decisions.parquet"
    if not dec_path.exists():
        raise FileNotFoundError(
            "pinch_hit_decisions.parquet not found — run src/model/pinch_hit_grade.py first"
        )
    df = pd.read_parquet(dec_path)

    team_lb = (
        df.groupby(["batting_team", "game_year"])
        .agg(
            n_ph=("decision", "count"),
            n_good=("decision", lambda x: (x == "GOOD_PH").sum()),
            total_run_value=("run_value", "sum"),
            avg_woba_gain=("woba_gain", "mean"),
            avg_leverage_weight=("leverage_weight", "mean"),
        )
        .reset_index()
    )
    team_lb["good_ph_rate"] = team_lb["n_good"] / team_lb["n_ph"]
    team_lb["run_value_per100"] = team_lb["total_run_value"] / team_lb["n_ph"] * 100
    team_lb["low_sample"] = team_lb["n_ph"] < 20
    team_lb["short_season"] = team_lb["game_year"] == 2020

    team_lb = team_lb.sort_values("run_value_per100", ascending=False)

    out_path = PROC / "leaderboard_pinch_hit_team.csv"
    team_lb.round(4).to_csv(out_path, index=False)
    print(f"Saved {len(team_lb):,} team-seasons -> {out_path}")
    return team_lb


if __name__ == "__main__":
    import sys
    sys.path.insert(0, str(ROOT))
    build_leaderboards()
