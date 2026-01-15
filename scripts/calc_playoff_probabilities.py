#!/usr/bin/env python3
import argparse
import csv
import itertools
from collections import defaultdict
import json
import random

DEFAULT_NUM_SIMULATIONS = 10000
TIE_PROBABILITY = 0.003  # ~0.3% of NFL games end in ties

HOME_FIELD_ADVANTAGE = 0.02
WIN_STREAK_THRESHOLD = 3
WIN_STREAK_BONUS = 0.03
DIVISIONAL_REGRESSION = 0.15
ELO_WEIGHT = 0.50
WIN_PCT_WEIGHT = 0.25
SOS_WEIGHT = 0.15
SOV_WEIGHT = 0.10
DEFAULT_ELO = 1200.0


def load_elo_data():
    """Load team ELO ratings from mega_elo.csv."""
    elo_map = {}
    with open('mega_elo.csv', 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            team = row.get('Team', '').strip()
            elo_str = row.get('Week 14+', '')
            if team and elo_str:
                try:
                    elo_map[team] = float(elo_str)
                except ValueError:
                    continue
    return elo_map


def load_rankings_data():
    rankings = {}
    max_week = {}
    with open('MEGA_rankings.csv', 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if int(row.get('seasonIndex', 0)) != 1:
                continue
            team = row['team'].strip()
            week = int(row.get('weekIndex', 0))
            rank = int(row.get('rank', 16))
            if team not in max_week or week > max_week[team]:
                max_week[team] = week
                rankings[team] = rank
    return rankings


def get_streak_modifier(streak):
    if streak >= WIN_STREAK_THRESHOLD:
        return WIN_STREAK_BONUS
    elif streak <= -WIN_STREAK_THRESHOLD:
        return -WIN_STREAK_BONUS
    return 0.0


def calculate_sov_rating(defeated_opponents, rankings):
    if not defeated_opponents:
        return 0.5
    ranks = []
    for opp in defeated_opponents:
        if opp in rankings:
            ranks.append(rankings[opp])
        else:
            ranks.append(16)
    avg_rank = sum(ranks) / len(ranks)
    return 1.0 - (avg_rank - 1) / 31


def is_divisional_game(home, away, teams_info):
    home_div = teams_info.get(home, {}).get('division', '')
    away_div = teams_info.get(away, {}).get('division', '')
    return home_div == away_div and home_div != ''


def load_data():
    teams_info = {}
    with open('MEGA_teams.csv', 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            team = row['displayName'].strip()
            streak_val = row.get('winLossStreak', '0')
            try:
                streak = int(streak_val)
                if streak > 127:
                    streak = streak - 256
            except (ValueError, TypeError):
                streak = 0
            teams_info[team] = {
                'division': row.get('divisionName', '').strip(),
                'conference': row.get('conferenceName', '').strip(),
                'win_streak': streak
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
                'completed': status in [2, 3, 4]
            })
    
    with open('output/ranked_sos_by_conference.csv', 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        sos_data = {row['team']: row for row in reader}
    
    for team in teams_info:
        if team in sos_data:
            teams_info[team]['past_sos'] = float(sos_data[team]['past_ranked_sos_avg'])
        else:
            teams_info[team]['past_sos'] = 0.5
    
    elo_data = load_elo_data()
    for team in teams_info:
        teams_info[team]['elo'] = elo_data.get(team, DEFAULT_ELO)
    
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
    
    return random.choice(remaining) if remaining else random.choice(teams)

def simulate_remaining_games(teams_info, stats, sos_data, games, rankings):
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
        
        home_elo = teams_info[home].get('elo', DEFAULT_ELO)
        away_elo = teams_info[away].get('elo', DEFAULT_ELO)
        home_elo_norm = max(0, min(1, (home_elo - 1000) / 400))
        away_elo_norm = max(0, min(1, (away_elo - 1000) / 400))
        
        home_sov = calculate_sov_rating(stats[home]['defeated_opponents'], rankings)
        away_sov = calculate_sov_rating(stats[away]['defeated_opponents'], rankings)
        
        home_rating = (
            home_elo_norm * ELO_WEIGHT +
            home_win_pct * WIN_PCT_WEIGHT +
            home_past_sos * SOS_WEIGHT +
            home_sov * SOV_WEIGHT
        )
        away_rating = (
            away_elo_norm * ELO_WEIGHT +
            away_win_pct * WIN_PCT_WEIGHT +
            away_past_sos * SOS_WEIGHT +
            away_sov * SOV_WEIGHT
        )
        
        if home_rating + away_rating > 0:
            home_prob = home_rating / (home_rating + away_rating)
        else:
            home_prob = 0.5
        
        home_prob += HOME_FIELD_ADVANTAGE
        
        home_streak = teams_info[home].get('win_streak', 0)
        away_streak = teams_info[away].get('win_streak', 0)
        home_prob += get_streak_modifier(home_streak)
        home_prob -= get_streak_modifier(away_streak)
        
        if is_divisional_game(home, away, teams_info):
            home_prob = home_prob + (0.5 - home_prob) * DIVISIONAL_REGRESSION
        
        home_prob = max(0.25, min(0.75, home_prob))
        
        rand_val = random.random()
        if rand_val < TIE_PROBABILITY:
            tie_score = random.randint(10, 27)
            simulated_games.append({
                'home': home,
                'away': away,
                'is_tie': True,
                'home_score': tie_score,
                'away_score': tie_score
            })
        elif rand_val < TIE_PROBABILITY + home_prob * (1 - TIE_PROBABILITY):
            winner = home
            loser = away
            winner_score = random.randint(17, 35)
            loser_score = random.randint(7, winner_score - 1)
            simulated_games.append({
                'home': home,
                'away': away,
                'is_tie': False,
                'winner': winner,
                'loser': loser,
                'winner_score': winner_score,
                'loser_score': loser_score
            })
        else:
            winner = away
            loser = home
            winner_score = random.randint(17, 35)
            loser_score = random.randint(7, winner_score - 1)
            simulated_games.append({
                'home': home,
                'away': away,
                'is_tie': False,
                'winner': winner,
                'loser': loser,
                'winner_score': winner_score,
                'loser_score': loser_score
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
            'conference_points_for': stats[team]['conference_points_for'],
            'conference_points_against': stats[team]['conference_points_against'],
            'defeated_opponents': list(stats[team]['defeated_opponents']),
            'opponents': list(stats[team]['opponents'])
        }
        for opp in stats[team]['head_to_head']:
            sim_stats[team]['head_to_head'][opp] = dict(stats[team]['head_to_head'][opp])
    
    for game in simulated_games:
        home = game['home']
        away = game['away']
        
        home_conf = teams_info[home]['conference']
        away_conf = teams_info[away]['conference']
        home_div = teams_info[home]['division']
        away_div = teams_info[away]['division']
        
        if game.get('is_tie', False):
            sim_stats[home]['T'] += 1
            sim_stats[away]['T'] += 1
            sim_stats[home]['head_to_head'][away]['T'] += 1
            sim_stats[away]['head_to_head'][home]['T'] += 1
            sim_stats[home]['opponents'].append(away)
            sim_stats[away]['opponents'].append(home)
            
            if home_conf == away_conf:
                sim_stats[home]['conference_T'] += 1
                sim_stats[away]['conference_T'] += 1
                tie_score = game.get('home_score', 0)
                sim_stats[home]['conference_points_for'] += tie_score
                sim_stats[home]['conference_points_against'] += tie_score
                sim_stats[away]['conference_points_for'] += tie_score
                sim_stats[away]['conference_points_against'] += tie_score
            
            if home_div == away_div:
                sim_stats[home]['division_T'] += 1
                sim_stats[away]['division_T'] += 1
        else:
            winner = game['winner']
            loser = game['loser']
            
            sim_stats[winner]['W'] += 1
            sim_stats[loser]['L'] += 1
            sim_stats[winner]['head_to_head'][loser]['W'] += 1
            sim_stats[loser]['head_to_head'][winner]['L'] += 1
            sim_stats[winner]['defeated_opponents'].append(loser)
            sim_stats[winner]['opponents'].append(loser)
            sim_stats[loser]['opponents'].append(winner)
            
            if home_conf == away_conf:
                sim_stats[winner]['conference_W'] += 1
                sim_stats[loser]['conference_L'] += 1
                winner_score = game.get('winner_score', 0)
                loser_score = game.get('loser_score', 0)
                sim_stats[winner]['conference_points_for'] += winner_score
                sim_stats[winner]['conference_points_against'] += loser_score
                sim_stats[loser]['conference_points_for'] += loser_score
                sim_stats[loser]['conference_points_against'] += winner_score
            
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

def calculate_playoff_probability_simulation(team_name, teams_info, stats, sos_data, games, rankings, num_simulations=1000):
    playoff_count = 0
    division_count = 0
    bye_count = 0
    conf = teams_info[team_name]['conference']
    
    for sim in range(num_simulations):
        simulated_games = simulate_remaining_games(teams_info, stats, sos_data, games, rankings)
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
    
    Uses conference-aware logic for games not involving target team:
    - Worst-case: Same-conference rivals win their games
    - Best-case: Same-conference rivals lose their games
    
    Special handling when team has 0 games remaining:
    - If other teams could finish with same record, don't mark as certain
    - This allows Monte Carlo to properly handle tiebreaker probabilities
    """
    remaining_games = [g for g in games if not g['completed']]
    conf = teams_info[team_name]['conference']
    
    team_remaining_games = [g for g in remaining_games if team_name in (g['home'], g['away'])]
    
    if not team_remaining_games and remaining_games:
        team_record = stats[team_name]['W'] + 0.5 * stats[team_name]['T']
        
        for other_team, other_stats in stats.items():
            if other_team == team_name:
                continue
            if teams_info.get(other_team, {}).get('conference') != conf:
                continue
            
            other_remaining = [g for g in remaining_games if other_team in (g['home'], g['away'])]
            if not other_remaining:
                continue
            
            other_current = other_stats['W'] + 0.5 * other_stats['T']
            other_max = other_current + len(other_remaining)
            other_min = other_current
            
            if abs(other_max - team_record) < 0.01 or abs(other_min - team_record) < 0.01:
                return None
            if other_min < team_record < other_max:
                return None
    
    if not remaining_games:
        return None
    
    worst_case_games = []
    for game in remaining_games:
        home, away = game['home'], game['away']
        if team_name in (home, away):
            winner = away if home == team_name else home
            loser = team_name
        else:
            home_conf = teams_info.get(home, {}).get('conference', '')
            away_conf = teams_info.get(away, {}).get('conference', '')
            home_is_rival = (home_conf == conf)
            away_is_rival = (away_conf == conf)
            if home_is_rival and not away_is_rival:
                winner, loser = home, away
            elif away_is_rival and not home_is_rival:
                winner, loser = away, home
            elif home_is_rival and away_is_rival:
                home_wins = stats.get(home, {}).get('W', 0)
                away_wins = stats.get(away, {}).get('W', 0)
                if home_wins >= away_wins:
                    winner, loser = home, away
                else:
                    winner, loser = away, home
            else:
                winner, loser = home, away
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
            home_conf = teams_info.get(home, {}).get('conference', '')
            away_conf = teams_info.get(away, {}).get('conference', '')
            home_is_rival = (home_conf == conf)
            away_is_rival = (away_conf == conf)
            if home_is_rival and not away_is_rival:
                winner, loser = away, home
            elif away_is_rival and not home_is_rival:
                winner, loser = home, away
            elif home_is_rival and away_is_rival:
                home_wins = stats.get(home, {}).get('W', 0)
                away_wins = stats.get(away, {}).get('W', 0)
                if home_wins >= away_wins:
                    winner, loser = away, home
                else:
                    winner, loser = home, away
            else:
                winner, loser = home, away
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


def cap_simulation_probability(raw_probability):
    """Cap simulation probabilities without certainty check (for division/bye).
    
    Since mathematical certainty for division/bye is complex to calculate,
    we simply prevent false 100%/0% from simulations.
    """
    if raw_probability >= 100:
        return 99.9
    if raw_probability <= 0:
        return 0.1
    return raw_probability

def main(num_simulations=DEFAULT_NUM_SIMULATIONS):
    teams_info, games, sos_data = load_data()
    stats = calculate_team_stats(teams_info, games)
    rankings = load_rankings_data()
    
    print("\n" + "="*80)
    print("SIMULATING PLAYOFF SCENARIOS")
    print("="*80)
    print(f"Running {num_simulations:,} simulations for each team's playoff chances...")
    print("Enhanced model: 50% ELO + 25% Win% + 15% SoS + 10% SoV + streak bonus")
    print(f"Home field advantage: +{HOME_FIELD_ADVANTAGE*100:.0f}%")
    print(f"Win streak bonus (>={WIN_STREAK_THRESHOLD}): +{WIN_STREAK_BONUS*100:.0f}%")
    print(f"Divisional regression: {DIVISIONAL_REGRESSION*100:.0f}% toward 50-50\n")
    
    results = {}
    
    for conf in ['AFC', 'NFC']:
        conf_teams = [t for t in teams_info if teams_info[t]['conference'] == conf]
        
        for i, team in enumerate(conf_teams, 1):
            print(f"  [{i}/{len(conf_teams)}] Simulating {team}...")
            certainty = check_mathematical_certainty(team, teams_info, stats, games)
            prob_results = calculate_playoff_probability_simulation(team, teams_info, stats, sos_data, games, rankings, num_simulations=num_simulations)
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
                'elo': teams_info[team]['elo'],
                'playoff_probability': round(cap_probability(prob_results['playoff_probability'], certainty), 1),
                'division_win_probability': round(cap_simulation_probability(prob_results['division_probability']), 1),
                'bye_probability': round(cap_simulation_probability(prob_results['bye_probability']), 1),
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
    print(f"\nUsing Monte Carlo simulation ({num_simulations:,} iterations per team)")
    print("Features:")
    print("  ✓ Enhanced rating: 50% ELO + 25% Win% + 15% SoS + 10% SoV")
    print(f"  ✓ Home field advantage: +{HOME_FIELD_ADVANTAGE*100:.0f}% (slight Madden boost)")
    print(f"  ✓ Win streak bonus (>={WIN_STREAK_THRESHOLD} wins): +{WIN_STREAK_BONUS*100:.0f}%")
    print(f"  ✓ Divisional games: {DIVISIONAL_REGRESSION*100:.0f}% regression toward 50-50")
    print("  ✓ ELO ratings for true team skill (from mega_elo.csv)")
    print("  ✓ Strength of victories from opponent power rankings")
    print("  ✓ Win probability capped at 25-75% (realistic variance)")
    print("  ✓ Proper NFL tiebreakers (H2H, Division%, Conference%, SoV, SoS)")
    print("  ✓ Mathematical certainty detection (clinched/eliminated)")
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
    
    parser = argparse.ArgumentParser(description='Calculate NFL playoff probabilities using Monte Carlo simulation')
    parser.add_argument('-n', '--num-simulations', type=int, default=DEFAULT_NUM_SIMULATIONS,
                        help=f'Number of simulations to run (default: {DEFAULT_NUM_SIMULATIONS})')
    parser.add_argument('-s', '--seed', type=int, default=None,
                        help='Random seed for reproducible results (default: None)')
    args = parser.parse_args()
    
    if args.seed is not None:
        random.seed(args.seed)
        print(f"Using random seed: {args.seed}")
    
    main(num_simulations=args.num_simulations)
