"""
Grades every intentional walk decision and produces a summary.

Grade logic:
  GOOD_IBB : run_value > 0  — IBB saved expected runs on net
  BAD_IBB  : run_value <= 0 — IBB cost expected runs on net

run_value = (batter_wOBA - next_wOBA) / WOBA_SCALE - re_cost
  where re_cost = (RE_after - RE_before) + immediate_runs_forced_in

Positive run_value means the matchup advantage of bypassing the current batter
(relative to the on-deck hitter) exceeded the run-expectancy price of the IBB.
Negative run_value means the IBB wasn't worth the RE cost.

Input:  data/processed/ibb_opportunities.parquet
Output: data/processed/ibb_decisions.parquet

Run (from repo root):
    python src/model/ibb_grade.py
"""
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
PROC = ROOT / "data" / "processed"
sys.path.insert(0, str(ROOT))


def build_ibb_decisions() -> pd.DataFrame:
    print("Loading IBB opportunity table...")
    opps = pd.read_parquet(PROC / "ibb_opportunities.parquet")
    print(f"  {len(opps):,} IBB events")

    opps["decision"] = opps["run_value"].apply(
        lambda v: "GOOD_IBB" if v > 0 else "BAD_IBB"
    )

    breakdown = opps["decision"].value_counts()
    n_total   = len(opps)
    n_good    = (opps["decision"] == "GOOD_IBB").sum()
    good_rate = n_good / n_total

    print(f"\nDecision breakdown:")
    print(breakdown.to_string())
    print(f"\nGood IBB rate: {good_rate:.1%}")
    print(f"Mean run value per IBB: {opps['run_value'].mean():+.4f}")
    print(f"Mean RE cost per IBB  : {opps['re_cost'].mean():+.4f}")

    # Base-state distribution for context
    print("\nBase state when IBB issued (% of total):")
    states = (
        opps.assign(
            state=opps["occ_1b"].astype(str) + opps["occ_2b"].astype(str) + opps["occ_3b"].astype(str)
        )
        .groupby("state").size()
        .sort_values(ascending=False)
    )
    for state, cnt in states.items():
        label = {
            "000": "Bases empty", "001": "Runner on 3B", "010": "Runner on 2B",
            "011": "Runners on 2B+3B", "100": "Runner on 1B",
            "101": "Runners on 1B+3B", "110": "Runners on 1B+2B",
            "111": "Bases loaded",
        }.get(state, state)
        print(f"  {label}: {cnt} ({cnt / n_total:.1%})")

    print(f"\nBases-loaded IBBs (forced run): {opps['ibb_run_scored'].sum():.0f}")

    out = PROC / "ibb_decisions.parquet"
    opps.to_parquet(out, index=False)
    print(f"\nSaved {len(opps):,} graded IBB decisions -> {out.name}")
    return opps


if __name__ == "__main__":
    build_ibb_decisions()
