"""
Builds the send/hold opportunity table from raw Statcast parquet files.
Output: data/processed/opportunities.parquet

Run (from repo root):
    python src/features/opportunities.py

Output columns:
    game_pk, game_date, game_year, inning, inning_topbot, outs_when_up,
    bat_score, fld_score, home_team, away_team,
    on_1b, on_2b, on_3b, batter,
    events, hit_location, hc_x, hc_y,
    runner_last, runner_sprint_speed,
    fielding_of_id, of_arm_strength, throw_distance_ft,
    outcome, des
"""
import unicodedata
from pathlib import Path

import pandas as pd
from pybaseball import playerid_reverse_lookup

from src.features.throw_distance import throw_distance_to_home, validate_distances

ROOT = Path(__file__).resolve().parents[2]
RAW  = ROOT / "data" / "raw"
REF  = ROOT / "data" / "reference"
PROC = ROOT / "data" / "processed"
PROC.mkdir(parents=True, exist_ok=True)

SEASONS = [2020, 2021, 2022, 2023, 2024, 2025, 2026]
OF_HITS = {"single", "double"}
OF_LOCATIONS = {7, 8, 9}
LOC_TO_FIELDER_COL = {7: "fielder_7", 8: "fielder_8", 9: "fielder_9"}

KEEP_COLS = [
    "game_pk", "game_date", "game_year", "inning", "inning_topbot",
    "outs_when_up", "bat_score", "fld_score", "home_team", "away_team",
    "on_1b", "on_2b", "on_3b", "batter",
    "events", "hit_location", "hc_x", "hc_y",
    "runner_last", "runner_sprint_speed",
    "fielding_of_id", "of_arm_strength", "throw_distance_ft",
    "outcome", "des",
]


# ── Outcome classification ────────────────────────────────────────────────────

def _norm(s: str) -> str:
    """Lowercase + strip accents for robust name matching against des text."""
    return unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode("ascii").lower()


def classify_outcome(des: str, runner_last: str) -> str:
    d = _norm(des)
    r = _norm(runner_last)
    if r + " out at home" in d:
        return "OUT_AT_HOME"
    if r + " scores" in d:
        return "SCORED"
    # Explicit advancement short of home — confirmed hold
    for advance in ("to 3rd", "to third", "to 2nd", "to second"):
        if r + " " + advance in d:
            return "HELD_AT_BASE"
    return "HELD_OR_UNKNOWN"


# ── Data loaders ──────────────────────────────────────────────────────────────

def _game_year(game_date) -> int:
    return int(str(game_date)[:4])


def load_statcast() -> pd.DataFrame:
    chunks = []
    for year in SEASONS:
        p = RAW / f"statcast_{year}.parquet"
        if not p.exists():
            print(f"  MISSING: {p.name} — run src/ingest/statcast_pull.py first")
            continue
        chunks.append(pd.read_parquet(p))
    if not chunks:
        raise FileNotFoundError("No statcast parquets found. Run ingest first.")
    df = pd.concat(chunks, ignore_index=True)
    print(f"Loaded {len(df):,} raw rows from {len(chunks)} season(s)")
    return df


def load_sprint_speed() -> dict[int, dict[float, float]]:
    result: dict[int, dict[float, float]] = {}
    for year in SEASONS:
        p = RAW / f"sprint_speed_{year}.parquet"
        if not p.exists():
            print(f"  MISSING: sprint_speed_{year}.parquet")
            continue
        sp = pd.read_parquet(p)
        result[year] = sp.set_index(sp["player_id"].astype(float))["sprint_speed"].to_dict()
    return result


_LOC_TO_ARM_COL = {7: "arm_lf", 8: "arm_cf", 9: "arm_rf"}


