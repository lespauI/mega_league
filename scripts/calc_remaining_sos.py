#!/usr/bin/env python3
import csv
import math
import os
from collections import defaultdict


def read_teams(teams_csv_path):
    teams = {}
    with open(teams_csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Normalize team name keys
            display_name = (row.get("displayName") or "").strip()
            team_name = (row.get("teamName") or "").strip()
            key = display_name or team_name
            if not key:
                continue

            # Parse wins/losses/ties
            def to_int(v):
                try:
                    return int(v)
                except Exception:
                    return 0

            wins = to_int(row.get("totalWins"))
            losses = to_int(row.get("totalLosses"))
            ties = to_int(row.get("totalTies"))
            gp = wins + losses + ties

            # Compute win_pct if possible
            win_pct_val = None
            if gp > 0:
                win_pct_val = (wins + 0.5 * ties) / gp
            else:
                # fallback to provided winPct if present and numeric
                wp = (row.get("winPct") or "").strip()
                try:
                    win_pct_val = float(wp)
                except Exception:
                    win_pct_val = 0.0

            teams[key] = {
                "conference": (row.get("conferenceName") or "").strip(),
                "wins": wins,
                "losses": losses,
                "ties": ties,
                "gp": gp,
                "win_pct": win_pct_val,
            }
    return teams


def read_games_split(games_csv_path):
    remaining = []
    past = []
    with open(games_csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            status = (row.get("status") or "").strip()
            home = (row.get("homeTeam") or "").strip()
            away = (row.get("awayTeam") or "").strip()
            if not home or not away:
                continue
            if status == "1":
                remaining.append((home, away))
            elif status in {"2", "3"}:  # treat these as completed games
                past.append((home, away))
            else:
                # ignore blanks or unknown statuses
                pass
    return remaining, past


def compute_sos(teams, remaining_games, past_games):
    # Build opponent lists per team
    opp_remaining = defaultdict(list)
    for home, away in remaining_games:
        opp_remaining[home].append(away)
        opp_remaining[away].append(home)

    opp_past = defaultdict(list)
    for home, away in past_games:
        opp_past[home].append(away)
        opp_past[away].append(home)

    results = []
    for team_name, info in teams.items():
        # Remaining
        opps_rem = opp_remaining.get(team_name, [])
        opp_wpcts_rem = []
        for opp_name in opps_rem:
            opp = teams.get(opp_name)
            if not opp:
                # opponent not found in teams list; skip
                continue
            opp_wpcts_rem.append(opp["win_pct"])

        remaining_games_count = len(opps_rem)
        if opp_wpcts_rem:
            rem_sos_sum = sum(opp_wpcts_rem)
            rem_sos_avg = rem_sos_sum / len(opp_wpcts_rem)
        else:
            rem_sos_sum = 0.0
            rem_sos_avg = 0.0

        # Past
        opps_past = opp_past.get(team_name, [])
        opp_wpcts_past = []
        for opp_name in opps_past:
            opp = teams.get(opp_name)
            if not opp:
                continue
            opp_wpcts_past.append(opp["win_pct"])

        if opp_wpcts_past:
            past_sos_sum = sum(opp_wpcts_past)
            past_sos_avg = past_sos_sum / len(opp_wpcts_past)
        else:
            past_sos_sum = 0.0
            past_sos_avg = 0.0

        total_sos_sum = past_sos_sum + rem_sos_sum

        results.append(
            {
                "team": team_name,
                "conference": info.get("conference", ""),
                "W": info.get("wins", 0),
                "L": info.get("losses", 0),
                "remaining_games": remaining_games_count,
                "sos_avg": round(rem_sos_avg, 4),
                "sos_sum": round(rem_sos_sum, 4),
                "past_sos_avg": round(past_sos_avg, 4),
                "total_sos": round(total_sos_sum, 4),
            }
        )

    return results


def write_output(results, output_path):
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    # Sort by conference then by sos_avg desc
    results_sorted = sorted(
        results, key=lambda r: (r.get("conference", ""), -r.get("sos_avg", 0.0), r.get("team", ""))
    )
    fieldnames = [
        "team",
        "conference",
        "W",
        "L",
        "remaining_games",
        "sos_avg",
        "sos_sum",
        "past_sos_avg",
        "total_sos",
    ]
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in results_sorted:
            writer.writerow(row)


def main():
    base_dir = os.getcwd()
    teams_csv = os.path.join(base_dir, "MEGA_teams.csv")
    games_csv = os.path.join(base_dir, "MEGA_games.csv")
    output_csv = os.path.join(base_dir, "output", "remaining_sos_by_conference.csv")

    teams = read_teams(teams_csv)
    remaining_games, past_games = read_games_split(games_csv)
    results = compute_sos(teams, remaining_games, past_games)
    write_output(results, output_csv)

    # Brief preview to stdout (top 5 per conference by avg)
    by_conf = defaultdict(list)
    for r in results:
        by_conf[r.get("conference", "")].append(r)

    for conf in sorted(by_conf.keys()):
        print(f"\n{conf} — top 5 by remaining SoS avg:")
        top5 = sorted(by_conf[conf], key=lambda x: -x["sos_avg"])[:5]
        for row in top5:
            print(
                f"  {row['team']} (record {row['W']}-{row['L']}): "
                f"games={row['remaining_games']}, avg={row['sos_avg']}, sum={row['sos_sum']}, "
                f"past_avg={row['past_sos_avg']}, total_sum={row['total_sos']}"
            )


if __name__ == "__main__":
    main()
