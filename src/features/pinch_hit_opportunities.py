"""
Pinch Hit Grader — opportunity identification.

Identifies every pinch hit appearance (a player substituted for the original
lineup slot before or during their at-bat) and assembles the context needed to
grade the substitution:

  - The pinch hitter's season wOBA vs. right-handed pitchers (wOBA_R) and vs.
    left-handed pitchers (wOBA_L) — we use the pitcher's actual hand for the matchup
  - The replaced batter's same splits
  - The current pitcher's wOBA-against by batter hand (wOBA_against_R / wOBA_against_L)
  - The base-out state RE24 run value of the situation

Pinch hit identification:
  Statcast records the batter's position in the batting order (bat_order / batter).
  A pinch hitter appears when the lineup slot's batter_id changes mid-game. We detect
  this by comparing the expected batter (from the starting lineup or most recent at-bat
  for that slot) to the actual batter at each plate appearance.

  The MLBAM play-by-play 'substitutions' array is more reliable: it surfaces
  'offensive_substitution' events with the bat_order, outgoing_player_id, and
  incoming_player_id. This is the preferred data source.

Platoon adjustment:
  We use season splits (vs. LHP, vs. RHP) from the Statcast woba_value field,
  filtered by the pitcher's p_throws. This is the same wOBA computation used
  by the IBB module but split by pitcher handedness.

Grading logic (in src/model/pinch_hit_grade.py):
  ph_woba  = pinch_hitter wOBA vs. pitcher_hand
  rep_woba = replaced_batter wOBA vs. pitcher_hand
  pit_woba = pitcher wOBA-against vs. batter hand (context on quality of opposition)

  woba_gain = ph_woba - rep_woba              (positive = upgrade)
  run_value = woba_gain / woba_scale * re_context_multiplier
  GOOD_PH   = woba_gain > 0 (pinch hitter is a better platoon matchup)

  woba_scale = 1.157 (FanGraphs standard for converting wOBA delta to run value)

Output:
  data/processed/pinch_hit_opportunities.parquet

Run:
    python -m src.features.pinch_hit_opportunities
"""

from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
RAW  = ROOT / "data" / "raw"
REF  = ROOT / "data" / "reference"
PROC = ROOT / "data" / "processed"
PROC.mkdir(parents=True, exist_ok=True)

SEASONS = [2020, 2021, 2022, 2023, 2024, 2025, 2026]

WOBA_SCALE = 1.157


def _load_pinch_hit_events() -> pd.DataFrame:
    """
    Pull pinch hit substitution events from MLBAM play-by-play.

    Each 'offensive_substitution' event with a bat_order and two player IDs
    (outgoing, incoming) is a pinch hit when the substitution type is 'Pinch Hitter'.

    NOT YET IMPLEMENTED. Use the same concurrent fetch pattern as steal_events.py.
    Endpoint: /api/v1/game/{game_pk}/playByPlay — filter substitutions array for
    type == 'Pinch Hitter'.
    """
    raise NotImplementedError(
        "Pinch hit event extraction not yet implemented. "
        "Pull from MLBAM play-by-play substitutions array, "
        "filter for type='Pinch Hitter'. "
        "See src/ingest/steal_events.py for the concurrent fetch pattern."
    )


