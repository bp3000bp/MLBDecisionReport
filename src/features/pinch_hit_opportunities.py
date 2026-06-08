"""
Pinch Hit Grader — opportunity identification.

For every pinch hit substitution (2020–2026 regular season), assembles the context
needed to grade whether the substitution improved expected offense:

  - ph_batter_id / replaced_batter_id: from MLBAM offensive_substitution events
  - Base-out state (on_1b, on_2b, on_3b, outs_when_up): from Statcast PA context
  - Pitcher hand (p_throws): from Statcast PA context
  - woba_vs_L / woba_vs_R (pinch hitter): season splits from Statcast
  - rep_woba_vs_L / rep_woba_vs_R (replaced batter): season splits from Statcast

Small-sample imputation: batters with fewer than MIN_PA_SPLIT (50) PA against a
pitcher hand in the season have their split replaced with the league average for that
hand × season. Logged per imputation type.

Output:
  data/processed/pinch_hit_opportunities.parquet

Run:
    python -m src.ingest.pinch_hit_events   # must run first
    python -m src.features.pinch_hit_opportunities
"""

from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
RAW  = ROOT / "data" / "raw"
PROC = ROOT / "data" / "processed"
PROC.mkdir(parents=True, exist_ok=True)

SEASONS     = [2020, 2021, 2022, 2023, 2024, 2025, 2026]
MIN_PA_SPLIT = 50

SC_COLS = [
    "game_pk", "at_bat_number",
    "pitcher", "p_throws", "stand",
    "on_1b", "on_2b", "on_3b", "outs_when_up",
    "home_team", "away_team", "inning_topbot",
]


def _load_pinch_hit_events() -> pd.DataFrame:
    """Concatenate per-season MLBAM PH event parquets."""
    parts = []
    for yr in SEASONS:
        p = RAW / f"pinch_hit_events_{yr}.parquet"
        if not p.exists():
            continue
        parts.append(pd.read_parquet(p))
    if not parts:
        raise FileNotFoundError(
            "No pinch_hit_events_*.parquet files found. "
            "Run: python -m src.ingest.pinch_hit_events"
        )
    df = pd.concat(parts, ignore_index=True)
    print(f"Loaded {len(df):,} raw PH substitutions across {df['game_year'].nunique()} seasons")
    return df


def _get_statcast_pa_context() -> pd.DataFrame:
    """
    First-pitch row per (game_pk, at_bat_number) from Statcast.
    Gives the pre-PA base-out state, pitcher hand, and team identifiers.
    """
    parts = []
    for yr in SEASONS:
        p = RAW / f"statcast_{yr}.parquet"
        if not p.exists():
            continue
        sc = pd.read_parquet(p, columns=SC_COLS)
        parts.append(sc)
    if not parts:
        raise FileNotFoundError("No statcast_*.parquet files found in data/raw/")

    sc = pd.concat(parts, ignore_index=True)
    # One row per PA: take the first pitch (lowest at_bat_number ordering = first event)
    # on_1b/on_2b/on_3b are the runner IDs at pitch time; they're stable within a clean PA
    pa = (
        sc.sort_values(["game_pk", "at_bat_number"])
        .groupby(["game_pk", "at_bat_number"], sort=False)
        .first()
        .reset_index()
    )
    print(f"Built PA context: {len(pa):,} plate appearances across {pa['game_pk'].nunique():,} games")
    return pa


def _build_batter_woba_splits() -> pd.DataFrame:
    """
    Season wOBA by batter × pitcher hand.

    Returns: [batter, game_year, woba_vs_L, n_pa_vs_L, woba_vs_R, n_pa_vs_R]
    """
    chunks_L, chunks_R = [], []
    for yr in SEASONS:
        p = RAW / f"statcast_{yr}.parquet"
        if not p.exists():
            continue
        sc = pd.read_parquet(p, columns=["batter", "p_throws", "woba_value", "woba_denom"])
        sc["game_year"] = yr
        sc = sc[sc["woba_denom"].notna() & (sc["woba_denom"] > 0)]
        for hand, chunks in [("L", chunks_L), ("R", chunks_R)]:
            sub = sc[sc["p_throws"] == hand]
            agg = (
                sub.groupby(["batter", "game_year"])
                .agg(**{
                    f"woba_vs_{hand}":   ("woba_value", "mean"),
                    f"n_pa_vs_{hand}":   ("woba_denom", "sum"),
                })
                .reset_index()
            )
            chunks.append(agg)

    left  = pd.concat(chunks_L, ignore_index=True) if chunks_L else pd.DataFrame()
    right = pd.concat(chunks_R, ignore_index=True) if chunks_R else pd.DataFrame()
    if left.empty or right.empty:
        return pd.DataFrame()
    return left.merge(right, on=["batter", "game_year"], how="outer")


