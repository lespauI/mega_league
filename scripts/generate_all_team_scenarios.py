#!/usr/bin/env python3
import os
import json
import random
from collections import Counter, defaultdict
from datetime import datetime, timezone

from calc_playoff_probabilities import (
    load_data,
    calculate_team_stats,
    simulate_remaining_games,
    determine_playoff_teams,
    TIE_PROBABILITY
)
from team_scenario_report import (
    get_remaining_games_for_team,
    calculate_game_probabilities,
    generate_markdown_report
)

DEFAULT_NUM_SIMULATIONS = 10000


def run_consolidated_simulations(teams_info, stats, sos_data, games, num_simulations):
    all_teams = list(teams_info.keys())
    
    team_data = {team: {
        'final_records': Counter(),
        'playoff_by_record': defaultdict(int),
        'division_by_record': defaultdict(int),
        'bye_by_record': defaultdict(int),
        'total_playoffs': 0,
        'total_division': 0,
        'total_bye': 0,
        'example_outcomes_by_record': {}
    } for team in all_teams}
    
    for sim in range(num_simulations):
        if (sim + 1) % 1000 == 0:
            print(f"  Simulation {sim + 1:,}/{num_simulations:,}...")
        
        simulated_games = simulate_remaining_games(teams_info, stats, sos_data, games)
        playoff_teams, division_winners, bye_teams = determine_playoff_teams(teams_info, stats, simulated_games)
        
        for team in all_teams:
            conf = teams_info[team]['conference']
            
            team_results = {
                'W': stats[team]['W'],
                'L': stats[team]['L'],
                'T': stats[team]['T']
            }
            
            game_outcomes = []
            for game in simulated_games:
                if game['home'] == team or game['away'] == team:
                    is_home = (game['home'] == team)
                    opponent = game['away'] if is_home else game['home']
                    
                    if game.get('is_tie', False):
                        outcome = 'T'
                        team_results['T'] += 1
                    elif game.get('winner') == team:
                        outcome = 'W'
                        team_results['W'] += 1
                    else:
                        outcome = 'L'
                        team_results['L'] += 1
                    
                    game_outcomes.append({
                        'opponent': opponent,
                        'outcome': outcome,
                        'is_home': is_home
                    })
            
            record_key = f"{team_results['W']}-{team_results['L']}-{team_results['T']}"
            team_data[team]['final_records'][record_key] += 1
            
            made_playoffs = team in playoff_teams[conf]
            won_division = team in division_winners[conf]
            got_bye = team in bye_teams[conf]
            
            if made_playoffs:
                team_data[team]['playoff_by_record'][record_key] += 1
                team_data[team]['total_playoffs'] += 1
            if won_division:
                team_data[team]['division_by_record'][record_key] += 1
                team_data[team]['total_division'] += 1
            if got_bye:
                team_data[team]['bye_by_record'][record_key] += 1
                team_data[team]['total_bye'] += 1
            
            if record_key not in team_data[team]['example_outcomes_by_record'] and game_outcomes:
                team_data[team]['example_outcomes_by_record'][record_key] = game_outcomes
    
    return team_data


