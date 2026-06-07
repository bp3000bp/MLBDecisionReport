"""
Converts processed leaderboard CSVs -> JSON files consumed by the Next.js web app.
Run after any pipeline change.

Outputs:
  web/data/leaderboard_team.json          (send/hold team-year)
  web/data/leaderboard_coach.json         (send/hold coach career)
  web/data/leaderboard_steal_team.json    (steal attempt team-year)
  web/data/leaderboard_steal_runner.json  (steal attempt runner career)
  web/data/meta.json                      (pipeline metadata: last_updated, years covered)
"""
import datetime
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


def _write(src: Path, dst: Path, label: str) -> None:
    if not src.exists():
        print(f"  MISSING {src.name} -- skipping")
        return
    df = pd.read_csv(src)
    dst.write_text(json.dumps(_clean(df), indent=2), encoding="utf-8")
    print(f"  Wrote {len(df)} {label} rows -> {dst.name}")


def _years_in_file(path: Path) -> list[int]:
    """Return sorted list of game_year values in a CSV, for metadata."""
    if not path.exists():
        return []
    try:
        df = pd.read_csv(path, usecols=["game_year"])
        return sorted(df["game_year"].dropna().astype(int).unique().tolist())
    except Exception:
        return []


def build() -> None:
    # Send/Hold module
    _write(PROC / "leaderboard_team.csv",  OUT / "leaderboard_team.json",  "send/hold team-year")
    _write(PROC / "leaderboard_coach.csv", OUT / "leaderboard_coach.json", "send/hold coach")

    # Steal Attempt module
    _write(PROC / "leaderboard_steal_team.csv",   OUT / "leaderboard_steal_team.json",   "steal team-year")
    _write(PROC / "leaderboard_steal_runner.csv",  OUT / "leaderboard_steal_runner.json",  "steal runner career")

    # IBB Decision module
    _write(PROC / "leaderboard_ibb_team.csv", OUT / "leaderboard_ibb_team.json", "IBB team-year")

    # Pipeline metadata
    today = datetime.date.today()
    send_hold_years = _years_in_file(PROC / "leaderboard_team.csv")
    steal_years = _years_in_file(PROC / "leaderboard_steal_team.csv")
    ibb_years = _years_in_file(PROC / "leaderboard_ibb_team.csv")
    meta = {
        "last_updated": today.isoformat(),
        "current_year": today.year,
        "send_hold_years": send_hold_years,
        "steal_years": steal_years,
        "ibb_years": ibb_years,
    }
    (OUT / "meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    print(f"  Wrote meta.json (last_updated={today.isoformat()})")


if __name__ == "__main__":
    build()
    print("Done.")
