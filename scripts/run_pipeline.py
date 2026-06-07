"""
Master pipeline runner for the MLB Decision Report.

Runs all stages in sequence. Intelligently skips existing historical parquets
(only re-pulls CURRENT_YEAR ingest data on each run).

Usage:
    python scripts/run_pipeline.py                  # full pipeline, all years
    python scripts/run_pipeline.py --current-only   # re-pull current year + rebuild downstream
    python scripts/run_pipeline.py --from features  # skip ingest, start from feature stage
    python scripts/run_pipeline.py --from model     # skip ingest + features
    python scripts/run_pipeline.py --from eval      # skip to leaderboard rebuild only
    python scripts/run_pipeline.py --from web       # just regenerate web JSON from existing CSVs
    python scripts/run_pipeline.py --rebuild-re24   # recompute RE24 table from statcast data

Stages:
    ingest    -- pull Statcast, sprint speed, steal events
    features  -- identify opportunities, merge context
    model     -- grade decisions (send/hold + steal)
    eval      -- build leaderboards
    web       -- export JSON for the web app
"""

import argparse
import datetime
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

CURRENT_YEAR = datetime.date.today().year
ALL_YEARS = [2020, 2021, 2022, 2023, 2024, 2025, 2026]
STAGE_ORDER = ["ingest", "features", "model", "eval", "web"]


def _header(msg: str) -> None:
    print(f"\n{'='*60}")
    print(f"  {msg}")
    print(f"{'='*60}")


def _elapsed(t0: float) -> str:
    s = int(time.time() - t0)
    return f"{s//60}m {s%60}s"


# ── Stage 1: Ingest ───────────────────────────────────────────────────────

def run_ingest(current_only: bool = False) -> None:
    from src.ingest.statcast_pull import pull_season as pull_statcast
    from src.ingest.sprint_speed_pull import pull_sprint_speed
    from src.ingest.steal_events import pull_season as pull_steal

    years = [CURRENT_YEAR] if current_only else ALL_YEARS
    label = f"CURRENT YEAR ({CURRENT_YEAR})" if current_only else "ALL YEARS"
    _header(f"STAGE 1: INGEST — {label}")

    for yr in years:
        t0 = time.time()
        print(f"\n-- {yr}: Statcast --")
        pull_statcast(yr)
        print(f"   done in {_elapsed(t0)}")

    for yr in years:
        t0 = time.time()
        print(f"\n-- {yr}: Sprint speed --")
        pull_sprint_speed(yr)
        print(f"   done in {_elapsed(t0)}")

    for yr in years:
        t0 = time.time()
        print(f"\n-- {yr}: Steal events --")
        pull_steal(yr)
        print(f"   done in {_elapsed(t0)}")


# ── Stage 2: Features ─────────────────────────────────────────────────────

def run_features() -> None:
    from src.features.opportunities import build_opportunities
    from src.features.steal_opportunities import build_steal_opportunities
    from src.features.ibb_opportunities import build_ibb_opportunities

    _header("STAGE 2: FEATURES")

    t0 = time.time()
    print("\n-- Send/hold opportunities --")
    build_opportunities()
    print(f"   done in {_elapsed(t0)}")

    t0 = time.time()
    print("\n-- Steal opportunities --")
    build_steal_opportunities()
    print(f"   done in {_elapsed(t0)}")

    t0 = time.time()
    print("\n-- IBB opportunities --")
    build_ibb_opportunities()
    print(f"   done in {_elapsed(t0)}")


# ── Stage 3: Model ────────────────────────────────────────────────────────

def run_model(rebuild_re24: bool = False) -> None:
    _header("STAGE 3: MODEL")

    if rebuild_re24:
        from src.model.re24 import compute_re24_from_statcast
        proc = ROOT / "data" / "processed"
        opp_path = proc / "opportunities.parquet"
        if opp_path.exists():
            print("\n-- Recomputing RE24 table from Statcast --")
            compute_re24_from_statcast(opp_path)
        else:
            print("  SKIP: opportunities.parquet not found — run features first")

    t0 = time.time()
    print("\n-- Send/hold grading --")
    from src.model.grade import run as grade_run
    grade_run()
    print(f"   done in {_elapsed(t0)}")

    t0 = time.time()
    print("\n-- Steal grading --")
    from src.model.steal_grade import build_steal_decisions
    build_steal_decisions()
    print(f"   done in {_elapsed(t0)}")

    t0 = time.time()
    print("\n-- IBB grading --")
    from src.model.ibb_grade import build_ibb_decisions
    build_ibb_decisions()
    print(f"   done in {_elapsed(t0)}")


# ── Stage 4: Eval ─────────────────────────────────────────────────────────

def run_eval() -> None:
    from src.eval.leaderboards import build_leaderboards
    from src.eval.steal_leaderboards import build_leaderboards as build_steal_leaderboards
    from src.eval.ibb_leaderboards import build_ibb_leaderboards

    _header("STAGE 4: EVAL")

    t0 = time.time()
    print("\n-- Send/hold leaderboards --")
    build_leaderboards()
    print(f"   done in {_elapsed(t0)}")

    t0 = time.time()
    print("\n-- Steal leaderboards --")
    build_steal_leaderboards()
    print(f"   done in {_elapsed(t0)}")

    t0 = time.time()
    print("\n-- IBB leaderboards --")
    build_ibb_leaderboards()
    print(f"   done in {_elapsed(t0)}")


# ── Stage 5: Web data ─────────────────────────────────────────────────────

def run_web() -> None:
    _header("STAGE 5: WEB DATA")
    from scripts.build_web_data import build
    build()


# ── Main ──────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="MLB Decision Report pipeline runner")
    parser.add_argument(
        "--current-only", action="store_true",
        help="Re-pull only CURRENT_YEAR ingest data, then rebuild downstream"
    )
    parser.add_argument(
        "--from", dest="from_stage", choices=STAGE_ORDER, default="ingest",
        metavar="STAGE",
        help="Start from this stage (ingest|features|model|eval|web)"
    )
    parser.add_argument(
        "--rebuild-re24", action="store_true",
        help="Recompute RE24 table from all Statcast data during model stage"
    )
    args = parser.parse_args()

    start_idx = STAGE_ORDER.index(args.from_stage)
    pipeline_start = time.time()

    print(f"MLB Decision Report pipeline")
    print(f"Date: {datetime.date.today()}  Current year: {CURRENT_YEAR}")
    print(f"Starting from: {args.from_stage}")
    if args.current_only:
        print(f"Mode: current-year refresh ({CURRENT_YEAR} only for ingest)")

    if start_idx <= STAGE_ORDER.index("ingest"):
        run_ingest(current_only=args.current_only)

    if start_idx <= STAGE_ORDER.index("features"):
        run_features()

    if start_idx <= STAGE_ORDER.index("model"):
        run_model(rebuild_re24=args.rebuild_re24)

    if start_idx <= STAGE_ORDER.index("eval"):
        run_eval()

    if start_idx <= STAGE_ORDER.index("web"):
        run_web()

    _header(f"PIPELINE COMPLETE in {_elapsed(pipeline_start)}")


if __name__ == "__main__":
    main()
