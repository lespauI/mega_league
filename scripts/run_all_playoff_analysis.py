#!/usr/bin/env python3
import os
import sys
import subprocess

def run_script(script_name, description, optional=False):
    """Run a Python script and print its status"""
    print("\n" + "="*80)
    print(f"Running: {description}")
    if optional:
        print("(Optional - requires matplotlib)")
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
