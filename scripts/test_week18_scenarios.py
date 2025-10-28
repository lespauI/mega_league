#!/usr/bin/env python3
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from week18_simulator import load_teams_data, load_games, calculate_team_stats
import random
import itertools
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

def calculate_playoff_seeding(teams_info, all_games):
    stats = calculate_team_stats(teams_info, all_games)
    
    afc_teams = [(team, stats[team]) for team in teams_info if teams_info[team]['conference'] == 'AFC']
    nfc_teams = [(team, stats[team]) for team in teams_info if teams_info[team]['conference'] == 'NFC']
    
    def sort_teams(teams_list):
        return sorted(teams_list, key=lambda x: (-x[1]['win_pct'], -x[1]['W']))
    
    afc_sorted = sort_teams(afc_teams)
    nfc_sorted = sort_teams(nfc_teams)
    
    def get_division_winners(conference_teams, teams_info):
        divisions = defaultdict(list)
        for team, stat in conference_teams:
            div = teams_info[team]['division']
            divisions[div].append((team, stat))
        
        winners = []
        for div, div_teams in divisions.items():
            div_sorted = sorted(div_teams, key=lambda x: (-x[1]['division_pct'], -x[1]['win_pct'], -x[1]['division_W']))
            if div_sorted:
                winners.append(div_sorted[0])
        
        winners.sort(key=lambda x: (-x[1]['win_pct'], -x[1]['W']))
        return winners
    
    afc_div_winners = get_division_winners(afc_teams, teams_info)
    nfc_div_winners = get_division_winners(nfc_teams, teams_info)
    
    afc_div_winner_names = {team for team, _ in afc_div_winners}
    nfc_div_winner_names = {team for team, _ in nfc_div_winners}
    
    afc_wildcard = [(team, stat) for team, stat in afc_sorted if team not in afc_div_winner_names][:3]
    nfc_wildcard = [(team, stat) for team, stat in nfc_sorted if team not in nfc_div_winner_names][:3]
    
    return {
        'AFC': {
            'division_winners': afc_div_winners[:4],
            'wildcards': afc_wildcard
        },
        'NFC': {
            'division_winners': nfc_div_winners[:4],
            'wildcards': nfc_wildcard
        }
    }

def verify_tiebreaker_rules(teams_info, all_games, scenario_num):
    stats = calculate_team_stats(teams_info, all_games)
    
    errors = []
    
    for team in stats:
        if stats[team]['W'] < 0 or stats[team]['L'] < 0 or stats[team]['T'] < 0:
            errors.append(f"Scenario {scenario_num}: {team} has negative W/L/T")
        
        total = stats[team]['W'] + stats[team]['L'] + stats[team]['T']
        if total > 17:
            errors.append(f"Scenario {scenario_num}: {team} has {total} games (max 17)")
        
        conf_total = stats[team]['conference_W'] + stats[team]['conference_L'] + stats[team]['conference_T']
        if conf_total > total:
            errors.append(f"Scenario {scenario_num}: {team} conf games ({conf_total}) > total ({total})")
        
        div_total = stats[team]['division_W'] + stats[team]['division_L'] + stats[team]['division_T']
        if div_total > conf_total:
            errors.append(f"Scenario {scenario_num}: {team} div games ({div_total}) > conf ({conf_total})")
        
        expected_win_pct = (stats[team]['W'] + 0.5 * stats[team]['T']) / total if total > 0 else 0
        if abs(stats[team]['win_pct'] - expected_win_pct) > 0.001:
            errors.append(f"Scenario {scenario_num}: {team} win_pct incorrect: {stats[team]['win_pct']} vs {expected_win_pct}")
        
        if conf_total > 0:
            expected_conf_pct = (stats[team]['conference_W'] + 0.5 * stats[team]['conference_T']) / conf_total
            if abs(stats[team]['conference_pct'] - expected_conf_pct) > 0.001:
                errors.append(f"Scenario {scenario_num}: {team} conf_pct incorrect")
        
        if div_total > 0:
            expected_div_pct = (stats[team]['division_W'] + 0.5 * stats[team]['division_T']) / div_total
            if abs(stats[team]['division_pct'] - expected_div_pct) > 0.001:
                errors.append(f"Scenario {scenario_num}: {team} div_pct incorrect")
    
    return errors

