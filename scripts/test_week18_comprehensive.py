#!/usr/bin/env python3
"""
Comprehensive test suite for week18_simulator.py Python functions.
Tests calculate_team_stats() with complex multi-team scenarios inspired by NFL tiebreaker rules.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from week18_simulator import calculate_team_stats
from collections import defaultdict


class TestFramework:
    def __init__(self):
        self.tests_passed = 0
        self.tests_failed = 0
    
    def assert_equal(self, actual, expected, msg=""):
        if actual == expected:
            return True
        raise AssertionError(f"{msg}\nExpected: {expected}\nActual: {actual}")
    
    def assert_almost_equal(self, actual, expected, places=3, msg=""):
        if abs(actual - expected) < 10**(-places):
            return True
        raise AssertionError(f"{msg}\nExpected: {expected:.6f}\nActual: {actual:.6f}")
    
    def run_test(self, test_name, test_func):
        try:
            test_func()
            self.tests_passed += 1
            print(f"✓ PASS: {test_name}")
        except AssertionError as e:
            self.tests_failed += 1
            print(f"✗ FAIL: {test_name}")
            print(f"  {str(e)}")
        except Exception as e:
            self.tests_failed += 1
            print(f"✗ ERROR: {test_name}")
            print(f"  {type(e).__name__}: {str(e)}")
    
    def print_summary(self):
        total = self.tests_passed + self.tests_failed
        print(f"\n{'='*60}")
        print(f"TEST SUMMARY")
        print(f"{'='*60}")
        print(f"Total Tests: {total}")
        print(f"Passed: {self.tests_passed} ({100*self.tests_passed/total if total > 0 else 0:.1f}%)")
        print(f"Failed: {self.tests_failed} ({100*self.tests_failed/total if total > 0 else 0:.1f}%)")
        print(f"{'='*60}\n")


def test_2team_head_to_head_sweep():
    """Test 2-team with clear head-to-head record (2-0)."""
    teams_info = {
        'Cowboys': {'division': 'NFC East', 'conference': 'NFC', 'logo_url': ''},
        'Eagles': {'division': 'NFC East', 'conference': 'NFC', 'logo_url': ''},
    }
    games = [
        {'home': 'Cowboys', 'away': 'Eagles', 'home_score': 24, 'away_score': 20, 'completed': True},
        {'home': 'Eagles', 'away': 'Cowboys', 'home_score': 17, 'away_score': 21, 'completed': True},
    ]
    
    stats = calculate_team_stats(teams_info, games)
    
    framework.assert_equal(stats['Cowboys']['head_to_head']['Eagles']['W'], 2, "Cowboys should have 2 H2H wins")
    framework.assert_equal(stats['Cowboys']['head_to_head']['Eagles']['L'], 0, "Cowboys should have 0 H2H losses")
    framework.assert_equal(stats['Eagles']['head_to_head']['Cowboys']['W'], 0, "Eagles should have 0 H2H wins")
    framework.assert_equal(stats['Eagles']['head_to_head']['Cowboys']['L'], 2, "Eagles should have 2 H2H losses")


def test_2team_head_to_head_split():
    """Test 2-team with split head-to-head record (1-1)."""
    teams_info = {
        'Cowboys': {'division': 'NFC East', 'conference': 'NFC', 'logo_url': ''},
        'Eagles': {'division': 'NFC East', 'conference': 'NFC', 'logo_url': ''},
    }
    games = [
        {'home': 'Cowboys', 'away': 'Eagles', 'home_score': 24, 'away_score': 20, 'completed': True},
        {'home': 'Eagles', 'away': 'Cowboys', 'home_score': 27, 'away_score': 21, 'completed': True},
    ]
    
    stats = calculate_team_stats(teams_info, games)
    
    framework.assert_equal(stats['Cowboys']['head_to_head']['Eagles']['W'], 1, "Cowboys should have 1 H2H win")
    framework.assert_equal(stats['Cowboys']['head_to_head']['Eagles']['L'], 1, "Cowboys should have 1 H2H loss")
    framework.assert_equal(stats['Eagles']['head_to_head']['Cowboys']['W'], 1, "Eagles should have 1 H2H win")
    framework.assert_equal(stats['Eagles']['head_to_head']['Cowboys']['L'], 1, "Eagles should have 1 H2H loss")


def test_3team_head_to_head_sweep():
    """Test 3-team with one team sweeping all others (2-0 vs rest)."""
    teams_info = {
        'Cowboys': {'division': 'NFC East', 'conference': 'NFC', 'logo_url': ''},
        'Eagles': {'division': 'NFC East', 'conference': 'NFC', 'logo_url': ''},
        'Giants': {'division': 'NFC East', 'conference': 'NFC', 'logo_url': ''},
    }
    games = [
        {'home': 'Cowboys', 'away': 'Eagles', 'home_score': 24, 'away_score': 20, 'completed': True},
        {'home': 'Cowboys', 'away': 'Giants', 'home_score': 28, 'away_score': 21, 'completed': True},
        {'home': 'Eagles', 'away': 'Giants', 'home_score': 21, 'away_score': 17, 'completed': True},
    ]
    
    stats = calculate_team_stats(teams_info, games)
    
    framework.assert_equal(stats['Cowboys']['head_to_head']['Eagles']['W'], 1, "Cowboys beat Eagles")
    framework.assert_equal(stats['Cowboys']['head_to_head']['Giants']['W'], 1, "Cowboys beat Giants")
    framework.assert_equal(stats['Cowboys']['head_to_head']['Eagles']['L'], 0, "Cowboys swept Eagles")
    framework.assert_equal(stats['Cowboys']['head_to_head']['Giants']['L'], 0, "Cowboys swept Giants")


def test_3team_circular_head_to_head():
    """Test 3-team with circular/rock-paper-scissors H2H (A>B, B>C, C>A)."""
    teams_info = {
        'Team A': {'division': 'AFC West', 'conference': 'AFC', 'logo_url': ''},
        'Team B': {'division': 'AFC West', 'conference': 'AFC', 'logo_url': ''},
        'Team C': {'division': 'AFC West', 'conference': 'AFC', 'logo_url': ''},
    }
    games = [
        {'home': 'Team A', 'away': 'Team B', 'home_score': 24, 'away_score': 20, 'completed': True},
        {'home': 'Team B', 'away': 'Team C', 'home_score': 27, 'away_score': 21, 'completed': True},
        {'home': 'Team C', 'away': 'Team A', 'home_score': 31, 'away_score': 28, 'completed': True},
    ]
    
    stats = calculate_team_stats(teams_info, games)
    
    framework.assert_equal(stats['Team A']['head_to_head']['Team B']['W'], 1, "A beat B")
    framework.assert_equal(stats['Team B']['head_to_head']['Team C']['W'], 1, "B beat C")
    framework.assert_equal(stats['Team C']['head_to_head']['Team A']['W'], 1, "C beat A")
    
    framework.assert_equal(stats['Team A']['W'], 1, "A has 1 win")
    framework.assert_equal(stats['Team A']['L'], 1, "A has 1 loss")
    framework.assert_equal(stats['Team B']['W'], 1, "B has 1 win")
    framework.assert_equal(stats['Team B']['L'], 1, "B has 1 loss")
    framework.assert_equal(stats['Team C']['W'], 1, "C has 1 win")
    framework.assert_equal(stats['Team C']['L'], 1, "C has 1 loss")


def test_4team_complex_division_records():
    """Test 4 teams with varying division and conference records."""
    teams_info = {
        'Team A': {'division': 'NFC North', 'conference': 'NFC', 'logo_url': ''},
        'Team B': {'division': 'NFC North', 'conference': 'NFC', 'logo_url': ''},
        'Team C': {'division': 'NFC North', 'conference': 'NFC', 'logo_url': ''},
        'Team D': {'division': 'NFC North', 'conference': 'NFC', 'logo_url': ''},
    }
    games = [
        {'home': 'Team A', 'away': 'Team B', 'home_score': 24, 'away_score': 20, 'completed': True},
        {'home': 'Team A', 'away': 'Team C', 'home_score': 28, 'away_score': 21, 'completed': True},
        {'home': 'Team A', 'away': 'Team D', 'home_score': 31, 'away_score': 27, 'completed': True},
        {'home': 'Team B', 'away': 'Team C', 'home_score': 21, 'away_score': 17, 'completed': True},
        {'home': 'Team B', 'away': 'Team D', 'home_score': 24, 'away_score': 21, 'completed': True},
        {'home': 'Team C', 'away': 'Team D', 'home_score': 20, 'away_score': 17, 'completed': True},
    ]
    
    stats = calculate_team_stats(teams_info, games)
    
    framework.assert_equal(stats['Team A']['division_W'], 3, "Team A has 3 division wins")
    framework.assert_equal(stats['Team A']['division_L'], 0, "Team A has 0 division losses")
    framework.assert_equal(stats['Team B']['division_W'], 2, "Team B has 2 division wins")
    framework.assert_equal(stats['Team B']['division_L'], 1, "Team B has 1 division loss")
    framework.assert_equal(stats['Team C']['division_W'], 1, "Team C has 1 division win")
    framework.assert_equal(stats['Team C']['division_L'], 2, "Team C has 2 division losses")
    framework.assert_equal(stats['Team D']['division_W'], 0, "Team D has 0 division wins")
    framework.assert_equal(stats['Team D']['division_L'], 3, "Team D has 3 division losses")
    
    framework.assert_almost_equal(stats['Team A']['division_pct'], 1.0, 3, "Team A div pct = 1.0")
    framework.assert_almost_equal(stats['Team B']['division_pct'], 0.667, 3, "Team B div pct = 0.667")


def test_common_games_4_opponents():
    """Test common games tracking with exactly 4 common opponents."""
    teams_info = {
        'Team A': {'division': 'AFC South', 'conference': 'AFC', 'logo_url': ''},
        'Team B': {'division': 'AFC South', 'conference': 'AFC', 'logo_url': ''},
        'Opp1': {'division': 'AFC North', 'conference': 'AFC', 'logo_url': ''},
        'Opp2': {'division': 'AFC North', 'conference': 'AFC', 'logo_url': ''},
        'Opp3': {'division': 'AFC East', 'conference': 'AFC', 'logo_url': ''},
        'Opp4': {'division': 'AFC East', 'conference': 'AFC', 'logo_url': ''},
    }
    games = [
        {'home': 'Team A', 'away': 'Opp1', 'home_score': 24, 'away_score': 20, 'completed': True},
        {'home': 'Team A', 'away': 'Opp2', 'home_score': 27, 'away_score': 14, 'completed': True},
        {'home': 'Team A', 'away': 'Opp3', 'home_score': 21, 'away_score': 24, 'completed': True},
        {'home': 'Team A', 'away': 'Opp4', 'home_score': 28, 'away_score': 17, 'completed': True},
        {'home': 'Team B', 'away': 'Opp1', 'home_score': 20, 'away_score': 23, 'completed': True},
        {'home': 'Team B', 'away': 'Opp2', 'home_score': 24, 'away_score': 21, 'completed': True},
        {'home': 'Team B', 'away': 'Opp3', 'home_score': 17, 'away_score': 20, 'completed': True},
        {'home': 'Team B', 'away': 'Opp4', 'home_score': 14, 'away_score': 17, 'completed': True},
    ]
    
    stats = calculate_team_stats(teams_info, games)
    
    common_opponents = set(stats['Team A']['opponents']) & set(stats['Team B']['opponents'])
    framework.assert_equal(len(common_opponents), 4, "Should have 4 common opponents")
    
    team_a_common_record = sum(1 for g in stats['Team A']['game_results'] 
                                if g['opponent'] in common_opponents and g['pf'] > g['pa'])
    team_b_common_record = sum(1 for g in stats['Team B']['game_results'] 
                                if g['opponent'] in common_opponents and g['pf'] > g['pa'])
    
    framework.assert_equal(team_a_common_record, 3, "Team A should be 3-1 in common games")
    framework.assert_equal(team_b_common_record, 1, "Team B should be 1-3 in common games")


def test_common_games_less_than_4():
    """Test scenario with less than 4 common opponents."""
    teams_info = {
        'Team A': {'division': 'NFC West', 'conference': 'NFC', 'logo_url': ''},
        'Team B': {'division': 'NFC West', 'conference': 'NFC', 'logo_url': ''},
        'Opp1': {'division': 'NFC South', 'conference': 'NFC', 'logo_url': ''},
        'Opp2': {'division': 'NFC South', 'conference': 'NFC', 'logo_url': ''},
        'Opp3': {'division': 'NFC South', 'conference': 'NFC', 'logo_url': ''},
    }
    games = [
        {'home': 'Team A', 'away': 'Opp1', 'home_score': 24, 'away_score': 20, 'completed': True},
        {'home': 'Team A', 'away': 'Opp2', 'home_score': 27, 'away_score': 21, 'completed': True},
        {'home': 'Team A', 'away': 'Opp3', 'home_score': 21, 'away_score': 24, 'completed': True},
        {'home': 'Team B', 'away': 'Opp1', 'home_score': 20, 'away_score': 23, 'completed': True},
        {'home': 'Team B', 'away': 'Opp2', 'home_score': 24, 'away_score': 27, 'completed': True},
    ]
    
    stats = calculate_team_stats(teams_info, games)
    
    common_opponents = set(stats['Team A']['opponents']) & set(stats['Team B']['opponents'])
    framework.assert_equal(len(common_opponents), 2, "Should have only 2 common opponents")


def test_strength_of_victory_complex():
    """Test SOV calculation with multiple defeated opponents of varying quality."""
    teams_info = {
        'Winner': {'division': 'AFC East', 'conference': 'AFC', 'logo_url': ''},
        'Good1': {'division': 'AFC North', 'conference': 'AFC', 'logo_url': ''},
        'Good2': {'division': 'AFC South', 'conference': 'AFC', 'logo_url': ''},
        'Bad1': {'division': 'AFC West', 'conference': 'AFC', 'logo_url': ''},
        'Bad2': {'division': 'NFC East', 'conference': 'NFC', 'logo_url': ''},
    }
    games = [
        {'home': 'Good1', 'away': 'Bad1', 'home_score': 28, 'away_score': 14, 'completed': True},
        {'home': 'Good1', 'away': 'Bad2', 'home_score': 31, 'away_score': 17, 'completed': True},
        {'home': 'Good2', 'away': 'Bad1', 'home_score': 24, 'away_score': 20, 'completed': True},
        {'home': 'Good2', 'away': 'Bad2', 'home_score': 27, 'away_score': 21, 'completed': True},
        {'home': 'Winner', 'away': 'Good1', 'home_score': 21, 'away_score': 17, 'completed': True},
        {'home': 'Winner', 'away': 'Good2', 'home_score': 24, 'away_score': 20, 'completed': True},
        {'home': 'Winner', 'away': 'Bad1', 'home_score': 35, 'away_score': 14, 'completed': True},
        {'home': 'Winner', 'away': 'Bad2', 'home_score': 28, 'away_score': 21, 'completed': True},
    ]
    
    stats = calculate_team_stats(teams_info, games)
    
    framework.assert_equal(len(stats['Winner']['defeated_opponents']), 4, "Winner defeated 4 opponents")
    framework.assert_equal(stats['Good1']['W'], 2, "Good1 has 2 wins")
    framework.assert_equal(stats['Good2']['W'], 2, "Good2 has 2 wins")
    framework.assert_equal(stats['Bad1']['W'], 0, "Bad1 has 0 wins")
    framework.assert_equal(stats['Bad2']['W'], 0, "Bad2 has 0 wins")
    
    good1_pct = stats['Good1']['win_pct']
    good2_pct = stats['Good2']['win_pct']
    bad1_pct = stats['Bad1']['win_pct']
    bad2_pct = stats['Bad2']['win_pct']
    expected_sov = (good1_pct + good2_pct + bad1_pct + bad2_pct) / 4
    
    framework.assert_almost_equal(stats['Winner']['strength_of_victory'], expected_sov, 3,
                                   "Winner SOV should be average of all defeated opponents")


def test_strength_of_schedule_complex():
    """Test SOS calculation with varied opponent quality."""
    teams_info = {
        'Team': {'division': 'NFC North', 'conference': 'NFC', 'logo_url': ''},
        'Strong1': {'division': 'NFC South', 'conference': 'NFC', 'logo_url': ''},
        'Strong2': {'division': 'NFC West', 'conference': 'NFC', 'logo_url': ''},
        'Weak1': {'division': 'NFC East', 'conference': 'NFC', 'logo_url': ''},
        'Weak2': {'division': 'AFC East', 'conference': 'AFC', 'logo_url': ''},
        'Other': {'division': 'AFC West', 'conference': 'AFC', 'logo_url': ''},
    }
    games = [
        {'home': 'Strong1', 'away': 'Other', 'home_score': 28, 'away_score': 14, 'completed': True},
        {'home': 'Strong1', 'away': 'Weak1', 'home_score': 31, 'away_score': 17, 'completed': True},
        {'home': 'Strong2', 'away': 'Other', 'home_score': 24, 'away_score': 20, 'completed': True},
        {'home': 'Strong2', 'away': 'Weak2', 'home_score': 27, 'away_score': 21, 'completed': True},
        {'home': 'Team', 'away': 'Strong1', 'home_score': 17, 'away_score': 21, 'completed': True},
        {'home': 'Team', 'away': 'Strong2', 'home_score': 20, 'away_score': 24, 'completed': True},
        {'home': 'Team', 'away': 'Weak1', 'home_score': 35, 'away_score': 14, 'completed': True},
        {'home': 'Team', 'away': 'Weak2', 'home_score': 28, 'away_score': 21, 'completed': True},
    ]
    
    stats = calculate_team_stats(teams_info, games)
    
    framework.assert_equal(len(stats['Team']['opponents']), 4, "Team played 4 opponents")
    
    strong1_pct = stats['Strong1']['win_pct']
    strong2_pct = stats['Strong2']['win_pct']
    weak1_pct = stats['Weak1']['win_pct']
    weak2_pct = stats['Weak2']['win_pct']
    expected_sos = (strong1_pct + strong2_pct + weak1_pct + weak2_pct) / 4
    
    framework.assert_almost_equal(stats['Team']['strength_of_schedule'], expected_sos, 3,
                                   "Team SOS should be average of all opponents")


def test_conference_points_tracking_mixed():
    """Test conference points are tracked only for conference games."""
    teams_info = {
        'NFC Team': {'division': 'NFC East', 'conference': 'NFC', 'logo_url': ''},
        'NFC Opp1': {'division': 'NFC West', 'conference': 'NFC', 'logo_url': ''},
        'NFC Opp2': {'division': 'NFC South', 'conference': 'NFC', 'logo_url': ''},
        'AFC Opp': {'division': 'AFC North', 'conference': 'AFC', 'logo_url': ''},
    }
    games = [
        {'home': 'NFC Team', 'away': 'NFC Opp1', 'home_score': 24, 'away_score': 20, 'completed': True},
        {'home': 'NFC Team', 'away': 'NFC Opp2', 'home_score': 31, 'away_score': 17, 'completed': True},
        {'home': 'NFC Team', 'away': 'AFC Opp', 'home_score': 28, 'away_score': 21, 'completed': True},
    ]
    
    stats = calculate_team_stats(teams_info, games)
    
    framework.assert_equal(stats['NFC Team']['points_for'], 83, "Total PF = 83")
    framework.assert_equal(stats['NFC Team']['points_against'], 58, "Total PA = 58")
    framework.assert_equal(stats['NFC Team']['conference_points_for'], 55, "Conference PF = 55 (24+31)")
    framework.assert_equal(stats['NFC Team']['conference_points_against'], 37, "Conference PA = 37 (20+17)")


def test_net_points_in_common_games():
    """Test net points calculation in common games."""
    teams_info = {
        'Team A': {'division': 'AFC West', 'conference': 'AFC', 'logo_url': ''},
        'Team B': {'division': 'AFC West', 'conference': 'AFC', 'logo_url': ''},
        'Opp1': {'division': 'AFC North', 'conference': 'AFC', 'logo_url': ''},
        'Opp2': {'division': 'AFC North', 'conference': 'AFC', 'logo_url': ''},
        'Opp3': {'division': 'AFC East', 'conference': 'AFC', 'logo_url': ''},
        'Opp4': {'division': 'AFC East', 'conference': 'AFC', 'logo_url': ''},
    }
    games = [
        {'home': 'Team A', 'away': 'Opp1', 'home_score': 28, 'away_score': 21, 'completed': True},
        {'home': 'Team A', 'away': 'Opp2', 'home_score': 24, 'away_score': 20, 'completed': True},
        {'home': 'Team A', 'away': 'Opp3', 'home_score': 31, 'away_score': 17, 'completed': True},
        {'home': 'Team A', 'away': 'Opp4', 'home_score': 21, 'away_score': 24, 'completed': True},
        {'home': 'Team B', 'away': 'Opp1', 'home_score': 24, 'away_score': 27, 'completed': True},
        {'home': 'Team B', 'away': 'Opp2', 'home_score': 27, 'away_score': 21, 'completed': True},
        {'home': 'Team B', 'away': 'Opp3', 'home_score': 20, 'away_score': 23, 'completed': True},
        {'home': 'Team B', 'away': 'Opp4', 'home_score': 28, 'away_score': 21, 'completed': True},
    ]
    
    stats = calculate_team_stats(teams_info, games)
    
    common_opponents = set(stats['Team A']['opponents']) & set(stats['Team B']['opponents'])
    
    team_a_net = sum(g['pf'] - g['pa'] for g in stats['Team A']['game_results'] 
                     if g['opponent'] in common_opponents)
    team_b_net = sum(g['pf'] - g['pa'] for g in stats['Team B']['game_results'] 
                     if g['opponent'] in common_opponents)
    
    framework.assert_equal(team_a_net, 22, "Team A net points in common games = +22")
    framework.assert_equal(team_b_net, 7, "Team B net points in common games = +7")


def test_net_points_all_games():
    """Test net points calculation in all games."""
    teams_info = {
        'Team': {'division': 'NFC East', 'conference': 'NFC', 'logo_url': ''},
        'Opp1': {'division': 'NFC West', 'conference': 'NFC', 'logo_url': ''},
        'Opp2': {'division': 'NFC South', 'conference': 'NFC', 'logo_url': ''},
        'Opp3': {'division': 'AFC North', 'conference': 'AFC', 'logo_url': ''},
    }
    games = [
        {'home': 'Team', 'away': 'Opp1', 'home_score': 28, 'away_score': 21, 'completed': True},
        {'home': 'Team', 'away': 'Opp2', 'home_score': 24, 'away_score': 20, 'completed': True},
        {'home': 'Team', 'away': 'Opp3', 'home_score': 17, 'away_score': 31, 'completed': True},
    ]
    
    stats = calculate_team_stats(teams_info, games)
    
    net_points = stats['Team']['points_for'] - stats['Team']['points_against']
    framework.assert_equal(net_points, -3, "Team net points = -3 (69-72)")
    framework.assert_equal(stats['Team']['points_for'], 69, "Team PF = 69")
    framework.assert_equal(stats['Team']['points_against'], 72, "Team PA = 72")


def test_net_touchdowns():
    """Test net touchdowns calculation."""
    teams_info = {
        'Team': {'division': 'AFC South', 'conference': 'AFC', 'logo_url': ''},
        'Opp1': {'division': 'AFC North', 'conference': 'AFC', 'logo_url': ''},
        'Opp2': {'division': 'AFC West', 'conference': 'AFC', 'logo_url': ''},
    }
    games = [
        {'home': 'Team', 'away': 'Opp1', 'home_score': 35, 'away_score': 28, 'completed': True},
        {'home': 'Team', 'away': 'Opp2', 'home_score': 42, 'away_score': 21, 'completed': True},
    ]
    
    stats = calculate_team_stats(teams_info, games)
    
    framework.assert_equal(stats['Team']['touchdowns'], 11, "Team TDs = 11 (35/7=5 + 42/7=6)")
    framework.assert_equal(stats['Opp1']['touchdowns'], 4, "Opp1 TDs = 4 (28/7)")
    framework.assert_equal(stats['Opp2']['touchdowns'], 3, "Opp2 TDs = 3 (21/7)")


def test_5team_division_scenario():
    """Test complex 5-team division scenario with mixed records."""
    teams_info = {
        'Team 1': {'division': 'AFC North', 'conference': 'AFC', 'logo_url': ''},
        'Team 2': {'division': 'AFC North', 'conference': 'AFC', 'logo_url': ''},
        'Team 3': {'division': 'AFC North', 'conference': 'AFC', 'logo_url': ''},
        'Team 4': {'division': 'AFC North', 'conference': 'AFC', 'logo_url': ''},
        'Out Conf': {'division': 'NFC South', 'conference': 'NFC', 'logo_url': ''},
    }
    games = [
        {'home': 'Team 1', 'away': 'Team 2', 'home_score': 24, 'away_score': 20, 'completed': True},
        {'home': 'Team 1', 'away': 'Team 3', 'home_score': 28, 'away_score': 21, 'completed': True},
        {'home': 'Team 2', 'away': 'Team 3', 'home_score': 21, 'away_score': 24, 'completed': True},
        {'home': 'Team 2', 'away': 'Team 4', 'home_score': 27, 'away_score': 24, 'completed': True},
        {'home': 'Team 3', 'away': 'Team 4', 'home_score': 31, 'away_score': 28, 'completed': True},
        {'home': 'Team 1', 'away': 'Out Conf', 'home_score': 35, 'away_score': 14, 'completed': True},
        {'home': 'Team 4', 'away': 'Out Conf', 'home_score': 17, 'away_score': 20, 'completed': True},
    ]
    
    stats = calculate_team_stats(teams_info, games)
    
    framework.assert_equal(stats['Team 1']['W'], 3, "Team 1 has 3 wins")
    framework.assert_equal(stats['Team 1']['division_W'], 2, "Team 1 has 2 division wins")
    framework.assert_equal(stats['Team 2']['W'], 1, "Team 2 has 1 win")
    framework.assert_equal(stats['Team 3']['W'], 2, "Team 3 has 2 wins")
    framework.assert_equal(stats['Team 3']['division_W'], 2, "Team 3 has 2 division wins")


def test_head_to_head_with_ties():
    """Test head-to-head tracking when games result in ties."""
    teams_info = {
        'Team A': {'division': 'NFC West', 'conference': 'NFC', 'logo_url': ''},
        'Team B': {'division': 'NFC West', 'conference': 'NFC', 'logo_url': ''},
    }
    games = [
        {'home': 'Team A', 'away': 'Team B', 'home_score': 24, 'away_score': 24, 'completed': True},
        {'home': 'Team B', 'away': 'Team A', 'home_score': 21, 'away_score': 21, 'completed': True},
    ]
    
    stats = calculate_team_stats(teams_info, games)
    
    framework.assert_equal(stats['Team A']['head_to_head']['Team B']['T'], 2, "Team A vs B has 2 ties")
    framework.assert_equal(stats['Team B']['head_to_head']['Team A']['T'], 2, "Team B vs A has 2 ties")
    framework.assert_equal(stats['Team A']['head_to_head']['Team B']['W'], 0, "Team A vs B has 0 wins")
    framework.assert_equal(stats['Team A']['head_to_head']['Team B']['L'], 0, "Team A vs B has 0 losses")


def test_conference_tie_in_division_game():
    """Test that division games also count as conference games for ties."""
    teams_info = {
        'Team A': {'division': 'AFC East', 'conference': 'AFC', 'logo_url': ''},
        'Team B': {'division': 'AFC East', 'conference': 'AFC', 'logo_url': ''},
    }
    games = [
        {'home': 'Team A', 'away': 'Team B', 'home_score': 20, 'away_score': 20, 'completed': True},
    ]
    
    stats = calculate_team_stats(teams_info, games)
    
    framework.assert_equal(stats['Team A']['T'], 1, "Team A has 1 tie overall")
    framework.assert_equal(stats['Team A']['conference_T'], 1, "Team A has 1 conference tie")
    framework.assert_equal(stats['Team B']['T'], 1, "Team B has 1 tie overall")
    framework.assert_equal(stats['Team B']['conference_T'], 1, "Team B has 1 conference tie")


def test_non_conference_game_no_conf_stats():
    """Test that non-conference games don't affect conference stats."""
    teams_info = {
        'AFC Team': {'division': 'AFC West', 'conference': 'AFC', 'logo_url': ''},
        'NFC Team': {'division': 'NFC East', 'conference': 'NFC', 'logo_url': ''},
    }
    games = [
        {'home': 'AFC Team', 'away': 'NFC Team', 'home_score': 28, 'away_score': 24, 'completed': True},
    ]
    
    stats = calculate_team_stats(teams_info, games)
    
    framework.assert_equal(stats['AFC Team']['W'], 1, "AFC Team has 1 win overall")
    framework.assert_equal(stats['AFC Team']['conference_W'], 0, "AFC Team has 0 conference wins")
    framework.assert_equal(stats['AFC Team']['conference_L'], 0, "AFC Team has 0 conference losses")
    framework.assert_equal(stats['AFC Team']['conference_points_for'], 0, "AFC Team conf PF = 0")
    framework.assert_equal(stats['NFC Team']['conference_W'], 0, "NFC Team has 0 conference wins")


