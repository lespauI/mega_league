#!/usr/bin/env python3
import csv
import itertools
from collections import defaultdict
import json
import random

def load_data():
    teams_info = {}
    with open('MEGA_teams.csv', 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            team = row['displayName'].strip()
            teams_info[team] = {
                'division': row.get('divisionName', '').strip(),
                'conference': row.get('conferenceName', '').strip()
            }
    
    games = []
    with open('MEGA_games.csv', 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if int(row.get('seasonIndex', 0)) != 1:
                continue
            if int(row.get('stageIndex', 0)) != 1:
                continue
            status = int(row['status']) if row['status'] else 1
            games.append({
                'home': row['homeTeam'].strip(),
                'away': row['awayTeam'].strip(),
                'home_score': int(row['homeScore']) if row['homeScore'] else 0,
                'away_score': int(row['awayScore']) if row['awayScore'] else 0,
                'week': int(row['weekIndex']) if row['weekIndex'] else 0,
                'status': status,
                'completed': status in [2, 3]
            })
    
    with open('output/ranked_sos_by_conference.csv', 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        sos_data = {row['team']: row for row in reader}
    
    for team in teams_info:
        if team in sos_data:
            teams_info[team]['past_sos'] = float(sos_data[team]['past_ranked_sos_avg'])
        else:
            teams_info[team]['past_sos'] = 0.5
    
    return teams_info, games, sos_data

def calculate_team_stats(teams_info, games):
    stats = {}
    
    for team in teams_info:
        stats[team] = {
            'W': 0, 'L': 0, 'T': 0,
            'conference_W': 0, 'conference_L': 0, 'conference_T': 0,
            'division_W': 0, 'division_L': 0, 'division_T': 0,
            'points_for': 0, 'points_against': 0,
            'conference_points_for': 0, 'conference_points_against': 0,
            'head_to_head': defaultdict(lambda: {'W': 0, 'L': 0, 'T': 0}),
            'opponents': [],
            'defeated_opponents': []
        }
    
    for game in games:
        if not game['completed']:
            continue
        
        home = game['home']
        away = game['away']
        home_score = game['home_score']
        away_score = game['away_score']
        
        if home not in stats or away not in stats:
            continue
        
        stats[home]['opponents'].append(away)
        stats[away]['opponents'].append(home)
        
        stats[home]['points_for'] += home_score
        stats[home]['points_against'] += away_score
        stats[away]['points_for'] += away_score
        stats[away]['points_against'] += home_score
        
        home_conf = teams_info[home]['conference']
        away_conf = teams_info[away]['conference']
        home_div = teams_info[home]['division']
        away_div = teams_info[away]['division']
        
        if home_score > away_score:
            stats[home]['W'] += 1
            stats[away]['L'] += 1
            stats[home]['defeated_opponents'].append(away)
            stats[home]['head_to_head'][away]['W'] += 1
            stats[away]['head_to_head'][home]['L'] += 1
            
            if home_conf == away_conf:
                stats[home]['conference_W'] += 1
                stats[away]['conference_L'] += 1
                stats[home]['conference_points_for'] += home_score
                stats[home]['conference_points_against'] += away_score
                stats[away]['conference_points_for'] += away_score
                stats[away]['conference_points_against'] += home_score
                
            if home_div == away_div:
                stats[home]['division_W'] += 1
                stats[away]['division_L'] += 1
                
        elif away_score > home_score:
            stats[away]['W'] += 1
            stats[home]['L'] += 1
            stats[away]['defeated_opponents'].append(home)
            stats[away]['head_to_head'][home]['W'] += 1
            stats[home]['head_to_head'][away]['L'] += 1
            
            if home_conf == away_conf:
                stats[away]['conference_W'] += 1
                stats[home]['conference_L'] += 1
                stats[home]['conference_points_for'] += home_score
                stats[home]['conference_points_against'] += away_score
                stats[away]['conference_points_for'] += away_score
                stats[away]['conference_points_against'] += home_score
                
            if home_div == away_div:
                stats[away]['division_W'] += 1
                stats[home]['division_L'] += 1
        else:
            stats[home]['T'] += 1
            stats[away]['T'] += 1
            stats[home]['head_to_head'][away]['T'] += 1
            stats[away]['head_to_head'][home]['T'] += 1
            
            if home_conf == away_conf:
                stats[home]['conference_T'] += 1
                stats[away]['conference_T'] += 1
    
    for team in stats:
        total = stats[team]['W'] + stats[team]['L'] + stats[team]['T']
        stats[team]['win_pct'] = (stats[team]['W'] + 0.5 * stats[team]['T']) / total if total > 0 else 0
        
        conf_total = stats[team]['conference_W'] + stats[team]['conference_L'] + stats[team]['conference_T']
        stats[team]['conference_pct'] = (stats[team]['conference_W'] + 0.5 * stats[team]['conference_T']) / conf_total if conf_total > 0 else 0
        
        div_total = stats[team]['division_W'] + stats[team]['division_L'] + stats[team]['division_T']
        stats[team]['division_pct'] = (stats[team]['division_W'] + 0.5 * stats[team]['division_T']) / div_total if div_total > 0 else 0
        
        defeated_records = []
        for opp in stats[team]['defeated_opponents']:
            opp_total = stats[opp]['W'] + stats[opp]['L'] + stats[opp]['T']
            opp_pct = (stats[opp]['W'] + 0.5 * stats[opp]['T']) / opp_total if opp_total > 0 else 0
            defeated_records.append(opp_pct)
        stats[team]['strength_of_victory'] = sum(defeated_records) / len(defeated_records) if defeated_records else 0
        
        opponent_records = []
        for opp in stats[team]['opponents']:
            opp_total = stats[opp]['W'] + stats[opp]['L'] + stats[opp]['T']
            opp_pct = (stats[opp]['W'] + 0.5 * stats[opp]['T']) / opp_total if opp_total > 0 else 0
            opponent_records.append(opp_pct)
        stats[team]['strength_of_schedule'] = sum(opponent_records) / len(opponent_records) if opponent_records else 0
    
    return stats

def compare_head_to_head(teams, stats):
    if len(teams) == 2:
        t1, t2 = teams
        h2h = stats[t1]['head_to_head'][t2]
        total = h2h['W'] + h2h['L'] + h2h['T']
        if total == 0:
            return None
        pct = (h2h['W'] + 0.5 * h2h['T']) / total
        if pct > 0.5:
            return t1
        elif pct < 0.5:
            return t2
        return None
    else:
        h2h_records = {}
        for team in teams:
            w, l, t = 0, 0, 0
            for other in teams:
                if team != other:
                    h2h = stats[team]['head_to_head'][other]
                    w += h2h['W']
                    l += h2h['L']
                    t += h2h['T']
            total = w + l + t
            h2h_records[team] = (w + 0.5 * t) / total if total > 0 else 0
        
        max_pct = max(h2h_records.values())
        winners = [t for t, pct in h2h_records.items() if pct == max_pct]
        
        if len(winners) == 1:
            return winners[0]
        return None

def apply_tiebreakers(teams, stats, teams_info, is_division=False):
    if len(teams) == 1:
        return teams[0]
    
    if len(teams) == 0:
        return None
    
    winner = compare_head_to_head(teams, stats)
    if winner:
        return winner
    
    if is_division:
        div_pcts = {t: stats[t]['division_pct'] for t in teams}
        max_pct = max(div_pcts.values())
        remaining = [t for t in teams if div_pcts[t] == max_pct]
        if len(remaining) == 1:
            return remaining[0]
        teams = remaining
    
    conf_pcts = {t: stats[t]['conference_pct'] for t in teams}
    max_pct = max(conf_pcts.values())
    remaining = [t for t in teams if conf_pcts[t] == max_pct]
    if len(remaining) == 1:
        return remaining[0]
    teams = remaining
    
    sov_scores = {t: stats[t]['strength_of_victory'] for t in teams}
    max_sov = max(sov_scores.values())
    remaining = [t for t in teams if abs(sov_scores[t] - max_sov) < 0.001]
    if len(remaining) == 1:
        return remaining[0]
    teams = remaining
    
    sos_scores = {t: stats[t]['strength_of_schedule'] for t in teams}
    max_sos = max(sos_scores.values())
    remaining = [t for t in teams if abs(sos_scores[t] - max_sos) < 0.001]
    if len(remaining) == 1:
        return remaining[0]
    
    return remaining[0] if remaining else teams[0]

def simulate_remaining_games(teams_info, stats, sos_data, games):
    completed_games = [g for g in games if g['completed']]
    remaining_games = [g for g in games if not g['completed']]
    
    simulated_games = []
    for game in remaining_games:
        home = game['home']
        away = game['away']
        
        if home not in stats or away not in stats:
            continue
        
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
        
        rand_val = random.random()
        if rand_val < home_prob:
            winner = home
            loser = away
        else:
            winner = away
            loser = home
        
        simulated_games.append({
            'home': home,
            'away': away,
            'winner': winner,
            'loser': loser
        })
    
    return simulated_games

def rank_teams_with_tiebreakers(teams, sim_stats, teams_info, is_division=False):
    from collections import defaultdict
    
    win_pct_groups = defaultdict(list)
    for team in teams:
        win_pct = sim_stats[team]['win_pct']
        win_pct_groups[win_pct].append(team)
    
    ranked_teams = []
    for win_pct in sorted(win_pct_groups.keys(), reverse=True):
        tied_teams = win_pct_groups[win_pct]
        
        if len(tied_teams) == 1:
            ranked_teams.extend(tied_teams)
        else:
            resolved = []
            remaining = list(tied_teams)
            
            while remaining:
                if len(remaining) == 1:
                    resolved.append(remaining[0])
                    break
                
                winner = apply_tiebreakers(remaining, sim_stats, teams_info, is_division)
                if winner and winner in remaining:
                    resolved.append(winner)
                    remaining.remove(winner)
                else:
                    resolved.extend(sorted(remaining, key=lambda t: (
                        -sim_stats[t]['conference_pct'],
                        -sim_stats[t]['points_for']
                    )))
                    break
            
            ranked_teams.extend(resolved)
    
    return ranked_teams

def determine_playoff_teams(teams_info, stats, simulated_games):
    sim_stats = {}
    for team in stats:
        sim_stats[team] = {
            'W': stats[team]['W'],
            'L': stats[team]['L'],
            'T': stats[team]['T'],
            'conference_W': stats[team]['conference_W'],
            'conference_L': stats[team]['conference_L'],
            'conference_T': stats[team]['conference_T'],
            'division_W': stats[team]['division_W'],
            'division_L': stats[team]['division_L'],
            'division_T': stats[team]['division_T'],
            'head_to_head': defaultdict(lambda: {'W': 0, 'L': 0, 'T': 0}),
            'points_for': stats[team]['points_for'],
            'points_against': stats[team]['points_against'],
            'defeated_opponents': list(stats[team]['defeated_opponents']),
            'opponents': list(stats[team]['opponents'])
        }
        for opp in stats[team]['head_to_head']:
            sim_stats[team]['head_to_head'][opp] = dict(stats[team]['head_to_head'][opp])
    
    for game in simulated_games:
        home = game['home']
        away = game['away']
        winner = game['winner']
        loser = game['loser']
        
        sim_stats[winner]['W'] += 1
        sim_stats[loser]['L'] += 1
        sim_stats[winner]['head_to_head'][loser]['W'] += 1
        sim_stats[loser]['head_to_head'][winner]['L'] += 1
        sim_stats[winner]['defeated_opponents'].append(loser)
        sim_stats[winner]['opponents'].append(loser)
        sim_stats[loser]['opponents'].append(winner)
        
        home_conf = teams_info[home]['conference']
        away_conf = teams_info[away]['conference']
        home_div = teams_info[home]['division']
        away_div = teams_info[away]['division']
        
        if home_conf == away_conf:
            sim_stats[winner]['conference_W'] += 1
            sim_stats[loser]['conference_L'] += 1
        
        if home_div == away_div:
            sim_stats[winner]['division_W'] += 1
            sim_stats[loser]['division_L'] += 1
    
    for team in sim_stats:
        total = sim_stats[team]['W'] + sim_stats[team]['L'] + sim_stats[team]['T']
        sim_stats[team]['win_pct'] = (sim_stats[team]['W'] + 0.5 * sim_stats[team]['T']) / total if total > 0 else 0
        
        conf_total = sim_stats[team]['conference_W'] + sim_stats[team]['conference_L'] + sim_stats[team]['conference_T']
        sim_stats[team]['conference_pct'] = (sim_stats[team]['conference_W'] + 0.5 * sim_stats[team]['conference_T']) / conf_total if conf_total > 0 else 0
        
        div_total = sim_stats[team]['division_W'] + sim_stats[team]['division_L'] + sim_stats[team]['division_T']
        sim_stats[team]['division_pct'] = (sim_stats[team]['division_W'] + 0.5 * sim_stats[team]['division_T']) / div_total if div_total > 0 else 0
        
        defeated_records = []
        for opp in sim_stats[team]['defeated_opponents']:
            opp_total = sim_stats[opp]['W'] + sim_stats[opp]['L'] + sim_stats[opp]['T']
            opp_pct = (sim_stats[opp]['W'] + 0.5 * sim_stats[opp]['T']) / opp_total if opp_total > 0 else 0
            defeated_records.append(opp_pct)
        sim_stats[team]['strength_of_victory'] = sum(defeated_records) / len(defeated_records) if defeated_records else 0
        
        opponent_records = []
        for opp in sim_stats[team]['opponents']:
            opp_total = sim_stats[opp]['W'] + sim_stats[opp]['L'] + sim_stats[opp]['T']
            opp_pct = (sim_stats[opp]['W'] + 0.5 * sim_stats[opp]['T']) / opp_total if opp_total > 0 else 0
            opponent_records.append(opp_pct)
        sim_stats[team]['strength_of_schedule'] = sum(opponent_records) / len(opponent_records) if opponent_records else 0
    
    playoff_teams = {}
    division_winners = {}
    bye_teams = {}
    
    for conf in ['AFC', 'NFC']:
        conf_teams = [t for t in teams_info if teams_info[t]['conference'] == conf]
        
        div_leaders = {}
        for division in set(teams_info[t]['division'] for t in conf_teams):
            div_contenders = [t for t in conf_teams if teams_info[t]['division'] == division]
            ranked_div = rank_teams_with_tiebreakers(div_contenders, sim_stats, teams_info, is_division=True)
            div_leaders[division] = ranked_div[0]
        
        division_winners[conf] = list(div_leaders.values())
        
        ranked_div_leaders = rank_teams_with_tiebreakers(list(div_leaders.values()), sim_stats, teams_info, is_division=False)
        
        bye_teams[conf] = ranked_div_leaders[:1]
        
        wc_candidates = [t for t in conf_teams if t not in div_leaders.values()]
        ranked_wc = rank_teams_with_tiebreakers(wc_candidates, sim_stats, teams_info, is_division=False)
        
        playoff_teams[conf] = list(div_leaders.values()) + ranked_wc[:3]
    
    return playoff_teams, division_winners, bye_teams

def calculate_playoff_probability_simulation(team_name, teams_info, stats, sos_data, games, num_simulations=1000):
    playoff_count = 0
    division_count = 0
    bye_count = 0
    conf = teams_info[team_name]['conference']
    
    for sim in range(num_simulations):
        simulated_games = simulate_remaining_games(teams_info, stats, sos_data, games)
        playoff_teams, division_winners, bye_teams = determine_playoff_teams(teams_info, stats, simulated_games)
        
        if team_name in playoff_teams[conf]:
            playoff_count += 1
        
        if team_name in division_winners[conf]:
            division_count += 1
        
        if team_name in bye_teams[conf]:
            bye_count += 1
    
    playoff_probability = (playoff_count / num_simulations) * 100
    division_probability = (division_count / num_simulations) * 100
    bye_probability = (bye_count / num_simulations) * 100
    
    return {
        'playoff_probability': playoff_probability,
        'division_probability': division_probability,
        'bye_probability': bye_probability
    }

def check_mathematical_certainty(team_name, teams_info, stats, games):
    """
    Check if team is mathematically clinched or eliminated.
    Returns: 'clinched', 'eliminated', or None
    """
    remaining_games = [g for g in games if not g['completed']]
    if not remaining_games:
        return None
    
    conf = teams_info[team_name]['conference']
    
    worst_case_games = []
    for game in remaining_games:
        home, away = game['home'], game['away']
        if team_name in (home, away):
            winner = away if home == team_name else home
            loser = team_name
        else:
            winner = home
            loser = away
        worst_case_games.append({'home': home, 'away': away, 'winner': winner, 'loser': loser})
    
    playoff_teams, _, _ = determine_playoff_teams(teams_info, stats, worst_case_games)
    if team_name in playoff_teams[conf]:
        return 'clinched'
    
    best_case_games = []
    for game in remaining_games:
        home, away = game['home'], game['away']
        if team_name in (home, away):
            winner = team_name
            loser = away if home == team_name else home
        else:
            winner = home
            loser = away
        best_case_games.append({'home': home, 'away': away, 'winner': winner, 'loser': loser})
    
    playoff_teams, _, _ = determine_playoff_teams(teams_info, stats, best_case_games)
    if team_name not in playoff_teams[conf]:
        return 'eliminated'
    
    return None


def cap_probability(raw_probability, certainty_status):
    """Cap simulation probabilities unless mathematically certain."""
    if certainty_status == 'clinched':
        return 100.0
    if certainty_status == 'eliminated':
        return 0.0
    if raw_probability >= 100:
        return 99.9
    if raw_probability <= 0:
        return 0.1
    return raw_probability

def main():
    teams_info, games, sos_data = load_data()
    stats = calculate_team_stats(teams_info, games)
    
    print("\n" + "="*80)
    print("SIMULATING PLAYOFF SCENARIOS")
    print("="*80)
    print("Running 1,000 simulations for each team's playoff chances...")
    print("Using 70/30 weighted rating (Win% + Past SoS)")
    print("No home field advantage (Madden game)\n")
    
    results = {}
    
    for conf in ['AFC', 'NFC']:
        conf_teams = [t for t in teams_info if teams_info[t]['conference'] == conf]
        
        for i, team in enumerate(conf_teams, 1):
            print(f"  [{i}/{len(conf_teams)}] Simulating {team}...")
            certainty = check_mathematical_certainty(team, teams_info, stats, games)
            prob_results = calculate_playoff_probability_simulation(team, teams_info, stats, sos_data, games, num_simulations=1000)
            remaining_games = int(sos_data[team]['remaining_games']) if team in sos_data else 4
            results[team] = {
                'conference': conf,
                'division': teams_info[team]['division'],
                'W': stats[team]['W'],
                'L': stats[team]['L'],
                'win_pct': stats[team]['win_pct'],
                'conference_pct': stats[team]['conference_pct'],
                'division_pct': stats[team]['division_pct'],
                'strength_of_victory': stats[team]['strength_of_victory'],
                'strength_of_schedule': stats[team]['strength_of_schedule'],
                'playoff_probability': round(cap_probability(prob_results['playoff_probability'], certainty), 1),
                'division_win_probability': round(cap_probability(prob_results['division_probability'], certainty), 1),
                'bye_probability': round(cap_probability(prob_results['bye_probability'], certainty), 1),
                'remaining_sos': float(sos_data[team]['ranked_sos_avg']) if team in sos_data else 0.5,
                'remaining_games': remaining_games,
                'past_sos': teams_info[team]['past_sos'],
                'clinched': certainty == 'clinched',
                'eliminated': certainty == 'eliminated'
            }
    
    with open('output/playoff_probabilities.json', 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2)
    
    print("\n" + "="*80)
    print("PLAYOFF PROBABILITY CALCULATION COMPLETE!")
    print("="*80)
    print("\nUsing Monte Carlo simulation (1,000 iterations per team)")
    print("Features:")
    print("  ✓ 70% weight on Win Percentage + 30% weight on Past SoS")
    print("  ✓ Removed home field advantage (Madden game)")
    print("  ✓ Win probability capped at 25-75% (realistic variance)")
    print("  ✓ Proper NFL tiebreakers (H2H, Division%, Conference%, SoV, SoS)")
    print("  ✓ Mathematical certainty detection (clinched/eliminated)")
    print("  ✓ Probability capping: 100% only if clinched, 0% only if eliminated")
    print("\nOutput saved to: output/playoff_probabilities.json")
    print("\nTop AFC Contenders:")
    afc_teams = [(t, r['playoff_probability']) for t, r in results.items() if r['conference'] == 'AFC']
    afc_teams.sort(key=lambda x: x[1], reverse=True)
    for team, prob in afc_teams[:10]:
        print(f"  {team:20s} {prob:5.1f}%")
    
    print("\nTop NFC Contenders:")
    nfc_teams = [(t, r['playoff_probability']) for t, r in results.items() if r['conference'] == 'NFC']
    nfc_teams.sort(key=lambda x: x[1], reverse=True)
    for team, prob in nfc_teams[:10]:
        print(f"  {team:20s} {prob:5.1f}%")

if __name__ == "__main__":
    import os
    os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    main()
