import unittest
from unittest.mock import patch

from mega.standings.match_probability import win_probability
from scripts.calc_playoff_probabilities import simulate_remaining_games


class MatchProbabilityTests(unittest.TestCase):
    def setUp(self):
        self.teams = {'A': {'past_sos': 0.6}, 'B': {'past_sos': 0.4}}
        self.stats = {'A': {'win_pct': 0.8}, 'B': {'win_pct': 0.2}}

    def test_known_probability_and_symmetry(self):
        p = win_probability('A', 'B', self.teams, self.stats)
        self.assertAlmostEqual(p, 0.74)
        self.assertAlmostEqual(p + win_probability('B', 'A', self.teams, self.stats), 1)
        self.assertEqual(p, win_probability('A', 'B', self.teams, self.stats, neutral=True))

    def test_force_win_performance_takes_precedence(self):
        self.teams['A']['performance_stats'] = {'win_pct': 0.2}
        self.assertAlmostEqual(win_probability('A', 'B', self.teams, self.stats), 0.32/0.58)

    def test_empty_records_and_caps(self):
        teams = {'A': {'past_sos': 0}, 'B': {'past_sos': 0}}
        stats = {'A': {'win_pct': 0}, 'B': {'win_pct': 0}}
        self.assertEqual(win_probability('A', 'B', teams, stats), 0.5)
        stats['A']['win_pct'] = 1
        self.assertEqual(win_probability('A', 'B', teams, stats), 0.75)
        self.assertEqual(win_probability('B', 'A', teams, stats), 0.25)

    def test_regular_season_uses_shared_probability(self):
        game = {'home': 'A', 'away': 'B', 'completed': False}
        # 0.7 is below shared p(A)=0.74. Reverse the conditional
        # probability using a mock to verify the caller consumes it.
        with patch('scripts.calc_playoff_probabilities.random.random', return_value=0.7):
            self.assertEqual(simulate_remaining_games(self.teams, self.stats, {}, [game], {})[0]['winner'], 'A')
            with patch('scripts.calc_playoff_probabilities.win_probability', return_value=0.6):
                self.assertEqual(simulate_remaining_games(self.teams, self.stats, {}, [game], {})[0]['winner'], 'B')

    def test_scenario_display_uses_shared_probability(self):
        # Compatibility script imports sibling modules from scripts/.
        import sys
        from pathlib import Path
        with patch.object(sys, 'path', [str(Path(__file__).resolve().parents[1] / 'scripts')] + sys.path):
            from scripts.team_scenario_report import calculate_game_probabilities
        game = {'home': 'A', 'away': 'B', 'completed': False, 'week': 0}
        self.teams['A']['performance_stats'] = {'win_pct': 0.2}
        p = win_probability('A', 'B', self.teams, self.stats)
        row = calculate_game_probabilities('A', self.teams, self.stats, [game])[0]
        self.assertAlmostEqual(row['win_prob'] / (row['win_prob'] + row['loss_prob']), p)
        self.assertAlmostEqual(row['win_prob'] + row['tie_prob'] + row['loss_prob'], 100)


class PostseasonVenueTests(unittest.TestCase):
    def test_equal_teams_home_bonus_and_neutral(self):
        from mega.standings.match_probability import postseason_win_probability
        teams = {t: {'past_sos': 0.5} for t in ('A', 'B')}
        stats = {t: {'win_pct': 0.5} for t in teams}
        p = postseason_win_probability('A', 'B', teams, stats)
        self.assertAlmostEqual(p, 1 / (1 + 10 ** (-75/400)))
        self.assertEqual(postseason_win_probability('A', 'B', teams, stats, neutral=True), 0.5)
        stats['A']['win_pct'] = 1
        stats['B']['win_pct'] = 0
        self.assertEqual(postseason_win_probability('A', 'B', teams, stats), 0.75)