def test_division_game_outside_conference():
    """Test that division games must be in same conference."""
    teams_info = {
        'Team A': {'division': 'AFC West', 'conference': 'AFC', 'logo_url': ''},
        'Team B': {'division': 'AFC West', 'conference': 'AFC', 'logo_url': ''},
        'Team C': {'division': 'Different', 'conference': 'AFC', 'logo_url': ''},
    }
    games = [
        {'home': 'Team A', 'away': 'Team B', 'home_score': 28, 'away_score': 24, 'completed': True},
        {'home': 'Team A', 'away': 'Team C', 'home_score': 31, 'away_score': 27, 'completed': True},
    ]
    
    stats = calculate_team_stats(teams_info, games)
    
    framework.assert_equal(stats['Team A']['division_W'], 1, "Team A has 1 division win (vs Team B)")
    framework.assert_equal(stats['Team A']['conference_W'], 2, "Team A has 2 conference wins")


def test_multiple_head_to_head_games():
    """Test head-to-head with multiple games between same teams."""
    teams_info = {
        'Cowboys': {'division': 'NFC East', 'conference': 'NFC', 'logo_url': ''},
        'Eagles': {'division': 'NFC East', 'conference': 'NFC', 'logo_url': ''},
    }
    games = [
        {'home': 'Cowboys', 'away': 'Eagles', 'home_score': 24, 'away_score': 20, 'completed': True},
        {'home': 'Eagles', 'away': 'Cowboys', 'home_score': 27, 'away_score': 24, 'completed': True},
        {'home': 'Cowboys', 'away': 'Eagles', 'home_score': 31, 'away_score': 28, 'completed': True},
    ]
    
    stats = calculate_team_stats(teams_info, games)
    
    framework.assert_equal(stats['Cowboys']['head_to_head']['Eagles']['W'], 2, "Cowboys 2 H2H wins")
    framework.assert_equal(stats['Cowboys']['head_to_head']['Eagles']['L'], 1, "Cowboys 1 H2H loss")
    framework.assert_equal(stats['Eagles']['head_to_head']['Cowboys']['W'], 1, "Eagles 1 H2H win")
    framework.assert_equal(stats['Eagles']['head_to_head']['Cowboys']['L'], 2, "Eagles 2 H2H losses")


