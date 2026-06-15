#!/usr/bin/env python3
"""Gera dashboard-stats-extra.json e dashboard-viz-data.json a partir do worldcup.json."""
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "worldcup-r" / "data-json" / "worldcup.json"
OUT_STATS = ROOT / "front-end" / "dashboard-stats-extra.json"
OUT_VIZ = ROOT / "front-end" / "dashboard-viz-data.json"
DASHBOARD = ROOT / "front-end" / "worldcup-dashboard.html"

KO_EXIT = {
    "round of 16",
    "quarter-finals",
    "quarter-final",
    "semi-finals",
    "semi-final",
    "third-place match",
}
CONF_ORDER = ["UEFA", "CONMEBOL", "CONCACAF", "CAF", "AFC", "OFC"]


def player_name(goal: dict) -> str:
    name = goal.get("scorer_name") or (
        f"{goal.get('given_name', '')} {goal.get('family_name', '')}"
    ).strip()
    if name.startswith("not applicable "):
        name = name.replace("not applicable ", "")
    return name


def top_scorers(data: dict, tids: set, limit: int = 15) -> list:
    counts = Counter()
    for goal in data["goals"]:
        if goal.get("own_goal") or goal["tournament_id"] not in tids:
            continue
        counts[player_name(goal)] += 1
    return counts.most_common(limit)


def best_single_cup(data: dict, tids: set) -> list | None:
    best = None
    years = {t["tournament_id"]: t["year"] for t in data["tournaments"]}
    for tid in tids:
        counts = Counter()
        for goal in data["goals"]:
            if goal.get("own_goal") or goal["tournament_id"] != tid:
                continue
            counts[player_name(goal)] += 1
        if not counts:
            continue
        name, goals = counts.most_common(1)[0]
        if not best or goals > best[1]:
            best = [name, goals, years[tid]]
    return best


def team_stats_all(data: dict, winners: dict, mens_tids: set, womens_tids: set) -> dict:
    teams = sorted({qt["team_name"] for qt in data["qualified_teams"]})
    out = {}
    for team in teams:
        rec = {}
        for gkey, tids in (
            ("all", mens_tids | womens_tids),
            ("mens", mens_tids),
            ("womens", womens_tids),
        ):
            participations = titles = second = third = ko_elim = 0
            for row in data["tournament_standings"]:
                if row["team_name"] != team or row["tournament_id"] not in tids:
                    continue
                if row["position"] == 1:
                    titles += 1
                elif row["position"] == 2:
                    second += 1
                elif row["position"] == 3:
                    third += 1
            for row in data["qualified_teams"]:
                if row["team_name"] != team or row["tournament_id"] not in tids:
                    continue
                participations += 1
                perf = row["performance"]
                tid = row["tournament_id"]
                if perf in KO_EXIT or (
                    perf == "final" and winners.get(tid) != team
                ):
                    ko_elim += 1
            rec[gkey] = {
                "copas": participations,
                "campeao": titles,
                "vice": second,
                "terceiro": third,
                "elim_mata_mata": ko_elim,
            }
        out[team] = rec
    return out


def build_match_results(data: dict, tids: set) -> dict:
    tour_years = {
        t["tournament_id"]: t["year"]
        for t in data["tournaments"]
        if t["tournament_id"] in tids
    }
    team_conf = {t["team_name"]: t["confederation_code"] for t in data["teams"]}
    apps: dict[tuple[str, str], list] = defaultdict(list)
    for row in data["team_appearances"]:
        if row["tournament_id"] not in tids:
            continue
        result = "W" if row["win"] else ("D" if row["draw"] else "L")
        apps[(row["team_name"], row["tournament_id"])].append((row["match_date"], result))

    max_matches: dict[str, int] = defaultdict(int)
    for (_team, tid), matches in apps.items():
        max_matches[tid] = max(max_matches[tid], len(matches))

    conf_teams: dict[str, set[str]] = defaultdict(set)
    for team, conf in team_conf.items():
        conf_teams[conf].add(team)

    years = sorted(set(tour_years.values()))
    confederations = []
    for conf in CONF_ORDER:
        teams_data = []
        for team in sorted(conf_teams.get(conf, [])):
            by_year = {}
            for tid, year in tour_years.items():
                key = (team, tid)
                if key not in apps:
                    continue
                matches = sorted(apps[key], key=lambda item: item[0])
                seq = "".join(match[1] for match in matches)
                pad = max_matches[tid] - len(seq)
                if pad > 0:
                    seq += "E" * pad
                by_year[str(year)] = seq
            if by_year:
                teams_data.append({"team": team, "years": by_year})
        if teams_data:
            confederations.append({"code": conf, "teams": teams_data})

    return {
        "years": years,
        "max_matches": {str(tour_years[tid]): max_matches[tid] for tid in max_matches},
        "confederations": confederations,
    }


