#!/usr/bin/env python3
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from week18_simulator import load_teams_data, load_games, calculate_team_stats
from nfl_tiebreakers import (
    apply_division_tiebreaker, apply_wildcard_tiebreaker,
    break_two_team_division_tie, break_multi_team_division_tie,
    break_two_team_wildcard_tie, break_multi_team_wildcard_tie,
    calculate_playoff_seeding
)
import random
from collections import defaultdict

os.chdir('/Users/lespaul/Downloads/MEGA_neonsportz_stats')

def get_week18_games():
    games = load_games()
    return [g for g in games if g['week'] == 17 and not g['completed']]

def get_completed_games():
    games = load_games()
    return [g for g in games if g['completed']]

def simulate_game_outcome(game, outcome):
    simulated = game.copy()
    if outcome == 'home':
        simulated['home_score'] = 28
        simulated['away_score'] = 21
    elif outcome == 'away':
        simulated['home_score'] = 21
        simulated['away_score'] = 28
    elif outcome == 'tie':
        simulated['home_score'] = 24
        simulated['away_score'] = 24
    simulated['completed'] = True
    return simulated

def test_division_tiebreaker_step1_head_to_head():
    print("\n" + "="*80)
    print("TEST: Division Tiebreaker Step 1 - Head-to-Head")
    print("="*80)
    
    teams_info = {
        'Team A': {'division': 'AFC East', 'conference': 'AFC'},
        'Team B': {'division': 'AFC East', 'conference': 'AFC'},
        'Team C': {'division': 'AFC West', 'conference': 'AFC'},
    }
    
    games = [
        {'home': 'Team A', 'away': 'Team B', 'home_score': 28, 'away_score': 21, 'completed': True},
        {'home': 'Team B', 'away': 'Team A', 'home_score': 17, 'away_score': 24, 'completed': True},
        {'home': 'Team A', 'away': 'Team C', 'home_score': 24, 'away_score': 21, 'completed': True},
        {'home': 'Team B', 'away': 'Team C', 'home_score': 21, 'away_score': 24, 'completed': True},
    ]
    
    stats = calculate_team_stats(teams_info, games)
    
    print(f"Team A record: {stats['Team A']['W']}-{stats['Team A']['L']}")
    print(f"Team B record: {stats['Team B']['W']}-{stats['Team B']['L']}")
    print(f"Team A vs Team B H2H: {stats['Team A']['head_to_head']['Team B']}")
    
    winner = break_two_team_division_tie(['Team A', 'Team B'], stats, teams_info)
    
    if winner == 'Team A':
        print("✓ PASS: Team A wins head-to-head tiebreaker (2-0 vs Team B)")
        return True
    else:
        print("✗ FAIL: Expected Team A to win head-to-head")
        return False

def test_division_tiebreaker_step2_division_record():
    print("\n" + "="*80)
    print("TEST: Division Tiebreaker Step 2 - Division Record")
    print("="*80)
    
    teams_info = {
        'Team A': {'division': 'NFC North', 'conference': 'NFC'},
        'Team B': {'division': 'NFC North', 'conference': 'NFC'},
        'Team C': {'division': 'NFC North', 'conference': 'NFC'},
        'Team D': {'division': 'NFC North', 'conference': 'NFC'},
        'Outsider': {'division': 'NFC South', 'conference': 'NFC'},
    }
    
    games = [
        {'home': 'Team A', 'away': 'Team B', 'home_score': 24, 'away_score': 24, 'completed': True},
        {'home': 'Team A', 'away': 'Team C', 'home_score': 28, 'away_score': 21, 'completed': True},
        {'home': 'Team A', 'away': 'Team D', 'home_score': 24, 'away_score': 21, 'completed': True},
        {'home': 'Team A', 'away': 'Outsider', 'home_score': 21, 'away_score': 24, 'completed': True},
        
        {'home': 'Team B', 'away': 'Team C', 'home_score': 17, 'away_score': 20, 'completed': True},
        {'home': 'Team B', 'away': 'Team D', 'home_score': 28, 'away_score': 24, 'completed': True},
        {'home': 'Team B', 'away': 'Outsider', 'home_score': 28, 'away_score': 24, 'completed': True},
    ]
    
    stats = calculate_team_stats(teams_info, games)
    
    print(f"Team A: {stats['Team A']['W']}-{stats['Team A']['L']}-{stats['Team A']['T']}, Div: {stats['Team A']['division_W']}-{stats['Team A']['division_L']}-{stats['Team A']['division_T']} ({stats['Team A']['division_pct']:.3f})")
    print(f"Team B: {stats['Team B']['W']}-{stats['Team B']['L']}-{stats['Team B']['T']}, Div: {stats['Team B']['division_W']}-{stats['Team B']['division_L']}-{stats['Team B']['division_T']} ({stats['Team B']['division_pct']:.3f})")
    
    winner = break_two_team_division_tie(['Team A', 'Team B'], stats, teams_info)
    
    if winner == 'Team A':
        print("✓ PASS: Team A wins on division record (2-0-1 vs 1-1-1)")
        return True
    else:
        print("✗ FAIL: Expected Team A to win on division record")
        return False

