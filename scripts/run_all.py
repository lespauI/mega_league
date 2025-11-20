#!/usr/bin/env python3
import sys
import subprocess
import os


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
    print("MEGA League Complete Analysis - Full Run")
    print("="*80)
    
    scripts = [
        ('stats_scripts/aggregate_team_stats.py', 'Team Statistics Aggregation', False),
        ('stats_scripts/aggregate_player_usage.py', 'Player Usage Distribution Analysis', False),
        ('scripts/calc_sos_season2_elo.py', 'Season 2 SoS (ELO) Calculation', False),
        ('scripts/calc_sos_by_rankings.py', 'Strength of Schedule Calculation', False),
        ('scripts/calc_playoff_probabilities.py', 'Playoff Probability Calculation', False),
        ('scripts/playoff_race_table.py', 'Playoff Race Table (AFC/NFC Double-Column)', False),
        ('scripts/playoff_race_html.py', 'Playoff Race HTML Report (with embedded table)', False),
        ('scripts/top_pick_race_analysis.py', 'Draft Pick Race Analysis & Visualizations', True),
        ('scripts/generate_index.py', 'Index Page Generation', False),
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
        print("\n📊 Team Statistics:")
        print("  • output/team_aggregated_stats.csv - Team statistics (84 metrics)")
        print("  • output/team_player_usage.csv - Player usage distribution (48 metrics)")
        print("\n🏈 Playoff Analysis:")
        print("  • output/ranked_sos_by_conference.csv - Strength of schedule data")
        print("  • output/sos/season2_elo.csv - Season 2 SoS (ELO) table")
        print("  • output/sos/season2_elo.json - Season 2 SoS (ELO) JSON")
        print("  • output/playoff_probabilities.json - Playoff probabilities data")
        print("  • docs/playoff_race_table.html - Interactive playoff race table")
        print("  • docs/playoff_race.html - Full playoff analysis report (with embedded table)")
        print("  • docs/playoff_race_report.md - Markdown playoff report")
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