def build_penalties(data: dict, tids: set) -> list:
    counts: dict[str, dict[str, int]] = defaultdict(lambda: {"scored": 0, "missed": 0})
    for pk in data["penalty_kicks"]:
        if pk["tournament_id"] not in tids:
            continue
        bucket = counts[pk["team_name"]]
        if pk["converted"]:
            bucket["scored"] += 1
        else:
            bucket["missed"] += 1
    rows = [
        {
            "team": team,
            "scored": values["scored"],
            "missed": values["missed"],
            "total": values["scored"] + values["missed"],
        }
        for team, values in counts.items()
    ]
    return sorted(rows, key=lambda row: -row["total"])


def build_goals_by_conf(data: dict, tids: set, conf_code: str, limit: int = 15) -> list:
    team_conf = {t["team_name"]: t["confederation_code"] for t in data["teams"]}
    counts = Counter()
    for goal in data["goals"]:
        if goal.get("own_goal") or goal["tournament_id"] not in tids:
            continue
        team = goal["player_team_name"]
        if team_conf.get(team) != conf_code:
            continue
        counts[team] += 1
    return counts.most_common(limit)


def opponent_map(data: dict) -> dict[str, dict[str, str]]:
    lookup: dict[str, dict[str, str]] = {}
    for match in data["matches"]:
        lookup[match["match_id"]] = {
            match["home_team_name"]: match["away_team_name"],
            match["away_team_name"]: match["home_team_name"],
        }
    return lookup


def build_h2h_events(data: dict, tids: set, opponents: dict) -> dict:
    goals = []
    for goal in data["goals"]:
        if goal["tournament_id"] not in tids:
            continue
        mid = goal["match_id"]
        team = goal["player_team_name"]
        opp = opponents.get(mid, {}).get(team)
        if not opp:
            continue
        minute = goal["minute_regulation"] + goal.get("minute_stoppage", 0)
        minute = min(max(minute, 1), 120)
        ko = 0 if "group" in goal["stage_name"].lower() else 1
        goals.append(
            [
                team,
                opp,
                minute,
                ko,
                1 if goal.get("own_goal") else 0,
                1 if goal.get("penalty") else 0,
            ]
        )

    matches = []
    for row in data["team_appearances"]:
        if row["tournament_id"] not in tids:
            continue
        opp = opponents.get(row["match_id"], {}).get(row["team_name"])
        if not opp:
            continue
        year = next(
            t["year"]
            for t in data["tournaments"]
            if t["tournament_id"] == row["tournament_id"]
        )
        matches.append(
            [
                row["team_name"],
                opp,
                year,
                row["goal_differential"],
                1 if row["knockout_stage"] else 0,
                row["match_date"],
            ]
        )

    bookings = []
    for row in data["bookings"]:
        if row["tournament_id"] not in tids:
            continue
        opp = opponents.get(row["match_id"], {}).get(row["team_name"])
        if not opp:
            continue
        minute = row["minute_regulation"] + row.get("minute_stoppage", 0)
        minute = min(max(minute, 1), 120)
        if row["red_card"]:
            card = "red"
        elif row["second_yellow_card"]:
            card = "second"
        else:
            card = "yellow"
        bookings.append(
            [
                row["team_name"],
                opp,
                minute,
                1 if "group" not in row["stage_name"].lower() else 0,
                card,
            ]
        )

    return {"goals": goals, "matches": matches, "bookings": bookings}


def timing_bucket(minute: int) -> str:
    if minute <= 15:
        return "1-15"
    if minute <= 30:
        return "16-30"
    if minute <= 45:
        return "31-45"
    if minute <= 60:
        return "46-60"
    if minute <= 75:
        return "61-75"
    if minute <= 90:
        return "76-90"
    return "90+"


def build_exploratory(data: dict, tids: set) -> dict:
    year_by_tid = {t["tournament_id"]: t["year"] for t in data["tournaments"]}
    mens_tids = {
        t["tournament_id"]
        for t in data["tournaments"]
        if "Men" in t["tournament_name"]
    }
    matches = []
    for row in data["matches"]:
        tid = row["tournament_id"]
        if tid not in tids:
            continue
        total = row["home_team_score"] + row["away_team_score"]
        if row["result"] == "home team win":
            result = 0
        elif row["result"] == "draw":
            result = 1
        else:
            result = 2
        matches.append(
            [
                year_by_tid[tid],
                row["home_team_name"],
                row["away_team_name"],
                total,
                result,
                1 if tid in mens_tids else 0,
            ]
        )

    goal_minutes = []
    for goal in data["goals"]:
        if goal.get("own_goal") or goal["tournament_id"] not in tids:
            continue
        minute = goal["minute_regulation"] + goal.get("minute_stoppage", 0)
        goal_minutes.append(
            [
                year_by_tid[goal["tournament_id"]],
                goal["player_team_name"],
                min(max(minute, 1), 120),
                1 if goal["tournament_id"] in mens_tids else 0,
            ]
        )

    return {"matches": matches, "goal_minutes": goal_minutes}


