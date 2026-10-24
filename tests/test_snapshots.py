"""Isolated contract tests for the former snapshot harness.

Importing this module only defines tests. Pipeline functions write into a
temporary fixture directory so test discovery never changes production data.
"""

from __future__ import annotations

import csv
import json
import random
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIXTURE_ROOT = ROOT / "tests" / "fixtures" / "refactor"
sys.path.insert(0, str(ROOT / "stats_scripts"))
sys.path.insert(0, str(ROOT / "scripts"))

from stats_common import load_csv  # noqa: E402
from build_player_team_stints import build_player_team_stints  # noqa: E402
from calc_sos_elo import read_games  # noqa: E402
import calc_playoff_probabilities as playoff  # noqa: E402


class InputContractTests(unittest.TestCase):
    def test_missing_and_malformed_csvs_are_errors_but_header_only_is_valid(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            with self.assertRaises(FileNotFoundError):
                load_csv(root / "missing.csv")

            header_only = root / "empty.csv"
            header_only.write_text("id,seasonIndex\n", encoding="utf-8")
            self.assertEqual(load_csv(header_only), [])

            no_header = root / "no-header.csv"
            no_header.write_text("", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "no header"):
                load_csv(no_header)

            extra_fields = root / "extra-fields.csv"
            extra_fields.write_text("a,b\n1,2,3\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "more fields"):
                load_csv(extra_fields)

            missing_fields = root / "missing-fields.csv"
            missing_fields.write_text("a,b\n1\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "fewer fields"):
                load_csv(missing_fields)

    def test_header_only_empty_trades_export_is_valid(self):
        self.assertEqual(load_csv(FIXTURE_ROOT / "empty_trades.csv"), [])


class TradeAwareStintTests(unittest.TestCase):
    def test_traded_player_has_separate_team_stints_and_reconciled_totals(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            for source, name in (
                ("teams.csv", "MEGA_teams.csv"),
                ("passing.csv", "MEGA_passing.csv"),
                ("rushing.csv", "MEGA_rushing.csv"),
                ("receiving.csv", "MEGA_receiving.csv"),
                ("defense.csv", "MEGA_defense.csv"),
                ("punting.csv", "MEGA_punting.csv"),
                ("kicking.csv", "MEGA_kicking.csv"),
            ):
                shutil.copyfile(FIXTURE_ROOT / source, root / name)

            build_player_team_stints(root)
            with (root / "output" / "player_team_stints.csv").open(newline="", encoding="utf-8") as stream:
                rows = list(csv.DictReader(stream))

            traded = [row for row in rows if row["player__rosterId"] == "7"]
            self.assertEqual({row["team"] for row in traded}, {"Alpha", "Beta"})
            self.assertTrue(all(row["multi_team_season"] == "True" for row in traded))
            by_team = {row["team"]: row for row in traded}
            self.assertEqual(float(by_team["Alpha"]["passTotalYds_raw"]), 100.0)
            self.assertEqual(float(by_team["Beta"]["passTotalYds_raw"]), 200.0)
            self.assertEqual(float(by_team["Alpha"]["passTotalYds"]), 100.0)
            self.assertEqual(float(by_team["Beta"]["passTotalYds"]), 130.0)
            self.assertEqual(float(by_team["Alpha"]["rushTotalYds"]), 30.0)
            self.assertEqual(float(by_team["Beta"]["rushTotalYds"]), 70.0)


class SeasonAndStandingsContractsTests(unittest.TestCase):
    def test_elo_game_selection_uses_season_and_regular_stage_not_row_offsets(self):
        fixture = FIXTURE_ROOT / "games_shuffled_seasons.csv"
        season_one = read_games(str(fixture), start_row=287, season_index=1)
        season_two = read_games(str(fixture), start_row=1, season_index=2)
        season_three = read_games(str(fixture), start_row=2, season_index=3)
        self.assertEqual([row["gameId"] for row in season_one], ["g1"])
        self.assertEqual([row["gameId"] for row in season_two], ["g2"])
        self.assertEqual([row["gameId"] for row in season_three], ["g3"])

    def test_tied_completed_games_count_as_half_win_and_postseason_rows_are_not_in_regular_input(self):
        teams = {
            "Alpha": {"conference": "AFC", "division": "North"},
            "Beta": {"conference": "AFC", "division": "North"},
        }
        games = [
            {"home": "Alpha", "away": "Beta", "home_score": 17, "away_score": 17, "completed": True},
            {"home": "Alpha", "away": "Beta", "home_score": 0, "away_score": 7, "completed": False},
        ]
        stats = playoff.calculate_team_stats(teams, games)
        self.assertEqual((stats["Alpha"]["W"], stats["Alpha"]["L"], stats["Alpha"]["T"]), (0, 0, 1))
        self.assertEqual((stats["Beta"]["W"], stats["Beta"]["L"], stats["Beta"]["T"]), (0, 0, 1))
        self.assertEqual(stats["Alpha"]["win_pct"], 0.5)
        self.assertEqual(stats["Beta"]["points_for"], 17)

    def test_seeded_simulation_matches_recorded_fixture_baseline(self):
        teams = {
            "Alpha": {"conference": "AFC", "division": "North", "past_sos": 0.5, "elo": 1000.0, "win_streak": 0},
            "Beta": {"conference": "AFC", "division": "North", "past_sos": 0.5, "elo": 1000.0, "win_streak": 0},
        }
        completed = [{"home": "Alpha", "away": "Beta", "home_score": 17, "away_score": 17, "completed": True}]
        stats = playoff.calculate_team_stats(teams, completed)
        remaining = [{"home": "Alpha", "away": "Beta", "completed": False}]
        baseline = json.loads((FIXTURE_ROOT / "baseline.json").read_text(encoding="utf-8"))

        random.seed(baseline["seed"])
        actual = []
        for _ in range(baseline["simulation_count"]):
            game = playoff.simulate_remaining_games(teams, stats, {}, remaining, {})[0]
            actual.append({key: game[key] for key in ("winner", "loser", "winner_score", "loser_score")})

        self.assertEqual(actual, baseline["outcomes"])


if __name__ == "__main__":
    unittest.main()
