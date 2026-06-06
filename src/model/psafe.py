"""
Logistic regression model for P(safe | runner sent home from 2B).

Training set: only plays where the runner was sent (outcome SCORED or OUT_AT_HOME).
Target: 1 = safe (SCORED), 0 = out (OUT_AT_HOME).

Features:
  throw_distance_ft    -- estimated distance from ball landing to home plate
  runner_sprint_speed  -- runner's season sprint speed (ft/s)
  of_arm_strength      -- fielder's positional arm strength (mph); median-imputed if missing
  is_double            -- 1 if hit type is double, 0 if single
  loc_lf               -- 1 if hit to LF (hit_location == 7), else 0
  loc_cf               -- 1 if hit to CF (hit_location == 8), else 0
  (RF = reference category)

Output: data/processed/psafe_model.pkl
"""
import pickle
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.calibration import CalibratedClassifierCV, calibration_curve
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedKFold, cross_val_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

ROOT = Path(__file__).resolve().parents[2]
PROC = ROOT / "data" / "processed"

FEATURE_COLS = [
    "throw_distance_ft",
    "runner_sprint_speed",
    "of_arm_strength",
    "is_double",
    "loc_lf",
    "loc_cf",
]


def _build_features(df: pd.DataFrame) -> pd.DataFrame:
    X = df.copy()
    X["is_double"] = (X["events"] == "double").astype(int)
    X["loc_lf"]    = (X["hit_location"] == 7).astype(int)
    X["loc_cf"]    = (X["hit_location"] == 8).astype(int)
    X = X[FEATURE_COLS].copy()

    n_missing_arm = X["of_arm_strength"].isna().sum()
    if n_missing_arm:
        med = X["of_arm_strength"].median()
        X["of_arm_strength"] = X["of_arm_strength"].fillna(med)
        print(f"  arm_strength: imputed {n_missing_arm} missing with median {med:.1f} mph")

    return X


def train(seed: int = 42) -> Pipeline:
    opps = pd.read_parquet(PROC / "opportunities.parquet")
    sent = opps[opps["outcome"].isin(["SCORED", "OUT_AT_HOME"])].copy()
    sent["target"] = (sent["outcome"] == "SCORED").astype(int)

    X = _build_features(sent)
    X = X.dropna()
    y = sent.loc[X.index, "target"]

    print(f"Training set: {len(X):,} plays  ({y.sum():,} safe / {(~y.astype(bool)).sum():,} out)")
    print(f"Safe rate (base rate): {y.mean():.1%}")

    # Step 1: balanced LR gives good discrimination despite 98% safe base rate.
    # Step 2: Platt scaling (CalibratedClassifierCV) maps balanced-model scores back
    #         to calibrated probabilities on the true 0-1 scale so P(safe) can be
    #         compared directly to P_breakeven from RE24.
    base = Pipeline([
        ("scaler", StandardScaler()),
        ("lr",     LogisticRegression(max_iter=500, random_state=seed, C=1.0,
                                      class_weight="balanced")),
    ])

    # Evaluate discrimination (AUC is class-imbalance insensitive)
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=seed)
    auc = cross_val_score(base, X, y, cv=cv, scoring="roc_auc")
    print(f"\n5-fold CV AUC-ROC: {auc.mean():.4f} (+/-{auc.std():.4f})")
    print("(AUC=0.5 is random; 1.0 is perfect discrimination)")

    # Fit calibrated model
    pipe = CalibratedClassifierCV(base, method="sigmoid", cv=5)
    pipe.fit(X, y)

    # Calibration check: binned predicted probability vs actual safe rate
    proba_cal = pipe.predict_proba(X)[:, 1]
    frac_pos, mean_pred = calibration_curve(y, proba_cal, n_bins=10, strategy="quantile")
    print("\nCalibration check (predicted P(safe) vs actual safe rate, in decile bins):")
    for mp, fp in zip(mean_pred, frac_pos):
        bar = "#" * int(fp * 20)
        print(f"  pred={mp:.2f}  actual={fp:.2f}  {bar}")

    # Coefficient summary (from one fold's base estimator for interpretability)
    first_cal = pipe.calibrated_classifiers_[0]
    lr_step = first_cal.estimator.named_steps["lr"]
    coefs = pd.Series(lr_step.coef_[0], index=FEATURE_COLS).sort_values(ascending=False)
    print("\nCoefficients (one fold, log-odds, standardized — sign/rank matters, not magnitude):")
    print(coefs.to_string())

    out = PROC / "psafe_model.pkl"
    with open(out, "wb") as f:
        pickle.dump(pipe, f)
    print(f"\nModel saved -> {out}")
    return pipe


def load_model() -> Pipeline:
    p = PROC / "psafe_model.pkl"
    if not p.exists():
        raise FileNotFoundError("psafe_model.pkl not found — run src/model/psafe.py first")
    with open(p, "rb") as f:
        return pickle.load(f)


def predict(pipe: Pipeline, opps: pd.DataFrame) -> pd.Series:
    """Apply P(safe) model to all opportunities (including holds)."""
    X = _build_features(opps).fillna(opps[["of_arm_strength"]].median().iloc[0])
    complete = X.dropna()
    proba = pd.Series(np.nan, index=opps.index, name="p_safe")
    proba.loc[complete.index] = pipe.predict_proba(complete)[:, 1]
    return proba


if __name__ == "__main__":
    sys.path.insert(0, str(ROOT))
    train()
