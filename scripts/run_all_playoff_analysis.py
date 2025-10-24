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
    if rank is None or rank <= 0:
        return None
    return (33 - rank) / 32.0


def mean_safe(values):
    vals = [v for v in values if v is not None]
    if not vals:
        return None
    return sum(vals) / len(vals)


def compute_strength_score(row, w_off=0.4, w_def=0.4, w_rank=0.2):
    off_keys = ["ptsForRank", "offTotalYdsRank", "offPassYdsRank", "offRushYdsRank"]
    off_vals = [norm_rank(to_int(row.get(k), None)) for k in off_keys]
    off_score = mean_safe(off_vals)

    def_keys = ["ptsAgainstRank", "defTotalYdsRank", "defPassYdsRank", "defRushYdsRank"]
    def_vals = [norm_rank(to_int(row.get(k), None)) for k in def_keys]
    def_score = mean_safe(def_vals)

    rank_val = norm_rank(to_int(row.get("rank"), None))
    prev_val = norm_rank(to_int(row.get("prevRank"), None))
    if prev_val is None:
        overall_score = rank_val
    else:
        overall_score = mean_safe([rank_val, prev_val])

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
    latest = {}
    with open(rankings_csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            team = (row.get("team") or "").strip()
            if not team:
                continue
            key = team
            si = to_int(row.get("seasonIndex"), -1)
            sti = to_int(row.get("stageIndex"), -1)
            wi = to_int(row.get("weekIndex"), -1)
            cur_key = (si, sti, wi)
            prev = latest.get(key)
            if prev is None:
                latest[key] = (cur_key, row)
            else:
                if cur_key > prev[0]:
                    latest[key] = (cur_key, row)

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
            status = (row.get("status") or "").strip()
            home = (row.get("homeTeam") or "").strip()
            away = (row.get("awayTeam") or "").strip()
            if not home or not away:
                continue
            if status == "1":
                remaining.append((home, away))
            elif status in {"2", "3"}:
                past.append((home, away))
            else:
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
        rem = opp_remaining.get(team, [])
        rem_scores = [strength_scores.get(o) for o in rem if strength_scores.get(o) is not None]
        if rem_scores:
            ranked_sos_sum = sum(rem_scores)
            ranked_sos_avg = ranked_sos_sum / len(rem_scores)
        else:
            ranked_sos_sum = 0.0
            ranked_sos_avg = 0.0

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


import sys
import subprocess

def run_script(script_name, description, optional=False):
    """Run a Python script and print its status"""
    print("\n" + "="*80)
    print(f"Running: {description}")
    if optional:
        print("(Optional)")
    print("="*80)
    
    try:
        result = subprocess.run(
            [sys.executable, script_name],
            cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            capture_output=False,
            text=True
        )
        
        if result.returncode == 0:
            print(f"✓ {description} completed successfully")
            return True
        else:
            if optional:
                print(f"⚠ {description} skipped (missing dependencies)")
                return True
            else:
                print(f"✗ {description} failed with exit code {result.returncode}")
                return False
            
    except Exception as e:
        if optional:
            print(f"⚠ {description} skipped: {str(e)}")
            return True
        else:
            print(f"✗ Error running {description}: {str(e)}")
            return False

def main():
    os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    print("\n" + "="*80)
    print("MEGA League Playoff & Draft Analysis - Full Run")
    print("="*80)
    
    scripts = [
        ('scripts/calc_sos_by_rankings.py', 'Strength of Schedule Calculation', False),
        ('scripts/calc_playoff_probabilities.py', 'Playoff Probability Calculation', False),
        ('scripts/playoff_race_table.py', 'Playoff Race Table (AFC/NFC Double-Column)', False),
        ('scripts/playoff_race_html.py', 'Playoff Race HTML Report (with embedded table)', False),
        ('scripts/top_pick_race_analysis.py', 'Draft Pick Race Analysis & Visualizations', True),
    ]
    
    results = []
    for script, description, optional in scripts:
        success = run_script(script, description, optional)
        results.append((description, success))
    
    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)
    
    for description, success in results:
        status = "✓" if success else "✗"
        print(f"{status} {description}")
    
    all_success = all(r[1] for r in results)
    
    if all_success:
        print("\n" + "="*80)
        print("ALL SCRIPTS COMPLETED SUCCESSFULLY!")
        print("="*80)
        print("\nGenerated files:")
        print("  • output/ranked_sos_by_conference.csv - Strength of schedule data")
        print("  • output/playoff_probabilities.json - Playoff probabilities data")
        print("  • docs/playoff_race_table.html - Interactive playoff race table")
        print("  • docs/playoff_race.html - Full playoff analysis report (with embedded table)")
        print("  • docs/playoff_race_report.md - Markdown playoff report")
        print("  • output/draft_race/draft_pick_race.png - Draft pick visualization")
        print("  • output/draft_race/tank_battle.png - Tank battle scatter plot")
        print("  • output/draft_race/draft_race_report.md - Draft analysis report")
        print("\nView docs/playoff_race.html in your browser for full analysis!")
    else:
        print("\n⚠️  Some scripts failed. Check the output above for details.")
        sys.exit(1)

if __name__ == "__main__":
    main()
