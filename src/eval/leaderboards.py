"""
Builds team-year and coach-career leaderboards from graded decisions.

Aggregation levels:
  1. batting_team x game_year  (with coach_name if coaches_3b.csv present)
  2. coach_name (career totals across all seasons coached)

Coach low-sample flag: < 150 total opportunities => low_sample = True.
2020 season flag: 60-game season; n_opportunities may be ~50-80 per team.

Primary narrative metric (empirical bin approach):
  bad_hold_runs_per100 -- runs left on table by holding, per 100 opportunities
  (high = coach over-held relative to break-even)

Saves:
  data/processed/leaderboard_team.parquet / .csv
  data/processed/leaderboard_coach.parquet / .csv  (only if coaches_3b.csv exists)
"""
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
PROC = ROOT / "data" / "processed"
REF  = ROOT / "data" / "reference"

LOW_SAMPLE_OPP = 150


def _batting_team(row: pd.Series) -> str:
    return row["home_team"] if row.get("inning_topbot") == "Bot" else row["away_team"]


def agg_group(g: pd.DataFrame) -> pd.Series:
    sent   = g["outcome"].isin(["SCORED", "OUT_AT_HOME"])
    held   = g["outcome"] == "HELD_AT_BASE"
    scored = g["outcome"] == "SCORED"
    bad_s  = g["decision_grade"] == "BAD_SEND"
    bad_h  = g["decision_grade"] == "BAD_HOLD"
    n_opp  = max(len(g), 1)

    bad_hold_rv = g.loc[bad_h, "run_value"].sum()
    bad_send_rv = g.loc[bad_s, "run_value"].sum()

    return pd.Series({
        "n_opportunities":       int(len(g)),
        "n_sent":                int(sent.sum()),
        "n_held":                int(held.sum()),
        "n_bad_send":            int(bad_s.sum()),
        "n_bad_hold":            int(bad_h.sum()),
        "bad_send_runs":         round(bad_send_rv, 2),
        "bad_hold_runs":         round(bad_hold_rv, 2),
        "net_run_value":         round(g["run_value"].sum(), 2),
        "bad_hold_runs_per100":  round(bad_hold_rv  / n_opp * 100, 2),
        "bad_send_runs_per100":  round(bad_send_rv  / n_opp * 100, 2),
        "net_run_value_per100":  round(g["run_value"].sum() / n_opp * 100, 2),
        "safe_rate":             round(scored.sum() / max(sent.sum(), 1), 3),
        "send_rate":             round(sent.sum()  / n_opp, 3),
    })


def _print_lb(lb: pd.DataFrame, label: str, key_cols: list[str]) -> None:
    print(f"\n{'='*64}")
    print(f"{label}")
    print(f"{'='*64}")
    print("\nTop 10 (most runs left on table per 100 opp):")
    print(lb.head(10)[key_cols].to_string(index=False))
    print("\nBottom 10 (fewest runs left / most aggressive):")
    print(lb.tail(10)[key_cols].to_string(index=False))


def build_leaderboards() -> pd.DataFrame:
    graded = pd.read_parquet(PROC / "graded_decisions.parquet")
    graded = graded[graded["decision_grade"] != "UNGRADED"].copy()
    graded["batting_team"] = graded.apply(_batting_team, axis=1)

    # Baseball Reference uses different abbreviations than Statcast for 8 teams
    BR_TO_SC = {"ARI": "AZ", "CHW": "CWS", "KCR": "KC", "OAK": "ATH",
                "SDP": "SD", "SFG": "SF", "TBR": "TB", "WSN": "WSH"}

    has_coaches = False
    coaches_path = REF / "coaches_3b.csv"
    if coaches_path.exists():
        coaches = pd.read_csv(coaches_path)
        required = {"team", "game_year", "coach_name"}
        if required.issubset(coaches.columns):
            coaches["team"] = coaches["team"].replace(BR_TO_SC)
            graded = graded.merge(
                coaches.rename(columns={"team": "batting_team"}),
                on=["batting_team", "game_year"],
                how="left",
            )
            has_coaches = True
            n_missing = graded["coach_name"].isna().sum()
            if n_missing:
                print(f"  WARN: {n_missing} graded plays have no coach match — check coaches_3b.csv")
        else:
            print(f"  WARN: coaches_3b.csv missing columns {required - set(coaches.columns)}")

    # ── Team-year leaderboard ─────────────────────────────────────────────
    group_cols = ["batting_team", "game_year"]
    if has_coaches and "coach_name" in graded.columns:
        group_cols.append("coach_name")

    lb_team = (
        graded
        .groupby(group_cols, group_keys=False)[graded.columns.difference(group_cols)]
        .apply(agg_group)
        .reset_index()
    )
    lb_team["low_sample"] = lb_team["n_opportunities"] < LOW_SAMPLE_OPP
    lb_team["short_season"] = lb_team["game_year"] == 2020
    lb_team = lb_team.sort_values("bad_hold_runs_per100", ascending=False)

    out_pq  = PROC / "leaderboard_team.parquet"
    out_csv = PROC / "leaderboard_team.csv"
    lb_team.to_parquet(out_pq, index=False)
    lb_team.to_csv(out_csv, index=False)
    print(f"Team leaderboard ({len(lb_team)} rows) -> {out_csv}")

    key_cols = ["batting_team", "game_year", "n_opportunities",
                "n_bad_hold", "bad_hold_runs", "bad_hold_runs_per100",
                "send_rate", "low_sample"]
    if has_coaches:
        key_cols.insert(2, "coach_name")
    _print_lb(lb_team, "TEAM-YEAR LEADERBOARD", key_cols)

    low = lb_team[lb_team["low_sample"]]
    if len(low):
        print(f"\n  ({len(low)} rows flagged low_sample — interpret with caution)")

    # ── Coach career leaderboard (if coaches loaded) ──────────────────────
    if has_coaches and "coach_name" in graded.columns:
        coaches_graded = graded[graded["coach_name"].notna()].copy()
        lb_coach = (
            coaches_graded
            .groupby("coach_name", group_keys=False)[coaches_graded.columns.difference(["coach_name"])]
            .apply(agg_group)
            .reset_index()
        )
        lb_coach["low_sample"]    = lb_coach["n_opportunities"] < LOW_SAMPLE_OPP
        lb_coach["seasons_coached"] = (
            graded[graded["coach_name"].notna()]
            .groupby("coach_name")["game_year"].nunique()
            .reindex(lb_coach["coach_name"])
            .values
        )
        lb_coach = lb_coach.sort_values("bad_hold_runs_per100", ascending=False)

        coach_pq  = PROC / "leaderboard_coach.parquet"
        coach_csv = PROC / "leaderboard_coach.csv"
        lb_coach.to_parquet(coach_pq, index=False)
        lb_coach.to_csv(coach_csv, index=False)
        print(f"\nCoach leaderboard ({len(lb_coach)} coaches) -> {coach_csv}")

        coach_key = ["coach_name", "seasons_coached", "n_opportunities",
                     "bad_hold_runs", "bad_hold_runs_per100", "send_rate", "low_sample"]
        _print_lb(lb_coach, "COACH CAREER LEADERBOARD", coach_key)

        low_coaches = lb_coach[lb_coach["low_sample"]]
        if len(low_coaches):
            print(f"\n  ({len(low_coaches)} coaches flagged low_sample < {LOW_SAMPLE_OPP} opportunities)")

    return lb_team


if __name__ == "__main__":
    sys.path.insert(0, str(ROOT))
    build_leaderboards()
