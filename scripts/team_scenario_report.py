#!/usr/bin/env python3
import argparse
import csv
import random
from collections import defaultdict, Counter
import json

from calc_playoff_probabilities import (
    load_data,
    load_rankings_data,
    calculate_team_stats,
    simulate_remaining_games,
    determine_playoff_teams,
    TIE_PROBABILITY
)

DEFAULT_NUM_SIMULATIONS = 10000

def get_remaining_games_for_team(team_name, games):
    remaining = []
    for game in games:
        if not game['completed'] and (game['home'] == team_name or game['away'] == team_name):
            remaining.append(game)
    return remaining

def calculate_game_probabilities(team_name, teams_info, stats, remaining_games):
    game_probs = []
    
    for game in remaining_games:
        home = game['home']
        away = game['away']
        display_week = game['week'] + 1
        
        is_home = (home == team_name)
        opponent = away if is_home else home
        
        home_win_pct = stats[home]['win_pct']
        away_win_pct = stats[away]['win_pct']
        home_past_sos = teams_info[home]['past_sos']
        away_past_sos = teams_info[away]['past_sos']
        
        home_rating = (home_win_pct * 0.7) + (home_past_sos * 0.3)
        away_rating = (away_win_pct * 0.7) + (away_past_sos * 0.3)
        
        if home_rating + away_rating > 0:
            home_prob = home_rating / (home_rating + away_rating)
        else:
            home_prob = 0.5
        
        home_prob = max(0.25, min(0.75, home_prob))
        
        team_win_prob = home_prob if is_home else (1 - home_prob)
        team_win_prob = team_win_prob * (1 - TIE_PROBABILITY)
        tie_prob = TIE_PROBABILITY
        team_loss_prob = (1 - team_win_prob - tie_prob)
        
        game_probs.append({
            'week': display_week,
            'opponent': opponent,
            'is_home': is_home,
            'win_prob': team_win_prob * 100,
            'tie_prob': tie_prob * 100,
            'loss_prob': team_loss_prob * 100
        })
    
    return game_probs

def run_team_scenarios(team_name, teams_info, stats, sos_data, games, rankings, num_simulations=10000):
    conf = teams_info[team_name]['conference']
    
    scenario_outcomes = []
    final_records = Counter()
    playoff_by_record = defaultdict(int)
    division_by_record = defaultdict(int)
    bye_by_record = defaultdict(int)
    
    remaining_for_team = get_remaining_games_for_team(team_name, games)
    
    for sim in range(num_simulations):
        simulated_games = simulate_remaining_games(teams_info, stats, sos_data, games, rankings)
        playoff_teams, division_winners, bye_teams = determine_playoff_teams(teams_info, stats, simulated_games)
        
        team_results = {
            'W': stats[team_name]['W'],
            'L': stats[team_name]['L'],
            'T': stats[team_name]['T']
        }
        
        game_outcomes = []
        for game in simulated_games:
            if game['home'] == team_name or game['away'] == team_name:
                is_home = (game['home'] == team_name)
                opponent = game['away'] if is_home else game['home']
                
                if game.get('is_tie', False):
                    outcome = 'T'
                    team_results['T'] += 1
                elif game.get('winner') == team_name:
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
        final_records[record_key] += 1
        
        made_playoffs = team_name in playoff_teams[conf]
        won_division = team_name in division_winners[conf]
        got_bye = team_name in bye_teams[conf]
        
        if made_playoffs:
            playoff_by_record[record_key] += 1
        if won_division:
            division_by_record[record_key] += 1
        if got_bye:
            bye_by_record[record_key] += 1
        
        scenario_outcomes.append({
            'record': record_key,
            'W': team_results['W'],
            'L': team_results['L'],
            'T': team_results['T'],
            'game_outcomes': game_outcomes,
            'made_playoffs': made_playoffs,
            'won_division': won_division,
            'got_bye': got_bye
        })
    
    return {
        'scenarios': scenario_outcomes,
        'final_records': final_records,
        'playoff_by_record': playoff_by_record,
        'division_by_record': division_by_record,
        'bye_by_record': bye_by_record,
        'num_simulations': num_simulations
    }

