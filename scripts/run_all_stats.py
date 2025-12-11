#!/usr/bin/env python3
import sys
import subprocess
import os


def run_script(script_name, description):
    """Run a Python script and print its status"""
    print("\n" + "="*80)
    print(f"Running: {description}")
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
            print(f"✗ {description} failed with exit code {result.returncode}")
            return False
            
    except Exception as e:
        print(f"✗ Error running {description}: {str(e)}")
        return False


def main():
    os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    print("\n" + "="*80)
    print("MEGA League Stats Analysis - Full Run")
    print("="*80)
    
    scripts = [
        ('stats_scripts/aggregate_team_stats.py', 'Team Statistics Aggregation'),
        ('stats_scripts/aggregate_player_usage.py', 'Player Usage Distribution Analysis'),
        ('stats_scripts/aggregate_rankings_stats.py', 'Team Rankings and Stats Aggregation'),
        ('stats_scripts/build_player_team_stints.py', 'Player/Team Stints Summary (Trade-Aware)'),
        ('scripts/generate_index.py', 'Index Page Generation'),
        ('scripts/verify_trade_stats.py', 'Trade Stats Verification (Multi-Team Invariants)'),
    ]
    
    results = []
    for script, description in scripts:
        success = run_script(script, description)
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
        print("  • output/team_aggregated_stats.csv - Team statistics (trade-aware, 80+ metrics)")
        print("  • output/team_player_usage.csv - Player usage distribution (trade-aware, 40+ metrics)")
        print("  • output/rankings_aggregated_stats.csv - Rankings and statistics combined")
        print("  • output/player_team_stints.csv - Player/team season stints (per-team splits for multi-team players)")
        print("  • output/traded_players_report.csv - Multi-team player summary & verification view")
        print("  • docs/index.html - Main navigation page")
        print("\nOpen docs/index.html in your browser to view all visualizations and stats reports!")
    else:
        print("\n⚠️  Some scripts failed. Check the output above for details.")
        sys.exit(1)


if __name__ == "__main__":
    main()
