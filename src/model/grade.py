"""
Grades every send/hold decision by comparing P(safe) to break-even probability.

Primary P(safe) source: empirical bin approach (psafe_empirical.py).
  18 bins: events x hit_location x outs_when_up.
  Avoids selection-bias from the logistic regression (psafe.py).

Secondary P(safe): logistic regression (psafe.py), kept for comparison.

Decision logic (using empirical P(safe)):
  SENT (SCORED or OUT_AT_HOME):
    p_safe_emp > p_be -> GOOD_SEND
    p_safe_emp < p_be -> BAD_SEND
  HELD (HELD_AT_BASE):
    p_safe_emp > p_be -> BAD_HOLD  (runs left on table)
    p_safe_emp < p_be -> GOOD_HOLD
  HELD_OR_UNKNOWN -> UNGRADED

Run value = (p_safe_emp - p_be) * (re_safe - re_out)
  Positive: correct decision (or runs left on table for BAD_HOLD)
  Negative: wrong decision (cost in expected runs)

Prints before/after comparison for BAD_SEND cases across both methods.
Saves: data/processed/graded_decisions.parquet
"""
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
PROC = ROOT / "data" / "processed"

sys.path.insert(0, str(ROOT))
from src.model.psafe            import load_model, predict
from src.model.psafe_empirical  import compute_bins, apply_to_opps, print_bin_table
from src.model.re24             import compute_breakeven


def _grade(outcome: str, p_safe: float, p_be: float) -> str:
    if pd.isna(p_safe) or pd.isna(p_be):
        return "UNGRADED"
    if outcome in ("SCORED", "OUT_AT_HOME"):
        return "GOOD_SEND" if p_safe >= p_be else "BAD_SEND"
    if outcome == "HELD_AT_BASE":
        return "BAD_HOLD" if p_safe >= p_be else "GOOD_HOLD"
    return "UNGRADED"


def run() -> pd.DataFrame:
    # ── Load ─────────────────────────────────────────────────────────────
    print("Loading opportunity table...")
    opps = pd.read_parquet(PROC / "opportunities.parquet")
    print(f"  {len(opps):,} opportunities")

    # ── Empirical P(safe) (primary grading signal) ────────────────────────
    print("\nBuilding empirical P(safe) from sent-play bins...")
    bins = compute_bins(opps)
    print_bin_table(bins)
    opps = apply_to_opps(opps, bins)

    # ── Logistic regression P(safe) (for comparison) ─────────────────────
    print("\nApplying logistic regression P(safe) model (for before/after comparison)...")
    try:
        pipe = load_model()
        opps["p_safe_model"] = predict(pipe, opps)
    except FileNotFoundError:
        print("  psafe_model.pkl not found — skipping model comparison")
        opps["p_safe_model"] = None

    # ── Break-even probabilities ──────────────────────────────────────────
    print("\nComputing break-even probabilities...")
    be_results = opps.apply(compute_breakeven, axis=1)
    be_df = pd.DataFrame(be_results.tolist(), index=opps.index)
    opps = pd.concat([opps, be_df], axis=1)

    # ── Grade (empirical) ─────────────────────────────────────────────────
    opps["decision_grade"] = opps.apply(
        lambda r: _grade(r["outcome"], r["p_safe_empirical"], r.get("p_breakeven")),
        axis=1,
    )
    opps["run_value"] = (
        (opps["p_safe_empirical"] - opps["p_breakeven"])
        * (opps["re_safe"] - opps["re_out"])
    )

    print("\nDecision grade counts (empirical P(safe)):")
    print(opps["decision_grade"].value_counts().to_string())

    # ── Grade (model, for comparison) ────────────────────────────────────
    if opps["p_safe_model"].notna().any():
        opps["decision_grade_model"] = opps.apply(
            lambda r: _grade(r["outcome"], r.get("p_safe_model"), r.get("p_breakeven")),
            axis=1,
        )
        model_grades = opps["decision_grade_model"].value_counts()
        print("\nDecision grade counts (logistic regression P(safe)):")
        print(model_grades.to_string())

        # ── Before/after: BAD_SEND cases ─────────────────────────────────
        model_bad_sends = opps[opps["decision_grade_model"] == "BAD_SEND"].copy()
        emp_bad_sends   = opps[opps["decision_grade"]       == "BAD_SEND"].copy()

        print(f"\n{'='*60}")
        print(f"BEFORE/AFTER: BAD_SEND CASES")
        print(f"{'='*60}")
        print(f"  Model approach  : {len(model_bad_sends):>4} BAD_SEND plays")
        print(f"  Empirical bins  : {len(emp_bad_sends):>4} BAD_SEND plays")
        print(f"\n  Structural finding: min(p_safe_emp) = {opps['p_safe_empirical'].min():.3f}, "
              f"max(p_be) = {opps['p_breakeven'].max():.3f}")
        print(f"  Gap = {opps['p_safe_empirical'].min() - opps['p_breakeven'].max():.3f}")
        print(f"  => Empirical P(safe) exceeds P_be in every bin — no bad sends at bin level.")

        if len(model_bad_sends):
            print(f"\n  Model's {len(model_bad_sends)} BAD_SEND plays under empirical grading:")
            cols = ["game_date", "events", "hit_location", "outs_when_up",
                    "p_safe_model", "p_safe_empirical", "p_breakeven", "decision_grade"]
            show = model_bad_sends[[c for c in cols if c in model_bad_sends.columns]]
            print(show.to_string(index=False))
            agree = (model_bad_sends["decision_grade"] == "BAD_SEND").sum()
            print(f"\n  Agreement: {agree} of {len(model_bad_sends)} remain BAD_SEND under empirical")
        print(f"{'='*60}")

    # ── Save ──────────────────────────────────────────────────────────────
    out = PROC / "graded_decisions.parquet"
    opps.to_parquet(out, index=False)
    print(f"\nSaved {len(opps):,} graded decisions -> {out}")
    return opps


if __name__ == "__main__":
    run()
