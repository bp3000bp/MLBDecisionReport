"""
Arm strength data from Baseball Savant — manual download required.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
USER ACTION REQUIRED
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Baseball Savant's arm-strength leaderboard has no stable API endpoint.
Download the CSV manually for each year 2020–2026:

  1. Go to Baseball Savant → Leaderboards → Arm Strength
     (search "baseball savant statcast arm strength leaderboard")

  2. For EACH year (2020, 2021, 2022, 2023, 2024, 2025, 2026):
       - Set "Season" to the target year
       - Set "Position" to Outfielders (or download all positions and filter here)
       - Set min opportunities to 10+ to exclude tiny samples
       - Click the CSV download button (do NOT guess the URL — use the button)
       Note: 2026 is an in-progress season — re-download periodically for fresh data.

  3. Save/rename each file to:
       data/reference/arm_strength_2020.csv
       data/reference/arm_strength_2021.csv
       data/reference/arm_strength_2022.csv
       data/reference/arm_strength_2023.csv
       data/reference/arm_strength_2024.csv
       data/reference/arm_strength_2025.csv
       data/reference/arm_strength_2026.csv

  4. Run this script to validate:
       python src/ingest/arm_strength.py

Expected CSV columns (Savant's current format — update COLUMN_MAP if names differ):
  player_id      — MLBAM player ID (integer)
  last_name      — player last name
  first_name     — player first name
  arm_strength   — average arm strength (mph)
  n_throws       — number of throws (for filtering)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
from pathlib import Path

import pandas as pd

REF = Path(__file__).resolve().parents[2] / "data" / "reference"
SEASONS = [2020, 2021, 2022, 2023, 2024, 2025, 2026]

# Actual Savant CSV column names (confirmed from downloaded files)
REQUIRED_COLS = ["player_id", "arm_lf", "arm_cf", "arm_rf", "arm_overall"]
EXPECTED_RANGE = (60.0, 105.0)   # mph — outside this = probably wrong column


def validate() -> None:
    found = []
    for year in SEASONS:
        p = REF / f"arm_strength_{year}.csv"
        if not p.exists():
            print(f"  MISSING  : {p.name}")
            continue

        df = pd.read_csv(p)
        missing = [c for c in REQUIRED_COLS if c not in df.columns]
        if missing:
            print(f"  BAD COLS : {p.name} — missing {missing}")
            print(f"    Found  : {list(df.columns)}")
            continue

        overall = df["arm_overall"].dropna()
        lo, hi = EXPECTED_RANGE
        out_of_range = (~overall.between(lo, hi)).sum()
        if out_of_range:
            print(f"  WARNING  : {p.name} has {out_of_range} rows outside {lo}–{hi} mph")

        n_lf = df["arm_lf"].notna().sum()
        n_cf = df["arm_cf"].notna().sum()
        n_rf = df["arm_rf"].notna().sum()
        print(
            f"  OK       : {p.name}  {len(df):>4} players  "
            f"arm_overall [{overall.min():.1f}, {overall.max():.1f}] mph  "
            f"position-specific: LF={n_lf} CF={n_cf} RF={n_rf}"
        )
        found.append(year)

    print()
    if found:
        print(f"Arm strength ready for years: {found}")
    else:
        print("No arm strength CSVs found — see instructions above.")


if __name__ == "__main__":
    validate()
