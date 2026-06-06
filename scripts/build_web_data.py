"""
Converts processed leaderboard CSVs -> JSON files consumed by the Next.js web app.
Run after any pipeline change that affects graded_decisions.parquet.

Output: web/data/leaderboard_team.json
        web/data/leaderboard_coach.json
"""
import json
from pathlib import Path

import pandas as pd

ROOT  = Path(__file__).resolve().parent.parent
PROC  = ROOT / "data" / "processed"
OUT   = ROOT / "web" / "data"
OUT.mkdir(parents=True, exist_ok=True)


def _clean(df: pd.DataFrame) -> list[dict]:
    """Convert DataFrame to JSON-serialisable list, rounding floats."""
    df = df.copy()
    for col in df.select_dtypes(include="float").columns:
        df[col] = df[col].round(3)
    for col in df.select_dtypes(include="bool").columns:
        df[col] = df[col].astype(bool)
    return json.loads(df.to_json(orient="records"))


def build() -> None:
    # Team leaderboard
    team = pd.read_csv(PROC / "leaderboard_team.csv")
    team_path = OUT / "leaderboard_team.json"
    team_path.write_text(json.dumps(_clean(team), indent=2))
    print(f"  Wrote {len(team)} team-year rows -> {team_path}")

    # Coach leaderboard
    coach_path_src = PROC / "leaderboard_coach.csv"
    if coach_path_src.exists():
        coach = pd.read_csv(coach_path_src)
        coach_out = OUT / "leaderboard_coach.json"
        coach_out.write_text(json.dumps(_clean(coach), indent=2))
        print(f"  Wrote {len(coach)} coach rows -> {coach_out}")
    else:
        print("  leaderboard_coach.csv not found — skipping (run leaderboards.py first)")


if __name__ == "__main__":
    build()
    print("Done.")
