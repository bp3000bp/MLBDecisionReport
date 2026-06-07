"""
Steal attempt grader.

Empirical P(safe) via 3-dimensional binning:
  - runner sprint speed tier (fast/medium/slow, based on season tertiles)
  - catcher pop time tier   (fast/average/slow, based on season tertiles)
  - outs_when_up            (0 / 1 / 2)

For each attempt: if P(safe) > P_be → GOOD_STEAL; else BAD_STEAL.
Run value per attempt = P(safe) × RE_safe + (1-P(safe)) × RE_out  –  RE_hold

Output: data/processed/steal_decisions.parquet

Run:
    python -m src.model.steal_grade
"""

from pathlib import Path

import pandas as pd
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
PROC = ROOT / "data" / "processed"

BIN_COLS        = ["speed_tier", "pop_tier", "outs_when_up"]
MIN_OBS         = 30    # minimum steal attempts per bin for stable P(safe)
SUCCESS_EVENTS  = {"stolen_base_2b", "stolen_base_3b"}


def _compute_tier(series: pd.Series, low_label: str = "slow", high_label: str = "fast") -> pd.Series:
    """Assign tertile-based tier (fast / medium / slow) using quantile cuts."""
    q33 = series.quantile(0.33)
    q67 = series.quantile(0.67)
    return pd.cut(
        series,
        bins=[-np.inf, q33, q67, np.inf],
        labels=[low_label, "medium", high_label],
        right=True,
    ).astype(str)


def compute_bins(df: pd.DataFrame) -> pd.DataFrame:
    """
    Returns a DataFrame of empirical P(safe) per bin.
    Bins with < MIN_OBS observations are flagged; their P(safe) falls back
    to the marginal rate for that outs level.
    """
    df = df.copy()

    # Tertile tiers (computed from the full dataset so they're stable across years)
    df["speed_tier"] = _compute_tier(df["runner_sprint_speed"].dropna().reindex(df.index))
    df["pop_tier"]   = _compute_tier(
        df["catcher_pop_time"].dropna().reindex(df.index),
        low_label="fast",   # lower pop time = better for catcher = harder for runner
        high_label="slow",
    )

    # Fill tiers for rows with missing speed / pop time (get median tier)
    for col in ["speed_tier", "pop_tier"]:
        df[col] = df[col].fillna("medium")

    df["outs_when_up"] = df["outs_when_up"].astype(int).astype(str)

    # Bin empirical P(safe)
    bin_grp = df.groupby(BIN_COLS, observed=True)["is_success"]
    bins = (
        bin_grp
        .agg(n_attempts="count", n_success="sum")
        .reset_index()
    )
    bins["p_safe_empirical"] = bins["n_success"] / bins["n_attempts"]
    bins["low_obs"]          = bins["n_attempts"] < MIN_OBS

    # For low-obs bins, use the marginal P(safe) for that outs level
    outs_marginal = (
        df.groupby("outs_when_up")["is_success"]
        .mean()
        .rename("p_safe_marginal")
        .reset_index()
    )
    bins = bins.merge(outs_marginal, on="outs_when_up", how="left")
    bins["p_safe_empirical"] = np.where(
        bins["low_obs"],
        bins["p_safe_marginal"],
        bins["p_safe_empirical"],
    )

    return bins[BIN_COLS + ["n_attempts", "n_success", "p_safe_empirical", "low_obs"]]


def apply_to_opps(df: pd.DataFrame, bins: pd.DataFrame) -> pd.DataFrame:
    """Join empirical P(safe) bins back to the opportunity-level data."""
    df = df.copy()

    # Rebuild tiers using the same logic as compute_bins
    speed_q33 = df["runner_sprint_speed"].quantile(0.33)
    speed_q67 = df["runner_sprint_speed"].quantile(0.67)
    pop_q33   = df["catcher_pop_time"].quantile(0.33)
    pop_q67   = df["catcher_pop_time"].quantile(0.67)

    df["speed_tier"] = pd.cut(
        df["runner_sprint_speed"],
        bins=[-np.inf, speed_q33, speed_q67, np.inf],
        labels=["slow", "medium", "fast"],
    ).astype(str).fillna("medium")

    df["pop_tier"] = pd.cut(
        df["catcher_pop_time"],
        bins=[-np.inf, pop_q33, pop_q67, np.inf],
        labels=["fast", "medium", "slow"],
    ).astype(str).fillna("medium")

    df["outs_when_up"] = df["outs_when_up"].astype(int).astype(str)

    df = df.merge(
        bins[BIN_COLS + ["p_safe_empirical", "low_obs", "n_attempts"]],
        on=BIN_COLS,
        how="left",
    )
    return df


def grade(df: pd.DataFrame) -> pd.DataFrame:
    """
    Assigns decision grades and computes run value.

    Run value per attempt:
        rv = P(safe) × RE_safe + (1 - P(safe)) × RE_out  –  RE_hold
        Positive = attempt added value vs holding.
        Negative = attempt cost value vs holding.
    """
    df = df.copy()

    df["decision"] = np.where(
        df["p_safe_empirical"] >= df["p_breakeven"],
        "GOOD_STEAL",
        "BAD_STEAL",
    )

    df["run_value"] = (
        df["p_safe_empirical"] * df["re_safe"]
        + (1 - df["p_safe_empirical"]) * df["re_out"]
        - df["re_hold"]
    )

    return df


def print_bin_table(bins: pd.DataFrame) -> None:
    print("\nEmpirical P(safe) bins:")
    print(f"{'speed':10} {'pop':10} {'outs':6} {'n':>7} {'p_safe':>8} {'low_obs':>8}")
    print("-" * 55)
    for _, r in bins.sort_values(BIN_COLS).iterrows():
        flag = "*" if r["low_obs"] else ""
        print(
            f"{r['speed_tier']:10} {r['pop_tier']:10} {r['outs_when_up']:6} "
            f"{r['n_attempts']:>7.0f} {r['p_safe_empirical']:>8.3f} {flag:>8}"
        )
    print("  * = below MIN_OBS threshold; marginal outs-level rate used")


def build_steal_decisions() -> pd.DataFrame:
    opp_path = PROC / "steal_opportunities.parquet"
    if not opp_path.exists():
        raise FileNotFoundError(
            "steal_opportunities.parquet not found — run src/features/steal_opportunities.py first"
        )
    df = pd.read_parquet(opp_path)

    # Drop rows we can't grade (no break-even, missing sprint speed)
    n_raw = len(df)
    df = df.dropna(subset=["p_breakeven", "runner_sprint_speed"])
    print(f"Loaded {n_raw:,} steal opportunities; {len(df):,} gradeable")

    # Compute bins and apply
    bins = compute_bins(df)
    print_bin_table(bins)

    df = apply_to_opps(df, bins)
    df = grade(df)

    print(f"\nDecision breakdown:")
    print(df["decision"].value_counts().to_string())
    print(f"\nMean run value per attempt: {df['run_value'].mean():.3f}")
    print(f"Good steal rate: {(df['decision']=='GOOD_STEAL').mean():.1%}")
    print(f"Overall success rate: {df['is_success'].mean():.1%}")

    out_path = PROC / "steal_decisions.parquet"
    df.to_parquet(out_path, index=False)
    print(f"\nSaved {len(df):,} graded steal decisions -> {out_path}")
    return df


if __name__ == "__main__":
    import sys
    sys.path.insert(0, str(ROOT))
    build_steal_decisions()