def _build_batter_woba_splits() -> pd.DataFrame:
    """
    Season wOBA by batter × pitcher hand (splits: vs_L, vs_R).

    Returns DataFrame with columns:
      [batter, game_year, woba_vs_L, n_pa_vs_L, woba_vs_R, n_pa_vs_R]
    """
    chunks = []
    for yr in SEASONS:
        p = RAW / f"statcast_{yr}.parquet"
        if not p.exists():
            continue
        sc = pd.read_parquet(p, columns=["batter", "game_date", "p_throws", "woba_value", "woba_denom"])
        sc["game_year"] = yr
        sc = sc[sc["woba_denom"].notna() & (sc["woba_denom"] > 0)]
        for hand in ["L", "R"]:
            sub = sc[sc["p_throws"] == hand]
            agg = (
                sub.groupby(["batter", "game_year"])
                .agg(**{f"woba_vs_{hand}": ("woba_value", "mean"), f"n_pa_vs_{hand}": ("woba_denom", "sum")})
                .reset_index()
            )
            chunks.append(agg)

    if not chunks:
        return pd.DataFrame()

    # Each chunk is a hand-specific split; pivot and merge
    chunks_L = [c for c in chunks if "woba_vs_L" in c.columns]
    chunks_R = [c for c in chunks if "woba_vs_R" in c.columns]
    left  = pd.concat(chunks_L, ignore_index=True) if chunks_L else pd.DataFrame()
    right = pd.concat(chunks_R, ignore_index=True) if chunks_R else pd.DataFrame()
    if left.empty or right.empty:
        return pd.DataFrame()
    splits = left.merge(right, on=["batter", "game_year"], how="outer")
    return splits


def _build_pitcher_woba_against_splits() -> pd.DataFrame:
    """
    Season wOBA-against by pitcher × batter hand (splits: vs_L batters, vs_R batters).

    Returns DataFrame with columns:
      [pitcher, game_year, woba_against_vs_L, woba_against_vs_R]
    """
    chunks_L, chunks_R = [], []
    for yr in SEASONS:
        p = RAW / f"statcast_{yr}.parquet"
        if not p.exists():
            continue
        sc = pd.read_parquet(p, columns=["pitcher", "game_date", "stand", "woba_value", "woba_denom"])
        sc["game_year"] = yr
        sc = sc[sc["woba_denom"].notna() & (sc["woba_denom"] > 0)]
        for hand, chunks in [("L", chunks_L), ("R", chunks_R)]:
            sub = sc[sc["stand"] == hand]
            agg = (
                sub.groupby(["pitcher", "game_year"])
                .agg(**{f"woba_against_vs_{hand}": ("woba_value", "mean")})
                .reset_index()
            )
            chunks.append(agg)

    left  = pd.concat(chunks_L, ignore_index=True) if chunks_L else pd.DataFrame()
    right = pd.concat(chunks_R, ignore_index=True) if chunks_R else pd.DataFrame()
    if left.empty or right.empty:
        return pd.DataFrame()
    return left.merge(right, on=["pitcher", "game_year"], how="outer")


def build_pinch_hit_opportunities() -> pd.DataFrame:
    """
    Main entry point. Not runnable until _load_pinch_hit_events() is implemented.
    """
    print("Loading pinch hit events from MLBAM play-by-play...")
    ph = _load_pinch_hit_events()   # will raise NotImplementedError

    print("Building batter wOBA splits from Statcast...")
    batter_splits = _build_batter_woba_splits()

    print("Building pitcher wOBA-against splits from Statcast...")
    pitcher_splits = _build_pitcher_woba_against_splits()

    # Join pinch hitter splits
    ph = ph.merge(
        batter_splits.rename(columns={"batter": "ph_batter_id"}),
        on=["ph_batter_id", "game_year"],
        how="left",
    )
    # Join replaced batter splits
    ph = ph.merge(
        batter_splits.rename(columns={"batter": "replaced_batter_id", "woba_vs_L": "rep_woba_vs_L", "woba_vs_R": "rep_woba_vs_R"}),
        on=["replaced_batter_id", "game_year"],
        how="left",
    )
    # Join pitcher splits
    ph = ph.merge(
        pitcher_splits,
        on=["pitcher", "game_year"],
        how="left",
    )

    # TODO: compute platoon-matched woba_gain based on p_throws
    # TODO: compute run_value from woba_gain × woba_scale × RE context

    out_path = PROC / "pinch_hit_opportunities.parquet"
    ph.to_parquet(out_path, index=False)
    print(f"Saved {len(ph):,} pinch hit opportunities -> {out_path}")
    return ph


if __name__ == "__main__":
    import sys
    sys.path.insert(0, str(ROOT))
    build_pinch_hit_opportunities()
