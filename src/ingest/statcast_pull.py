"""
Pulls Statcast event-level data for 2020-present and saves as parquet.
Run once per completed season; re-runs automatically for the current season.

Usage (from repo root):
    python src/ingest/statcast_pull.py          # all known seasons
    python src/ingest/statcast_pull.py 2025     # single year
    python src/ingest/statcast_pull.py 2026     # current season (always re-pulls)
"""
import sys
import datetime
from pathlib import Path

import pandas as pd
from pybaseball import statcast, cache

cache.enable()

RAW = Path(__file__).resolve().parents[2] / "data" / "raw"
RAW.mkdir(parents=True, exist_ok=True)

CURRENT_YEAR = datetime.date.today().year

# Completed seasons — fixed bounds.
_FIXED_SEASONS: dict[int, tuple[str, str]] = {
    2020: ("2020-07-23", "2020-09-27"),   # COVID shortened
    2021: ("2021-04-01", "2021-10-03"),
    2022: ("2022-04-07", "2022-10-05"),   # lockout-delayed start
    2023: ("2023-03-30", "2023-10-01"),
    2024: ("2024-03-20", "2024-09-29"),
    2025: ("2025-03-27", "2025-09-28"),   # verify exact end if pulling post-season
}

# In-progress seasons — only a start date; end is computed at runtime as yesterday.
_IN_PROGRESS_STARTS: dict[int, str] = {
    2026: "2026-03-26",
}


def _season_bounds(year: int) -> tuple[str, str]:
    if year in _FIXED_SEASONS:
        return _FIXED_SEASONS[year]
    if year in _IN_PROGRESS_STARTS:
        yesterday = (datetime.date.today() - datetime.timedelta(days=1)).isoformat()
        return _IN_PROGRESS_STARTS[year], yesterday
    raise ValueError(f"No season bounds defined for {year}")


SEASON_BOUNDS = {y: _season_bounds(y)
                 for y in list(_FIXED_SEASONS) + list(_IN_PROGRESS_STARTS)}

CHUNK_DAYS = 28   # pull month-by-month to avoid timeouts


def pull_season(year: int) -> None:
    out = RAW / f"statcast_{year}.parquet"
    if out.exists() and year != CURRENT_YEAR:
        print(f"{year}: {out.name} already exists — delete to re-pull")
        return
    if out.exists() and year == CURRENT_YEAR:
        print(f"{year}: in-progress season — re-pulling to capture new games …")

    start_str, end_str = _season_bounds(year)
    start = datetime.date.fromisoformat(start_str)
    end   = datetime.date.fromisoformat(end_str)

    print(f"{year}: pulling {start_str} -> {end_str}")
    chunks = []
    cur = start
    while cur <= end:
        chunk_end = min(cur + datetime.timedelta(days=CHUNK_DAYS - 1), end)
        print(f"  pulling {cur} -> {chunk_end}")
        chunk = statcast(start_dt=str(cur), end_dt=str(chunk_end))
        chunks.append(chunk)
        cur = chunk_end + datetime.timedelta(days=1)

    df = pd.concat(chunks, ignore_index=True)
    df.to_parquet(out, index=False)
    print(f"  {year}: saved {len(df):,} rows -> {out.name}")


if __name__ == "__main__":
    years = [int(y) for y in sys.argv[1:]] if len(sys.argv) > 1 else list(SEASON_BOUNDS)
    for y in years:
        print(f"\n=== {y} ===")
        pull_season(y)
    print("\nDone.")