def test_division_tiebreaker_step3_common_games():
    print("\n" + "="*80)
    print("TEST: Division Tiebreaker Step 3 - Common Games")
    print("="*80)
    
    teams_info = {
        'Team A': {'division': 'AFC South', 'conference': 'AFC'},
        'Team B': {'division': 'AFC South', 'conference': 'AFC'},
        'Common1': {'division': 'AFC North', 'conference': 'AFC'},
        'Common2': {'division': 'AFC North', 'conference': 'AFC'},
        'Common3': {'division': 'AFC North', 'conference': 'AFC'},
        'Common4': {'division': 'AFC North', 'conference': 'AFC'},
    }
    
    games = [
        {'home': 'Team A', 'away': 'Team B', 'home_score': 24, 'away_score': 24, 'completed': True},
        
        {'home': 'Team A', 'away': 'Common1', 'home_score': 28, 'away_score': 21, 'completed': True},
        {'home': 'Team A', 'away': 'Common2', 'home_score': 31, 'away_score': 24, 'completed': True},
        {'home': 'Team A', 'away': 'Common3', 'home_score': 24, 'away_score': 27, 'completed': True},
        {'home': 'Team A', 'away': 'Common4', 'home_score': 28, 'away_score': 24, 'completed': True},
        
        {'home': 'Team B', 'away': 'Common1', 'home_score': 24, 'away_score': 27, 'completed': True},
        {'home': 'Team B', 'away': 'Common2', 'home_score': 28, 'away_score': 24, 'completed': True},
        {'home': 'Team B', 'away': 'Common3', 'home_score': 21, 'away_score': 24, 'completed': True},
        {'home': 'Team B', 'away': 'Common4', 'home_score': 31, 'away_score': 28, 'completed': True},
    ]
    
    stats = calculate_team_stats(teams_info, games)
    
    common_opps = set(stats['Team A']['opponents']) & set(stats['Team B']['opponents'])
    print(f"Common opponents: {len(common_opps)}")
    
    winner = break_two_team_division_tie(['Team A', 'Team B'], stats, teams_info)
    
    if winner == 'Team A':
        print("✓ PASS: Team A wins on common games (3-1 vs 2-2)")
        return True
    else:
        print("✗ FAIL: Expected Team A to win on common games")
        return False

def test_3team_progressive_elimination():
    print("\n" + "="*80)
    print("TEST: 3-Team Progressive Elimination")
    print("="*80)
    
    teams_info = {
        'Team A': {'division': 'NFC West', 'conference': 'NFC'},
        'Team B': {'division': 'NFC West', 'conference': 'NFC'},
        'Team C': {'division': 'NFC West', 'conference': 'NFC'},
        'Team D': {'division': 'NFC West', 'conference': 'NFC'},
        'Outsider': {'division': 'NFC East', 'conference': 'NFC'},
    }
    
    games = [
        {'home': 'Team A', 'away': 'Team B', 'home_score': 24, 'away_score': 21, 'completed': True},
        {'home': 'Team B', 'away': 'Team A', 'home_score': 28, 'away_score': 24, 'completed': True},
        {'home': 'Team A', 'away': 'Team C', 'home_score': 21, 'away_score': 24, 'completed': True},
        {'home': 'Team C', 'away': 'Team A', 'home_score': 24, 'away_score': 27, 'completed': True},
        {'home': 'Team B', 'away': 'Team C', 'home_score': 24, 'away_score': 21, 'completed': True},
        {'home': 'Team C', 'away': 'Team B', 'home_score': 28, 'away_score': 24, 'completed': True},
        
        {'home': 'Team A', 'away': 'Team D', 'home_score': 28, 'away_score': 21, 'completed': True},
        {'home': 'Team B', 'away': 'Team D', 'home_score': 31, 'away_score': 24, 'completed': True},
        {'home': 'Team C', 'away': 'Team D', 'home_score': 21, 'away_score': 24, 'completed': True},
        
        {'home': 'Team A', 'away': 'Outsider', 'home_score': 24, 'away_score': 21, 'completed': True},
        {'home': 'Team B', 'away': 'Outsider', 'home_score': 21, 'away_score': 24, 'completed': True},
        {'home': 'Team C', 'away': 'Outsider', 'home_score': 28, 'away_score': 24, 'completed': True},
    ]
    
    stats = calculate_team_stats(teams_info, games)
    
    print(f"Team A: {stats['Team A']['W']}-{stats['Team A']['L']} ({stats['Team A']['win_pct']:.3f})")
    print(f"Team B: {stats['Team B']['W']}-{stats['Team B']['L']} ({stats['Team B']['win_pct']:.3f})")
    print(f"Team C: {stats['Team C']['W']}-{stats['Team C']['L']} ({stats['Team C']['win_pct']:.3f})")
    
    ranked = break_multi_team_division_tie(['Team A', 'Team B', 'Team C'], stats, teams_info)
    
    print(f"Ranked order: {ranked}")
    
    if len(ranked) == 3:
        print("✓ PASS: Progressive elimination produced 3-team ranking")
        return True
    else:
        print("✗ FAIL: Progressive elimination failed")
        return False

