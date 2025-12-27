#!/usr/bin/env python3
import csv
import os
from collections import defaultdict


def to_int(val, default=None):
    try:
        v = int(val)
        return v
    except Exception:
        return default


def norm_rank(rank):
    # Normalize a rank 1..32 to 1..~0.03125 (higher is better)
    if rank is None or rank <= 0:
        return None
    return (33 - rank) / 32.0


def mean_safe(values):
    vals = [v for v in values if v is not None]
    if not vals:
        return None
    return sum(vals) / len(vals)


def compute_strength_score(row, w_off=0.4, w_def=0.4, w_rank=0.2):
    # Offense metrics
    off_keys = ["ptsForRank", "offTotalYdsRank", "offPassYdsRank", "offRushYdsRank"]
    off_vals = [norm_rank(to_int(row.get(k), None)) for k in off_keys]
    off_score = mean_safe(off_vals)

    # Defense metrics
    def_keys = ["ptsAgainstRank", "defTotalYdsRank", "defPassYdsRank", "defRushYdsRank"]
    def_vals = [norm_rank(to_int(row.get(k), None)) for k in def_keys]
    def_score = mean_safe(def_vals)

    # Overall/trend
    rank_val = norm_rank(to_int(row.get("rank"), None))
    prev_val = norm_rank(to_int(row.get("prevRank"), None))
    if prev_val is None:
        overall_score = rank_val
    else:
        overall_score = mean_safe([rank_val, prev_val])

    # Reweight if some groups missing
    parts = []
    if off_score is not None and w_off > 0:
        parts.append((off_score, w_off))
    if def_score is not None and w_def > 0:
        parts.append((def_score, w_def))
    if overall_score is not None and w_rank > 0:
        parts.append((overall_score, w_rank))

    if not parts:
        return None

    total_w = sum(w for _, w in parts)
    return sum(s * w for s, w in parts) / total_w


def read_latest_rankings(rankings_csv_path):
    # Keep latest by (seasonIndex, stageIndex, weekIndex) for Season 2 only
    latest = {}
    with open(rankings_csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            team = (row.get("team") or "").strip()
            if not team:
                continue
            si = to_int(row.get("seasonIndex"), -1)
            sti = to_int(row.get("stageIndex"), -1)
            if si != 1:
                continue
            key = team
            wi = to_int(row.get("weekIndex"), -1)
            cur_key = (si, sti, wi)
            prev = latest.get(key)
            if prev is None:
                latest[key] = (cur_key, row)
            else:
                if cur_key > prev[0]:
                    latest[key] = (cur_key, row)

    # Compute strength score per team
    scores = {}
    for team, (_, row) in latest.items():
        score = compute_strength_score(row)
        if score is not None:
            scores[team] = score
    return scores


def read_games_split(games_csv_path):
    remaining = []
    past = []
    with open(games_csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            si = to_int(row.get("seasonIndex"), -1)
            sti = to_int(row.get("stageIndex"), -1)
            if si != 1 or sti != 1:
                continue
            status = (row.get("status") or "").strip()
            home = (row.get("homeTeam") or "").strip()
            away = (row.get("awayTeam") or "").strip()
            if not home or not away:
                continue
            if status == "1":
                remaining.append((home, away))
            elif status in {"2", "3"}:  # completed
                past.append((home, away))
            else:
                # ignore other/blank
                pass
    return remaining, past


def read_teams_info(teams_csv_path):
    info = {}
    with open(teams_csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            display_name = (row.get("displayName") or "").strip()
            team_name = (row.get("teamName") or "").strip()
            key = display_name or team_name
            if not key:
                continue

            def to_int0(v):
                try:
                    return int(v)
                except Exception:
                    return 0

            info[key] = {
                "conference": (row.get("conferenceName") or "").strip(),
                "W": to_int0(row.get("totalWins")),
                "L": to_int0(row.get("totalLosses")),
                "T": to_int0(row.get("totalTies")),
            }
    return info


def compute_ranked_sos(teams_info, strength_scores, remaining_games, past_games):
    opp_remaining = defaultdict(list)
    for h, a in remaining_games:
        opp_remaining[h].append(a)
        opp_remaining[a].append(h)

    opp_past = defaultdict(list)
    for h, a in past_games:
        opp_past[h].append(a)
        opp_past[a].append(h)

    results = []
    for team, meta in teams_info.items():
        # Remaining
        rem = opp_remaining.get(team, [])
        rem_scores = [strength_scores.get(o) for o in rem if strength_scores.get(o) is not None]
        if rem_scores:
            ranked_sos_sum = sum(rem_scores)
            ranked_sos_avg = ranked_sos_sum / len(rem_scores)
        else:
            ranked_sos_sum = 0.0
            ranked_sos_avg = 0.0

        # Past
        past = opp_past.get(team, [])
        past_scores = [strength_scores.get(o) for o in past if strength_scores.get(o) is not None]
        if past_scores:
            past_ranked_sos_sum = sum(past_scores)
            past_ranked_sos_avg = past_ranked_sos_sum / len(past_scores)
        else:
            past_ranked_sos_sum = 0.0
            past_ranked_sos_avg = 0.0

        total_ranked_sos = ranked_sos_sum + past_ranked_sos_sum

        results.append(
            {
                "team": team,
                "conference": meta.get("conference", ""),
                "W": meta.get("W", 0),
                "L": meta.get("L", 0),
                "T": meta.get("T", 0),
                "remaining_games": len(rem),
                "ranked_sos_avg": round(ranked_sos_avg, 4),
                "ranked_sos_sum": round(ranked_sos_sum, 4),
                "past_ranked_sos_avg": round(past_ranked_sos_avg, 4),
                "total_ranked_sos": round(total_ranked_sos, 4),
            }
        )

    return results


def write_output(results, output_path):
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    results_sorted = sorted(
        results, key=lambda r: (r.get("conference", ""), -r.get("ranked_sos_avg", 0.0), r.get("team", ""))
    )
    fieldnames = [
        "team",
        "conference",
        "W",
        "L",
        "T",
        "remaining_games",
        "ranked_sos_avg",
        "ranked_sos_sum",
        "past_ranked_sos_avg",
        "total_ranked_sos",
    ]
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in results_sorted:
            writer.writerow(row)


def main():
    base_dir = os.getcwd()
    rankings_csv = os.path.join(base_dir, "MEGA_rankings.csv")
    games_csv = os.path.join(base_dir, "MEGA_games.csv")
    teams_csv = os.path.join(base_dir, "MEGA_teams.csv")
    output_csv = os.path.join(base_dir, "output", "ranked_sos_by_conference.csv")

    strength_scores = read_latest_rankings(rankings_csv)
    remaining, past = read_games_split(games_csv)
    teams_info = read_teams_info(teams_csv)
    results = compute_ranked_sos(teams_info, strength_scores, remaining, past)
    write_output(results, output_csv)

    # Console preview
    by_conf = defaultdict(list)
    for r in results:
        by_conf[r.get("conference", "")].append(r)

    for conf in sorted(by_conf.keys()):
        print(f"\n{conf} — top 5 by ranked SoS avg:")
        top5 = sorted(by_conf[conf], key=lambda x: -x["ranked_sos_avg"])[:5]
        for row in top5:
            print(
                f"  {row['team']} (record {row['W']}-{row['L']}-{row['T']}): "
                f"games={row['remaining_games']}, avg={row['ranked_sos_avg']}, sum={row['ranked_sos_sum']}, "
                f"past_avg={row['past_ranked_sos_avg']}, total_sum={row['total_ranked_sos']}"
            )


if __name__ == "__main__":
    main()