def build_team_scenarios_json(teams_info, stats, sos_data, games, team_data, num_simulations):
    result = {
        'generated_at': datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
        'num_simulations': num_simulations,
        'teams': {}
    }
    
    for team in sorted(teams_info.keys()):
        conf = teams_info[team]['conference']
        div = teams_info[team]['division']
        current_record = f"{stats[team]['W']}-{stats[team]['L']}-{stats[team]['T']}"
        
        remaining_games = get_remaining_games_for_team(team, games)
        game_probs = calculate_game_probabilities(team, teams_info, stats, remaining_games)
        
        data = team_data[team]
        
        sorted_records = sorted(
            data['final_records'].items(),
            key=lambda x: (-int(x[0].split('-')[0]), int(x[0].split('-')[1]))
        )
        
        record_outcomes = []
        for record, count in sorted_records:
            freq_pct = (count / num_simulations) * 100
            playoff_pct = (data['playoff_by_record'][record] / count * 100) if count > 0 else 0
            division_pct = (data['division_by_record'][record] / count * 100) if count > 0 else 0
            bye_pct = (data['bye_by_record'][record] / count * 100) if count > 0 else 0
            
            record_outcome = {
                'record': record,
                'frequency': count,
                'percentage': round(freq_pct, 2),
                'playoff_pct': round(playoff_pct, 1),
                'division_pct': round(division_pct, 1),
                'bye_pct': round(bye_pct, 1)
            }
            
            if record in data['example_outcomes_by_record']:
                record_outcome['example_outcomes'] = data['example_outcomes_by_record'][record]
            
            record_outcomes.append(record_outcome)
        
        sorted_by_freq = sorted(data['final_records'].items(), key=lambda x: -x[1])
        most_likely_record, most_likely_count = sorted_by_freq[0] if sorted_by_freq else ('0-0-0', 0)
        most_likely_pct = (most_likely_count / num_simulations) * 100 if num_simulations > 0 else 0
        
        most_likely = {
            'record': most_likely_record,
            'frequency': most_likely_count,
            'percentage': round(most_likely_pct, 2)
        }
        if most_likely_record in data['example_outcomes_by_record']:
            most_likely['example_outcomes'] = data['example_outcomes_by_record'][most_likely_record]
        
        remaining_games_data = []
        for gp in game_probs:
            remaining_games_data.append({
                'week': gp['week'],
                'opponent': gp['opponent'],
                'is_home': gp['is_home'],
                'win_prob': round(gp['win_prob'], 1),
                'tie_prob': round(gp['tie_prob'], 1),
                'loss_prob': round(gp['loss_prob'], 1)
            })
        
        overall_playoff = (data['total_playoffs'] / num_simulations) * 100
        overall_division = (data['total_division'] / num_simulations) * 100
        overall_bye = (data['total_bye'] / num_simulations) * 100
        
        result['teams'][team] = {
            'conference': conf,
            'division': div,
            'current_record': current_record,
            'win_pct': round(stats[team]['win_pct'], 3),
            'remaining_games': remaining_games_data,
            'game_count': len(remaining_games_data),
            'overall_probabilities': {
                'playoff': round(overall_playoff, 1),
                'division': round(overall_division, 1),
                'bye': round(overall_bye, 1)
            },
            'record_outcomes': record_outcomes,
            'most_likely': most_likely
        }
    
    return result


def main(num_simulations=DEFAULT_NUM_SIMULATIONS, seed=None, generate_markdown=False):
    if seed is not None:
        random.seed(seed)
    
    os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    teams_info, games, sos_data = load_data()
    stats = calculate_team_stats(teams_info, games)
    
    os.makedirs('output', exist_ok=True)
    
    print("\n" + "="*80)
    print("GENERATING CONSOLIDATED TEAM SCENARIOS")
    print("="*80)
    print(f"Running {num_simulations:,} simulations (all teams tracked simultaneously)...\n")
    
    team_data = run_consolidated_simulations(teams_info, stats, sos_data, games, num_simulations)
    
    print("\nBuilding JSON output...")
    scenarios_json = build_team_scenarios_json(teams_info, stats, sos_data, games, team_data, num_simulations)
    
    json_path = 'output/team_scenarios.json'
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(scenarios_json, f, indent=2)
    
    print(f"  Saved: {json_path}")
    
    if generate_markdown:
        os.makedirs('docs/team_scenarios', exist_ok=True)
        print("\nGenerating markdown reports (optional)...")
        
        for i, team in enumerate(sorted(teams_info.keys()), 1):
            md_content = generate_markdown_report(team, teams_info, stats, sos_data, games, num_simulations)
            safe_filename = team.replace(' ', '_').replace('/', '_')
            output_path = f'docs/team_scenarios/{safe_filename}.md'
            
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(md_content)
            
            if i % 10 == 0:
                print(f"  [{i}/{len(teams_info)}] Markdown reports...")
    
    print("\n" + "="*80)
    print("GENERATION COMPLETE!")
    print("="*80)
    print(f"\nTeams processed: {len(teams_info)}")
    print(f"Total simulations: {num_simulations:,}")
    print(f"Primary output: output/team_scenarios.json")
    if generate_markdown:
        print(f"Markdown reports: docs/team_scenarios/")
    print()


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Generate consolidated Monte Carlo scenario data for all teams')
    parser.add_argument('-n', '--simulations', type=int, default=DEFAULT_NUM_SIMULATIONS,
                       help=f'Number of simulations (default: {DEFAULT_NUM_SIMULATIONS})')
    parser.add_argument('-s', '--seed', type=int, default=None,
                       help='Random seed for reproducibility')
    parser.add_argument('--markdown', action='store_true',
                       help='Also generate markdown reports (for backward compatibility)')
    
    args = parser.parse_args()
    main(num_simulations=args.simulations, seed=args.seed, generate_markdown=args.markdown)
