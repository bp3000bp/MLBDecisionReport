"""
Builds steal-attempt leaderboards from graded steal decisions.

Two levels:
  1. batting_team × game_year  — team season view
  2. runner (runner_id)        — individual player career view

Primary metrics:
  bad_steal_runs_per100  — run value lost per 100 attempts (negative = cost)
  good_steal_rate        — fraction of attempts that were P(safe) > P_be

Run:
    python -m src.eval.steal_leaderboards
"""
import datetime
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
PROC = ROOT / "data" / "processed"

CURRENT_YEAR = datetime.date.today().year
LOW_SAMPLE_ATT = 50    # flag runner-seasons with fewer than this many attempts


def agg_steal_group(g: pd.DataFrame) -> pd.Series:
    good   = g["decision"] == "GOOD_STEAL"
    bad    = g["decision"] == "BAD_STEAL"
    n      = max(len(g), 1)
    n_2b   = (g["base_stolen"] == "2B").sum()
    n_3b   = (g["base_stolen"] == "3B").sum()

    bad_rv = g.loc[bad, "run_value"].sum()
    good_rv= g.loc[good, "run_value"].sum()
    total_rv = g["run_value"].sum()

    return pd.Series({
        "n_attempts":           int(len(g)),
        "n_success":            int(g["is_success"].sum()),
        "n_caught":             int((~g["is_success"]).sum()),
        "n_2b_attempts":        int(n_2b),
        "n_3b_attempts":        int(n_3b),
        "n_good_steal":         int(good.sum()),
        "n_bad_steal":          int(bad.sum()),
        "success_rate":         round(g["is_success"].mean(), 3),
        "good_steal_rate":      round(good.mean(), 3),
        "total_run_value":      round(total_rv, 2),
        "bad_steal_runs":       round(bad_rv, 2),
        "good_steal_runs":      round(good_rv, 2),
        "run_value_per100":     round(total_rv / n * 100, 2),
        "bad_steal_runs_per100":round(bad_rv  / n * 100, 2),
    })


def build_leaderboards() -> None:
    decisions_path = PROC / "steal_decisions.parquet"
    if not decisions_path.exists():
        raise FileNotFoundError(
            "steal_decisions.parquet not found — run src/model/steal_grade.py first"
        )

    dec = pd.read_parquet(decisions_path)
    print(f"Loaded {len(dec):,} graded steal decisions")

    # ── Team × year leaderboard ───────────────────────────────────────────────
    team_grp = dec.groupby(
        ["batting_team", "game_year"],
        group_keys=False,
    )[dec.columns.difference(["batting_team", "game_year"])].apply(agg_steal_group)

    team_lb = team_grp.reset_index()
    team_lb["low_sample"]   = team_lb["n_attempts"] < LOW_SAMPLE_ATT
    team_lb["short_season"] = team_lb["game_year"] == 2020
    team_lb["in_progress"]  = team_lb["game_year"] == CURRENT_YEAR

    team_out_pq  = PROC / "leaderboard_steal_team.parquet"
    team_out_csv = PROC / "leaderboard_steal_team.csv"
    team_lb.to_parquet(team_out_pq, index=False)
    team_lb.to_csv(team_out_csv, index=False)
    print(f"\nTeam steal leaderboard: {len(team_lb)} team-seasons")
    print(team_lb.sort_values("bad_steal_runs_per100").head(10).to_string())

    # ── Runner career leaderboard ─────────────────────────────────────────────
    runner_grp = dec.groupby(
        ["runner_id", "runner_name"],
        group_keys=False,
    )[dec.columns.difference(["runner_id", "runner_name"])].apply(agg_steal_group)

    runner_lb = runner_grp.reset_index()

    # Career stats across years
    runner_lb["seasons"] = (
        dec.groupby("runner_id")["game_year"]
        .nunique()
        .reindex(runner_lb["runner_id"])
        .values
    )

    runner_lb["low_sample"] = runner_lb["n_attempts"] < LOW_SAMPLE_ATT

    runner_out_pq  = PROC / "leaderboard_steal_runner.parquet"
    runner_out_csv = PROC / "leaderboard_steal_runner.csv"
    runner_lb.to_parquet(runner_out_pq, index=False)
    runner_lb.to_csv(runner_out_csv, index=False)

    print(f"\nRunner steal leaderboard: {len(runner_lb)} runners")
    print("\nTop 10 most efficient base-stealers (run_value_per100):")
    top = runner_lb[runner_lb["n_attempts"] >= LOW_SAMPLE_ATT].nlargest(10, "run_value_per100")
    print(top[["runner_name", "n_attempts", "success_rate", "good_steal_rate",
               "run_value_per100", "bad_steal_runs_per100"]].to_string())

    print(f"\nSaved team leaderboard  -> {team_out_csv}")
    print(f"Saved runner leaderboard -> {runner_out_csv}")


if __name__ == "__main__":
    import sys
    sys.path.insert(0, str(ROOT))
    build_leaderboards()