def build_team_goal_rates(data: dict, tids: set) -> dict:
    stats: dict[str, dict[str, float]] = defaultdict(lambda: {"gf": 0, "ga": 0, "n": 0})
    for row in data["team_appearances"]:
        if row["tournament_id"] not in tids:
            continue
        bucket = stats[row["team_name"]]
        bucket["gf"] += row["goals_for"]
        bucket["ga"] += row["goals_against"]
        bucket["n"] += 1
    out = {}
    for team, bucket in stats.items():
        if bucket["n"]:
            out[team] = {
                "gf": round(bucket["gf"] / bucket["n"], 3),
                "ga": round(bucket["ga"] / bucket["n"], 3),
            }
    return out


def embed_json_in_html(html: str, script_id: str, payload: dict) -> str:
    blob = json.dumps(payload, ensure_ascii=False)
    replacement = (
        f'<script id="{script_id}" type="application/json">\n{blob}\n</script>'
    )
    pattern = rf'<script id="{script_id}" type="application/json">.*?</script>'
    if re.search(pattern, html, flags=re.S):
        return re.sub(pattern, replacement, html, count=1, flags=re.S)
    return html.replace("<script>\nconst DB =", replacement + "\n<script>\nconst DB =", 1)


def main() -> None:
    with SRC.open(encoding="utf-8") as fh:
        data = json.load(fh)

    winners = {t["tournament_id"]: t["winner"] for t in data["tournaments"]}
    mens_tids = {
        t["tournament_id"]
        for t in data["tournaments"]
        if "Men" in t["tournament_name"]
    }
    womens_tids = {
        t["tournament_id"]
        for t in data["tournaments"]
        if "Women" in t["tournament_name"]
    }
    all_tids = mens_tids | womens_tids
    opponents = opponent_map(data)

    stats_payload = {
        "top_scorers_mens": top_scorers(data, mens_tids),
        "top_scorers_womens": top_scorers(data, womens_tids),
        "best_single_cup_mens": best_single_cup(data, mens_tids),
        "best_single_cup_womens": best_single_cup(data, womens_tids),
        "best_single_cup_all": best_single_cup(data, all_tids),
        "team_stats": team_stats_all(data, winners, mens_tids, womens_tids),
    }

    viz_payload = {
        "match_results": {
            "all": build_match_results(data, all_tids),
            "mens": build_match_results(data, mens_tids),
            "womens": build_match_results(data, womens_tids),
        },
        "penalties": {
            "all": build_penalties(data, all_tids),
            "mens": build_penalties(data, mens_tids),
            "womens": build_penalties(data, womens_tids),
        },
        "goals_by_conf": {
            "UEFA": {
                "all": build_goals_by_conf(data, all_tids, "UEFA"),
                "mens": build_goals_by_conf(data, mens_tids, "UEFA"),
                "womens": build_goals_by_conf(data, womens_tids, "UEFA"),
            },
            "CONMEBOL": {
                "all": build_goals_by_conf(data, all_tids, "CONMEBOL"),
                "mens": build_goals_by_conf(data, mens_tids, "CONMEBOL"),
                "womens": build_goals_by_conf(data, womens_tids, "CONMEBOL"),
            },
        },
        "h2h": {
            "all": build_h2h_events(data, all_tids, opponents),
            "mens": build_h2h_events(data, mens_tids, opponents),
            "womens": build_h2h_events(data, womens_tids, opponents),
        },
        "goal_rates": {
            "all": build_team_goal_rates(data, all_tids),
            "mens": build_team_goal_rates(data, mens_tids),
            "womens": build_team_goal_rates(data, womens_tids),
        },
        "exploratory": {
            "all": build_exploratory(data, all_tids),
            "mens": build_exploratory(data, mens_tids),
            "womens": build_exploratory(data, womens_tids),
        },
    }

    OUT_STATS.parent.mkdir(parents=True, exist_ok=True)
    OUT_STATS.write_text(json.dumps(stats_payload, ensure_ascii=False), encoding="utf-8")
    OUT_VIZ.write_text(json.dumps(viz_payload, ensure_ascii=False), encoding="utf-8")
    print(f"Wrote {OUT_STATS}")
    print(f"Wrote {OUT_VIZ}")

    if DASHBOARD.exists():
        html = DASHBOARD.read_text(encoding="utf-8")
        html = embed_json_in_html(html, "stats-extra-data", stats_payload)
        DASHBOARD.write_text(html, encoding="utf-8")
        print(f"Updated inline stats in {DASHBOARD}")


if __name__ == "__main__":
    main()
