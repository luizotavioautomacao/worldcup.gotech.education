#!/usr/bin/env python3
"""Fetch Copa 2026 live scores and write a cached snapshot JSON.

Merges @kickoff26/data (schedule/teams/venues) with ESPN scoreboard by date.
See .plans/worldcup/docs/architecture.md
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
import urllib.error
import urllib.request
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

KICKOFF_BASE = "https://unpkg.com/@kickoff26/data@0.2.0/data/"
ESPN_SCOREBOARD = (
    "https://site.api.espn.com/apis/site/v2/sports/soccer/fifa.world/scoreboard"
)
TOURNAMENT_START = date(2026, 6, 11)
TOURNAMENT_END = date(2026, 7, 19)
REQUEST_TIMEOUT = 15

SCRIPT_DIR = Path(__file__).resolve().parent
WORLDCUP_ROOT = SCRIPT_DIR.parent
DEFAULT_OUTPUT = WORLDCUP_ROOT / "output" / "worldcup2026-snapshot.json"

ESPN_FINISHED = {"STATUS_FINAL", "STATUS_FULL_TIME"}
ESPN_LIVE = {
    "STATUS_IN_PROGRESS",
    "STATUS_FIRST_HALF",
    "STATUS_SECOND_HALF",
    "STATUS_HALFTIME",
    "STATUS_END_PERIOD",
}


def fetch_json(url: str) -> dict | list:
    req = urllib.request.Request(url, headers={"User-Agent": "worldcup-fetch/1.0"})
    with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
        return json.loads(resp.read().decode())


def espn_date_range(start: date, end: date):
    current = start
    while current <= end:
        yield current.strftime("%Y%m%d")
        current += timedelta(days=1)


TEAM_ALIASES = {
    "turkiye": "turkey",
    "tuerkiye": "turkey",
    "czechia": "czech-republic",
    "bosnia-and-herzegovina": "bosnia-herzegovina",
    "united-states": "usa",
    "korea-republic": "south-korea",
    "republic-of-korea": "south-korea",
    "cote-divoire": "ivory-coast",
    "cote-d-ivoire": "ivory-coast",
    "dr-congo": "dr-congo",
    "democratic-republic-of-congo": "dr-congo",
    "saudi-arabia": "saudi-arabia",
    "cape-verde": "cape-verde",
    "cabo-verde": "cape-verde",
    "curaao": "curacao",
}


def normalize_team_key(name: str) -> str:
    if not name:
        return ""
    s = unicodedata.normalize("NFKD", name)
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    s = s.lower().replace("&", "and").replace("'", "")
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return TEAM_ALIASES.get(s, s)


def team_name_matches(kickoff_id: str, espn_name: str) -> bool:
    k = normalize_team_key(kickoff_id)
    e = normalize_team_key(espn_name)
    if not k or not e:
        return False
    if k == e or k in e or e in k:
        return True
    return len(k) >= 4 and len(e) >= 4 and k[:4] == e[:4]


def find_match(matches: list[dict], home_name: str, away_name: str) -> dict | None:
    for match in matches:
        if team_name_matches(match["team1"], home_name) and team_name_matches(
            match["team2"], away_name
        ):
            return match
    return None


def map_espn_status(status_name: str | None) -> str | None:
    if not status_name:
        return None
    if status_name in ESPN_FINISHED:
        return "finished"
    if status_name in ESPN_LIVE:
        return "live"
    return None


def parse_score(value) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def enrich_with_espn(matches: list[dict], events: list[dict]) -> int:
    """Overlay ESPN scores onto kickoff26 matches. Returns count enriched."""
    enriched = 0
    for evt in events:
        competitors = (evt.get("competitions") or [{}])[0].get("competitors") or []
        home = next((c for c in competitors if c.get("homeAway") == "home"), None)
        away = next((c for c in competitors if c.get("homeAway") == "away"), None)
        if not home or not away:
            continue

        home_team = home.get("team") or {}
        away_team = away.get("team") or {}
        home_name = home_team.get("displayName") or home_team.get("shortDisplayName") or ""
        away_name = away_team.get("displayName") or away_team.get("shortDisplayName") or ""

        match = find_match(matches, home_name, away_name)
        if not match:
            continue

        status_name = (evt.get("status") or {}).get("type", {}).get("name")
        mapped = map_espn_status(status_name)
        if mapped:
            match["status"] = mapped

        home_score = parse_score(home.get("score"))
        away_score = parse_score(away.get("score"))
        if home_score is not None and away_score is not None:
            match["score"] = {
                "ft": [home_score, away_score],
                "ht": [None, None],
                "et": None,
                "pens": None,
            }

        match["_espn_enriched"] = True
        enriched += 1
    return enriched


def load_kickoff26() -> tuple[list, dict, dict]:
    matches = fetch_json(KICKOFF_BASE + "matches.json")
    teams_list = fetch_json(KICKOFF_BASE + "teams.json")
    venues_list = fetch_json(KICKOFF_BASE + "venues.json")
    teams = {t["id"]: t for t in teams_list}
    venues = {v["id"]: v for v in venues_list}
    return matches, teams, venues


def fetch_espn_events(start: date, end: date) -> list[dict]:
    events: list[dict] = []
    for day in espn_date_range(start, end):
        url = f"{ESPN_SCOREBOARD}?dates={day}"
        try:
            data = fetch_json(url)
        except urllib.error.URLError as exc:
            print(f"warn: ESPN {day}: {exc}", file=sys.stderr)
            continue
        day_events = data.get("events") or []
        events.extend(day_events)
        print(f"espn {day}: {len(day_events)} event(s)", file=sys.stderr)
    return events


def reconcile_stale_live(matches: list[dict]) -> None:
    """Mark live matches as finished when kickoff + max duration has passed."""
    now = datetime.now(timezone.utc)
    max_duration = timedelta(hours=3)
    for match in matches:
        if match.get("status") != "live":
            continue
        kickoff_str = match.get("kickoff_utc")
        if not kickoff_str:
            continue
        kickoff = datetime.fromisoformat(kickoff_str.replace("Z", "+00:00"))
        if now > kickoff + max_duration:
            match["status"] = "finished"


def compute_stats(matches: list[dict]) -> dict[str, int]:
    stats = {"finished": 0, "live": 0, "scheduled": 0}
    for match in matches:
        status = match.get("status", "scheduled")
        if status in stats:
            stats[status] += 1
    return stats


def build_snapshot(end_date: date | None = None) -> dict:
    today = datetime.now(timezone.utc).date()
    end = min(end_date or today, TOURNAMENT_END)
    if end < TOURNAMENT_START:
        end = TOURNAMENT_START

    print("fetching kickoff26...", file=sys.stderr)
    matches, teams, venues = load_kickoff26()

    print(f"fetching ESPN {TOURNAMENT_START} .. {end}...", file=sys.stderr)
    events = fetch_espn_events(TOURNAMENT_START, end)
    enriched = enrich_with_espn(matches, events)
    reconcile_stale_live(matches)

    stats = compute_stats(matches)
    snapshot = {
        "updated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace(
            "+00:00", "Z"
        ),
        "source": "kickoff26+espn" if enriched else "kickoff26",
        "stats": stats,
        "matches": matches,
        "teams": teams,
        "venues": venues,
    }
    print(
        f"done: {enriched} enriched, "
        f"{stats['finished']} finished / {stats['live']} live / {stats['scheduled']} scheduled",
        file=sys.stderr,
    )
    return snapshot


def main() -> int:
    parser = argparse.ArgumentParser(description="Build Copa 2026 live snapshot JSON")
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help=f"Output path (default: {DEFAULT_OUTPUT})",
    )
    parser.add_argument(
        "--end-date",
        type=str,
        default=None,
        help="Last tournament day to fetch from ESPN (YYYY-MM-DD, UTC). Default: today.",
    )
    args = parser.parse_args()

    end_date = None
    if args.end_date:
        end_date = date.fromisoformat(args.end_date)

    snapshot = build_snapshot(end_date=end_date)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n")
    print(f"wrote {args.output}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