def format_prob(value, include_emoji=False):
    if value >= 60:
        emoji = "🟢 " if include_emoji else ""
        return f"{emoji}<span class='prob-high'>{value:.1f}%</span>"
    elif value < 40:
        emoji = "🔴 " if include_emoji else ""
        return f"{emoji}<span class='prob-low'>{value:.1f}%</span>"
    else:
        emoji = "🟡 " if include_emoji else ""
        return f"{emoji}<span class='prob-medium'>{value:.1f}%</span>"

def generate_markdown_report(team_name, teams_info, stats, sos_data, games, rankings, num_simulations=10000):
    conf = teams_info[team_name]['conference']
    div = teams_info[team_name]['division']
    current_record = f"{stats[team_name]['W']}-{stats[team_name]['L']}-{stats[team_name]['T']}"
    
    remaining_games = get_remaining_games_for_team(team_name, games)
    game_probs = calculate_game_probabilities(team_name, teams_info, stats, remaining_games)
    
    results = run_team_scenarios(team_name, teams_info, stats, sos_data, games, rankings, num_simulations)
    
    sorted_by_frequency = sorted(results['final_records'].items(), key=lambda x: -x[1])
    most_likely_record, most_likely_count = sorted_by_frequency[0]
    most_likely_pct = (most_likely_count / num_simulations) * 100
    
    sorted_records = sorted(results['final_records'].items(), 
                           key=lambda x: (-int(x[0].split('-')[0]), int(x[0].split('-')[1])))
    
    md = []
    md.append(f"# 🏈 Monte Carlo Scenario Report: {team_name}\n")
    md.append(f"**📍 Conference:** {conf}  ")
    md.append(f"**🏆 Division:** {div}  ")
    md.append(f"**📊 Current Record:** {current_record}  ")
    md.append(f"**📈 Win %:** {stats[team_name]['win_pct']:.3f}  ")
    md.append(f"**🎲 Simulations:** {num_simulations:,}\n")
    
    md.append("---\n")
    md.append("## 📅 Remaining Games & Win Probabilities\n")
    
    if not remaining_games:
        md.append("*✅ No remaining games - season complete!*\n")
    else:
        md.append("| Week | Opponent | Location | Win % | Tie % | Loss % |")
        md.append("|------|----------|----------|-------|-------|--------|")
        for gp in game_probs:
            location = "🏠 HOME" if gp['is_home'] else "✈️ AWAY"
            win_formatted = format_prob(gp['win_prob'])
            tie_formatted = f"<span class='prob-tie'>{gp['tie_prob']:.1f}%</span>"
            loss_formatted = format_prob(100 - gp['win_prob'] - gp['tie_prob'])
            md.append(f"| {gp['week']} | {gp['opponent']} | {location} | {win_formatted} | {tie_formatted} | {loss_formatted} |")
        md.append("")
    
    md.append("---\n")
    md.append("## 🎯 Most Probable Outcome\n")
    md.append(f"**📌 Final Record:** {most_likely_record}  ")
    md.append(f"**🎲 Probability:** {format_prob(most_likely_pct, True)} ({most_likely_count:,}/{num_simulations:,} simulations)\n")
    
    matching_scenarios = [s for s in results['scenarios'] if s['record'] == most_likely_record]
    if matching_scenarios and matching_scenarios[0]['game_outcomes']:
        md.append("### 🎬 Example of how this happens:\n")
        for go in matching_scenarios[0]['game_outcomes']:
            location = "vs" if go['is_home'] else "@"
            if go['outcome'] == 'W':
                outcome_symbol = "✅"
                outcome_text = "WIN"
            elif go['outcome'] == 'T':
                outcome_symbol = "🟡"
                outcome_text = "TIE"
            else:
                outcome_symbol = "❌"
                outcome_text = "LOSS"
            md.append(f"- {outcome_symbol} {location} {go['opponent']} **({outcome_text})**")
        md.append("")
    
    playoff_count = results['playoff_by_record'][most_likely_record]
    division_count = results['division_by_record'][most_likely_record]
    bye_count = results['bye_by_record'][most_likely_record]
    
    playoff_pct_for_record = (playoff_count / most_likely_count * 100) if most_likely_count > 0 else 0
    division_pct_for_record = (division_count / most_likely_count * 100) if most_likely_count > 0 else 0
    bye_pct_for_record = (bye_count / most_likely_count * 100) if most_likely_count > 0 else 0
    
    md.append(f"**🎲 With this {most_likely_record} record:**")
    md.append(f"- 🏆 Make Playoffs: {format_prob(playoff_pct_for_record, True)}")
    md.append(f"- 👑 Win Division: {format_prob(division_pct_for_record, True)}")
    md.append(f"- 🎫 Earn Bye: {format_prob(bye_pct_for_record, True)}\n")
    
    md.append("---\n")
    md.append("## 📊 Overall Probabilities\n")
    
    total_playoff = sum(results['playoff_by_record'].values())
    total_division = sum(results['division_by_record'].values())
    total_bye = sum(results['bye_by_record'].values())
    
    playoff_prob = (total_playoff / num_simulations) * 100
    division_prob = (total_division / num_simulations) * 100
    bye_prob = (total_bye / num_simulations) * 100
    
    md.append(f"- **🏆 Make Playoffs:** {format_prob(playoff_prob, True)} ({total_playoff:,}/{num_simulations:,} simulations)")
    md.append(f"- **👑 Win Division:** {format_prob(division_prob, True)} ({total_division:,}/{num_simulations:,} simulations)")
    md.append(f"- **🎫 Earn Bye:** {format_prob(bye_prob, True)} ({total_bye:,}/{num_simulations:,} simulations)\n")
    
    md.append("---\n")
    md.append("## 📋 All Scenario Outcomes\n")
    md.append("| Final Record | Frequency | % | Playoff % | Division % | Bye % |")
    md.append("|--------------|-----------|---|-----------|------------|-------|")
    
    for record, count in sorted_records:
        freq_pct = (count / num_simulations) * 100
        playoff_pct = (results['playoff_by_record'][record] / count * 100) if count > 0 else 0
        division_pct = (results['division_by_record'][record] / count * 100) if count > 0 else 0
        bye_pct = (results['bye_by_record'][record] / count * 100) if count > 0 else 0
        
        freq_formatted = format_prob(freq_pct) if freq_pct >= 5 else f"<span class='prob-verylow'>{freq_pct:.2f}%</span>"
        md.append(f"| {record} | {count:,} | {freq_formatted} | {format_prob(playoff_pct)} | {format_prob(division_pct)} | {format_prob(bye_pct)} |")
    
    md.append("")
    md.append("---\n")
    md.append("## 🔥 Top 5 Most Common Scenarios\n")
    
    top_scenarios = sorted_records[:5]
    
    for i, (record, count) in enumerate(top_scenarios, 1):
        freq_pct = (count / num_simulations) * 100
        emoji_rank = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣"][i-1]
        md.append(f"### {emoji_rank} #{i}: {record} ({count:,} times, {format_prob(freq_pct, True)})\n")
        
        matching_scenarios = [s for s in results['scenarios'] if s['record'] == record]
        if matching_scenarios:
            example = matching_scenarios[0]
            
            if example['game_outcomes']:
                md.append("**🎬 Example game outcomes:**")
                for go in example['game_outcomes']:
                    location = "vs" if go['is_home'] else "@"
                    if go['outcome'] == 'W':
                        outcome_symbol = "✅"
                    elif go['outcome'] == 'T':
                        outcome_symbol = "🟡"
                    else:
                        outcome_symbol = "❌"
                    md.append(f"- {outcome_symbol} {location} {go['opponent']}")
                md.append("")
            
            playoff_count = results['playoff_by_record'][record]
            playoff_pct_for_record = (playoff_count / count * 100) if count > 0 else 0
            md.append(f"**🏆 Playoff chances with this record:** {format_prob(playoff_pct_for_record, True)}\n")
    
    return "\n".join(md)