def test_zero_opponents():
    """Test team with no completed games."""
    teams_info = {
        'Team A': {'division': 'AFC North', 'conference': 'AFC', 'logo_url': ''},
        'Team B': {'division': 'AFC North', 'conference': 'AFC', 'logo_url': ''},
    }
    games = []
    
    stats = calculate_team_stats(teams_info, games)
    
    framework.assert_equal(stats['Team A']['W'], 0, "Team A has 0 wins")
    framework.assert_equal(stats['Team A']['L'], 0, "Team A has 0 losses")
    framework.assert_equal(stats['Team A']['win_pct'], 0, "Team A win_pct = 0")
    framework.assert_equal(stats['Team A']['strength_of_victory'], 0, "Team A SOV = 0")
    framework.assert_equal(stats['Team A']['strength_of_schedule'], 0, "Team A SOS = 0")


def test_all_ties():
    """Test scenario where all games are ties."""
    teams_info = {
        'Team A': {'division': 'NFC South', 'conference': 'NFC', 'logo_url': ''},
        'Team B': {'division': 'NFC South', 'conference': 'NFC', 'logo_url': ''},
        'Team C': {'division': 'NFC South', 'conference': 'NFC', 'logo_url': ''},
    }
    games = [
        {'home': 'Team A', 'away': 'Team B', 'home_score': 20, 'away_score': 20, 'completed': True},
        {'home': 'Team B', 'away': 'Team C', 'home_score': 17, 'away_score': 17, 'completed': True},
        {'home': 'Team C', 'away': 'Team A', 'home_score': 24, 'away_score': 24, 'completed': True},
    ]
    
    stats = calculate_team_stats(teams_info, games)
    
    framework.assert_equal(stats['Team A']['W'], 0, "Team A has 0 wins")
    framework.assert_equal(stats['Team A']['L'], 0, "Team A has 0 losses")
    framework.assert_equal(stats['Team A']['T'], 2, "Team A has 2 ties")
    framework.assert_almost_equal(stats['Team A']['win_pct'], 0.5, 3, "Team A win_pct = 0.5")
    framework.assert_equal(len(stats['Team A']['defeated_opponents']), 0, "Team A defeated 0 opponents")