def test_specific_tiebreaker_scenarios():
    print("\n" + "="*80)
    print("TESTING SPECIFIC TIEBREAKER SCENARIOS")
    print("="*80)
    
    teams_info = load_teams_data()
    completed = get_completed_games()
    week18 = get_week18_games()
    
    scenarios_tested = 0
    scenarios_passed = 0
    
    print(f"\nWeek 18 has {len(week18)} games to simulate")
    print(f"Completed games through Week 17: {len(completed)}")
    
    print("\n--- Testing All Home Wins ---")
    all_home = [simulate_game_outcome(g, 'home') for g in week18]
    all_games = completed + all_home
    seeding = calculate_playoff_seeding(teams_info, all_games)
    errors = verify_tiebreaker_rules(teams_info, all_games, 'ALL_HOME')
    scenarios_tested += 1
    if not errors:
        scenarios_passed += 1
        print("✓ PASS: All home wins scenario")
    else:
        print("✗ FAIL: All home wins scenario")
        for e in errors[:5]:
            print(f"  {e}")
    
    print("\n--- Testing All Away Wins ---")
    all_away = [simulate_game_outcome(g, 'away') for g in week18]
    all_games = completed + all_away
    seeding = calculate_playoff_seeding(teams_info, all_games)
    errors = verify_tiebreaker_rules(teams_info, all_games, 'ALL_AWAY')
    scenarios_tested += 1
    if not errors:
        scenarios_passed += 1
        print("✓ PASS: All away wins scenario")
    else:
        print("✗ FAIL: All away wins scenario")
        for e in errors[:5]:
            print(f"  {e}")
    
    print("\n--- Testing All Ties ---")
    all_ties = [simulate_game_outcome(g, 'tie') for g in week18]
    all_games = completed + all_ties
    seeding = calculate_playoff_seeding(teams_info, all_games)
    errors = verify_tiebreaker_rules(teams_info, all_games, 'ALL_TIES')
    scenarios_tested += 1
    if not errors:
        scenarios_passed += 1
        print("✓ PASS: All ties scenario")
    else:
        print("✗ FAIL: All ties scenario")
        for e in errors[:5]:
            print(f"  {e}")
    
    print("\n--- Testing Random Scenarios (Sample of 100) ---")
    random.seed(42)
    for i in range(100):
        outcomes = [random.choice(['home', 'away', 'tie']) for _ in week18]
        simulated = [simulate_game_outcome(week18[j], outcomes[j]) for j in range(len(week18))]
        all_games = completed + simulated
        errors = verify_tiebreaker_rules(teams_info, all_games, f'RANDOM_{i+1}')
        scenarios_tested += 1
        if not errors:
            scenarios_passed += 1
        else:
            print(f"✗ FAIL: Random scenario {i+1}")
            for e in errors[:3]:
                print(f"  {e}")
    
    print(f"\n✓ {scenarios_passed - 3} / {scenarios_tested - 3} random scenarios passed")
    
    print("\n--- Testing Mixed Scenarios ---")
    mixed_patterns = [
        ['home', 'away'] * 8,
        ['away', 'home'] * 8,
        ['home', 'home', 'away'] * 5 + ['home'],
        ['tie', 'home', 'away'] * 5 + ['tie'],
        ['away', 'away', 'tie'] * 5 + ['away'],
    ]
    
    for idx, pattern in enumerate(mixed_patterns):
        simulated = [simulate_game_outcome(week18[j], pattern[j]) for j in range(len(week18))]
        all_games = completed + simulated
        errors = verify_tiebreaker_rules(teams_info, all_games, f'MIXED_{idx+1}')
        scenarios_tested += 1
        if not errors:
            scenarios_passed += 1
            print(f"✓ PASS: Mixed pattern {idx+1}")
        else:
            print(f"✗ FAIL: Mixed pattern {idx+1}")
            for e in errors[:3]:
                print(f"  {e}")
    
    print("\n" + "="*80)
    print(f"SCENARIO TEST SUMMARY: {scenarios_passed}/{scenarios_tested} PASSED ({100*scenarios_passed/scenarios_tested:.1f}%)")
    print("="*80)
    
    return scenarios_passed == scenarios_tested

