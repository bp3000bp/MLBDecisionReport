"""
Step 1 — Data Spike for the Send/Hold Decision Grader
=====================================================
GOAL: answer three feasibility questions in one sitting, before building anything real.

  Q1. Can we cleanly ISOLATE send/hold opportunities from public Statcast data?
  Q2. Can we RECONSTRUCT the outcome (runner scored / held / thrown out) per opportunity?
  Q3. Can we ATTACH the model inputs we need (runner speed now; OF arm strength next)?

Run this on YOUR machine — pybaseball scrapes Baseball Savant, which must be reachable
(it is blocked in Claude's sandbox, so I couldn't execute it here; the logic is verified
against pybaseball's real function signatures).

    pip install pybaseball pandas
    python data_spike.py

Start small: a ~2-week window keeps it fast while still yielding a few hundred opportunities.
Widen the dates once the logic looks right.
"""

import unicodedata
import pandas as pd
from pybaseball import statcast, statcast_sprint_speed, playerid_reverse_lookup

pd.set_option("display.max_colwidth", 120)
pd.set_option("display.width", 160)

# --- Config: a small, fast slice to prove the pipeline ----------------------
START, END, YEAR = "2024-06-01", "2024-06-14", 2024

# ---------------------------------------------------------------------------
# Q1 — Isolate opportunities: runner on 2B, ball put in play, hit to outfield
# ---------------------------------------------------------------------------
print(f"Pulling Statcast {START} -> {END} (this takes a minute)...")
df = statcast(start_dt=START, end_dt=END)
print(f"  raw rows (one per pitch): {len(df):,}")

OF_HITS = {"single", "double"}
opps = df[
    df["on_2b"].notna()
    & df["events"].isin(OF_HITS)
    & df["hit_location"].isin([7, 8, 9])
].copy()

print(f"\nQ1  Candidate send/hold opportunities (runner on 2B, OF hit): {len(opps):,}")
print(opps[["game_date", "events", "hit_location", "hc_x", "hc_y", "des"]].head(8).to_string(index=False))

# ---------------------------------------------------------------------------
# Name lookup — resolve on_2b MLBAM IDs → last names for outcome attribution
# ---------------------------------------------------------------------------
runner_ids = opps["on_2b"].dropna().astype(int).unique().tolist()
id_lookup = playerid_reverse_lookup(runner_ids, key_type="mlbam")
id_to_last = dict(zip(id_lookup["key_mlbam"], id_lookup["name_last"]))
opps["runner_last"] = opps["on_2b"].astype(int).map(id_to_last)

# ---------------------------------------------------------------------------
# Q2 — Reconstruct the outcome from the play description text (`des`)
#      Spike-grade heuristic; v1 will harden this (or back it with Retrosheet
#      play-by-play, which encodes advancement explicitly).
# ---------------------------------------------------------------------------

def _norm(s: str) -> str:
    """Lowercase + strip accents so 'Suárez' matches 'suarez' in des text."""
    return unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode("ascii").lower()

def classify_naive(des: str) -> str:
    """Original heuristic: any 'scores' anywhere in des."""
    d = str(des).lower()
    if "out at home" in d or "thrown out at home" in d:
        return "OUT_AT_HOME"
    if "scores" in d:
        return "SCORED"
    return "HELD_OR_UNKNOWN"

def classify_outcome(des: str, runner_last: str) -> str:
    """Attributed: check that THIS runner's last name precedes 'scores' or 'out at home'."""
    d = _norm(des)
    r = _norm(runner_last)
    if r + " out at home" in d:
        return "OUT_AT_HOME"
    if r + " scores" in d:
        return "SCORED"
    return "HELD_OR_UNKNOWN"

opps["outcome_naive"] = opps["des"].apply(classify_naive)
opps["outcome"] = opps.apply(lambda row: classify_outcome(row["des"], row["runner_last"]), axis=1)

naive_scored = (opps["outcome_naive"] == "SCORED").sum()
attr_scored  = (opps["outcome"] == "SCORED").sum()
false_pos    = naive_scored - attr_scored

print("\nQ2  Outcome reconstruction — naive vs. attributed:")
print(f"   Naive SCORED     : {naive_scored}")
print(f"   Attributed SCORED: {attr_scored}  ({false_pos} removed — different runner scored, not the on-2B runner)")
print("\n   Attributed outcome counts:")
print(opps["outcome"].value_counts().to_string())
print("\n   Examples of each:")
for label in ["SCORED", "OUT_AT_HOME", "HELD_OR_UNKNOWN"]:
    ex = opps.loc[opps["outcome"] == label, ["runner_last", "des"]].head(2)
    for _, row in ex.iterrows():
        print(f"   [{label}] ({row['runner_last']}) {row['des']}")

# ---------------------------------------------------------------------------
# Q3 — Attach a model input: runner sprint speed (join on the on_2b player id)
# ---------------------------------------------------------------------------
print(f"\nPulling {YEAR} sprint speed leaderboard...")
speed = statcast_sprint_speed(YEAR, min_opp=5)
speed_lookup = speed.set_index(speed["player_id"].astype(float))["sprint_speed"]
opps["runner_id"] = opps["on_2b"].astype(float)
opps["runner_sprint_speed"] = opps["runner_id"].map(speed_lookup)

matched = opps["runner_sprint_speed"].notna().mean()
print(f"Q3  Runner sprint speed join rate: {matched:.0%} of opportunities")
print(opps[["runner_last", "runner_sprint_speed", "outcome"]].head(6).to_string(index=False))

# ---------------------------------------------------------------------------
# Feasibility verdict
# ---------------------------------------------------------------------------
print("\n" + "=" * 60)
print("FEASIBILITY VERDICT")
print("=" * 60)
print(f"Q1 opportunities isolated  : {len(opps):,}  (want: comfortably >100 in 2 weeks)")
known_naive = (opps["outcome_naive"] != "HELD_OR_UNKNOWN").mean()
known_attr  = (opps["outcome"] != "HELD_OR_UNKNOWN").mean()
print(f"Q2 outcomes parsed cleanly : {known_attr:.0%} attributed  (was {known_naive:.0%} naive — delta = false-positive bleed)")
print(f"Q3 speed join rate         : {matched:.0%}")
print("""
NEXT after this passes:
  - Add OF arm strength (Savant arm-strength CSV, 2020+) keyed on the fielding OF.
  - Approximate throw distance from (hc_x, hc_y) to home/third; sanity-check it.
  - Then: build P(safe) model + run-expectancy break-even layer.
""")