def test_game_results_structure():
    """Test that game_results contains correct structure."""
    teams_info = {
        'Home': {'division': 'AFC West', 'conference': 'AFC', 'logo_url': ''},
        'Away': {'division': 'AFC East', 'conference': 'AFC', 'logo_url': ''},
    }
    games = [
        {'home': 'Home', 'away': 'Away', 'home_score': 28, 'away_score': 24, 'completed': True},
    ]
    
    stats = calculate_team_stats(teams_info, games)
    
    framework.assert_equal(len(stats['Home']['game_results']), 1, "Home has 1 game result")
    framework.assert_equal(stats['Home']['game_results'][0]['opponent'], 'Away', "Opponent is Away")
    framework.assert_equal(stats['Home']['game_results'][0]['pf'], 28, "Home pf = 28")
    framework.assert_equal(stats['Home']['game_results'][0]['pa'], 24, "Home pa = 24")
    
    framework.assert_equal(len(stats['Away']['game_results']), 1, "Away has 1 game result")
    framework.assert_equal(stats['Away']['game_results'][0]['opponent'], 'Home', "Opponent is Home")
    framework.assert_equal(stats['Away']['game_results'][0]['pf'], 24, "Away pf = 24")
    framework.assert_equal(stats['Away']['game_results'][0]['pa'], 28, "Away pa = 28")


