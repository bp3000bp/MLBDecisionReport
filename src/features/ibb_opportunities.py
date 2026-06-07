"""
Builds the IBB (intentional walk) opportunity table from raw Statcast parquets.

For each IBB event (events == 'intent_walk'), we compute:
  - Pre-IBB base-out state and RE24 lookup
  - Post-IBB base-out state (deterministic walk mechanics) and RE24 lookup
  - RE cost of the IBB = (RE_after - RE_before) + immediate runs forced in
  - Batter's season wOBA, computed from woba_value/woba_denom in the same Statcast data
    (no external API or ID mapping needed)
  - Next batter's season wOBA (from the at-bat sequence in the same half-inning)
  - run_value = (batter_wOBA - next_wOBA) / WOBA_SCALE - re_cost
    Positive = IBB saved runs (GOOD_IBB), negative = IBB cost runs (BAD_IBB)

All inputs come from data already pulled by statcast_pull.py. No manual downloads required.

Output: data/processed/ibb_opportunities.parquet

Run (from repo root):
    python src/features/ibb_opportunities.py
"""
import sys
import time
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
RAW  = ROOT / "data" / "raw"
REF  = ROOT / "data" / "reference"
PROC = ROOT / "data" / "processed"
PROC.mkdir(parents=True, exist_ok=True)

sys.path.insert(0, str(ROOT))

SEASONS = [2020, 2021, 2022, 2023, 2024, 2025, 2026]

# Standard FanGraphs wOBA-to-runs scaling factor.
# Converts a wOBA difference between two batters to expected run difference per PA.
WOBA_SCALE = 1.157

# Minimum PA threshold: if a batter has fewer than this many PA in the season,
# fall back to league average wOBA rather than their noisy sample.
MIN_PA = 50

_STATCAST_COLS = [
    "game_pk", "game_date", "game_year", "inning", "inning_topbot",
    "at_bat_number", "outs_when_up", "batter",
    "on_1b", "on_2b", "on_3b", "events",
    "woba_value", "woba_denom",
    "home_team", "away_team",
]


def _load_statcast() -> pd.DataFrame:
    frames = []
    for yr in SEASONS:
        p = RAW / f"statcast_{yr}.parquet"
        if not p.exists():
            print(f"  WARNING: {p.name} not found — skipping {yr}")
            continue
        df = pd.read_parquet(p, columns=_STATCAST_COLS)
        frames.append(df)
    return pd.concat(frames, ignore_index=True)


def _batter_season_woba(df: pd.DataFrame) -> pd.DataFrame:
    """
    Compute each batter's season wOBA from Statcast woba_value/woba_denom.
    IBBs have woba_denom=0 so they are naturally excluded from the denominator.
    Returns DataFrame: batter, game_year, woba, pa_count.
    """
    pa = df[(df["woba_denom"] == 1) & df["woba_value"].notna()].copy()
    agg = (
        pa.groupby(["batter", "game_year"])
        .agg(woba_sum=("woba_value", "sum"), pa_count=("woba_denom", "sum"))
        .reset_index()
    )
    agg["woba"] = (agg["woba_sum"] / agg["pa_count"]).round(4)
    return agg[["batter", "game_year", "woba", "pa_count"]]


def _league_woba_by_year(df: pd.DataFrame) -> dict[int, float]:
    pa = df[(df["woba_denom"] == 1) & df["woba_value"].notna()]
    lg = (
        pa.groupby("game_year")
        .agg(s=("woba_value", "sum"), n=("woba_denom", "sum"))
        .reset_index()
    )
    lg["lg_woba"] = lg["s"] / lg["n"]
    return dict(zip(lg["game_year"], lg["lg_woba"]))


def _post_ibb_state(on_1b: bool, on_2b: bool, on_3b: bool) -> tuple[int, int, int, int]:
    """
    Compute base state after an intentional walk.
    Walk mechanics: batter goes to 1B; runners advance only if forced (runner on 1B).
    Returns (new_1b, new_2b, new_3b, runs_scored).
    """
    if on_1b and on_2b and on_3b:
        # Bases loaded → all runners forced, run scores
        return 1, 1, 1, 1
    elif on_1b and on_2b:
        # 1B + 2B occupied → fill bases (runner on 2B forced to 3B)
        return 1, 1, 1, 0
    elif on_1b:
        # 1B occupied → runner forced to 2B; 3B unchanged
        return 1, 1, int(on_3b), 0
    else:
        # 1B empty → batter takes 1B, no force; existing runners stay
        return 1, int(on_2b), int(on_3b), 0