def print_team_report(team_name, teams_info, stats, sos_data, games, rankings, num_simulations=10000):
    print("\n" + "="*80)
    print(f"MONTE CARLO SCENARIO REPORT: {team_name}")
    print("="*80)
    
    conf = teams_info[team_name]['conference']
    div = teams_info[team_name]['division']
    current_record = f"{stats[team_name]['W']}-{stats[team_name]['L']}-{stats[team_name]['T']}"
    
    print(f"\nConference: {conf}")
    print(f"Division: {div}")
    print(f"Current Record: {current_record}")
    print(f"Win %: {stats[team_name]['win_pct']:.3f}")
    print(f"\nRunning {num_simulations:,} simulations...\n")
    
    remaining_games = get_remaining_games_for_team(team_name, games)
    game_probs = calculate_game_probabilities(team_name, teams_info, stats, remaining_games)
    
    print("-" * 80)
    print("REMAINING GAMES & WIN PROBABILITIES")
    print("-" * 80)
    
    if not remaining_games:
        print("No remaining games - season complete!")
    else:
        print(f"\n{'Week':<6} {'Opponent':<25} {'Location':<10} {'Win %':<8} {'Tie %':<8} {'Loss %':<8}")
        print("-" * 80)
        for gp in game_probs:
            location = "HOME" if gp['is_home'] else "AWAY"
            print(f"{gp['week']:<6} {gp['opponent']:<25} {location:<10} {gp['win_prob']:>6.1f}% {gp['tie_prob']:>6.1f}% {gp['loss_prob']:>6.1f}%")
    
    print("\n" + "-" * 80)
    print("RUNNING SIMULATIONS...")
    print("-" * 80)
    
    results = run_team_scenarios(team_name, teams_info, stats, sos_data, games, rankings, num_simulations)
    
    sorted_by_frequency = sorted(results['final_records'].items(), key=lambda x: -x[1])
    most_likely_record, most_likely_count = sorted_by_frequency[0]
    most_likely_pct = (most_likely_count / num_simulations) * 100
    
    sorted_records = sorted(results['final_records'].items(), 
                           key=lambda x: (-int(x[0].split('-')[0]), int(x[0].split('-')[1])))
    
    print("\n" + "="*80)
    print("MOST PROBABLE OUTCOME")
    print("="*80)
    
    print(f"\nFinal Record: {most_likely_record}")
    print(f"Probability: {most_likely_pct:.2f}% ({most_likely_count:,}/{num_simulations:,} simulations)")
    
    matching_scenarios = [s for s in results['scenarios'] if s['record'] == most_likely_record]
    if matching_scenarios and matching_scenarios[0]['game_outcomes']:
        print(f"\nExample of how this happens:")
        for go in matching_scenarios[0]['game_outcomes']:
            location = "vs" if go['is_home'] else "@"
            outcome_symbol = "✓" if go['outcome'] == 'W' else ("○" if go['outcome'] == 'T' else "✗")
            outcome_text = "WIN" if go['outcome'] == 'W' else ("TIE" if go['outcome'] == 'T' else "LOSS")
            print(f"   {outcome_symbol} {location} {go['opponent']:<25} ({outcome_text})")
    
    playoff_count = results['playoff_by_record'][most_likely_record]
    division_count = results['division_by_record'][most_likely_record]
    bye_count = results['bye_by_record'][most_likely_record]
    
    playoff_pct_for_record = (playoff_count / most_likely_count * 100) if most_likely_count > 0 else 0
    division_pct_for_record = (division_count / most_likely_count * 100) if most_likely_count > 0 else 0
    bye_pct_for_record = (bye_count / most_likely_count * 100) if most_likely_count > 0 else 0
    
    print(f"\nWith this {most_likely_record} record:")
    print(f"   Make Playoffs: {playoff_pct_for_record:>6.1f}%")
    print(f"   Win Division:  {division_pct_for_record:>6.1f}%")
    print(f"   Earn Bye:      {bye_pct_for_record:>6.1f}%")
    
    print("\n" + "="*80)
    print("SCENARIO OUTCOMES")
    print("="*80)
    
    print(f"\n{'Final Record':<15} {'Frequency':<12} {'%':<8} {'Playoff %':<12} {'Division %':<12} {'Bye %':<12}")
    print("-" * 80)
    
    for record, count in sorted_records:
        freq_pct = (count / num_simulations) * 100
        playoff_pct = (results['playoff_by_record'][record] / count * 100) if count > 0 else 0
        division_pct = (results['division_by_record'][record] / count * 100) if count > 0 else 0
        bye_pct = (results['bye_by_record'][record] / count * 100) if count > 0 else 0
        
        print(f"{record:<15} {count:>6,} {freq_pct:>10.2f}% {playoff_pct:>10.1f}% {division_pct:>10.1f}% {bye_pct:>10.1f}%")
    
    print("\n" + "="*80)
    print("OVERALL PROBABILITIES")
    print("="*80)
    
    total_playoff = sum(results['playoff_by_record'].values())
    total_division = sum(results['division_by_record'].values())
    total_bye = sum(results['bye_by_record'].values())
    
    playoff_prob = (total_playoff / num_simulations) * 100
    division_prob = (total_division / num_simulations) * 100
    bye_prob = (total_bye / num_simulations) * 100
    
    print(f"\nMake Playoffs:  {playoff_prob:>6.2f}%  ({total_playoff:,}/{num_simulations:,} simulations)")
    print(f"Win Division:   {division_prob:>6.2f}%  ({total_division:,}/{num_simulations:,} simulations)")
    print(f"Earn Bye:       {bye_prob:>6.2f}%  ({total_bye:,}/{num_simulations:,} simulations)")
    
    print("\n" + "="*80)
    print("MOST COMMON SCENARIOS")
    print("="*80)
    
    top_scenarios = sorted_records[:5]
    
    for i, (record, count) in enumerate(top_scenarios, 1):
        freq_pct = (count / num_simulations) * 100
        print(f"\n#{i}: {record} ({count:,} times, {freq_pct:.2f}%)")
        
        matching_scenarios = [s for s in results['scenarios'] if s['record'] == record]
        if matching_scenarios:
            example = matching_scenarios[0]
            
            if example['game_outcomes']:
                print(f"   Example game outcomes:")
                for go in example['game_outcomes']:
                    location = "vs" if go['is_home'] else "@"
                    outcome_symbol = "✓" if go['outcome'] == 'W' else ("○" if go['outcome'] == 'T' else "✗")
                    print(f"      {outcome_symbol} {location} {go['opponent']}")
            
            playoff_count = results['playoff_by_record'][record]
            playoff_pct_for_record = (playoff_count / count * 100) if count > 0 else 0
            print(f"   Playoff chances with this record: {playoff_pct_for_record:.1f}%")
    
    print("\n" + "="*80)
    print("END OF REPORT")
    print("="*80 + "\n")