def test_defaultdict_head_to_head():
    """Test that head_to_head returns default dict for non-existent opponent."""
    teams_info = {
        'Team A': {'division': 'NFC East', 'conference': 'NFC', 'logo_url': ''},
        'Team B': {'division': 'NFC East', 'conference': 'NFC', 'logo_url': ''},
        'Team C': {'division': 'NFC East', 'conference': 'NFC', 'logo_url': ''},
    }
    games = [
        {'home': 'Team A', 'away': 'Team B', 'home_score': 24, 'away_score': 20, 'completed': True},
    ]
    
    stats = calculate_team_stats(teams_info, games)
    
    non_existent_h2h = stats['Team A']['head_to_head']['Team C']
    framework.assert_equal(non_existent_h2h['W'], 0, "Non-existent H2H should have W=0")
    framework.assert_equal(non_existent_h2h['L'], 0, "Non-existent H2H should have L=0")
    framework.assert_equal(non_existent_h2h['T'], 0, "Non-existent H2H should have T=0")


def test_high_scoring_games():
    """Test calculation with high-scoring games."""
    teams_info = {
        'Offense1': {'division': 'AFC South', 'conference': 'AFC', 'logo_url': ''},
        'Offense2': {'division': 'AFC South', 'conference': 'AFC', 'logo_url': ''},
    }
    games = [
        {'home': 'Offense1', 'away': 'Offense2', 'home_score': 52, 'away_score': 49, 'completed': True},
    ]
    
    stats = calculate_team_stats(teams_info, games)
    
    framework.assert_equal(stats['Offense1']['points_for'], 52, "Offense1 PF = 52")
    framework.assert_equal(stats['Offense1']['points_against'], 49, "Offense1 PA = 49")
    framework.assert_equal(stats['Offense1']['touchdowns'], 7, "Offense1 TDs = 7 (52/7)")
    framework.assert_equal(stats['Offense2']['touchdowns'], 7, "Offense2 TDs = 7 (49/7)")


def test_shutout_game():
    """Test calculation with shutout game (0 points)."""
    teams_info = {
        'Defense': {'division': 'NFC North', 'conference': 'NFC', 'logo_url': ''},
        'Offense': {'division': 'NFC North', 'conference': 'NFC', 'logo_url': ''},
    }
    games = [
        {'home': 'Defense', 'away': 'Offense', 'home_score': 21, 'away_score': 0, 'completed': True},
    ]
    
    stats = calculate_team_stats(teams_info, games)
    
    framework.assert_equal(stats['Defense']['points_for'], 21, "Defense PF = 21")
    framework.assert_equal(stats['Defense']['points_against'], 0, "Defense PA = 0")
    framework.assert_equal(stats['Offense']['points_for'], 0, "Offense PF = 0")
    framework.assert_equal(stats['Offense']['points_against'], 21, "Offense PA = 21")
    framework.assert_equal(stats['Offense']['touchdowns'], 0, "Offense TDs = 0")


def test_3team_same_record_all_h2h_tied():
    """Test 3 teams with identical 10-7 records, all 1-1 in H2H (no sweep)."""
    teams_info = {
        'Team A': {'division': 'AFC North', 'conference': 'AFC', 'logo_url': ''},
        'Team B': {'division': 'AFC North', 'conference': 'AFC', 'logo_url': ''},
        'Team C': {'division': 'AFC North', 'conference': 'AFC', 'logo_url': ''},
        'Opp1': {'division': 'AFC South', 'conference': 'AFC', 'logo_url': ''},
        'Opp2': {'division': 'AFC South', 'conference': 'AFC', 'logo_url': ''},
    }
    
    games = [
        {'home': 'Team A', 'away': 'Team B', 'home_score': 24, 'away_score': 20, 'completed': True},
        {'home': 'Team B', 'away': 'Team A', 'home_score': 27, 'away_score': 21, 'completed': True},
        {'home': 'Team B', 'away': 'Team C', 'home_score': 28, 'away_score': 24, 'completed': True},
        {'home': 'Team C', 'away': 'Team B', 'home_score': 31, 'away_score': 27, 'completed': True},
        {'home': 'Team A', 'away': 'Team C', 'home_score': 21, 'away_score': 17, 'completed': True},
        {'home': 'Team C', 'away': 'Team A', 'home_score': 24, 'away_score': 20, 'completed': True},
        {'home': 'Team A', 'away': 'Opp1', 'home_score': 35, 'away_score': 14, 'completed': True},
        {'home': 'Team B', 'away': 'Opp1', 'home_score': 28, 'away_score': 21, 'completed': True},
        {'home': 'Team C', 'away': 'Opp1', 'home_score': 31, 'away_score': 24, 'completed': True},
        {'home': 'Opp2', 'away': 'Team A', 'home_score': 17, 'away_score': 21, 'completed': True},
        {'home': 'Opp2', 'away': 'Team B', 'home_score': 14, 'away_score': 17, 'completed': True},
        {'home': 'Opp2', 'away': 'Team C', 'home_score': 20, 'away_score': 24, 'completed': True},
    ]
    
    stats = calculate_team_stats(teams_info, games)
    
    framework.assert_equal(stats['Team A']['W'], 4, "Team A: 4-2")
    framework.assert_equal(stats['Team A']['L'], 2, "Team A: 4-2")
    framework.assert_equal(stats['Team B']['W'], 4, "Team B: 4-2")
    framework.assert_equal(stats['Team B']['L'], 2, "Team B: 4-2")
    framework.assert_equal(stats['Team C']['W'], 4, "Team C: 4-2")
    framework.assert_equal(stats['Team C']['L'], 2, "Team C: 4-2")
    
    framework.assert_equal(stats['Team A']['head_to_head']['Team B']['W'], 1, "A vs B: 1-1")
    framework.assert_equal(stats['Team A']['head_to_head']['Team B']['L'], 1, "A vs B: 1-1")
    framework.assert_equal(stats['Team B']['head_to_head']['Team C']['W'], 1, "B vs C: 1-1")
    framework.assert_equal(stats['Team B']['head_to_head']['Team C']['L'], 1, "B vs C: 1-1")
    framework.assert_equal(stats['Team A']['head_to_head']['Team C']['W'], 1, "A vs C: 1-1")
    framework.assert_equal(stats['Team A']['head_to_head']['Team C']['L'], 1, "A vs C: 1-1")


