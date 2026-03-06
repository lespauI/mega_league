#!/usr/bin/env python3
import os
import sys

from run_utils import run_script


def main():
    os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    print("\n" + "="*80)
    print("MEGA League Complete Analysis - Full Run")
    print("="*80)
    
    scripts = [
        ('stats_scripts/aggregate_team_stats.py', 'Team Statistics Aggregation', False, None),
        ('stats_scripts/aggregate_player_usage.py', 'Player Usage Distribution Analysis', False, None),
        ('stats_scripts/aggregate_rankings_stats.py', 'Team Rankings & Stats Aggregation', False, None),
        ('stats_scripts/build_player_team_stints.py', 'Player/Team Stints Summary (Trade-Aware)', False, None),
        ('scripts/calc_sos_season2_elo.py', 'Season 2 SoS (ELO) Calculation', False, None),
        ('scripts/calc_sos_season3_elo.py', 'Season 3 SoS (ELO) Calculation', False, None),
        ('scripts/calc_sos_by_rankings.py', 'Strength of Schedule Calculation', False, ['--season-index', '2', '--out-csv', 'output/ranked_sos_by_conference.csv']),
        ('scripts/generate_all_team_scenarios.py', 'Team-by-Team Playoff Scenario Analysis (includes playoff probabilities)', False, None),
        ('scripts/playoff_race_table.py', 'Playoff Race Table (AFC/NFC Double-Column)', False, None),
        ('scripts/playoff_race_html.py', 'Playoff Race HTML Report (with embedded table)', False, None),
        ('scripts/generate_team_scenario_html.py', 'Team Scenario HTML Viewer', False, None),
        ('scripts/top_pick_race_analysis.py', 'Draft Pick Race Analysis & Visualizations', True, None),
        ('scripts/generate_index.py', 'Index Page Generation', False, None),
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
        print("\n" + "="*80)
        print("ALL SCRIPTS COMPLETED SUCCESSFULLY!")
        print("="*80)
        print("\nGenerated files & verifications:")
        print("\n📊 Team Statistics & Verifications:")
        print("  • output/team_aggregated_stats.csv - Team statistics (84 metrics)")
        print("  • output/team_player_usage.csv - Player usage distribution (48 metrics)")
        print("  • output/team_rankings_stats.csv - Rankings and stats aggregation")
        print("  • output/player_team_stints.csv - Player/team season stints (trade-aware)")
        print("  • output/traded_players_report.csv - Multi-team player summary")
        print("  • scripts/verify_trade_stats.py - Trade stats invariants verified via console")
        print("\n🏈 Playoff Analysis:")
        print("  • output/ranked_sos_by_conference_season3.csv - Strength of schedule data (Season 3)")
        print("  • output/sos/season2_elo.csv - Season 2 SoS (ELO) table")
        print("  • output/sos/season2_elo.json - Season 2 SoS (ELO) JSON")
        print("  • output/sos/season3_elo.csv - Season 3 SoS (ELO) table")
        print("  • output/sos/season3_elo.json - Season 3 SoS (ELO) JSON")
        print("  • output/playoff_probabilities.json - Playoff probabilities data")
        print("  • docs/playoff_race_table.html - Interactive playoff race table")
        print("  • docs/playoff_race.html - Full playoff analysis report (with embedded table)")
        print("  • docs/playoff_race_report.md - Markdown playoff report")
        print("  • docs/team_scenarios/*.md - Individual team scenario reports")
        print("  • docs/team_scenarios.html - Team scenario viewer with dropdown selector")
        print("\n📈 Draft Analysis:")
        print("  • output/draft_race/draft_pick_race.png - Draft pick visualization")
        print("  • output/draft_race/tank_battle.png - Tank battle scatter plot")
        print("  • output/draft_race/draft_race_report.md - Draft analysis report")
        print("\n🌐 Web Interface:")
        print("  • docs/index.html - Main navigation page")
        print("\n✨ Open docs/index.html in your browser to view all visualizations!")
    else:
        print("\n⚠️  Some scripts failed. Check the output above for details.")
        sys.exit(1)


if __name__ == "__main__":
    main()