def main():
    parser = argparse.ArgumentParser(
        description='Generate detailed Monte Carlo scenario report for a specific team',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s "Jaguars"
  %(prog)s "Kansas City Chiefs" --simulations 50000
  %(prog)s "Bengals" -n 20000
        """
    )
    parser.add_argument('team', type=str, help='Team name (e.g., "Jaguars", "Kansas City Chiefs")')
    parser.add_argument('-n', '--simulations', type=int, default=DEFAULT_NUM_SIMULATIONS,
                       help=f'Number of simulations (default: {DEFAULT_NUM_SIMULATIONS})')
    parser.add_argument('-s', '--seed', type=int, default=None,
                       help='Random seed for reproducibility')
    
    args = parser.parse_args()
    
    if args.seed is not None:
        random.seed(args.seed)
    
    import os
    os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    teams_info, games, sos_data = load_data()
    stats = calculate_team_stats(teams_info, games)
    rankings = load_rankings_data()
    
    team_name = args.team.strip()
    
    if team_name not in teams_info:
        print(f"\nError: Team '{team_name}' not found!")
        print("\nAvailable teams:")
        for conf in ['AFC', 'NFC']:
            conf_teams = sorted([t for t in teams_info if teams_info[t]['conference'] == conf])
            print(f"\n{conf}:")
            for team in conf_teams:
                print(f"  - {team}")
        return
    
    print_team_report(team_name, teams_info, stats, sos_data, games, rankings, num_simulations=args.simulations)

if __name__ == "__main__":
    main()
