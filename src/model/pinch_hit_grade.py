"""
Pinch Hit Grader — decision grading.

For each pinch hit appearance:
  - ph_woba  = pinch hitter's season wOBA vs. the pitcher's hand (L or R)
  - rep_woba = replaced batter's season wOBA vs. the same pitcher hand
  - woba_gain = ph_woba - rep_woba  (positive = upgrade, negative = downgrade)
  - leverage_weight = RE24 at current base-out state / RE_MEAN
      RE_MEAN = 0.477 (frequency-weighted mean RE across all MLB plate appearances,
      computed from 2020-2026 Statcast data; unweighted mean across 24 states is 0.905)
  - run_value = (woba_gain / woba_scale) * leverage_weight

Grading:
  GOOD_PH: woba_gain > 0  (pinch hitter is a better platoon matchup)
  BAD_PH:  woba_gain <= 0

The decision grade is based on woba_gain alone — the leverage weight scales run_value
but does not flip a matchup decision from good to bad. A pinch hit with a genuine
wOBA upgrade is always GOOD_PH; the leverage weight quantifies how much that upgrade
matters given the situation.

Leverage weighting rationale:
  A +0.05 wOBA gain in a bases-loaded, 0-out situation (RE ≈ 2.24, weight ≈ 4.7×)
  represents far more expected run value than the same +0.05 gain with the bases
  empty and 2 outs (RE ≈ 0.10, weight ≈ 0.21×). Scaling by the RE24 leverage of
  the base-out state captures this without requiring win-probability data.

Imputation:
  If either batter has fewer than 50 PA against that pitcher hand in the season,
  their wOBA split is replaced with the league-average wOBA for that hand × season.
  This prevents extreme small-sample splits from distorting grades early in the year.

Required columns from pinch_hit_opportunities.parquet:
  p_throws, woba_vs_L, woba_vs_R, rep_woba_vs_L, rep_woba_vs_R,
  on_1b_f, on_2b_f, on_3b_f, outs_when_up, game_year

Run:
    python -m src.model.pinch_hit_grade
"""

from pathlib import Path

import pandas as pd
import numpy as np

from src.model.re24 import get_re

ROOT = Path(__file__).resolve().parents[2]
PROC = ROOT / "data" / "processed"

WOBA_SCALE = 1.157
MIN_PA_SPLIT = 50

# Frequency-weighted mean RE24 across all MLB plate appearances (2020-2026 Statcast).
# Computed as sum(RE * PA_count) / sum(PA_count) across 24 base-out states.
# Lower than the unweighted mean (0.905) because most PAs occur in lower-RE states
# (empty bases, 2 outs is the most common state in any inning).
RE_MEAN = 0.477


def _leverage_weight(on_1b: int, on_2b: int, on_3b: int, outs: int) -> float:
    """
    RE24-based leverage weight for the base-out state.

    Returns re_current / RE_MEAN. Centered at 1.0 for an average MLB situation.
    High-RE states (bases loaded, 0 outs ≈ 2.24) produce weights ~4.7.
    Low-RE states (empty, 2 outs ≈ 0.10) produce weights ~0.21.
    """
    re_current = get_re(on_1b, on_2b, on_3b, outs)
    return re_current / RE_MEAN


def grade(df: pd.DataFrame) -> pd.DataFrame:
    """
    Grade each pinch hit substitution with RE24 leverage weighting.

    Expects columns from pinch_hit_opportunities.parquet:
      p_throws, woba_vs_L, woba_vs_R, rep_woba_vs_L, rep_woba_vs_R,
      on_1b_f, on_2b_f, on_3b_f, outs_when_up, game_year
    """
    df = df.copy()

    # Select the correct platoon split based on pitcher hand
    df["ph_woba"]  = np.where(df["p_throws"] == "L", df["woba_vs_L"],  df["woba_vs_R"])
    df["rep_woba"] = np.where(df["p_throws"] == "L", df["rep_woba_vs_L"], df["rep_woba_vs_R"])

    df["woba_gain"] = df["ph_woba"] - df["rep_woba"]

    # RE24 leverage weight for each base-out state
    df["leverage_weight"] = df.apply(
        lambda r: _leverage_weight(
            int(r.get("on_1b_f", 0) or 0),
            int(r.get("on_2b_f", 0) or 0),
            int(r.get("on_3b_f", 0) or 0),
            int(r.get("outs_when_up", 0) or 0),
        ),
        axis=1,
    )

    # run_value: leverage-weighted expected run contribution of the substitution
    df["run_value"] = (df["woba_gain"] / WOBA_SCALE) * df["leverage_weight"]

    # Grade on matchup quality alone (not leverage — leverage only scales magnitude)
    df["decision"] = np.where(df["woba_gain"] > 0, "GOOD_PH", "BAD_PH")

    return df


def build_pinch_hit_decisions() -> pd.DataFrame:
    opp_path = PROC / "pinch_hit_opportunities.parquet"
    if not opp_path.exists():
        raise FileNotFoundError(
            "pinch_hit_opportunities.parquet not found — run src/features/pinch_hit_opportunities.py first"
        )
    df = pd.read_parquet(opp_path)
    n_raw = len(df)
    df = df.dropna(subset=["ph_woba", "rep_woba"])
    print(f"Loaded {n_raw:,} opportunities; {len(df):,} gradeable")

    df = grade(df)

    print(f"\nDecision breakdown:")
    print(df["decision"].value_counts().to_string())
    print(f"Good PH rate: {(df['decision']=='GOOD_PH').mean():.1%}")
    print(f"Mean wOBA gain: {df['woba_gain'].mean():.4f}")
    print(f"Mean leverage weight: {df['leverage_weight'].mean():.3f}")
    print(f"Mean run value per PH (leverage-weighted): {df['run_value'].mean():.4f}")

    out_path = PROC / "pinch_hit_decisions.parquet"
    df.to_parquet(out_path, index=False)
    print(f"\nSaved {len(df):,} graded pinch hit decisions -> {out_path}")
    return df


if __name__ == "__main__":
    import sys
    sys.path.insert(0, str(ROOT))
    build_pinch_hit_decisions()