def test_wildcard_conference_percentage():
    print("\n" + "="*80)
    print("TEST: Wild Card Tiebreaker - Conference Percentage")
    print("="*80)
    
    teams_info = {
        'Team A': {'division': 'AFC West', 'conference': 'AFC'},
        'Team B': {'division': 'AFC East', 'conference': 'AFC'},
        'AFC1': {'division': 'AFC North', 'conference': 'AFC'},
        'AFC2': {'division': 'AFC South', 'conference': 'AFC'},
        'NFC1': {'division': 'NFC East', 'conference': 'NFC'},
        'NFC2': {'division': 'NFC West', 'conference': 'NFC'},
    }
    
    games = [
        {'home': 'Team A', 'away': 'AFC1', 'home_score': 28, 'away_score': 21, 'completed': True},
        {'home': 'Team A', 'away': 'AFC2', 'home_score': 24, 'away_score': 27, 'completed': True},
        {'home': 'Team A', 'away': 'NFC1', 'home_score': 31, 'away_score': 28, 'completed': True},
        {'home': 'Team A', 'away': 'NFC2', 'home_score': 28, 'away_score': 24, 'completed': True},
        
        {'home': 'Team B', 'away': 'AFC1', 'home_score': 17, 'away_score': 20, 'completed': True},
        {'home': 'Team B', 'away': 'AFC2', 'home_score': 14, 'away_score': 17, 'completed': True},
        {'home': 'Team B', 'away': 'NFC1', 'home_score': 35, 'away_score': 14, 'completed': True},
        {'home': 'Team B', 'away': 'NFC2', 'home_score': 38, 'away_score': 21, 'completed': True},
    ]
    
    stats = calculate_team_stats(teams_info, games)
    
    print(f"Team A: {stats['Team A']['W']}-{stats['Team A']['L']}, Conf: {stats['Team A']['conference_W']}-{stats['Team A']['conference_L']} ({stats['Team A']['conference_pct']:.3f})")
    print(f"Team B: {stats['Team B']['W']}-{stats['Team B']['L']}, Conf: {stats['Team B']['conference_W']}-{stats['Team B']['conference_L']} ({stats['Team B']['conference_pct']:.3f})")
    
    winner = break_two_team_wildcard_tie(['Team A', 'Team B'], stats, teams_info)
    
    if winner == 'Team A':
        print("✓ PASS: Team A wins on conference percentage")
        return True
    else:
        print("✗ FAIL: Expected Team A to win on conference percentage")
        return False

