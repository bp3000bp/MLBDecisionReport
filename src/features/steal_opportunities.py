"""
Builds the steal-attempt opportunity table.

Sources:
  - data/raw/steal_events_{year}.parquet  (from MLBAM play-by-play via steal_events.py)
  - data/raw/statcast_{year}.parquet      (base-out state, catcher fielder_2)
  - data/raw/sprint_speed_{year}.parquet  (runner speed)
  - data/reference/poptime_{year}.csv     (catcher pop time to 2B/3B)
  - data/reference/re24_table.csv         (run-expectancy states)

Output:
  data/processed/steal_opportunities.parquet

Join logic:
  steal_events.at_bat_number (= atBatIndex + 1) matches statcast.at_bat_number
  per game_pk.  The statcast row gives us on_1b/2b/3b, outs_when_up, fielder_2
  (catcher MLBAM id), and team info.  Catcher from credits (caught-stealing only)
  takes priority over fielder_2.

Run:
    python -m src.features.steal_opportunities
"""

from pathlib import Path

import pandas as pd

from src.model.re24 import get_re

ROOT = Path(__file__).resolve().parents[2]
RAW  = ROOT / "data" / "raw"
REF  = ROOT / "data" / "reference"
PROC = ROOT / "data" / "processed"
PROC.mkdir(parents=True, exist_ok=True)

SEASONS = [2020, 2021, 2022, 2023, 2024, 2025, 2026]

# Focus on 2B and 3B steals for v1
STEAL_2B = {"stolen_base_2b", "caught_stealing_2b", "pickoff_caught_stealing_2b"}
STEAL_3B = {"stolen_base_3b", "caught_stealing_3b", "pickoff_caught_stealing_3b"}
HOME_EVENTS = {"stolen_base_home", "caught_stealing_home"}   # excluded from v1

# Minimum catcher pop-time observations to use (otherwise use league avg)
MIN_POP_OBS = 10


# ── Loaders ───────────────────────────────────────────────────────────────────

def _load_steal_events() -> pd.DataFrame:
    chunks = []
    for yr in SEASONS:
        p = RAW / f"steal_events_{yr}.parquet"
        if not p.exists():
            print(f"  MISSING steal_events_{yr}.parquet — run src/ingest/steal_events.py first")
            continue
        chunks.append(pd.read_parquet(p))
    if not chunks:
        raise FileNotFoundError("No steal event parquets found.")
    df = pd.concat(chunks, ignore_index=True)
    return df


def _build_sc_ab_context() -> pd.DataFrame:
    """
    One row per (game_pk, at_bat_number) with base-out state and catcher ID.
    Uses the first pitch of each at-bat (outs_when_up and on_* don't change
    within an at-bat).
    """
    chunks = []
    for yr in SEASONS:
        p = RAW / f"statcast_{yr}.parquet"
        if not p.exists():
            print(f"  MISSING statcast_{yr}.parquet")
            continue
        sc = pd.read_parquet(p, columns=[
            "game_pk", "at_bat_number", "pitch_number",
            "game_date", "inning", "inning_topbot",
            "outs_when_up", "on_1b", "on_2b", "on_3b",
            "fielder_2", "home_team", "away_team",
            "bat_score", "fld_score",
        ])
        chunks.append(sc)

    sc_all = pd.concat(chunks, ignore_index=True)
    sc_all["game_year"] = sc_all["game_date"].astype(str).str[:4].astype(int)

    # First pitch per at-bat to get the pre-AB base state
    first_pitch = (
        sc_all
        .sort_values(["game_pk", "at_bat_number", "pitch_number"])
        .groupby(["game_pk", "at_bat_number"], as_index=False)
        .first()
    )
    # Catcher: some pitches have null fielder_2 (IBBs); take the first non-null
    catcher_map = (
        sc_all.dropna(subset=["fielder_2"])
        .sort_values(["game_pk", "at_bat_number", "pitch_number"])
        .groupby(["game_pk", "at_bat_number"])["fielder_2"]
        .first()
        .reset_index()
        .rename(columns={"fielder_2": "catcher_id_sc"})
    )
    ctx = first_pitch.merge(catcher_map, on=["game_pk", "at_bat_number"], how="left")
    return ctx


def _load_sprint_speed() -> dict[tuple[int, int], float]:
    """Returns {(player_id_int, year): sprint_speed}"""
    out: dict[tuple[int, int], float] = {}
    for yr in SEASONS:
        p = RAW / f"sprint_speed_{yr}.parquet"
        if not p.exists():
            continue
        sp = pd.read_parquet(p)[["player_id", "sprint_speed"]].dropna()
        for _, row in sp.iterrows():
            out[(int(row["player_id"]), yr)] = float(row["sprint_speed"])
    return out


