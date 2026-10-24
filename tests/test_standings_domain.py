"""Parity contracts for the shared completed-game standings calculation."""

import unittest

from scripts.standings_domain import calculate_team_stats


TEAMS = {
    "A": {"conference": "AFC", "division": "East"},
    "B": {"conference": "AFC", "division": "East"},
    "C": {"conference": "AFC", "division": "West"},
    "D": {"conference": "NFC", "division": "East"},
}

GAMES = [
    {"home": "A", "away": "B", "home_score": 21, "away_score": 14, "completed": True},
    {"home": "B", "away": "C", "home_score": 10, "away_score": 10, "completed": True},
    {"home": "C", "away": "D", "home_score": 7, "away_score": 14, "completed": True},
    {"home": "A", "away": "D", "home_score": 17, "away_score": 7, "completed": True},
    {"home": "A", "away": "C", "home_score": 99, "away_score": 0, "completed": False},
    {"home": "missing", "away": "A", "home_score": 3, "away_score": 0, "completed": True},
]


class StandingsDomainTests(unittest.TestCase):
    def test_completed_results_keep_records_ties_and_strength_metrics(self):
        stats = calculate_team_stats(TEAMS, GAMES)

        self.assertEqual((stats["A"]["W"], stats["A"]["L"], stats["A"]["T"]), (2, 0, 0))
        self.assertEqual((stats["B"]["W"], stats["B"]["L"], stats["B"]["T"]), (0, 1, 1))
        self.assertEqual((stats["C"]["W"], stats["C"]["L"], stats["C"]["T"]), (0, 1, 1))
        self.assertEqual((stats["D"]["W"], stats["D"]["L"], stats["D"]["T"]), (1, 1, 0))
        self.assertEqual(stats["A"]["head_to_head"]["B"], {"W": 1, "L": 0, "T": 0})
        self.assertEqual((stats["B"]["conference_L"], stats["B"]["conference_T"]), (1, 1))
        self.assertEqual((stats["A"]["division_W"], stats["A"]["division_L"]), (2, 0))
        self.assertEqual(stats["A"]["points_for"], 38)
        self.assertEqual(stats["A"]["points_against"], 21)
        self.assertEqual(stats["A"]["strength_of_victory"], 0.375)
        self.assertEqual(stats["A"]["strength_of_schedule"], 0.375)
        self.assertNotIn("game_results", stats["A"])
        self.assertNotIn("touchdowns", stats["A"])

    def test_week18_optional_tiebreaker_details_are_added_without_changing_core_records(self):
        base = calculate_team_stats(TEAMS, GAMES)
        extended = calculate_team_stats(
            TEAMS, GAMES, include_game_results=True, include_touchdowns=True
        )

        for team in TEAMS:
            for key, value in base[team].items():
                self.assertEqual(extended[team][key], value)
        self.assertEqual(extended["A"]["game_results"], [
            {"opponent": "B", "pf": 21, "pa": 14},
            {"opponent": "D", "pf": 17, "pa": 7},
        ])
        self.assertEqual(extended["A"]["touchdowns"], 5)
        self.assertEqual(extended["B"]["touchdowns"], 3)


if __name__ == "__main__":
    unittest.main()
