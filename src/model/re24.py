"""
Run-expectancy (RE24) table and break-even P(safe) calculation.

The RE24 table maps base-out states to expected runs scored through end of inning.
State: (on_1b, on_2b, on_3b, outs) — each 0 or 1.

data/reference/re24_table.csv is a placeholder (modern-era MLB estimates from
published research). It will be recomputed from the 2020-2024 Statcast pull
once opportunities.parquet is built — see compute_re24_from_statcast() below.

State transition assumptions (stated explicitly for methodology writeup):
  - Runner from 3B (if present): always scores on any OF hit
  - Runner from 1B: advances to 2B on a single, to 3B on a double
  - Batter: reaches 1B on single, 2B on double
  - Outs 3 = end of inning, RE = 0
These simplify a small fraction of complex plays; effects are minor at the aggregate level.
"""
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
REF  = ROOT / "data" / "reference"

_re24_table: dict[tuple[int, int, int, int], float] = {}


def _load_table() -> None:
    global _re24_table
    if _re24_table:
        return
    df = pd.read_csv(REF / "re24_table.csv")
    for _, row in df.iterrows():
        key = (int(row["on_1b"]), int(row["on_2b"]), int(row["on_3b"]), int(row["outs"]))
        _re24_table[key] = float(row["re"])


def get_re(on_1b: int, on_2b: int, on_3b: int, outs: int) -> float:
    _load_table()
    if outs >= 3:
        return 0.0
    return _re24_table[(int(on_1b), int(on_2b), int(on_3b), int(outs))]


def compute_breakeven(row: pd.Series) -> dict | None:
    """
    Returns break-even P(safe) and the RE deltas needed to compute run value later.

    Returns None if the state is degenerate (RE_safe == RE_out).
    """
    outs  = int(row["outs_when_up"])
    on_1b = int(pd.notna(row.get("on_1b")))
    on_3b = int(pd.notna(row.get("on_3b")))
    is_dbl = row["events"] == "double"

    # Runs that score regardless of our runner's outcome
    # (Runner from 3B is assumed to score on any OF hit — true ~95% of the time)
    runs_others = on_3b

    if is_dbl:
        # Batter ends on 2B; runner from 1B goes to 3B
        b1_base = (0, 1, on_1b)   # (on_1b, on_2b, on_3b) after batter's hit, excluding our runner
    else:
        # Batter ends on 1B; runner from 1B goes to 2B
        b1_base = (1, on_1b, 0)

    # After SCORED: our runner not on base
    re_safe = runs_others + 1 + get_re(*b1_base, outs)

    # After OUT: our runner out at home (+1 out added)
    re_out  = runs_others + get_re(*b1_base, outs + 1)

    # After HOLD: our runner stops at 3B
    b1_hold = (b1_base[0], b1_base[1], 1)   # same as base state but on_3b forced to 1
    # Special case: if b1_base already has on_3b=1 (runner from 1B went to 3B on double),
    # hold is still valid — runner from 2B can't also be on 3B, so he's crowded out.
    # Approximate: if two runners would land on 3B, treat one as scoring (most favorable hold).
    if b1_base[2] == 1 and is_dbl:
        b1_hold = (b1_base[0], b1_base[1], 1)   # keep one runner on 3B; crowding simplified away
    re_hold = runs_others + get_re(*b1_hold, outs)

    denom = re_safe - re_out
    if abs(denom) < 0.001:
        return None

    p_be = max(0.0, min(1.0, (re_hold - re_out) / denom))
    return {
        "p_breakeven": p_be,
        "re_safe":     re_safe,
        "re_out":      re_out,
        "re_hold":     re_hold,
    }


def compute_re24_from_statcast(statcast_path: Path) -> pd.DataFrame:
    """
    Recompute RE24 from the full Statcast data.
    Replaces the placeholder values in re24_table.csv.

    For each plate appearance, RE = runs scored from that PA to end of inning.
    Requires grouping by (game_pk, inning, inning_topbot).
    """
    df = pd.read_parquet(statcast_path)

    # Keep one row per plate appearance (last pitch)
    pa = (
        df.sort_values(["game_pk", "at_bat_number", "pitch_number"])
        .groupby(["game_pk", "at_bat_number"])
        .last()
        .reset_index()
    )
    pa["on_1b_f"] = pa["on_1b"].notna().astype(int)
    pa["on_2b_f"] = pa["on_2b"].notna().astype(int)
    pa["on_3b_f"] = pa["on_3b"].notna().astype(int)
    pa["outs_f"]  = pa["outs_when_up"].astype(int)

    # Runs scored to end of inning: max(post_bat_score) - current bat_score within inning group
    pa["bat_score"] = pd.to_numeric(pa["bat_score"], errors="coerce")
    pa["post_bat_score"] = pd.to_numeric(pa.get("post_bat_score", pd.NA), errors="coerce")

    def inning_runs_remaining(group: pd.DataFrame) -> pd.Series:
        # post_bat_score at end of inning minus bat_score at each PA
        max_score = group["post_bat_score"].max() if "post_bat_score" in group else group["bat_score"].max()
        return max_score - group["bat_score"]

    pa["runs_roi"] = (
        pa.groupby(["game_pk", "inning", "inning_topbot"], group_keys=False)
        .apply(inning_runs_remaining)
    )

    re24 = (
        pa.groupby(["on_1b_f", "on_2b_f", "on_3b_f", "outs_f"])["runs_roi"]
        .mean()
        .reset_index()
        .rename(columns={"on_1b_f": "on_1b", "on_2b_f": "on_2b",
                         "on_3b_f": "on_3b", "outs_f": "outs", "runs_roi": "re"})
    )

    out_path = REF / "re24_table.csv"
    re24.to_csv(out_path, index=False)
    print(f"RE24 table recomputed from data -> {out_path}")
    print(re24.to_string(index=False))
    _re24_table.clear()   # force reload on next get_re() call
    return re24


if __name__ == "__main__":
    import sys
    sys.path.insert(0, str(ROOT))
    _load_table()
    print("RE24 table (placeholder):")
    for (b1, b2, b3, o), re in sorted(_re24_table.items()):
        print(f"  {b1}{b2}{b3} {o}out  {re:.2f}")