def _load_pop_time() -> tuple[pd.DataFrame, dict[tuple[int, int, str], float]]:
    """
    Returns (raw_df, lookup) where lookup is:
        {(catcher_mlbam_id, year, 'pop_2b_sba'|'pop_3b_sba'): pop_time_seconds}
    Only catchers with >= MIN_POP_OBS are included; others get league-average imputation later.
    """
    frames = []
    for yr in SEASONS:
        p = REF / f"poptime_{yr}.csv"
        if not p.exists():
            continue
        df = pd.read_csv(p)
        df["game_year"] = yr
        frames.append(df)
    if not frames:
        return pd.DataFrame(), {}

    pop = pd.concat(frames, ignore_index=True)
    lookup: dict[tuple[int, int, str], float] = {}
    for _, row in pop.iterrows():
        eid = int(row["entity_id"])
        yr  = int(row["game_year"])
        for col in ["pop_2b_sba", "pop_3b_sba"]:
            cnt_col = col.replace("_sba", "_sba_count")
            if cnt_col in row and pd.notna(row[cnt_col]) and int(row[cnt_col]) < MIN_POP_OBS:
                continue   # too few obs; will get league avg
            val = row.get(col)
            if pd.notna(val):
                lookup[(eid, yr, col)] = float(val)
    return pop, lookup


# ── Break-even calculation ────────────────────────────────────────────────────

def _compute_breakeven_steal(row: pd.Series) -> dict | None:
    """
    Break-even P(safe) for a steal attempt.

    We assert the definitional pre-steal state (the steal type tells us which
    base must be empty and which runner is moving) and use statcast only for
    uninvolved runners: on_3b for steal-of-2B; on_1b for steal-of-3B.  This
    handles double-steal situations where statcast's at-bat-start state would
    otherwise show the simultaneous steal partner as still occupying their base.
    """
    outs = int(row["outs_when_up"])
    base = row["base_stolen"]

    # "Other" runner positions from statcast at-bat start (best available approximation)
    on_3b_statcast = int(row["on_3b_f"]) if pd.notna(row.get("on_3b_f")) else 0
    on_1b_statcast = int(row["on_1b_f"]) if pd.notna(row.get("on_1b_f")) else 0

    if base == "2B":
        # Definitional pre-steal state: runner on 1B (on_1b=1), 2B empty (on_2b=0)
        re_hold = get_re(on_1b=1, on_2b=0, on_3b=on_3b_statcast, outs=outs)
        re_safe = get_re(on_1b=0, on_2b=1, on_3b=on_3b_statcast, outs=outs)
        re_out  = get_re(on_1b=0, on_2b=0, on_3b=on_3b_statcast, outs=outs + 1)
    elif base == "3B":
        # Definitional pre-steal state: runner on 2B (on_2b=1), 3B empty (on_3b=0)
        re_hold = get_re(on_1b=on_1b_statcast, on_2b=1, on_3b=0, outs=outs)
        re_safe = get_re(on_1b=on_1b_statcast, on_2b=0, on_3b=1, outs=outs)
        re_out  = get_re(on_1b=on_1b_statcast, on_2b=0, on_3b=0, outs=outs + 1)
    else:
        return None   # home steals excluded from v1

    denom = re_safe - re_out
    if abs(denom) < 0.001:
        return None

    p_be = max(0.0, min(1.0, (re_hold - re_out) / denom))
    return {
        "p_breakeven": p_be,
        "re_hold": re_hold,
        "re_safe": re_safe,
        "re_out":  re_out,
    }


# ── Main ─────────────────────────────────────────────────────────────────────