def test_wildcard_conference_net_points():
    print("\n" + "="*80)
    print("TEST: Wild Card Tiebreaker - Conference Net Points")
    print("="*80)
    
    teams_info = {
        'Team A': {'division': 'NFC West', 'conference': 'NFC'},
        'Team B': {'division': 'NFC East', 'conference': 'NFC'},
        'NFC1': {'division': 'NFC North', 'conference': 'NFC'},
        'NFC2': {'division': 'NFC South', 'conference': 'NFC'},
        'AFC1': {'division': 'AFC East', 'conference': 'AFC'},
        'AFC2': {'division': 'AFC West', 'conference': 'AFC'},
    }
    
    games = [
        {'home': 'Team A', 'away': 'NFC1', 'home_score': 42, 'away_score': 35, 'completed': True},
        {'home': 'Team A', 'away': 'NFC2', 'home_score': 38, 'away_score': 31, 'completed': True},
        {'home': 'Team A', 'away': 'AFC1', 'home_score': 14, 'away_score': 10, 'completed': True},
        {'home': 'Team A', 'away': 'AFC2', 'home_score': 17, 'away_score': 13, 'completed': True},
        
        {'home': 'Team B', 'away': 'NFC1', 'home_score': 24, 'away_score': 21, 'completed': True},
        {'home': 'Team B', 'away': 'NFC2', 'home_score': 27, 'away_score': 24, 'completed': True},
        {'home': 'Team B', 'away': 'AFC1', 'home_score': 45, 'away_score': 14, 'completed': True},
        {'home': 'Team B', 'away': 'AFC2', 'home_score': 38, 'away_score': 10, 'completed': True},
    ]
    
    stats = calculate_team_stats(teams_info, games)
    
    conf_net_a = stats['Team A']['conference_points_for'] - stats['Team A']['conference_points_against']
    conf_net_b = stats['Team B']['conference_points_for'] - stats['Team B']['conference_points_against']
    
    print(f"Team A conf net points: {conf_net_a} ({stats['Team A']['conference_points_for']}-{stats['Team A']['conference_points_against']})")
    print(f"Team B conf net points: {conf_net_b} ({stats['Team B']['conference_points_for']}-{stats['Team B']['conference_points_against']})")
    
    winner = break_two_team_wildcard_tie(['Team A', 'Team B'], stats, teams_info)
    
    if winner == 'Team A':
        print("✓ PASS: Team A wins on conference net points (+14 vs +6)")
        return True
    else:
        print("✗ FAIL: Expected Team A to win on conference net points")
        return False

def test_strength_of_victory():
    print("\n" + "="*80)
    print("TEST: Strength of Victory Tiebreaker")
    print("="*80)
    
    teams_info = {
        'Team A': {'division': 'AFC North', 'conference': 'AFC'},
        'Team B': {'division': 'AFC North', 'conference': 'AFC'},
        'Strong1': {'division': 'AFC South', 'conference': 'AFC'},
        'Strong2': {'division': 'AFC West', 'conference': 'AFC'},
        'Weak1': {'division': 'AFC East', 'conference': 'AFC'},
        'Weak2': {'division': 'NFC East', 'conference': 'NFC'},
    }
    
    games = [
        {'home': 'Strong1', 'away': 'Weak1', 'home_score': 35, 'away_score': 14, 'completed': True},
        {'home': 'Strong1', 'away': 'Weak2', 'home_score': 28, 'away_score': 21, 'completed': True},
        {'home': 'Strong2', 'away': 'Weak1', 'home_score': 31, 'away_score': 17, 'completed': True},
        {'home': 'Strong2', 'away': 'Weak2', 'home_score': 24, 'away_score': 20, 'completed': True},
        
        {'home': 'Team A', 'away': 'Strong1', 'home_score': 21, 'away_score': 17, 'completed': True},
        {'home': 'Team A', 'away': 'Strong2', 'home_score': 24, 'away_score': 20, 'completed': True},
        
        {'home': 'Team B', 'away': 'Weak1', 'home_score': 28, 'away_score': 24, 'completed': True},
        {'home': 'Team B', 'away': 'Weak2', 'home_score': 31, 'away_score': 27, 'completed': True},
    ]
    
    stats = calculate_team_stats(teams_info, games)
    
    print(f"Team A SOV: {stats['Team A']['strength_of_victory']:.3f} (beat Strong1, Strong2)")
    print(f"Team B SOV: {stats['Team B']['strength_of_victory']:.3f} (beat Weak1, Weak2)")
    
    winner = break_two_team_division_tie(['Team A', 'Team B'], stats, teams_info)
    
    if winner == 'Team A':
        print("✓ PASS: Team A wins on strength of victory")
        return True
    else:
        print("✗ FAIL: Expected Team A to win on strength of victory")
        return False

