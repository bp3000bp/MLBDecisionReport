"""
Builds the IBB team-year leaderboard from graded IBB decisions.

Graded from the FIELDING TEAM's perspective (they called the IBB).

Primary metric: run_value_per100
  - Positive = IBBs added value on net (matchup gains exceeded RE cost)
  - Negative = IBBs cost expected runs on net (common — most IBBs have limited value)

Low sample flag: < 20 IBBs in a team-season.

Saves:
  data/processed/leaderboard_ibb_team.csv
  data/processed/leaderboard_ibb_team.parquet

Run (from repo root):
    python src/eval/ibb_leaderboards.py
"""
import sys
import datetime
from pathlib import Path

import pandas as pd

CURRENT_YEAR = datetime.date.today().year

ROOT = Path(__file__).resolve().parents[2]
PROC = ROOT / "data" / "processed"
sys.path.insert(0, str(ROOT))

LOW_SAMPLE_IBB = 20


def build_ibb_leaderboards() -> pd.DataFrame:
    print("Loaded IBB decisions...")
    decisions = pd.read_parquet(PROC / "ibb_decisions.parquet")
    print(f"  {len(decisions):,} graded IBB decisions")

    # ── Team-year leaderboard ─────────────────────────────────────────────
    def _agg(g: pd.DataFrame) -> pd.Series:
        n        = len(g)
        good     = (g["decision"] == "GOOD_IBB")
        bad      = (g["decision"] == "BAD_IBB")
        total_rv = g["run_value"].sum()
        bad_rv   = g.loc[bad, "run_value"].sum()   # negative number

        return pd.Series({
            "n_ibb":               n,
            "n_good_ibb":          int(good.sum()),
            "n_bad_ibb":           int(bad.sum()),
            "good_ibb_rate":       round(good.sum() / max(n, 1), 3),
            "avg_re_cost":         round(g["re_cost"].mean(), 3),
            "avg_batter_woba":     round(g["batter_woba_adj"].mean(), 3),
            "avg_next_woba":       round(g["next_woba_adj"].mean(), 3),
            "total_run_value":     round(total_rv, 2),
            "bad_ibb_runs":        round(abs(bad_rv), 2),
            "run_value_per100":    round(total_rv / max(n, 1) * 100, 2),
            "bad_ibb_runs_per100": round(abs(bad_rv) / max(n, 1) * 100, 2),
        })

    lb = (
        decisions
        .groupby(["fielding_team", "game_year"], group_keys=False)
        [decisions.columns.difference(["fielding_team", "game_year"])]
        .apply(_agg)
        .reset_index()
    )

    lb["low_sample"]  = lb["n_ibb"] < LOW_SAMPLE_IBB
    lb["short_season"] = lb["game_year"] == 2020
    lb["in_progress"] = lb["game_year"] == CURRENT_YEAR

    lb = lb.sort_values("run_value_per100", ascending=False)

    out_pq  = PROC / "leaderboard_ibb_team.parquet"
    out_csv = PROC / "leaderboard_ibb_team.csv"
    lb.to_parquet(out_pq, index=False)
    lb.to_csv(out_csv, index=False)
    print(f"IBB team leaderboard ({len(lb)} rows) -> {out_csv.name}")

    key = ["fielding_team", "game_year", "n_ibb", "good_ibb_rate",
           "run_value_per100", "total_run_value", "low_sample"]

    print("\n=== IBB TEAM-YEAR LEADERBOARD ===")
    print("\nTop 10 (best IBB decisions, highest run value per 100):")
    print(lb.head(10)[key].to_string(index=False))
    print("\nBottom 10 (worst IBB decisions, lowest run value per 100):")
    print(lb.tail(10)[key].to_string(index=False))

    n_low = lb["low_sample"].sum()
    if n_low:
        print(f"\n  ({n_low} team-seasons flagged low_sample < {LOW_SAMPLE_IBB} IBBs)")

    return lb


if __name__ == "__main__":
    build_ibb_leaderboards()
