import random
import unittest
from collections import Counter

from mega.standings.postseason import superbowl_appearance_probabilities, simulate_conference_champions


class PostseasonTests(unittest.TestCase):
    def setUp(self):
        self.fields = {conf: [f'{conf}{i}' for i in range(1, 8)] for conf in ('AFC', 'NFC')}
        self.ratings = {team: 1000 for field in self.fields.values() for team in field}
        self.probability = lambda home, away, neutral=False: 0.5

    def test_bracket_reseeding_stops_at_conference_finals(self):
        calls = []
        def probability(home, away, *, neutral=False):
            calls.append((home, away, neutral))
            return 0 if (home, away) == ('AFC2', 'AFC7') else 1
        result = simulate_conference_champions(self.fields, probability, random.Random(0))
        self.assertEqual(calls[:6], [('AFC2', 'AFC7', False),
                                    ('AFC3', 'AFC6', False),
                                    ('AFC4', 'AFC5', False),
                                    ('AFC1', 'AFC7', False),
                                    ('AFC3', 'AFC4', False),
                                    ('AFC1', 'AFC3', False)])
        self.assertEqual(len(calls), 12)
        self.assertEqual(result, {'AFC': 'AFC1', 'NFC': 'NFC1'})
        self.assertFalse(any(neutral for _, _, neutral in calls))

    def test_shared_counts_repeatable_and_sum_to_100_per_conference(self):
        teams = list(self.ratings) + ['eliminated']
        def run():
            return superbowl_appearance_probabilities(teams, lambda: self.fields, self.probability,
                                              random.Random(0), simulations=20000)
        result = run()
        self.assertEqual(result, run())
        self.assertAlmostEqual(sum(result.values()), 200)
        for field in self.fields.values():
            self.assertAlmostEqual(sum(result[team] for team in field), 100)
        self.assertEqual(result['eliminated'], 0)
        self.assertGreater(result['AFC1'], result['AFC5'])
        self.assertGreater(result['NFC1'], result['NFC5'])

    def test_bye_follows_drawn_seed_instead_of_probability_threshold(self):
        rng = random.Random(1)
        counts = Counter()
        for i in range(20000):
            fields = {c: list(f) for c, f in self.fields.items()}
            # Two equally strong teams exchange seeds 1/5 equally often.
            if i % 2:
                fields['AFC'][0], fields['AFC'][4] = fields['AFC'][4], fields['AFC'][0]
            counts.update(simulate_conference_champions(fields, self.probability, rng).values())
        self.assertLess(abs(counts['AFC1']-counts['AFC5']) / 20000, 0.015)

    def test_standings_return_ordered_seeds(self):
        from scripts.calc_playoff_probabilities import determine_playoff_teams
        from mega.standings.records import calculate_team_stats
        teams = {f'{conf}{i}': {'conference': conf, 'division': f'{conf}{i // 2}'}
                 for conf in ('AFC', 'NFC') for i in range(8)}
        stats = calculate_team_stats(teams, [])
        for conf in ('AFC', 'NFC'):
            for i, wins in enumerate((10, 9, 12, 8, 14, 7, 16, 6)):
                stats[f'{conf}{i}']['W'] = wins
                stats[f'{conf}{i}']['L'] = 17 - wins
        fields, divisions, byes = determine_playoff_teams(teams, stats, [])
        for conf in ('AFC', 'NFC'):
            self.assertEqual(fields[conf], [f'{conf}{i}' for i in (6, 4, 2, 0, 1, 3, 5)])
            self.assertEqual(byes[conf], fields[conf][:1])
            self.assertEqual(set(divisions[conf]), set(fields[conf][:4]))

    def test_invalid_fields_fail(self):
        with self.assertRaises(ValueError):
            simulate_conference_champions({'AFC': self.fields['AFC']}, self.probability, random.Random(0))
