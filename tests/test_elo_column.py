"""Regression checks for snapshot-specific ELO column selection."""

import csv
import tempfile
import unittest
from pathlib import Path

from scripts.common import read_elo_map


class EloColumnTests(unittest.TestCase):
    def test_declared_week_wins_over_a_newer_available_column(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "mega_elo.csv"
            with path.open("w", newline="", encoding="utf-8") as stream:
                writer = csv.DictWriter(stream, fieldnames=["Team", "GM", "Week 8+", "Week 12+"])
                writer.writeheader()
                writer.writerow({"Team": "Alpha", "GM": "GM A", "Week 8+": "1000", "Week 12+": "1200"})
            self.assertEqual(read_elo_map(str(path), source_week=8), {"alpha": 1000.0})
            self.assertEqual(read_elo_map(str(path), source_week=12), {"alpha": 1200.0})
            with self.assertRaisesRegex(ValueError, "Week 13\+"):
                read_elo_map(str(path), source_week=13)


if __name__ == "__main__":
    unittest.main()
