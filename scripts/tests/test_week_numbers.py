#!/usr/bin/env python3
import os
import sys
import unittest


SCRIPTS_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

from team_scenario_report import calculate_game_probabilities  # noqa: E402


class WeekNumberTests(unittest.TestCase):
    def test_remaining_games_use_one_based_weeks(self):
        team_name = "Cowboys"
        opponent_name = "Eagles"

        teams_info = {
            team_name: {"past_sos": 0.5},
            opponent_name: {"past_sos": 0.5},
        }
        stats = {
            team_name: {"win_pct": 0.6},
            opponent_name: {"win_pct": 0.4},
        }
        remaining_games = [
            {
                "home": team_name,
                "away": opponent_name,
                "week": 14,
                "completed": False,
            }
        ]

        game_probs = calculate_game_probabilities(
            team_name, teams_info, stats, remaining_games
        )

        self.assertEqual(len(game_probs), 1)
        self.assertEqual(
            game_probs[0]["week"],
            15,
            "Expected display week to be 1-based (weekIndex + 1)",
        )


if __name__ == "__main__":
    unittest.main()

