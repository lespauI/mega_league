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
        
        if home_win_pct + away_win_pct > 0:
            base_home_prob = home_win_pct / (home_win_pct + away_win_pct)
        else:
            base_home_prob = 0.5
        
        home_advantage = 0.07
        home_prob = base_home_prob + home_advantage
        
        home_prob = max(0.20, min(0.80, home_prob))
        
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
            'points_against': stats[team]['points_against']
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
    
    playoff_teams = {}
    division_winners = {}
    bye_teams = {}
    
    for conf in ['AFC', 'NFC']:
        conf_teams = [t for t in teams_info if teams_info[t]['conference'] == conf]
        
        div_leaders = {}
        for division in set(teams_info[t]['division'] for t in conf_teams):
            div_contenders = [t for t in conf_teams if teams_info[t]['division'] == division]
            div_contenders.sort(key=lambda t: (
                -sim_stats[t]['win_pct'],
                -sim_stats[t]['division_pct'],
                -sim_stats[t]['conference_pct'],
                -sim_stats[t]['points_for']
            ))
            div_leaders[division] = div_contenders[0]
        
        division_winners[conf] = list(div_leaders.values())
        
        sorted_div_leaders = sorted(div_leaders.values(), key=lambda t: (
            -sim_stats[t]['win_pct'],
            -sim_stats[t]['conference_pct'],
            -sim_stats[t]['points_for']
        ))
        
        bye_teams[conf] = sorted_div_leaders[:1]
        
        wc_candidates = [t for t in conf_teams if t not in div_leaders.values()]
        wc_candidates.sort(key=lambda t: (
            -sim_stats[t]['win_pct'],
            -sim_stats[t]['conference_pct'],
            -sim_stats[t]['points_for']
        ))
        
        playoff_teams[conf] = list(div_leaders.values()) + wc_candidates[:3]
    
    return playoff_teams, division_winners, bye_teams

def calculate_playoff_probability_simulation(team_name, teams_info, stats, sos_data, games, num_simulations=10000):
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

