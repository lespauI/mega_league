#!/usr/bin/env python3
import os
import random
from team_scenario_report import (
    load_data,
    calculate_team_stats,
    generate_markdown_report
)

DEFAULT_NUM_SIMULATIONS = 10000

def main(num_simulations=DEFAULT_NUM_SIMULATIONS, seed=None):
    if seed is not None:
        random.seed(seed)
    
    os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    teams_info, games, sos_data = load_data()
    stats = calculate_team_stats(teams_info, games)
    
    os.makedirs('docs/team_scenarios', exist_ok=True)
    
    print("\n" + "="*80)
    print("GENERATING TEAM SCENARIO REPORTS")
    print("="*80)
    print(f"Running {num_simulations:,} simulations per team...\n")
    
    all_teams = sorted(teams_info.keys())
    
    for i, team in enumerate(all_teams, 1):
        print(f"  [{i}/{len(all_teams)}] Generating report for {team}...")
        
        md_content = generate_markdown_report(team, teams_info, stats, sos_data, games, num_simulations)
        
        safe_filename = team.replace(' ', '_').replace('/', '_')
        output_path = f'docs/team_scenarios/{safe_filename}.md'
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(md_content)
    
    print("\n" + "="*80)
    print("GENERATION COMPLETE!")
    print("="*80)
    print(f"\nGenerated {len(all_teams)} team scenario reports")
    print(f"Output directory: docs/team_scenarios/")
    print(f"Simulations per team: {num_simulations:,}\n")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Generate Monte Carlo scenario reports for all teams')
    parser.add_argument('-n', '--simulations', type=int, default=DEFAULT_NUM_SIMULATIONS,
                       help=f'Number of simulations per team (default: {DEFAULT_NUM_SIMULATIONS})')
    parser.add_argument('-s', '--seed', type=int, default=None,
                       help='Random seed for reproducibility')
    
    args = parser.parse_args()
    main(num_simulations=args.simulations, seed=args.seed)