def test_3team_same_record_division_pct_breaks_tie():
    """Test 3 teams same overall record, division record breaks tie."""
    teams_info = {
        'Team A': {'division': 'NFC East', 'conference': 'NFC', 'logo_url': ''},
        'Team B': {'division': 'NFC East', 'conference': 'NFC', 'logo_url': ''},
        'Team C': {'division': 'NFC East', 'conference': 'NFC', 'logo_url': ''},
        'Team D': {'division': 'NFC East', 'conference': 'NFC', 'logo_url': ''},
        'OutDiv': {'division': 'NFC West', 'conference': 'NFC', 'logo_url': ''},
    }
    
    games = [
        {'home': 'Team A', 'away': 'Team B', 'home_score': 24, 'away_score': 21, 'completed': True},
        {'home': 'Team B', 'away': 'Team A', 'home_score': 27, 'away_score': 24, 'completed': True},
        {'home': 'Team A', 'away': 'Team C', 'home_score': 28, 'away_score': 24, 'completed': True},
        {'home': 'Team C', 'away': 'Team A', 'home_score': 31, 'away_score': 28, 'completed': True},
        {'home': 'Team A', 'away': 'Team D', 'home_score': 35, 'away_score': 14, 'completed': True},
        {'home': 'Team A', 'away': 'Team D', 'home_score': 28, 'away_score': 21, 'completed': True},
        {'home': 'Team B', 'away': 'Team C', 'home_score': 21, 'away_score': 24, 'completed': True},
        {'home': 'Team C', 'away': 'Team B', 'home_score': 24, 'away_score': 27, 'completed': True},
        {'home': 'Team B', 'away': 'Team D', 'home_score': 31, 'away_score': 28, 'completed': True},
        {'home': 'Team D', 'away': 'Team B', 'home_score': 24, 'away_score': 21, 'completed': True},
        {'home': 'Team C', 'away': 'Team D', 'home_score': 28, 'away_score': 24, 'completed': True},
        {'home': 'Team D', 'away': 'Team C', 'home_score': 21, 'away_score': 24, 'completed': True},
        {'home': 'Team A', 'away': 'OutDiv', 'home_score': 14, 'away_score': 17, 'completed': True},
        {'home': 'Team B', 'away': 'OutDiv', 'home_score': 17, 'away_score': 20, 'completed': True},
        {'home': 'Team C', 'away': 'OutDiv', 'home_score': 20, 'away_score': 17, 'completed': True},
    ]
    
    stats = calculate_team_stats(teams_info, games)
    
    framework.assert_equal(stats['Team A']['W'], 4, "Team A: 4 wins")
    framework.assert_equal(stats['Team B']['W'], 3, "Team B: 3 wins")
    framework.assert_equal(stats['Team C']['W'], 4, "Team C: 4 wins")
    
    framework.assert_equal(stats['Team A']['division_W'], 4, "Team A: 4 div wins")
    framework.assert_equal(stats['Team A']['division_L'], 2, "Team A: 2 div losses")
    framework.assert_equal(stats['Team B']['division_W'], 2, "Team B: 2 div wins")
    framework.assert_equal(stats['Team B']['division_L'], 4, "Team B: 4 div losses")
    framework.assert_equal(stats['Team C']['division_W'], 3, "Team C: 3 div wins")
    framework.assert_equal(stats['Team C']['division_L'], 3, "Team C: 3 div losses")
    
    framework.assert_almost_equal(stats['Team A']['division_pct'], 0.667, 3, "Team A div_pct = .667")
    framework.assert_almost_equal(stats['Team B']['division_pct'], 0.333, 3, "Team B div_pct = .333")
    framework.assert_almost_equal(stats['Team C']['division_pct'], 0.500, 3, "Team C div_pct = .500")


def test_3team_same_record_conference_pct_breaks_tie():
    """Test 3 teams same record, conference record breaks tie."""
    teams_info = {
        'Team A': {'division': 'AFC West', 'conference': 'AFC', 'logo_url': ''},
        'Team B': {'division': 'AFC East', 'conference': 'AFC', 'logo_url': ''},
        'Team C': {'division': 'AFC South', 'conference': 'AFC', 'logo_url': ''},
        'AFCOpp1': {'division': 'AFC North', 'conference': 'AFC', 'logo_url': ''},
        'AFCOpp2': {'division': 'AFC North', 'conference': 'AFC', 'logo_url': ''},
        'AFCOpp3': {'division': 'AFC North', 'conference': 'AFC', 'logo_url': ''},
        'NFCOpp1': {'division': 'NFC East', 'conference': 'NFC', 'logo_url': ''},
        'NFCOpp2': {'division': 'NFC West', 'conference': 'NFC', 'logo_url': ''},
    }
    
    games = [
        {'home': 'Team A', 'away': 'AFCOpp1', 'home_score': 28, 'away_score': 24, 'completed': True},
        {'home': 'Team A', 'away': 'AFCOpp2', 'home_score': 31, 'away_score': 27, 'completed': True},
        {'home': 'Team A', 'away': 'AFCOpp3', 'home_score': 21, 'away_score': 24, 'completed': True},
        {'home': 'Team A', 'away': 'NFCOpp1', 'home_score': 24, 'away_score': 20, 'completed': True},
        {'home': 'Team A', 'away': 'NFCOpp2', 'home_score': 27, 'away_score': 24, 'completed': True},
        {'home': 'Team B', 'away': 'AFCOpp1', 'home_score': 21, 'away_score': 24, 'completed': True},
        {'home': 'Team B', 'away': 'AFCOpp2', 'home_score': 28, 'away_score': 24, 'completed': True},
        {'home': 'Team B', 'away': 'AFCOpp3', 'home_score': 17, 'away_score': 20, 'completed': True},
        {'home': 'Team B', 'away': 'NFCOpp1', 'home_score': 35, 'away_score': 14, 'completed': True},
        {'home': 'Team B', 'away': 'NFCOpp2', 'home_score': 31, 'away_score': 21, 'completed': True},
        {'home': 'Team C', 'away': 'AFCOpp1', 'home_score': 24, 'away_score': 27, 'completed': True},
        {'home': 'Team C', 'away': 'AFCOpp2', 'home_score': 21, 'away_score': 24, 'completed': True},
        {'home': 'Team C', 'away': 'AFCOpp3', 'home_score': 17, 'away_score': 20, 'completed': True},
        {'home': 'Team C', 'away': 'NFCOpp1', 'home_score': 42, 'away_score': 21, 'completed': True},
        {'home': 'Team C', 'away': 'NFCOpp2', 'home_score': 35, 'away_score': 28, 'completed': True},
    ]
    
    stats = calculate_team_stats(teams_info, games)
    
    framework.assert_equal(stats['Team A']['W'], 4, "Team A: 4 wins")
    framework.assert_equal(stats['Team B']['W'], 3, "Team B: 3 wins")
    framework.assert_equal(stats['Team C']['W'], 2, "Team C: 2 wins")
    
    framework.assert_equal(stats['Team A']['conference_W'], 2, "Team A: 2 conf wins")
    framework.assert_equal(stats['Team A']['conference_L'], 1, "Team A: 1 conf loss")
    framework.assert_equal(stats['Team B']['conference_W'], 1, "Team B: 1 conf win")
    framework.assert_equal(stats['Team B']['conference_L'], 2, "Team B: 2 conf losses")
    framework.assert_equal(stats['Team C']['conference_W'], 0, "Team C: 0 conf wins")
    framework.assert_equal(stats['Team C']['conference_L'], 3, "Team C: 3 conf losses")
    
    framework.assert_almost_equal(stats['Team A']['conference_pct'], 0.667, 3, "Team A conf_pct = .667")
    framework.assert_almost_equal(stats['Team B']['conference_pct'], 0.333, 3, "Team B conf_pct = .333")
    framework.assert_almost_equal(stats['Team C']['conference_pct'], 0.000, 3, "Team C conf_pct = 0")


