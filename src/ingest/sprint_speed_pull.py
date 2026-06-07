"""
Pulls Baseball Savant sprint speed leaderboard for 2020-present and saves as parquet.
Run once per completed season; re-runs automatically for the current season.

Usage (from repo root):
    python src/ingest/sprint_speed_pull.py       # all seasons
    python src/ingest/sprint_speed_pull.py 2026  # single year (current — always re-pulls)
"""
import sys
import datetime
from pathlib import Path

import pandas as pd
from pybaseball import statcast_sprint_speed

RAW = Path(__file__).resolve().parents[2] / "data" / "raw"
RAW.mkdir(parents=True, exist_ok=True)

CURRENT_YEAR = datetime.date.today().year
SEASONS = [2020, 2021, 2022, 2023, 2024, 2025, 2026]
MIN_OPP = 5   # minimum sprint-speed opportunities to be included


def pull_sprint_speed(year: int) -> None:
    out = RAW / f"sprint_speed_{year}.parquet"
    if out.exists() and year != CURRENT_YEAR:
        print(f"{year}: {out.name} already exists — delete to re-pull")
        return
    if out.exists() and year == CURRENT_YEAR:
        print(f"{year}: in-progress season — re-pulling sprint speed …")

    print(f"Pulling {year} sprint speed (min_opp={MIN_OPP})...")
    df = statcast_sprint_speed(year, min_opp=MIN_OPP)
    df.to_parquet(out, index=False)
    print(f"  {year}: saved {len(df):,} players -> {out.name}")


if __name__ == "__main__":
    years = [int(y) for y in sys.argv[1:]] if len(sys.argv) > 1 else SEASONS
    for y in years:
        pull_sprint_speed(y)
    print("\nDone.")