def calculate_playoff_probability(team_name, teams_info, stats, sos_data, remaining_games):
    conf = teams_info[team_name]['conference']
    div = teams_info[team_name]['division']
    
    conf_teams = [t for t in teams_info if teams_info[t]['conference'] == conf]
    div_teams = [t for t in conf_teams if teams_info[t]['division'] == div]
    
    div_leaders = {}
    for division in set(teams_info[t]['division'] for t in conf_teams):
        div_contenders = [t for t in conf_teams if teams_info[t]['division'] == division]
        div_contenders.sort(key=lambda t: (-stats[t]['win_pct'], -stats[t]['conference_pct'], -stats[t]['strength_of_schedule']))
        div_leaders[division] = div_contenders[0]
    
    is_div_leader = (div_leaders[div] == team_name)
    
    current_wins = stats[team_name]['W']
    current_losses = stats[team_name]['L']
    current_ties = stats[team_name]['T']
    win_pct = stats[team_name]['win_pct']
    
    team_remaining = int(sos_data[team_name]['remaining_games']) if team_name in sos_data else remaining_games
    team_sos = float(sos_data[team_name]['ranked_sos_avg']) if team_name in sos_data else 0.5
    
    expected_wins = team_remaining * (1.0 - team_sos)
    projected_wins = current_wins + expected_wins
    max_possible_wins = current_wins + team_remaining
    min_possible_wins = current_wins
    
    if is_div_leader:
        can_clinch = True
        max_threat = 0
        
        for rival in div_teams:
            if rival == team_name:
                continue
            
            rival_remaining = int(sos_data[rival]['remaining_games']) if rival in sos_data else remaining_games
            rival_max_wins = stats[rival]['W'] + rival_remaining
            rival_max_pct = (rival_max_wins + 0.5 * stats[rival]['T']) / (stats[rival]['W'] + stats[rival]['L'] + stats[rival]['T'] + rival_remaining)
            
            if rival_max_wins > min_possible_wins or (rival_max_wins == min_possible_wins and rival_max_pct >= win_pct):
                can_clinch = False
                max_threat = max(max_threat, rival_max_wins)
        
        if can_clinch:
            return 100.0
        
        base_prob = 70.0
        
        lead_size = min_possible_wins - max_threat
        
        if lead_size >= 2:
            base_prob = 95.0
        elif lead_size >= 1:
            base_prob = 85.0
        elif lead_size >= 0:
            base_prob = 70.0
        else:
            base_prob = 55.0
        
        div_contenders = sorted(
            [t for t in div_teams if t != team_name],
            key=lambda t: -stats[t]['win_pct']
        )
        
        if div_contenders:
            closest_rival = div_contenders[0]
            rival_wins = stats[closest_rival]['W']
            rival_remaining = int(sos_data[closest_rival]['remaining_games']) if closest_rival in sos_data else remaining_games
            rival_sos = float(sos_data[closest_rival]['ranked_sos_avg']) if closest_rival in sos_data else 0.5
            rival_projected_wins = rival_wins + rival_remaining * (1.0 - rival_sos)
            
            win_diff = projected_wins - rival_projected_wins
            
            if win_diff >= 2.0:
                base_prob = min(98.0, base_prob + 15)
            elif win_diff >= 1.0:
                base_prob = min(95.0, base_prob + 10)
            elif win_diff >= 0.5:
                base_prob = min(90.0, base_prob + 5)
            elif win_diff >= 0:
                base_prob = max(60.0, base_prob - 5)
            elif win_diff >= -0.5:
                base_prob = max(50.0, base_prob - 10)
            else:
                base_prob = max(40.0, base_prob - 20)
            
            h2h_record = stats[team_name]['head_to_head'][closest_rival]
            h2h_total = h2h_record['W'] + h2h_record['L'] + h2h_record['T']
            if h2h_total > 0:
                h2h_pct = (h2h_record['W'] + 0.5 * h2h_record['T']) / h2h_total
                if h2h_pct > 0.6:
                    base_prob = min(98.0, base_prob + 5)
                elif h2h_pct < 0.4:
                    base_prob = max(35.0, base_prob - 5)
        
        games_remaining_factor = (team_remaining / 17.0) * 10
        base_prob = base_prob - games_remaining_factor + 5
        
        return min(99.0, max(30.0, base_prob))
    
    else:
        div_leader = div_leaders[div]
        leader_wins = stats[div_leader]['W']
        leader_remaining = int(sos_data[div_leader]['remaining_games']) if div_leader in sos_data else remaining_games
        leader_max_wins = leader_wins + leader_remaining
        
        can_win_division = (max_possible_wins > leader_wins)
        
        if not can_win_division and leader_remaining > 0:
            leader_min_wins = leader_wins
            can_win_division = (max_possible_wins >= leader_min_wins)
        
        all_conf_teams_info = []
        for t in conf_teams:
            t_remaining = int(sos_data[t]['remaining_games']) if t in sos_data else remaining_games
            t_sos = float(sos_data[t]['remaining_sos']) if t in sos_data and 'remaining_sos' in sos_data[t] else 0.5
            t_projected = stats[t]['W'] + t_remaining * (1.0 - t_sos)
            
            all_conf_teams_info.append({
                'team': t,
                'wins': stats[t]['W'],
                'losses': stats[t]['L'],
                'ties': stats[t]['T'],
                'win_pct': stats[t]['win_pct'],
                'remaining': t_remaining,
                'max_wins': stats[t]['W'] + t_remaining,
                'min_wins': stats[t]['W'],
                'projected_wins': t_projected,
                'is_div_leader': t in div_leaders.values()
            })
        
        all_conf_teams_info.sort(key=lambda x: (-x['win_pct'], -stats[x['team']]['conference_pct']))
        
        wc_candidates = [t for t in all_conf_teams_info if not t['is_div_leader']]
        
        teams_clearly_better = 0
        for candidate in wc_candidates:
            if candidate['team'] == team_name:
                continue
            if candidate['min_wins'] > max_possible_wins:
                teams_clearly_better += 1
        
        if teams_clearly_better >= 3:
            if not can_win_division:
                return 0.0
        
        teams_that_can_beat_us = 0
        for candidate in wc_candidates:
            if candidate['team'] == team_name:
                continue
            if candidate['max_wins'] > min_possible_wins:
                teams_that_can_beat_us += 1
        
        if teams_that_can_beat_us <= 2 and can_win_division:
            return 100.0
        
        wc_candidates_sorted = sorted(wc_candidates, key=lambda x: -x['projected_wins'])
        
        try:
            our_wc_position = next(i for i, c in enumerate(wc_candidates_sorted) if c['team'] == team_name)
        except StopIteration:
            our_wc_position = len(wc_candidates_sorted) - 1
        
        if our_wc_position == 0:
            base_wc_prob = 80.0
        elif our_wc_position == 1:
            base_wc_prob = 70.0
        elif our_wc_position == 2:
            base_wc_prob = 60.0
        elif our_wc_position == 3:
            base_wc_prob = 45.0
        elif our_wc_position == 4:
            base_wc_prob = 30.0
        elif our_wc_position == 5:
            base_wc_prob = 18.0
        elif our_wc_position == 6:
            base_wc_prob = 10.0
        else:
            base_wc_prob = max(1.0, 10.0 - (our_wc_position - 6) * 2)
        
        if our_wc_position < len(wc_candidates_sorted) - 1:
            next_team = wc_candidates_sorted[our_wc_position + 1]
            proj_diff = projected_wins - next_team['projected_wins']
            if proj_diff > 1.5:
                base_wc_prob = min(95.0, base_wc_prob + 15)
            elif proj_diff > 0.5:
                base_wc_prob = min(90.0, base_wc_prob + 8)
        
        if our_wc_position > 0 and our_wc_position < 3:
            prev_team = wc_candidates_sorted[our_wc_position - 1]
            proj_diff = prev_team['projected_wins'] - projected_wins
            if proj_diff > 1.5:
                base_wc_prob = max(5.0, base_wc_prob - 15)
            elif proj_diff > 0.5:
                base_wc_prob = max(10.0, base_wc_prob - 8)
        
        div_prob = 0.0
        if can_win_division:
            win_diff_from_leader = projected_wins - (leader_wins + leader_remaining * (1.0 - float(sos_data[div_leader]['ranked_sos_avg']) if div_leader in sos_data else 0.5))
            
            if win_diff_from_leader >= 1.0:
                div_prob = 25.0
            elif win_diff_from_leader >= 0.5:
                div_prob = 15.0
            elif win_diff_from_leader >= 0:
                div_prob = 8.0
            elif win_diff_from_leader >= -0.5:
                div_prob = 4.0
            else:
                div_prob = 1.0
        
        combined_prob = base_wc_prob + div_prob * (1.0 - base_wc_prob / 100.0)
        
        conf_record_boost = (stats[team_name]['conference_pct'] - 0.5) * 10
        combined_prob += conf_record_boost
        
        return min(98.0, max(0.5, combined_prob))