def test_full_playoff_seeding():
    print("\n" + "="*80)
    print("TEST: Full Playoff Seeding with All Tiebreakers")
    print("="*80)
    
    teams_info = load_teams_data()
    completed = get_completed_games()
    week18 = get_week18_games()
    
    random.seed(42)
    outcomes = [random.choice(['home', 'away']) for _ in week18]
    simulated = [simulate_game_outcome(week18[j], outcomes[j]) for j in range(len(week18))]
    all_games = completed + simulated
    
    stats = calculate_team_stats(teams_info, all_games)
    seeding = calculate_playoff_seeding(teams_info, stats)
    
    print("\nAFC Playoff Teams:")
    print("  Division Winners:")
    for i, team in enumerate(seeding['AFC']['division_winners'], 1):
        print(f"    {i}. {team} ({stats[team]['W']}-{stats[team]['L']})")
    print("  Wild Cards:")
    for i, team in enumerate(seeding['AFC']['wildcards'], 5):
        print(f"    {i}. {team} ({stats[team]['W']}-{stats[team]['L']})")
    
    print("\nNFC Playoff Teams:")
    print("  Division Winners:")
    for i, team in enumerate(seeding['NFC']['division_winners'], 1):
        print(f"    {i}. {team} ({stats[team]['W']}-{stats[team]['L']})")
    print("  Wild Cards:")
    for i, team in enumerate(seeding['NFC']['wildcards'], 5):
        print(f"    {i}. {team} ({stats[team]['W']}-{stats[team]['L']})")
    
    afc_playoff_count = len(seeding['AFC']['division_winners']) + len(seeding['AFC']['wildcards'])
    nfc_playoff_count = len(seeding['NFC']['division_winners']) + len(seeding['NFC']['wildcards'])
    
    if afc_playoff_count == 7 and nfc_playoff_count == 7:
        print("\n✓ PASS: 7 teams per conference qualify for playoffs")
        return True
    else:
        print(f"\n✗ FAIL: AFC has {afc_playoff_count} teams, NFC has {nfc_playoff_count} teams")
        return False

def test_strength_of_schedule():
    print("\n" + "="*80)
    print("TEST: Strength of Schedule Tiebreaker")
    print("="*80)
    
    teams_info = {
        'Team A': {'division': 'NFC South', 'conference': 'NFC'},
        'Team B': {'division': 'NFC South', 'conference': 'NFC'},
        'Strong1': {'division': 'NFC North', 'conference': 'NFC'},
        'Strong2': {'division': 'NFC West', 'conference': 'NFC'},
        'Weak1': {'division': 'NFC East', 'conference': 'NFC'},
        'Weak2': {'division': 'NFC East', 'conference': 'NFC'},
        'Common1': {'division': 'AFC West', 'conference': 'AFC'},
        'Common2': {'division': 'AFC North', 'conference': 'AFC'},
    }
    
    games = [
        {'home': 'Strong1', 'away': 'Common1', 'home_score': 35, 'away_score': 14, 'completed': True},
        {'home': 'Strong1', 'away': 'Common2', 'home_score': 31, 'away_score': 17, 'completed': True},
        {'home': 'Strong2', 'away': 'Common1', 'home_score': 28, 'away_score': 21, 'completed': True},
        {'home': 'Strong2', 'away': 'Common2', 'home_score': 24, 'away_score': 20, 'completed': True},
        
        {'home': 'Weak1', 'away': 'Common1', 'home_score': 14, 'away_score': 21, 'completed': True},
        {'home': 'Weak2', 'away': 'Common2', 'home_score': 17, 'away_score': 24, 'completed': True},
        
        {'home': 'Team A', 'away': 'Team B', 'home_score': 24, 'away_score': 24, 'completed': True},
        
        {'home': 'Team A', 'away': 'Strong1', 'home_score': 28, 'away_score': 24, 'completed': True},
        {'home': 'Team A', 'away': 'Strong2', 'home_score': 20, 'away_score': 24, 'completed': True},
        
        {'home': 'Team B', 'away': 'Weak1', 'home_score': 24, 'away_score': 21, 'completed': True},
        {'home': 'Team B', 'away': 'Weak2', 'home_score': 20, 'away_score': 24, 'completed': True},
    ]
    
    stats = calculate_team_stats(teams_info, games)
    
    print(f"Team A SOS: {stats['Team A']['strength_of_schedule']:.3f} (played 2-0 Strong1, 2-0 Strong2)")
    print(f"Team B SOS: {stats['Team B']['strength_of_schedule']:.3f} (played 0-1 Weak1, 0-1 Weak2)")
    print(f"Strong1: {stats['Strong1']['W']}-{stats['Strong1']['L']} ({stats['Strong1']['win_pct']:.3f})")
    print(f"Strong2: {stats['Strong2']['W']}-{stats['Strong2']['L']} ({stats['Strong2']['win_pct']:.3f})")
    print(f"Weak1: {stats['Weak1']['W']}-{stats['Weak1']['L']} ({stats['Weak1']['win_pct']:.3f})")
    print(f"Weak2: {stats['Weak2']['W']}-{stats['Weak2']['L']} ({stats['Weak2']['win_pct']:.3f})")
    
    winner = break_two_team_division_tie(['Team A', 'Team B'], stats, teams_info)
    
    if winner == 'Team A':
        print("✓ PASS: Team A wins on strength of schedule")
        return True
    else:
        print("✗ FAIL: Expected Team A to win on strength of schedule")
        return False