def test_4team_same_record_gradual_elimination():
    """Test 4 teams with same record, eliminated one by one through tiebreakers."""
    teams_info = {
        'Team 1': {'division': 'NFC North', 'conference': 'NFC', 'logo_url': ''},
        'Team 2': {'division': 'NFC North', 'conference': 'NFC', 'logo_url': ''},
        'Team 3': {'division': 'NFC North', 'conference': 'NFC', 'logo_url': ''},
        'Team 4': {'division': 'NFC North', 'conference': 'NFC', 'logo_url': ''},
        'Opp A': {'division': 'NFC South', 'conference': 'NFC', 'logo_url': ''},
        'Opp B': {'division': 'NFC South', 'conference': 'NFC', 'logo_url': ''},
    }
    
    games = [
        {'home': 'Team 1', 'away': 'Team 2', 'home_score': 24, 'away_score': 21, 'completed': True},
        {'home': 'Team 2', 'away': 'Team 3', 'home_score': 27, 'away_score': 24, 'completed': True},
        {'home': 'Team 3', 'away': 'Team 4', 'home_score': 28, 'away_score': 24, 'completed': True},
        {'home': 'Team 4', 'away': 'Team 1', 'home_score': 31, 'away_score': 28, 'completed': True},
        {'home': 'Team 1', 'away': 'Team 3', 'home_score': 21, 'away_score': 24, 'completed': True},
        {'home': 'Team 2', 'away': 'Team 4', 'home_score': 28, 'away_score': 31, 'completed': True},
        {'home': 'Team 1', 'away': 'Opp A', 'home_score': 35, 'away_score': 28, 'completed': True},
        {'home': 'Team 2', 'away': 'Opp A', 'home_score': 24, 'away_score': 27, 'completed': True},
        {'home': 'Team 3', 'away': 'Opp A', 'home_score': 28, 'away_score': 31, 'completed': True},
        {'home': 'Team 4', 'away': 'Opp A', 'home_score': 31, 'away_score': 21, 'completed': True},
        {'home': 'Team 1', 'away': 'Opp B', 'home_score': 21, 'away_score': 17, 'completed': True},
        {'home': 'Team 2', 'away': 'Opp B', 'home_score': 28, 'away_score': 24, 'completed': True},
        {'home': 'Team 3', 'away': 'Opp B', 'home_score': 24, 'away_score': 21, 'completed': True},
        {'home': 'Team 4', 'away': 'Opp B', 'home_score': 27, 'away_score': 24, 'completed': True},
    ]
    
    stats = calculate_team_stats(teams_info, games)
    
    framework.assert_equal(stats['Team 1']['W'], 4, "Team 1: 4 wins")
    framework.assert_equal(stats['Team 1']['L'], 2, "Team 1: 2 losses")
    framework.assert_equal(stats['Team 2']['W'], 3, "Team 2: 3 wins")
    framework.assert_equal(stats['Team 2']['L'], 3, "Team 2: 3 losses")
    framework.assert_equal(stats['Team 3']['W'], 4, "Team 3: 4 wins")
    framework.assert_equal(stats['Team 3']['L'], 2, "Team 3: 2 losses")
    framework.assert_equal(stats['Team 4']['W'], 4, "Team 4: 4 wins")
    framework.assert_equal(stats['Team 4']['L'], 2, "Team 4: 2 losses")
    
    framework.assert_equal(stats['Team 1']['division_W'], 2, "Team 1: 2 div wins")
    framework.assert_equal(stats['Team 2']['division_W'], 1, "Team 2: 1 div win")
    framework.assert_equal(stats['Team 3']['division_W'], 2, "Team 3: 2 div wins")
    framework.assert_equal(stats['Team 4']['division_W'], 2, "Team 4: 2 div wins")


def test_wildcard_net_points_conference_only():
    """Test wild card tiebreaker uses conference points, not common game points."""
    teams_info = {
        'WC Team A': {'division': 'AFC West', 'conference': 'AFC', 'logo_url': ''},
        'WC Team B': {'division': 'AFC East', 'conference': 'AFC', 'logo_url': ''},
        'AFCOpp1': {'division': 'AFC North', 'conference': 'AFC', 'logo_url': ''},
        'AFCOpp2': {'division': 'AFC South', 'conference': 'AFC', 'logo_url': ''},
        'NFCOpp1': {'division': 'NFC East', 'conference': 'NFC', 'logo_url': ''},
        'NFCOpp2': {'division': 'NFC West', 'conference': 'NFC', 'logo_url': ''},
    }
    
    games = [
        {'home': 'WC Team A', 'away': 'AFCOpp1', 'home_score': 42, 'away_score': 35, 'completed': True},
        {'home': 'WC Team A', 'away': 'AFCOpp2', 'home_score': 38, 'away_score': 31, 'completed': True},
        {'home': 'WC Team A', 'away': 'NFCOpp1', 'home_score': 14, 'away_score': 10, 'completed': True},
        {'home': 'WC Team A', 'away': 'NFCOpp2', 'home_score': 17, 'away_score': 13, 'completed': True},
        {'home': 'WC Team B', 'away': 'AFCOpp1', 'home_score': 24, 'away_score': 21, 'completed': True},
        {'home': 'WC Team B', 'away': 'AFCOpp2', 'home_score': 27, 'away_score': 24, 'completed': True},
        {'home': 'WC Team B', 'away': 'NFCOpp1', 'home_score': 45, 'away_score': 14, 'completed': True},
        {'home': 'WC Team B', 'away': 'NFCOpp2', 'home_score': 38, 'away_score': 10, 'completed': True},
    ]
    
    stats = calculate_team_stats(teams_info, games)
    
    framework.assert_equal(stats['WC Team A']['conference_points_for'], 80, "WC A conf PF = 80")
    framework.assert_equal(stats['WC Team A']['conference_points_against'], 66, "WC A conf PA = 66")
    framework.assert_equal(stats['WC Team B']['conference_points_for'], 51, "WC B conf PF = 51")
    framework.assert_equal(stats['WC Team B']['conference_points_against'], 45, "WC B conf PA = 45")
    
    wc_a_conf_net = stats['WC Team A']['conference_points_for'] - stats['WC Team A']['conference_points_against']
    wc_b_conf_net = stats['WC Team B']['conference_points_for'] - stats['WC Team B']['conference_points_against']
    
    framework.assert_equal(wc_a_conf_net, 14, "WC A conference net = +14")
    framework.assert_equal(wc_b_conf_net, 6, "WC B conference net = +6")
    
    wc_a_total_net = stats['WC Team A']['points_for'] - stats['WC Team A']['points_against']
    wc_b_total_net = stats['WC Team B']['points_for'] - stats['WC Team B']['points_against']
    
    framework.assert_equal(wc_a_total_net, 22, "WC A total net = +22")
    framework.assert_equal(wc_b_total_net, 65, "WC B total net = +65")


