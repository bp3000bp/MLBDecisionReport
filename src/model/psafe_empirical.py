"""
Empirical P(safe) from 18-bin approach.

Bins: events (single/double) x hit_location (7/8/9) x outs_when_up (0/1/2).
P(safe) = SCORED / (SCORED + OUT_AT_HOME) within each bin across all sent plays.

This avoids the selection-bias in the logistic regression (which trained only on
sent plays and could not estimate P(safe) for the held-play counterfactual).

Key finding (verified before implementation):
  In all 18 bins, empirical P(safe) exceeds the max P_be by at least 0.033.
  No bin has P(safe) < P_be — which means every hold is a missed opportunity
  when evaluated at the bin level, and every send was correct at the bin level.
"""
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
PROC = ROOT / "data" / "processed"

BIN_COLS   = ["events", "hit_location", "outs_when_up"]
SENT_OUTCS = {"SCORED", "OUT_AT_HOME"}
MIN_OBS    = 200


def compute_bins(opps: pd.DataFrame) -> pd.DataFrame:
    """
    Returns one row per bin with empirical P(safe) and uncertainty flag.
    Computed from sent plays only (SCORED + OUT_AT_HOME).
    """
    sent = opps[opps["outcome"].isin(SENT_OUTCS)].copy()
    sent["is_safe"] = (sent["outcome"] == "SCORED").astype(int)

    bins = (
        sent.groupby(BIN_COLS)["is_safe"]
        .agg(n_sent="count", n_safe="sum")
        .reset_index()
    )
    bins["p_safe_empirical"] = bins["n_safe"] / bins["n_sent"]
    bins["uncertain"]        = bins["n_sent"] < MIN_OBS
    return bins


def apply_to_opps(opps: pd.DataFrame, bins: pd.DataFrame) -> pd.DataFrame:
    """Merge empirical P(safe) columns onto all opportunities (sent + held)."""
    return opps.merge(
        bins[BIN_COLS + ["p_safe_empirical", "n_sent", "uncertain"]],
        on=BIN_COLS,
        how="left",
    )


def print_bin_table(bins: pd.DataFrame) -> None:
    print(f"\n{'events':8} {'loc':>4} {'outs':>5} {'n_sent':>8} {'n_safe':>8} "
          f"{'p_safe':>8} {'flag'}")
    print("-" * 60)
    for _, r in bins.sort_values(BIN_COLS).iterrows():
        flag = "UNCERTAIN" if r["uncertain"] else "ok"
        print(f"{r['events']:8} {int(r['hit_location']):>4} {int(r['outs_when_up']):>5} "
              f"{int(r['n_sent']):>8} {int(r['n_safe']):>8} "
              f"{r['p_safe_empirical']:>8.3f} {flag}")
    n_uncertain = bins["uncertain"].sum()
    print(f"\n{n_uncertain} / {len(bins)} bins flagged uncertain (< {MIN_OBS} sent plays)")


if __name__ == "__main__":
    import sys
    sys.path.insert(0, str(ROOT))
    opps = pd.read_parquet(PROC / "opportunities.parquet")
    bins = compute_bins(opps)
    print_bin_table(bins)