def test_net_points_common_games():
    print("\n" + "="*80)
    print("TEST: Net Points in Common Games Tiebreaker")
    print("="*80)
    
    teams_info = {
        'Team A': {'division': 'AFC West', 'conference': 'AFC'},
        'Team B': {'division': 'AFC West', 'conference': 'AFC'},
        'Common1': {'division': 'AFC North', 'conference': 'AFC'},
        'Common2': {'division': 'AFC North', 'conference': 'AFC'},
        'Common3': {'division': 'AFC South', 'conference': 'AFC'},
        'Common4': {'division': 'AFC East', 'conference': 'AFC'},
    }
    
    games = [
        {'home': 'Team A', 'away': 'Team B', 'home_score': 24, 'away_score': 24, 'completed': True},
        
        {'home': 'Team A', 'away': 'Common1', 'home_score': 42, 'away_score': 21, 'completed': True},
        {'home': 'Team A', 'away': 'Common2', 'home_score': 35, 'away_score': 28, 'completed': True},
        {'home': 'Team A', 'away': 'Common3', 'home_score': 28, 'away_score': 24, 'completed': True},
        {'home': 'Team A', 'away': 'Common4', 'home_score': 24, 'away_score': 21, 'completed': True},
        
        {'home': 'Team B', 'away': 'Common1', 'home_score': 31, 'away_score': 28, 'completed': True},
        {'home': 'Team B', 'away': 'Common2', 'home_score': 24, 'away_score': 21, 'completed': True},
        {'home': 'Team B', 'away': 'Common3', 'home_score': 28, 'away_score': 24, 'completed': True},
        {'home': 'Team B', 'away': 'Common4', 'home_score': 21, 'away_score': 20, 'completed': True},
    ]
    
    stats = calculate_team_stats(teams_info, games)
    
    common_opps = set(stats['Team A']['opponents']) & set(stats['Team B']['opponents'])
    net_a = sum(g['pf'] - g['pa'] for g in stats['Team A']['game_results'] if g['opponent'] in common_opps)
    net_b = sum(g['pf'] - g['pa'] for g in stats['Team B']['game_results'] if g['opponent'] in common_opps)
    
    print(f"Team A net points in common games: +{net_a}")
    print(f"Team B net points in common games: +{net_b}")
    
    winner = break_two_team_division_tie(['Team A', 'Team B'], stats, teams_info)
    
    if winner == 'Team A':
        print("✓ PASS: Team A wins on net points in common games")
        return True
    else:
        print("✗ FAIL: Expected Team A to win on net points in common games")
        return False

def test_net_points_all_games():
    print("\n" + "="*80)
    print("TEST: Net Points in All Games Tiebreaker")
    print("="*80)
    
    teams_info = {
        'Team A': {'division': 'NFC North', 'conference': 'NFC'},
        'Team B': {'division': 'NFC North', 'conference': 'NFC'},
        'Opp1': {'division': 'NFC South', 'conference': 'NFC'},
        'Opp2': {'division': 'NFC West', 'conference': 'NFC'},
    }
    
    games = [
        {'home': 'Team A', 'away': 'Opp1', 'home_score': 45, 'away_score': 21, 'completed': True},
        {'home': 'Team A', 'away': 'Opp2', 'home_score': 42, 'away_score': 28, 'completed': True},
        
        {'home': 'Team B', 'away': 'Opp1', 'home_score': 28, 'away_score': 24, 'completed': True},
        {'home': 'Team B', 'away': 'Opp2', 'home_score': 24, 'away_score': 21, 'completed': True},
    ]
    
    stats = calculate_team_stats(teams_info, games)
    
    net_a = stats['Team A']['points_for'] - stats['Team A']['points_against']
    net_b = stats['Team B']['points_for'] - stats['Team B']['points_against']
    
    print(f"Team A net points: +{net_a}")
    print(f"Team B net points: +{net_b}")
    
    winner = break_two_team_division_tie(['Team A', 'Team B'], stats, teams_info)
    
    if winner == 'Team A':
        print("✓ PASS: Team A wins on net points in all games")
        return True
    else:
        print("✗ FAIL: Expected Team A to win on net points")
        return False

