"""
Pulls Statcast event-level data for 2020-2024 and saves as parquet.
Run once per season; output is gitignored.

Usage (from repo root):
    python src/ingest/statcast_pull.py          # all 5 seasons
    python src/ingest/statcast_pull.py 2024     # single year
"""
import sys
import datetime
from pathlib import Path

import pandas as pd
from pybaseball import statcast, cache

cache.enable()

RAW = Path(__file__).resolve().parents[2] / "data" / "raw"
RAW.mkdir(parents=True, exist_ok=True)

SEASON_BOUNDS: dict[int, tuple[str, str]] = {
    2020: ("2020-07-23", "2020-09-27"),   # COVID shortened
    2021: ("2021-04-01", "2021-10-03"),
    2022: ("2022-04-07", "2022-10-05"),   # lockout-delayed start
    2023: ("2023-03-30", "2023-10-01"),
    2024: ("2024-03-20", "2024-09-29"),
}

CHUNK_DAYS = 28   # pull month-by-month to avoid timeouts; pybaseball chunks by day internally


def pull_season(year: int) -> None:
    out = RAW / f"statcast_{year}.parquet"
    if out.exists():
        print(f"{year}: {out.name} already exists — delete to re-pull")
        return

    start_str, end_str = SEASON_BOUNDS[year]
    start = datetime.date.fromisoformat(start_str)
    end   = datetime.date.fromisoformat(end_str)

    chunks = []
    cur = start
    while cur <= end:
        chunk_end = min(cur + datetime.timedelta(days=CHUNK_DAYS - 1), end)
        print(f"  {year}: pulling {cur} -> {chunk_end}")
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