def load_arm_strength() -> dict[tuple[int, int, int], float] | None:
    """Returns {(player_id, year, hit_location): arm_strength_mph} or None.

    Uses position-specific arm strength (arm_lf/cf/rf) where available;
    falls back to arm_overall for players with too few position-specific throws.
    """
    frames = []
    for year in SEASONS:
        p = REF / f"arm_strength_{year}.csv"
        if p.exists():
            df = pd.read_csv(p)
            df["season"] = year
            frames.append(df)
    if not frames:
        return None

    arm = pd.concat(frames, ignore_index=True)
    if "player_id" not in arm.columns:
        print("  WARNING: arm_strength CSV missing 'player_id' — skipping")
        return None

    lookup: dict[tuple[int, int, int], float] = {}
    for _, row in arm.iterrows():
        pid = int(row["player_id"])
        yr  = int(row["season"])
        for loc, col in _LOC_TO_ARM_COL.items():
            val = row.get(col)
            if pd.isna(val):
                val = row.get("arm_overall")   # fallback
            if pd.notna(val):
                lookup[(pid, yr, loc)] = float(val)
    return lookup if lookup else None


# ── Main ─────────────────────────────────────────────────────────────────────

def build_opportunities() -> pd.DataFrame:
    # 1. Load & filter
    df = load_statcast()
    opps = df[
        df["on_2b"].notna()
        & df["events"].isin(OF_HITS)
        & df["hit_location"].isin(OF_LOCATIONS)
    ].copy()
    opps["game_year"] = opps["game_date"].apply(_game_year)
    print(f"Identified {len(opps):,} candidate opportunities (runner on 2B, OF hit)")

    # 2. Which outfielder fielded the ball
    def get_fielder(row):
        col = LOC_TO_FIELDER_COL.get(int(row["hit_location"]))
        return row[col] if col and col in row.index else None
    opps["fielding_of_id"] = opps.apply(get_fielder, axis=1)

    # 3. Runner name lookup (used for outcome attribution)
    print("Resolving runner names via playerid_reverse_lookup...")
    runner_ids = opps["on_2b"].dropna().astype(int).unique().tolist()
    id_lookup = playerid_reverse_lookup(runner_ids, key_type="mlbam")
    id_to_last = dict(zip(id_lookup["key_mlbam"], id_lookup["name_last"]))
    opps["runner_last"] = opps["on_2b"].astype(int).map(id_to_last)
    n_missing = opps["runner_last"].isna().sum()
    if n_missing:
        print(f"  WARNING: {n_missing} runners unresolved — those rows -> HELD_OR_UNKNOWN")

    # 4. Outcome classification
    opps["outcome"] = opps.apply(
        lambda r: (
            classify_outcome(r["des"], r["runner_last"])
            if pd.notna(r["runner_last"]) else "HELD_OR_UNKNOWN"
        ),
        axis=1,
    )
    print("Outcome distribution:")
    print(opps["outcome"].value_counts().to_string())

    # 5. Sprint speed (year-matched)
    speed_by_year = load_sprint_speed()
    opps["runner_sprint_speed"] = opps.apply(
        lambda r: speed_by_year.get(r["game_year"], {}).get(float(r["on_2b"])),
        axis=1,
    )
    print(f"Sprint speed join rate: {opps['runner_sprint_speed'].notna().mean():.0%}")

    # 6. Throw distance
    opps["throw_distance_ft"] = opps.apply(
        lambda r: throw_distance_to_home(r["hc_x"], r["hc_y"])
        if pd.notna(r["hc_x"]) and pd.notna(r["hc_y"]) else None,
        axis=1,
    )
    validate_distances(opps["throw_distance_ft"].dropna())

    # 7. Arm strength (optional — only if CSVs downloaded)
    arm_lookup = load_arm_strength()
    if arm_lookup:
        # Key: (fielder MLBAM id, season year, hit_location 7/8/9)
        # Uses position-specific arm_lf/cf/rf; falls back to arm_overall
        opps["of_arm_strength"] = opps.apply(
            lambda r: arm_lookup.get((int(r["fielding_of_id"]), r["game_year"], int(r["hit_location"])))
            if pd.notna(r["fielding_of_id"]) else None,
            axis=1,
        )
        print(f"Arm strength join rate: {opps['of_arm_strength'].notna().mean():.0%}")
    else:
        opps["of_arm_strength"] = None
        print("Arm strength: not yet available (see src/ingest/arm_strength.py)")

    # 8. Save
    out = opps[[c for c in KEEP_COLS if c in opps.columns]].copy()
    out_path = PROC / "opportunities.parquet"
    out.to_parquet(out_path, index=False)
    print(f"\nSaved {len(out):,} opportunities -> {out_path}")
    return out


if __name__ == "__main__":
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    build_opportunities()
