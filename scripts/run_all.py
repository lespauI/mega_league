#!/usr/bin/env python3
import argparse
import os
import sys

from run_utils import run_script, season_start_row, publish_browser_data


def main(season_index=0):
    os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    print("\n" + "="*80)
    print("MEGA League Complete Analysis - Full Run")
    print("="*80)
    
    season = season_index + 1
    season_args = ['--season-index', str(season_index)]
    first_row = season_start_row(season_index)

    scripts = [
        ('stats_scripts/build_player_team_stints.py', 'Player/Team Stints Summary (Trade-Aware)', False, None),
        ('stats_scripts/aggregate_team_stats.py', 'Team Statistics Aggregation', False, None),
        ('stats_scripts/aggregate_player_usage.py', 'Player Usage Distribution Analysis', False, None),
        ('stats_scripts/aggregate_rankings_stats.py', 'Team Rankings & Stats Aggregation', False, None),
        ('scripts/calc_sos_elo.py', f'Season {season} SoS (ELO)', False, ['--season-index', str(season), '--start-row', str(first_row)]),
        ('scripts/calc_sos_by_rankings.py', f'Season {season} Rankings SoS', False, season_args + ['--out-csv', 'output/ranked_sos_by_conference.csv']),
        ('scripts/generate_all_team_scenarios.py', 'Team-by-Team Playoff Scenario Analysis (includes playoff probabilities)', False, season_args),
        ('scripts/playoff_race_table.py', 'Playoff Race Table (AFC/NFC Double-Column)', False, season_args),
        ('scripts/playoff_race_html.py', 'Playoff Race HTML Report (with embedded table)', False, season_args),
        ('scripts/generate_team_scenario_html.py', 'Team Scenario HTML Viewer', False, None),
        ('scripts/top_pick_race_analysis.py', 'Draft Pick Race Analysis & Visualizations', True, None),
        ('scripts/power_rankings_roster.py', 'Roster Power Rankings', False, None),
        ('scripts/verify_trade_stats.py', 'Trade Stats Verification (Multi-Team Invariants)', False, None),
    ]
    
    results = []
    for script, description, optional, extra_args in scripts:
        success = run_script(script, description, optional, extra_args)
        results.append((description, success))
    
    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)
    
    for description, success in results:
        status = "✓" if success else "✗"
        print(f"{status} {description}")
    
    all_success = all(r[1] for r in results)
    
    if all_success:
        publish_browser_data(season_index)
        if not run_script('scripts/generate_index.py', 'Index Page Generation'):
            sys.exit(1)
        print(f"\nSeason {season} analysis complete (CSV seasonIndex={season_index}).")
        print("Results: output/; browser data: docs/data/; open index.html at the repository root.")
    else:
        print("\n⚠️  Some scripts failed. Check the output above for details.")
        sys.exit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run analysis for one CSV season")
    parser.add_argument("--season-index", type=int, default=0, help="Zero-based CSV season index (default: 0)")
    main(season_index=parser.parse_args().season_index)