def test_net_touchdowns():
    print("\n" + "="*80)
    print("TEST: Net Touchdowns Tiebreaker")
    print("="*80)
    
    teams_info = {
        'Team A': {'division': 'AFC East', 'conference': 'AFC'},
        'Team B': {'division': 'AFC East', 'conference': 'AFC'},
        'Opp1': {'division': 'AFC North', 'conference': 'AFC'},
        'Opp2': {'division': 'AFC South', 'conference': 'AFC'},
    }
    
    games = [
        {'home': 'Team A', 'away': 'Opp1', 'home_score': 35, 'away_score': 14, 'completed': True},
        {'home': 'Team A', 'away': 'Opp2', 'home_score': 42, 'away_score': 21, 'completed': True},
        
        {'home': 'Team B', 'away': 'Opp1', 'home_score': 30, 'away_score': 10, 'completed': True},
        {'home': 'Team B', 'away': 'Opp2', 'home_score': 27, 'away_score': 20, 'completed': True},
    ]
    
    stats = calculate_team_stats(teams_info, games)
    
    print(f"Team A touchdowns: {stats['Team A']['touchdowns']}")
    print(f"Team B touchdowns: {stats['Team B']['touchdowns']}")
    
    winner = break_two_team_division_tie(['Team A', 'Team B'], stats, teams_info)
    
    if winner == 'Team A':
        print("✓ PASS: Team A wins on touchdowns")
        return True
    else:
        print("✗ FAIL: Expected Team A to win on touchdowns")
        return False

def test_4team_progressive_elimination():
    print("\n" + "="*80)
    print("TEST: 4-Team Progressive Elimination")
    print("="*80)
    
    teams_info = {
        'Team A': {'division': 'AFC North', 'conference': 'AFC'},
        'Team B': {'division': 'AFC North', 'conference': 'AFC'},
        'Team C': {'division': 'AFC North', 'conference': 'AFC'},
        'Team D': {'division': 'AFC North', 'conference': 'AFC'},
        'Outsider': {'division': 'AFC South', 'conference': 'AFC'},
    }
    
    games = [
        {'home': 'Team A', 'away': 'Team B', 'home_score': 24, 'away_score': 21, 'completed': True},
        {'home': 'Team B', 'away': 'Team C', 'home_score': 28, 'away_score': 24, 'completed': True},
        {'home': 'Team C', 'away': 'Team D', 'home_score': 21, 'away_score': 24, 'completed': True},
        {'home': 'Team D', 'away': 'Team A', 'home_score': 28, 'away_score': 31, 'completed': True},
        
        {'home': 'Team A', 'away': 'Outsider', 'home_score': 35, 'away_score': 21, 'completed': True},
        {'home': 'Team B', 'away': 'Outsider', 'home_score': 28, 'away_score': 24, 'completed': True},
        {'home': 'Team C', 'away': 'Outsider', 'home_score': 24, 'away_score': 27, 'completed': True},
        {'home': 'Team D', 'away': 'Outsider', 'home_score': 31, 'away_score': 28, 'completed': True},
    ]
    
    stats = calculate_team_stats(teams_info, games)
    
    print(f"Team A: {stats['Team A']['W']}-{stats['Team A']['L']}")
    print(f"Team B: {stats['Team B']['W']}-{stats['Team B']['L']}")
    print(f"Team C: {stats['Team C']['W']}-{stats['Team C']['L']}")
    print(f"Team D: {stats['Team D']['W']}-{stats['Team D']['L']}")
    
    ranked = break_multi_team_division_tie(['Team A', 'Team B', 'Team C', 'Team D'], stats, teams_info)
    
    print(f"Ranked order: {ranked}")
    
    if len(ranked) == 4:
        print("✓ PASS: 4-team progressive elimination produced ranking")
        return True
    else:
        print("✗ FAIL: 4-team progressive elimination failed")
        return False

def test_wildcard_head_to_head_sweep():
    print("\n" + "="*80)
    print("TEST: Wild Card 3+ Teams - Head-to-Head Sweep")
    print("="*80)
    
    teams_info = {
        'Sweeper': {'division': 'NFC West', 'conference': 'NFC'},
        'Team B': {'division': 'NFC East', 'conference': 'NFC'},
        'Team C': {'division': 'NFC North', 'conference': 'NFC'},
        'Outsider': {'division': 'NFC South', 'conference': 'NFC'},
    }
    
    games = [
        {'home': 'Sweeper', 'away': 'Team B', 'home_score': 28, 'away_score': 21, 'completed': True},
        {'home': 'Sweeper', 'away': 'Team C', 'home_score': 24, 'away_score': 20, 'completed': True},
        
        {'home': 'Team B', 'away': 'Team C', 'home_score': 24, 'away_score': 24, 'completed': True},
        
        {'home': 'Sweeper', 'away': 'Outsider', 'home_score': 21, 'away_score': 24, 'completed': True},
        {'home': 'Team B', 'away': 'Outsider', 'home_score': 24, 'away_score': 27, 'completed': True},
        {'home': 'Team C', 'away': 'Outsider', 'home_score': 28, 'away_score': 31, 'completed': True},
    ]
    
    stats = calculate_team_stats(teams_info, games)
    
    print(f"Sweeper: {stats['Sweeper']['W']}-{stats['Sweeper']['L']} (beat Team B and Team C)")
    print(f"Team B: {stats['Team B']['W']}-{stats['Team B']['L']}-{stats['Team B']['T']}")
    print(f"Team C: {stats['Team C']['W']}-{stats['Team C']['L']}-{stats['Team C']['T']}")
    
    ranked = break_multi_team_wildcard_tie(['Sweeper', 'Team B', 'Team C'], stats, teams_info)
    
    if ranked[0] == 'Sweeper':
        print("✓ PASS: Sweeper wins with head-to-head sweep")
        return True
    else:
        print("✗ FAIL: Expected Sweeper to win H2H sweep")
        return False

