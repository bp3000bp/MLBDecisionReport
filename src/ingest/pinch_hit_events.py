"""
Pinch hit substitution event ingest from the MLBAM Stats API.

Identifies every pinch hit substitution in each regular-season game by parsing
'offensive_substitution' action events in play-by-play where
position.name == "Pinch Hitter".

Pipeline:
  1. Fetch regular-season schedule for each year → list of game_pk values
     (only Final games, so in-progress seasons work naturally).
  2. For each game, fetch play-by-play and extract PH substitutions.
  3. Save per-year parquet to data/raw/pinch_hit_events_{year}.parquet.

Output schema joins to statcast via (game_pk, at_bat_number),
where at_bat_number = parent atBatIndex + 1 (MLBAM is 0-based, statcast is 1-based).

Usage:
    python -m src.ingest.pinch_hit_events          # all seasons
    python -m src.ingest.pinch_hit_events 2026     # current season (always re-pulls)
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


def _fetch_ph_for_game(game_pk: int) -> list[dict]:
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

        for event in play.get("playEvents", []):
            if not event.get("isSubstitution", False):
                continue
            if event.get("position", {}).get("name", "") != "Pinch Hitter":
                continue

            ph_id  = event.get("player", {}).get("id")
            rep_id = event.get("replacedPlayer", {}).get("id")
            if ph_id is None or rep_id is None:
                continue

            rows.append({
                "game_pk":            game_pk,
                "atbat_index":        atbat_i,
                "at_bat_number":      atbat_i + 1,  # 1-based, matches statcast
                "inning":             inning,
                "half_inning":        half,
                "ph_batter_id":       ph_id,
                "replaced_batter_id": rep_id,
                "batting_order":      event.get("battingOrder", ""),
                "outs_at_sub":        event.get("count", {}).get("outs", 0),
            })

    return rows


def pull_season(year: int) -> None:
    out = RAW / f"pinch_hit_events_{year}.parquet"
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
        futures = {pool.submit(_fetch_ph_for_game, gk): gk for gk in game_pks}
        for fut in as_completed(futures):
            rows = fut.result()
            all_rows.extend(rows)
            done += 1
            if done % 200 == 0:
                log.info("%d: %d/%d games, %d PH events so far", year, done, len(game_pks), len(all_rows))

    df = pd.DataFrame(all_rows)
    if df.empty:
        log.warning("%d: no PH events found — check MLBAM availability", year)
        df = pd.DataFrame(columns=[
            "game_pk", "atbat_index", "at_bat_number", "inning", "half_inning",
            "ph_batter_id", "replaced_batter_id", "batting_order", "outs_at_sub",
        ])
    df["game_year"] = year
    df.to_parquet(out, index=False)
    log.info("%d: saved %d PH substitutions → %s", year, len(df), out.name)

    if not df.empty:
        log.info("%d: ~%.0f PH per team-season", year, len(df) / 30)


if __name__ == "__main__":
    years = [int(y) for y in sys.argv[1:]] if len(sys.argv) > 1 else SEASONS
    t0 = time.time()
    for yr in years:
        pull_season(yr)
    log.info("Done in %.1fs", time.time() - t0)
