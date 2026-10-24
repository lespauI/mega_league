"""Contract tests for real SoS verifier failures."""

import csv
import json
from pathlib import Path
import tempfile
import unittest

from scripts.verify_sos_elo import check_schedules, check_sos


class VerifySosEloTests(unittest.TestCase):
    def _write_artifacts(self, root: Path, missing_elo: bool = False) -> None:
        schedule_dir = root / "output" / "schedules" / "season1"
        sos_dir = root / "output" / "sos"
        schedule_dir.mkdir(parents=True)
        sos_dir.mkdir(parents=True)
        elo_a = None if missing_elo else 1000.0
        schedule = {
            "Alpha": {"team": "Alpha", "games": 1, "schedule": [
                {"opponent": "Beta", "homeAway": "home", "date": "", "gameId": "g1", "oppElo": elo_a}
            ]},
            "Beta": {"team": "Beta", "games": 1, "schedule": [
                {"opponent": "Alpha", "homeAway": "away", "date": "", "gameId": "g1", "oppElo": 1001.0}
            ]},
        }
        (schedule_dir / "all_schedules.json").write_text(json.dumps(schedule), encoding="utf-8")

        rows = [
            {"team": "Alpha", "games": 1, "avg_opp_elo": 1001, "league_avg_opp_elo": 1000.5,
             "plus_minus_vs_avg": 0.5, "sos_index": 101, "rank": 1},
            {"team": "Beta", "games": 1, "avg_opp_elo": 1000, "league_avg_opp_elo": 1000.5,
             "plus_minus_vs_avg": -0.5, "sos_index": 99, "rank": 2},
        ]
        fields = list(rows[0])
        with (sos_dir / "season1_elo.csv").open("w", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(stream, fieldnames=fields)
            writer.writeheader()
            writer.writerows(rows)
        (sos_dir / "season1_elo.json").write_text(json.dumps(rows), encoding="utf-8")

    def test_checks_schedule_reciprocity_and_sos_contract(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self._write_artifacts(root)
            summary = check_schedules(root, 1)
            self.assertEqual(summary, {"teams": 2, "games": 1})
            self.assertEqual(check_sos(root, 1, summary), {"teams": 2, "games_per_team": 1})

    def test_missing_opponent_elo_fails_instead_of_passing_a_stub(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self._write_artifacts(root, missing_elo=True)
            with self.assertRaisesRegex(ValueError, "opponent ELO"):
                check_schedules(root, 1)


if __name__ == "__main__":
    unittest.main()