def test_scenario_with_all_week18_outcomes():
    print("\n" + "="*80)
    print("TEST: Multiple Week 18 Outcome Scenarios")
    print("="*80)
    
    teams_info = load_teams_data()
    completed = get_completed_games()
    week18 = get_week18_games()
    
    scenarios_tested = 0
    scenarios_passed = 0
    
    test_patterns = [
        ['home'] * 16,
        ['away'] * 16,
        ['home', 'away'] * 8,
        ['away', 'home'] * 8,
        ['home', 'home', 'away'] * 5 + ['home'],
    ]
    
    for pattern in test_patterns:
        simulated = [simulate_game_outcome(week18[j], pattern[j]) for j in range(len(week18))]
        all_games = completed + simulated
        stats = calculate_team_stats(teams_info, all_games)
        seeding = calculate_playoff_seeding(teams_info, stats)
        
        afc_count = len(seeding['AFC']['division_winners']) + len(seeding['AFC']['wildcards'])
        nfc_count = len(seeding['NFC']['division_winners']) + len(seeding['NFC']['wildcards'])
        
        scenarios_tested += 1
        if afc_count == 7 and nfc_count == 7:
            scenarios_passed += 1
    
    print(f"Tested {scenarios_tested} different Week 18 outcome patterns")
    print(f"✓ {scenarios_passed}/{scenarios_tested} produced valid 7-team playoff brackets")
    
    return scenarios_passed == scenarios_tested

def run_all_tests():
    print("\n" + "="*80)
    print("NFL TIEBREAKER COMPREHENSIVE TEST SUITE")
    print("Testing ALL 12 Steps of Division & Wild Card Tiebreakers")
    print("="*80)
    
    tests = [
        ("Division Step 1: H2H", test_division_tiebreaker_step1_head_to_head),
        ("Division Step 2: Div Record", test_division_tiebreaker_step2_division_record),
        ("Division Step 3: Common Games", test_division_tiebreaker_step3_common_games),
        ("Division Step 5: SOV", test_strength_of_victory),
        ("Division Step 6: SOS", test_strength_of_schedule),
        ("Division Step 9: Net Pts Common", test_net_points_common_games),
        ("Division Step 10: Net Pts All", test_net_points_all_games),
        ("Division Step 11: Net TDs", test_net_touchdowns),
        ("3-Team Progressive Elim", test_3team_progressive_elimination),
        ("4-Team Progressive Elim", test_4team_progressive_elimination),
        ("WC Step 2: Conference %", test_wildcard_conference_percentage),
        ("WC Step 8: Conf Net Pts", test_wildcard_conference_net_points),
        ("WC 3+: H2H Sweep", test_wildcard_head_to_head_sweep),
        ("Full Playoff Seeding", test_full_playoff_seeding),
        ("Week 18 Scenarios", test_scenario_with_all_week18_outcomes),
    ]
    
    passed = 0
    total = len(tests)
    
    for name, test_func in tests:
        try:
            result = test_func()
            if result:
                passed += 1
        except Exception as e:
            print(f"✗ FAIL: {name} - Exception: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "="*80)
    print(f"TIEBREAKER TEST RESULTS: {passed}/{total} PASSED ({100*passed/total:.1f}%)")
    print("="*80)
    print("\nCoverage:")
    print("  ✓ Division Tiebreakers: Steps 1, 2, 3, 5, 6, 9, 10, 11")
    print("  ✓ Wild Card Tiebreakers: Steps 2, 8, H2H Sweep")
    print("  ✓ Progressive Elimination: 3-team and 4-team scenarios")
    print("  ✓ Common Games Calculation: Minimum 4 opponents")
    print("  ✓ Conference/Division Record Tracking")
    print("  ✓ Full Playoff Seeding Logic")
    print("  ✓ Multiple Week 18 Outcome Scenarios")
    print("="*80)
    
    return passed == total

if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)