def test_3team_with_tie_games_in_h2h():
    """Test 3 teams where tie games exist in head-to-head matchups."""
    teams_info = {
        'Team X': {'division': 'NFC South', 'conference': 'NFC', 'logo_url': ''},
        'Team Y': {'division': 'NFC South', 'conference': 'NFC', 'logo_url': ''},
        'Team Z': {'division': 'NFC South', 'conference': 'NFC', 'logo_url': ''},
        'Other': {'division': 'NFC West', 'conference': 'NFC', 'logo_url': ''},
    }
    
    games = [
        {'home': 'Team X', 'away': 'Team Y', 'home_score': 24, 'away_score': 24, 'completed': True},
        {'home': 'Team Y', 'away': 'Team X', 'home_score': 27, 'away_score': 24, 'completed': True},
        {'home': 'Team Y', 'away': 'Team Z', 'home_score': 20, 'away_score': 20, 'completed': True},
        {'home': 'Team Z', 'away': 'Team Y', 'home_score': 21, 'away_score': 17, 'completed': True},
        {'home': 'Team X', 'away': 'Team Z', 'home_score': 28, 'away_score': 21, 'completed': True},
        {'home': 'Team Z', 'away': 'Team X', 'home_score': 24, 'away_score': 24, 'completed': True},
        {'home': 'Team X', 'away': 'Other', 'home_score': 31, 'away_score': 27, 'completed': True},
        {'home': 'Team Y', 'away': 'Other', 'home_score': 28, 'away_score': 24, 'completed': True},
        {'home': 'Team Z', 'away': 'Other', 'home_score': 24, 'away_score': 21, 'completed': True},
    ]
    
    stats = calculate_team_stats(teams_info, games)
    
    framework.assert_equal(stats['Team X']['W'], 2, "Team X: 2 wins")
    framework.assert_equal(stats['Team X']['L'], 1, "Team X: 1 loss")
    framework.assert_equal(stats['Team X']['T'], 2, "Team X: 2 ties")
    framework.assert_equal(stats['Team Y']['W'], 2, "Team Y: 2 wins")
    framework.assert_equal(stats['Team Y']['L'], 1, "Team Y: 1 loss")
    framework.assert_equal(stats['Team Y']['T'], 1, "Team Y: 1 tie")
    framework.assert_equal(stats['Team Z']['W'], 2, "Team Z: 2 wins")
    framework.assert_equal(stats['Team Z']['L'], 1, "Team Z: 1 loss")
    framework.assert_equal(stats['Team Z']['T'], 2, "Team Z: 2 ties")
    
    framework.assert_equal(stats['Team X']['head_to_head']['Team Y']['T'], 1, "X vs Y: 1 tie")
    framework.assert_equal(stats['Team X']['head_to_head']['Team Z']['T'], 1, "X vs Z: 1 tie")
    framework.assert_equal(stats['Team Y']['head_to_head']['Team Z']['T'], 1, "Y vs Z: 1 tie")


def test_common_games_exactly_4_vs_more():
    """Test teams with exactly 4 common opponents vs teams with more."""
    teams_info = {
        'Team 1': {'division': 'AFC North', 'conference': 'AFC', 'logo_url': ''},
        'Team 2': {'division': 'AFC North', 'conference': 'AFC', 'logo_url': ''},
        'Common1': {'division': 'AFC South', 'conference': 'AFC', 'logo_url': ''},
        'Common2': {'division': 'AFC South', 'conference': 'AFC', 'logo_url': ''},
        'Common3': {'division': 'AFC East', 'conference': 'AFC', 'logo_url': ''},
        'Common4': {'division': 'AFC East', 'conference': 'AFC', 'logo_url': ''},
        'Common5': {'division': 'AFC West', 'conference': 'AFC', 'logo_url': ''},
    }
    
    games = [
        {'home': 'Team 1', 'away': 'Common1', 'home_score': 28, 'away_score': 21, 'completed': True},
        {'home': 'Team 1', 'away': 'Common2', 'home_score': 31, 'away_score': 24, 'completed': True},
        {'home': 'Team 1', 'away': 'Common3', 'home_score': 24, 'away_score': 27, 'completed': True},
        {'home': 'Team 1', 'away': 'Common4', 'home_score': 35, 'away_score': 28, 'completed': True},
        {'home': 'Team 1', 'away': 'Common5', 'home_score': 28, 'away_score': 24, 'completed': True},
        {'home': 'Team 2', 'away': 'Common1', 'home_score': 24, 'away_score': 27, 'completed': True},
        {'home': 'Team 2', 'away': 'Common2', 'home_score': 27, 'away_score': 24, 'completed': True},
        {'home': 'Team 2', 'away': 'Common3', 'home_score': 21, 'away_score': 24, 'completed': True},
        {'home': 'Team 2', 'away': 'Common4', 'home_score': 31, 'away_score': 28, 'completed': True},
        {'home': 'Team 2', 'away': 'Common5', 'home_score': 24, 'away_score': 21, 'completed': True},
    ]
    
    stats = calculate_team_stats(teams_info, games)
    
    common_opponents = set(stats['Team 1']['opponents']) & set(stats['Team 2']['opponents'])
    framework.assert_equal(len(common_opponents), 5, "Should have 5 common opponents")
    
    team1_common_wins = sum(1 for g in stats['Team 1']['game_results'] 
                            if g['opponent'] in common_opponents and g['pf'] > g['pa'])
    team2_common_wins = sum(1 for g in stats['Team 2']['game_results'] 
                            if g['opponent'] in common_opponents and g['pf'] > g['pa'])
    
    framework.assert_equal(team1_common_wins, 4, "Team 1: 4-1 in common games")
    framework.assert_equal(team2_common_wins, 3, "Team 2: 3-2 in common games")


if __name__ == '__main__':
    framework = TestFramework()
    
    print("="*60)
    print("COMPREHENSIVE WEEK18 SIMULATOR TESTS")
    print("Testing calculate_team_stats() with complex scenarios")
    print("="*60 + "\n")
    
    print("HEAD-TO-HEAD SCENARIOS")
    print("-"*60)
    framework.run_test("2-team head-to-head sweep", test_2team_head_to_head_sweep)
    framework.run_test("2-team head-to-head split", test_2team_head_to_head_split)
    framework.run_test("3-team head-to-head sweep", test_3team_head_to_head_sweep)
    framework.run_test("3-team circular head-to-head", test_3team_circular_head_to_head)
    framework.run_test("Multiple H2H games", test_multiple_head_to_head_games)
    framework.run_test("Head-to-head with ties", test_head_to_head_with_ties)
    print()
    
    print("3+ TEAMS SAME RECORD (CRITICAL)")
    print("-"*60)
    framework.run_test("3-team same record all H2H tied", test_3team_same_record_all_h2h_tied)
    framework.run_test("3-team division % breaks tie", test_3team_same_record_division_pct_breaks_tie)
    framework.run_test("3-team conference % breaks tie", test_3team_same_record_conference_pct_breaks_tie)
    framework.run_test("4-team gradual elimination", test_4team_same_record_gradual_elimination)
    framework.run_test("3-team with tie games in H2H", test_3team_with_tie_games_in_h2h)
    print()
    
    print("DIVISION & CONFERENCE RECORDS")
    print("-"*60)
    framework.run_test("4-team complex division records", test_4team_complex_division_records)
    framework.run_test("5-team division scenario", test_5team_division_scenario)
    framework.run_test("Conference tie in division game", test_conference_tie_in_division_game)
    framework.run_test("Non-conference game stats", test_non_conference_game_no_conf_stats)
    framework.run_test("Division game validation", test_division_game_outside_conference)
    print()
    
    print("COMMON GAMES")
    print("-"*60)
    framework.run_test("Common games with 4 opponents", test_common_games_4_opponents)
    framework.run_test("Common games with less than 4", test_common_games_less_than_4)
    framework.run_test("Common games exactly 4 vs more", test_common_games_exactly_4_vs_more)
    print()
    
    print("STRENGTH METRICS")
    print("-"*60)
    framework.run_test("Strength of victory complex", test_strength_of_victory_complex)
    framework.run_test("Strength of schedule complex", test_strength_of_schedule_complex)
    print()
    
    print("POINTS & SCORING")
    print("-"*60)
    framework.run_test("Conference points tracking mixed", test_conference_points_tracking_mixed)
    framework.run_test("Net points in common games", test_net_points_in_common_games)
    framework.run_test("Net points in all games", test_net_points_all_games)
    framework.run_test("Net touchdowns", test_net_touchdowns)
    framework.run_test("High scoring games", test_high_scoring_games)
    framework.run_test("Shutout game", test_shutout_game)
    print()
    
    print("WILD CARD SPECIFIC")
    print("-"*60)
    framework.run_test("WC net points conference only", test_wildcard_net_points_conference_only)
    print()
    
    print("EDGE CASES")
    print("-"*60)
    framework.run_test("Team with zero opponents", test_zero_opponents)
    framework.run_test("All games are ties", test_all_ties)
    framework.run_test("Game results structure", test_game_results_structure)
    framework.run_test("DefaultDict head-to-head", test_defaultdict_head_to_head)
    print()
    
    framework.print_summary()