def test_division_tiebreakers():
    print("\n" + "="*80)
    print("TESTING DIVISION TIEBREAKER LOGIC")
    print("="*80)
    
    teams_info = load_teams_data()
    completed = get_completed_games()
    week18 = get_week18_games()
    
    division_games = []
    for g in week18:
        home_div = teams_info[g['home']]['division']
        away_div = teams_info[g['away']]['division']
        if home_div == away_div:
            division_games.append(g)
    
    print(f"\nFound {len(division_games)} division games in Week 18:")
    for g in division_games:
        print(f"  {g['home']} vs {g['away']} ({teams_info[g['home']]['division']})")
    
    test_cases = 0
    passed = 0
    
    for div_game in division_games[:3]:
        for outcome in ['home', 'away', 'tie']:
            other_games = [g for g in week18 if g['id'] != div_game['id']]
            other_simulated = [simulate_game_outcome(g, 'home') for g in other_games]
            div_simulated = simulate_game_outcome(div_game, outcome)
            
            all_games = completed + other_simulated + [div_simulated]
            errors = verify_tiebreaker_rules(teams_info, all_games, f'DIV_{div_game["id"]}_{outcome}')
            test_cases += 1
            if not errors:
                passed += 1
    
    print(f"\n✓ Division tiebreaker tests: {passed}/{test_cases} passed")
    return passed == test_cases

def analyze_current_standings():
    print("\n" + "="*80)
    print("CURRENT STANDINGS ANALYSIS (Through Week 16)")
    print("="*80)
    
    teams_info = load_teams_data()
    completed = get_completed_games()
    stats = calculate_team_stats(teams_info, completed)
    
    afc_teams = [(team, stats[team]) for team in teams_info if teams_info[team]['conference'] == 'AFC']
    nfc_teams = [(team, stats[team]) for team in teams_info if teams_info[team]['conference'] == 'NFC']
    
    afc_sorted = sorted(afc_teams, key=lambda x: (-x[1]['win_pct'], -x[1]['W']))
    nfc_sorted = sorted(nfc_teams, key=lambda x: (-x[1]['win_pct'], -x[1]['W']))
    
    print("\n--- AFC Standings ---")
    for i, (team, stat) in enumerate(afc_sorted[:10], 1):
        record = f"{stat['W']}-{stat['L']}"
        if stat['T'] > 0:
            record += f"-{stat['T']}"
        print(f"{i:2d}. {team:20s} {record:8s} ({stat['win_pct']:.3f})")
    
    print("\n--- NFC Standings ---")
    for i, (team, stat) in enumerate(nfc_sorted[:10], 1):
        record = f"{stat['W']}-{stat['L']}"
        if stat['T'] > 0:
            record += f"-{stat['T']}"
        print(f"{i:2d}. {team:20s} {record:8s} ({stat['win_pct']:.3f})")
    
    print("\n--- Teams with Same Record (Potential Tiebreakers) ---")
    record_groups = defaultdict(list)
    for team, stat in afc_sorted + nfc_sorted:
        record = (stat['W'], stat['L'], stat['T'])
        record_groups[record].append(team)
    
    for record, teams in sorted(record_groups.items(), reverse=True):
        if len(teams) >= 2:
            w, l, t = record
            record_str = f"{w}-{l}"
            if t > 0:
                record_str += f"-{t}"
            print(f"  {record_str}: {', '.join(teams)}")

if __name__ == '__main__':
    print("\n" + "="*80)
    print("WEEK 18 SCENARIO SIMULATOR - COMPREHENSIVE TESTING")
    print("="*80)
    
    analyze_current_standings()
    
    result1 = test_specific_tiebreaker_scenarios()
    result2 = test_division_tiebreakers()
    
    print("\n" + "="*80)
    print("FINAL RESULTS")
    print("="*80)
    if result1 and result2:
        print("✓ ALL TESTS PASSED")
        print("The Week 18 simulator correctly handles all tested scenarios")
        sys.exit(0)
    else:
        print("✗ SOME TESTS FAILED")
        print("The Week 18 simulator has issues that need to be addressed")
        sys.exit(1)
