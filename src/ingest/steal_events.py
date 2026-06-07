"""
Steal-attempt event ingest from the MLBAM Stats API.

pybaseball's statcast() only returns pitch-level rows — between-pitch steal
events are excluded by design.  The MLBAM play-by-play endpoint
(/api/v1/game/{game_pk}/playByPlay) embeds steal runner movements in every
at-bat's `runners` array and is the authoritative public source.

Pipeline:
  1. Fetch regular-season schedule for each year → list of game_pk values
     (only Final games are included, so in-progress seasons work naturally).
  2. For each game, fetch play-by-play and extract steal runner movements.
  3. Save per-year parquet to data/raw/steal_events_{year}.parquet.

The output schema joins cleanly to statcast via (game_pk, at_bat_number),
where at_bat_number = atBatIndex + 1 (MLBAM is 0-based, statcast is 1-based).

Usage:
    python -m src.ingest.steal_events          # all seasons
    python -m src.ingest.steal_events 2026     # current season (always re-pulls)
"""

import sys
import time
import datetime
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import requests
import pandas as pd

RAW = Path(__file__).resolve().parents[2] / "data" / "raw"
RAW.mkdir(parents=True, exist_ok=True)

CURRENT_YEAR = datetime.date.today().year
SEASONS = [2020, 2021, 2022, 2023, 2024, 2025, 2026]
STEAL_EVENTS = {
    "stolen_base_2b", "caught_stealing_2b",
    "stolen_base_3b", "caught_stealing_3b",
    "stolen_base_home", "caught_stealing_home",
    "pickoff_caught_stealing_2b", "pickoff_caught_stealing_3b",
}

SCHEDULE_URL = (
    "https://statsapi.mlb.com/api/v1/schedule"
    "?sportId=1&season={year}&gameType=R"
    "&fields=dates,date,games,gamePk,status,abstractGameState"
)
PBP_URL = "https://statsapi.mlb.com/api/v1/game/{game_pk}/playByPlay"

MAX_WORKERS = 15
REQUEST_TIMEOUT = 30

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
log = logging.getLogger(__name__)


def _get_schedule(year: int) -> list[int]:
    resp = requests.get(SCHEDULE_URL.format(year=year), timeout=REQUEST_TIMEOUT)
    resp.raise_for_status()
    data = resp.json()
    game_pks = []
    for date_entry in data.get("dates", []):
        for game in date_entry.get("games", []):
            state = game.get("status", {}).get("abstractGameState", "")
            if state == "Final":
                game_pks.append(game["gamePk"])
    return game_pks


def _fetch_steals_for_game(game_pk: int) -> list[dict]:
    try:
        resp = requests.get(
            PBP_URL.format(game_pk=game_pk),
            timeout=REQUEST_TIMEOUT,
            headers={"User-Agent": "mlb-decision-grader/1.0"},
        )
        resp.raise_for_status()
    except Exception as exc:
        log.warning("game_pk=%d fetch error: %s", game_pk, exc)
        return []

    rows = []
    for play in resp.json().get("allPlays", []):
        about   = play.get("about", {})
        atbat_i = about.get("atBatIndex", -1)
        inning  = about.get("inning", -1)
        half    = about.get("halfInning", "")  # "top" or "bottom"

        for runner in play.get("runners", []):
            details = runner.get("details", {})
            etype   = details.get("eventType", "")
            if etype not in STEAL_EVENTS:
                continue

            movement  = runner.get("movement", {})
            runner_id = details.get("runner", {}).get("id")
            runner_nm = details.get("runner", {}).get("fullName", "")
            is_out    = movement.get("isOut", False)

            # Determine catcher from credits (present on caught-stealing plays)
            catcher_id = None
            for credit in runner.get("credits", []):
                pos = credit.get("position", {}).get("code", "")
                if pos == "2":
                    catcher_id = credit.get("player", {}).get("id")
                    break

            rows.append({
                "game_pk":      game_pk,
                "atbat_index":  atbat_i,          # 0-based; at_bat_number = atbat_index + 1
                "at_bat_number": atbat_i + 1,     # 1-based, matches statcast
                "inning":       inning,
                "half_inning":  half,
                "event_type":   etype,
                "base_from":    movement.get("start"),
                "base_to":      movement.get("end"),
                "out_base":     movement.get("outBase"),
                "is_success":   not is_out,
                "runner_id":    runner_id,
                "runner_name":  runner_nm,
                "catcher_id_credits": catcher_id,  # populated for caught-stealing only
            })

    return rows


def pull_season(year: int) -> None:
    out = RAW / f"steal_events_{year}.parquet"
    if out.exists() and year != CURRENT_YEAR:
        df = pd.read_parquet(out)
        log.info("%d: %s already exists (%d rows) — delete to re-pull", year, out.name, len(df))
        return
    if out.exists() and year == CURRENT_YEAR:
        log.info("%d: in-progress season — re-pulling to capture new games …", year)

    log.info("%d: fetching schedule …", year)
    game_pks = _get_schedule(year)
    log.info("%d: %d games to process", year, len(game_pks))

    all_rows: list[dict] = []
    done = 0

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        futures = {pool.submit(_fetch_steals_for_game, gk): gk for gk in game_pks}
        for fut in as_completed(futures):
            rows = fut.result()
            all_rows.extend(rows)
            done += 1
            if done % 200 == 0:
                log.info("%d: %d/%d games, %d steal events so far", year, done, len(game_pks), len(all_rows))

    df = pd.DataFrame(all_rows)
    if df.empty:
        log.warning("%d: no steal events found — check MLBAM availability", year)
        df = pd.DataFrame(columns=[
            "game_pk", "atbat_index", "at_bat_number", "inning", "half_inning",
            "event_type", "base_from", "base_to", "out_base", "is_success",
            "runner_id", "runner_name", "catcher_id_credits",
        ])
    df["game_year"] = year
    df.to_parquet(out, index=False)
    log.info("%d: saved %d steal events → %s", year, len(df), out.name)

    # Quick sanity
    if not df.empty:
        log.info("%d: event breakdown:\n%s", year, df["event_type"].value_counts().to_string())


if __name__ == "__main__":
    years = [int(y) for y in sys.argv[1:]] if len(sys.argv) > 1 else SEASONS
    t0 = time.time()
    for yr in years:
        pull_season(yr)
    log.info("Done in %.1fs", time.time() - t0)