def main():
    teams_info, games, sos_data = load_data()
    stats = calculate_team_stats(teams_info, games)
    
    print("\n" + "="*80)
    print("SIMULATING PLAYOFF SCENARIOS...")
    print("="*80)
    print("Running 1,000 simulations for each team's playoff chances...\n")
    
    results = {}
    
    for conf in ['AFC', 'NFC']:
        conf_teams = [t for t in teams_info if teams_info[t]['conference'] == conf]
        
        for i, team in enumerate(conf_teams, 1):
            print(f"  [{i}/{len(conf_teams)}] Simulating {team}...")
            prob_results = calculate_playoff_probability_simulation(team, teams_info, stats, sos_data, games, num_simulations=1000)
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
                'playoff_probability': round(prob_results['playoff_probability'], 1),
                'division_win_probability': round(prob_results['division_probability'], 1),
                'bye_probability': round(prob_results['bye_probability'], 1),
                'remaining_sos': float(sos_data[team]['ranked_sos_avg']) if team in sos_data else 0.5,
                'remaining_games': int(sos_data[team]['remaining_games']) if team in sos_data else 4
            }
    
    with open('output/playoff_probabilities.json', 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2)
    
    print("\n" + "="*80)
    print("PLAYOFF PROBABILITY CALCULATION COMPLETE!")
    print("="*80)
    print("\nUsing Monte Carlo simulation (1,000 iterations per team)")
    print("Calculated probabilities for all 32 teams considering:")
    print("  ✓ Current standings and records")
    print("  ✓ Remaining game outcomes (simulated)")
    print("  ✓ Division tiebreakers")
    print("  ✓ Conference tiebreakers")
    print("  ✓ Head-to-head records")
    print("  ✓ Team strength (win percentage)")
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