def build_steal_opportunities() -> pd.DataFrame:
    print("Loading steal events...")
    steal = _load_steal_events()
    # Exclude home steals from v1
    steal = steal[~steal["event_type"].isin(HOME_EVENTS)].copy()
    steal["base_stolen"] = steal["event_type"].apply(
        lambda e: "2B" if e in STEAL_2B else "3B"
    )
    print(f"  {len(steal):,} steal events (2B+3B) across {steal['game_year'].nunique()} seasons")

    print("Building statcast at-bat context...")
    ctx = _build_sc_ab_context()
    ctx["on_1b_f"] = ctx["on_1b"].notna().astype(int)
    ctx["on_2b_f"] = ctx["on_2b"].notna().astype(int)
    ctx["on_3b_f"] = ctx["on_3b"].notna().astype(int)

    # Derive batting team from inning_topbot and home/away
    ctx["batting_team"] = ctx.apply(
        lambda r: r["away_team"] if r["inning_topbot"] == "Top" else r["home_team"],
        axis=1,
    )

    # Join steal events to statcast AB context
    steal = steal.merge(
        ctx[[
            "game_pk", "at_bat_number",
            "on_1b_f", "on_2b_f", "on_3b_f", "outs_when_up",
            "catcher_id_sc", "batting_team", "home_team", "away_team",
            "inning", "bat_score", "fld_score",
        ]],
        on=["game_pk", "at_bat_number"],
        how="left",
    )

    # Catcher ID: credits (caught stealing) > statcast fielder_2
    steal["catcher_id"] = steal["catcher_id_credits"].fillna(steal["catcher_id_sc"])
    steal["catcher_id"] = pd.to_numeric(steal["catcher_id"], errors="coerce")

    joined = len(steal)
    missing_ctx = steal["outs_when_up"].isna().sum()
    print(f"  Context join: {joined - missing_ctx}/{joined} rows matched ({missing_ctx} missing)")

    # Drop rows where we can't compute break-even
    steal = steal.dropna(subset=["outs_when_up"])

    print("Loading sprint speed...")
    speed_lookup = _load_sprint_speed()
    steal["runner_sprint_speed"] = steal.apply(
        lambda r: speed_lookup.get((int(r["runner_id"]), int(r["game_year"])))
        if pd.notna(r["runner_id"]) and pd.notna(r["game_year"]) else None,
        axis=1,
    )
    print(f"  Sprint speed join rate: {steal['runner_sprint_speed'].notna().mean():.0%}")

    print("Loading catcher pop time...")
    pop_df, pop_lookup = _load_pop_time()
    league_avg_2b = (
        pop_df.groupby("game_year")["pop_2b_sba"].mean().to_dict()
        if not pop_df.empty else {}
    )
    league_avg_3b = (
        pop_df.groupby("game_year")["pop_3b_sba"].mean().to_dict()
        if not pop_df.empty else {}
    )

    def get_pop(row):
        yr  = int(row["game_year"]) if pd.notna(row["game_year"]) else None
        cid = int(row["catcher_id"]) if pd.notna(row["catcher_id"]) else None
        col = "pop_2b_sba" if row["base_stolen"] == "2B" else "pop_3b_sba"
        if cid and yr:
            val = pop_lookup.get((cid, yr, col))
            if val is not None:
                return val, False  # (pop_time, is_imputed)
        avg = (league_avg_2b if col == "pop_2b_sba" else league_avg_3b).get(yr)
        return avg, True

    pop_results = steal.apply(get_pop, axis=1)
    steal["catcher_pop_time"] = [r[0] for r in pop_results]
    steal["catcher_pop_imputed"] = [r[1] for r in pop_results]
    print(f"  Pop time join rate: {steal['catcher_pop_time'].notna().mean():.0%}")
    print(f"  Pop time imputed:   {steal['catcher_pop_imputed'].mean():.0%}")

    print("Computing RE24 break-even...")
    be_results = steal.apply(_compute_breakeven_steal, axis=1)
    steal["p_breakeven"] = [r["p_breakeven"] if r else None for r in be_results]
    steal["re_hold"]     = [r["re_hold"]     if r else None for r in be_results]
    steal["re_safe"]     = [r["re_safe"]     if r else None for r in be_results]
    steal["re_out"]      = [r["re_out"]      if r else None for r in be_results]

    n_be = steal["p_breakeven"].notna().sum()
    print(f"  Break-even computed for {n_be}/{len(steal)} rows")

    # Save
    keep_cols = [
        "game_pk", "game_year", "inning", "batting_team", "home_team", "away_team",
        "outs_when_up", "on_1b_f", "on_2b_f", "on_3b_f", "bat_score", "fld_score",
        "at_bat_number", "half_inning",
        "event_type", "base_stolen", "is_success",
        "runner_id", "runner_name", "runner_sprint_speed",
        "catcher_id", "catcher_pop_time", "catcher_pop_imputed",
        "p_breakeven", "re_hold", "re_safe", "re_out",
    ]
    out = steal[[c for c in keep_cols if c in steal.columns]].copy()
    out_path = PROC / "steal_opportunities.parquet"
    out.to_parquet(out_path, index=False)
    print(f"\nSaved {len(out):,} steal opportunities -> {out_path}")
    print("Base stolen breakdown:")
    print(out["base_stolen"].value_counts().to_string())
    print("Success rate:", out["is_success"].mean().round(3))
    return out


if __name__ == "__main__":
    import sys
    sys.path.insert(0, str(ROOT))
    build_steal_opportunities()
