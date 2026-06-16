#!/usr/bin/env python3
"""Smoke test for ESPN World Cup scoreboard API.

Usage:
  python3 scripts/test_espn_scoreboard.py
  python3 scripts/test_espn_scoreboard.py --team france
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.request
from datetime import datetime, timezone

ESPN_SCOREBOARD = (
    "https://site.api.espn.com/apis/site/v2/sports/soccer/fifa.world/scoreboard"
)
ESPN_BROKEN = (
    "https://site.api.espn.com/apis/site/v2/sports/soccer/fifa.world.2026/scoreboard"
)
SNAPSHOT_GITHUB = (
    "https://raw.githubusercontent.com/luizotavioautomacao/worldcup.gotech.education/"
    "refs/heads/main/output/worldcup2026-snapshot.json"
)


def fetch_json(url: str) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": "worldcup-test/1.0"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode())


def print_events(label: str, data: dict, team_filter: str | None) -> None:
    events = data.get("events") or []
    print(f"\n=== {label} ({len(events)} events) ===")
    now = datetime.now(timezone.utc)
    needle = (team_filter or "").lower()
    for evt in events:
        comp = (evt.get("competitions") or [{}])[0]
        competitors = comp.get("competitors") or []
        home = next((c for c in competitors if c.get("homeAway") == "home"), {})
        away = next((c for c in competitors if c.get("homeAway") == "away"), {})
        hname = (home.get("team") or {}).get("displayName", "?")
        aname = (away.get("team") or {}).get("displayName", "?")
        if needle and needle not in hname.lower() and needle not in aname.lower():
            continue
        status = (evt.get("status") or {}).get("type") or {}
        date = evt.get("date", "?")
        age_min = "?"
        if date != "?":
            dt = datetime.fromisoformat(date.replace("Z", "+00:00"))
            age_min = f"{(now - dt).total_seconds() / 60:.0f}min"
        print(
            f"  {date} (+{age_min}) | {hname} {home.get('score', '?')}-{away.get('score', '?')} "
            f"{aname} | {status.get('name', '?')} ({status.get('detail', '')})"
        )


def main() -> int:
    parser = argparse.ArgumentParser(description="Test ESPN scoreboard endpoints")
    parser.add_argument("--team", help="Filter by team name substring (e.g. france)")
    args = parser.parse_args()

    print(f"UTC now: {datetime.now(timezone.utc).isoformat()}")

    try:
        print_events("fifa.world/scoreboard", fetch_json(ESPN_SCOREBOARD), args.team)
    except Exception as exc:
        print(f"\nERROR fifa.world/scoreboard: {exc}", file=sys.stderr)

    try:
        fetch_json(ESPN_BROKEN)
        print("\nWARN: fifa.world.2026/scoreboard unexpectedly succeeded")
    except Exception as exc:
        print(f"\n=== fifa.world.2026/scoreboard (expected fail) ===\n  {exc}")

    try:
        snap = fetch_json(SNAPSHOT_GITHUB)
        print(f"\n=== GitHub snapshot ===")
        print(f"  updated_at: {snap.get('updated_at')}")
        print(f"  stats: {snap.get('stats')}")
        if args.team:
            for m in snap.get("matches") or []:
                if args.team in m.get("team1", "") or args.team in m.get("team2", ""):
                    print(f"  {m.get('team1')} vs {m.get('team2')}: {m.get('status')} {m.get('score')}")
    except Exception as exc:
        print(f"\nERROR snapshot: {exc}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