def _load_re24() -> pd.DataFrame:
    return pd.read_csv(REF / "re24_table.csv")


def _re_lookup(re24: pd.DataFrame, occ1: int, occ2: int, occ3: int, outs: int) -> float:
    row = re24[
        (re24["on_1b"] == occ1) & (re24["on_2b"] == occ2) &
        (re24["on_3b"] == occ3) & (re24["outs"] == outs)
    ]
    return float(row["re"].iloc[0]) if len(row) else 0.0


def _adj_woba(row: pd.Series, woba_col: str, pa_col: str, lg_woba: float) -> float:
    """Return batter's wOBA if they have MIN_PA, else league average."""
    woba = row.get(woba_col)
    pa   = row.get(pa_col, 0)
    if pd.notna(woba) and pa >= MIN_PA:
        return float(woba)
    return lg_woba


def build_ibb_opportunities() -> pd.DataFrame:
    t0 = time.time()

    print("Loading Statcast data...")
    df = _load_statcast()
    print(f"  {len(df):,} rows across {sorted(df['game_year'].unique())} seasons")

    # ── Batter season wOBA ────────────────────────────────────────────────
    print("Computing batter season wOBA from Statcast woba_value...")
    batter_woba = _batter_season_woba(df)
    lg_woba     = _league_woba_by_year(df)
    print(f"  {len(batter_woba):,} batter-seasons")
    for yr, w in sorted(lg_woba.items()):
        print(f"    {yr} league avg wOBA: {w:.3f}")

    # ── Extract IBB events ────────────────────────────────────────────────
    print("Extracting intentional walk events...")
    ibb = df[df["events"] == "intent_walk"].copy()
    by_year = ibb.groupby("game_year").size()
    print(f"  Total: {len(ibb):,} IBBs\n{by_year.to_string()}")

    # Fielding team = the team that issued the IBB (pitching team)
    # Top of inning: away team bats → home team pitches/fields
    # Bot of inning: home team bats → away team pitches/fields
    ibb["fielding_team"] = ibb.apply(
        lambda r: r["home_team"] if r["inning_topbot"] == "Top" else r["away_team"], axis=1
    )
    ibb["batting_team"] = ibb.apply(
        lambda r: r["away_team"] if r["inning_topbot"] == "Top" else r["home_team"], axis=1
    )

    # Base occupancy as 0/1 integers
    ibb["occ_1b"] = ibb["on_1b"].notna().astype(int)
    ibb["occ_2b"] = ibb["on_2b"].notna().astype(int)
    ibb["occ_3b"] = ibb["on_3b"].notna().astype(int)

    # ── RE24 lookups ──────────────────────────────────────────────────────
    re24 = _load_re24()

    ibb["re_before"] = ibb.apply(
        lambda r: _re_lookup(re24, r["occ_1b"], r["occ_2b"], r["occ_3b"], int(r["outs_when_up"])),
        axis=1,
    )

    post = ibb.apply(
        lambda r: _post_ibb_state(bool(r["occ_1b"]), bool(r["occ_2b"]), bool(r["occ_3b"])),
        axis=1, result_type="expand",
    )
    ibb[["post_1b", "post_2b", "post_3b", "ibb_run_scored"]] = post

    ibb["re_after"] = ibb.apply(
        lambda r: _re_lookup(re24, int(r["post_1b"]), int(r["post_2b"]), int(r["post_3b"]), int(r["outs_when_up"])),
        axis=1,
    )

    # RE cost: change in future expected runs + immediate run forced in (bases-loaded IBB)
    ibb["re_cost"] = (ibb["re_after"] - ibb["re_before"]) + ibb["ibb_run_scored"]

    # ── Batter wOBA join ──────────────────────────────────────────────────
    ibb = ibb.merge(
        batter_woba.rename(columns={"woba": "batter_woba", "pa_count": "batter_pa"}),
        on=["batter", "game_year"], how="left",
    )
    ibb["lg_woba"] = ibb["game_year"].map(lg_woba)
    ibb["batter_woba_adj"] = ibb.apply(
        lambda r: _adj_woba(r, "batter_woba", "batter_pa", r["lg_woba"]), axis=1
    )
    ibb["batter_imputed"] = ibb["batter_pa"].isna() | (ibb["batter_pa"] < MIN_PA)
    n_imp = ibb["batter_imputed"].sum()
    print(f"  Batter wOBA imputed to league avg: {n_imp} ({n_imp/len(ibb):.0%})")

    # ── Next-batter identification ────────────────────────────────────────
    print("Identifying next batter in each half-inning...")

    # One row per completed at-bat (events is non-null for the final pitch of each PA)
    ab_seq = (
        df[df["events"].notna()]
        [["game_pk", "inning", "inning_topbot", "at_bat_number", "batter"]]
        .drop_duplicates(subset=["game_pk", "at_bat_number"])
        .sort_values(["game_pk", "at_bat_number"])
        .reset_index(drop=True)
    )

    # Build dict: (game_pk, inning, inning_topbot) -> sorted [(at_bat_number, batter_id)]
    hi_map: dict[tuple, list] = {}
    for (gpk, inn, topbot), grp in ab_seq.groupby(["game_pk", "inning", "inning_topbot"]):
        hi_map[(gpk, inn, topbot)] = sorted(zip(grp["at_bat_number"], grp["batter"]))

    def _next_batter(row: pd.Series):
        key = (row["game_pk"], row["inning"], row["inning_topbot"])
        cur = row["at_bat_number"]
        for ab_num, batter_id in hi_map.get(key, []):
            if ab_num > cur:
                return batter_id
        return None

    ibb["next_batter"] = ibb.apply(_next_batter, axis=1)
    n_no_next = ibb["next_batter"].isna().sum()
    print(f"  IBBs with no next batter in inning (end-of-inning): {n_no_next}")

    # ── Next-batter wOBA join ─────────────────────────────────────────────
    ibb = ibb.merge(
        batter_woba.rename(columns={
            "batter": "next_batter", "woba": "next_woba", "pa_count": "next_pa",
        }),
        on=["next_batter", "game_year"], how="left",
    )
    ibb["next_woba_adj"] = ibb.apply(
        lambda r: _adj_woba(r, "next_woba", "next_pa", r["lg_woba"]), axis=1
    )
    ibb["next_imputed"] = ibb["next_pa"].isna() | (ibb["next_pa"] < MIN_PA) | ibb["next_batter"].isna()

    # ── Run value calculation ─────────────────────────────────────────────
    # run_value > 0: IBB saved runs (GOOD_IBB)
    # run_value <= 0: IBB cost runs (BAD_IBB)
    ibb["matchup_adv"] = (ibb["batter_woba_adj"] - ibb["next_woba_adj"]) / WOBA_SCALE
    ibb["run_value"]   = ibb["matchup_adv"] - ibb["re_cost"]

    # ── Output ────────────────────────────────────────────────────────────
    keep = [
        "game_pk", "game_date", "game_year", "inning", "inning_topbot",
        "at_bat_number", "outs_when_up",
        "batter", "fielding_team", "batting_team",
        "occ_1b", "occ_2b", "occ_3b",
        "post_1b", "post_2b", "post_3b", "ibb_run_scored",
        "re_before", "re_after", "re_cost",
        "batter_woba_adj", "batter_pa", "batter_imputed",
        "lg_woba",
        "next_batter", "next_woba_adj", "next_pa", "next_imputed",
        "matchup_adv", "run_value",
    ]
    ibb = ibb[[c for c in keep if c in ibb.columns]].copy()

    out = PROC / "ibb_opportunities.parquet"
    ibb.to_parquet(out, index=False)
    elapsed = int(time.time() - t0)
    print(f"\nSaved {len(ibb):,} IBB opportunities -> {out.name}")
    print(f"   done in {elapsed // 60}m {elapsed % 60}s")
    return ibb


if __name__ == "__main__":
    build_ibb_opportunities()