def build_pinch_hit_opportunities() -> pd.DataFrame:
    print("Loading pinch hit events from MLBAM...")
    ph = _load_pinch_hit_events()

    print("Loading Statcast PA context...")
    pa_ctx = _get_statcast_pa_context()

    # Join MLBAM events to Statcast PA context on game_pk + at_bat_number
    ph = ph.merge(
        pa_ctx[["game_pk", "at_bat_number", "pitcher", "p_throws", "stand",
                "on_1b", "on_2b", "on_3b", "outs_when_up",
                "home_team", "away_team", "inning_topbot"]],
        on=["game_pk", "at_bat_number"],
        how="left",
    )
    n_unmatched = ph["pitcher"].isna().sum()
    if n_unmatched > 0:
        print(f"  Warning: {n_unmatched:,} PH events had no Statcast PA match (excluded)")
    ph = ph[ph["pitcher"].notna()].copy()

    # Batting team from half-inning indicator
    ph["batting_team"] = np.where(
        ph["inning_topbot"] == "Top",
        ph["away_team"],
        ph["home_team"],
    )

    # Base-occupancy flags (1/0) for RE24 lookup
    ph["on_1b_f"] = ph["on_1b"].notna().astype(float)
    ph["on_2b_f"] = ph["on_2b"].notna().astype(float)
    ph["on_3b_f"] = ph["on_3b"].notna().astype(float)

    print("Building batter wOBA splits...")
    batter_splits = _build_batter_woba_splits()

    # League average per season for imputation
    lg_avg = (
        batter_splits.groupby("game_year")
        .agg(lg_woba_vs_L=("woba_vs_L", "mean"), lg_woba_vs_R=("woba_vs_R", "mean"))
        .reset_index()
    )

    # Join PH batter splits
    ph = ph.merge(
        batter_splits.rename(columns={"batter": "ph_batter_id"}),
        on=["ph_batter_id", "game_year"],
        how="left",
    )
    # Join replaced batter splits (rename to rep_ prefix)
    ph = ph.merge(
        batter_splits.rename(columns={
            "batter":    "replaced_batter_id",
            "woba_vs_L": "rep_woba_vs_L",
            "woba_vs_R": "rep_woba_vs_R",
            "n_pa_vs_L": "rep_n_pa_vs_L",
            "n_pa_vs_R": "rep_n_pa_vs_R",
        }),
        on=["replaced_batter_id", "game_year"],
        how="left",
    )
    ph = ph.merge(lg_avg, on="game_year", how="left")

    # Impute small samples with league average
    ph_low_L = ph["n_pa_vs_L"].fillna(0) < MIN_PA_SPLIT
    ph_low_R = ph["n_pa_vs_R"].fillna(0) < MIN_PA_SPLIT
    rep_low_L = ph["rep_n_pa_vs_L"].fillna(0) < MIN_PA_SPLIT
    rep_low_R = ph["rep_n_pa_vs_R"].fillna(0) < MIN_PA_SPLIT
    print(
        f"  Imputed {ph_low_L.sum():,} PH vs-L, {ph_low_R.sum():,} PH vs-R, "
        f"{rep_low_L.sum():,} rep vs-L, {rep_low_R.sum():,} rep vs-R (< {MIN_PA_SPLIT} PA)"
    )
    ph["woba_vs_L"]     = np.where(ph_low_L, ph["lg_woba_vs_L"], ph["woba_vs_L"])
    ph["woba_vs_R"]     = np.where(ph_low_R, ph["lg_woba_vs_R"], ph["woba_vs_R"])
    ph["rep_woba_vs_L"] = np.where(rep_low_L, ph["lg_woba_vs_L"], ph["rep_woba_vs_L"])
    ph["rep_woba_vs_R"] = np.where(rep_low_R, ph["lg_woba_vs_R"], ph["rep_woba_vs_R"])

    out_path = PROC / "pinch_hit_opportunities.parquet"
    ph.to_parquet(out_path, index=False)
    print(f"Saved {len(ph):,} pinch hit opportunities -> {out_path}")
    return ph


if __name__ == "__main__":
    import sys
    sys.path.insert(0, str(ROOT))
    build_pinch_hit_opportunities()
