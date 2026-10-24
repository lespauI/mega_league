"""Week 18 consumes only the selected regular-season schedule."""

import csv
from pathlib import Path
import tempfile
import unittest

from scripts.standings_domain import calculate_team_stats
from scripts.week18_simulator import load_games


FIELDS = [
    "id", "seasonIndex", "stageIndex", "weekIndex", "status", "homeTeam", "awayTeam",
    "homeScore", "awayScore",
]


class Week18InputTests(unittest.TestCase):
    def test_load_games_filters_season_and_regular_stage_before_standings_and_week18_selection(self):
        rows = [
            {"id": "pre", "seasonIndex": "0", "stageIndex": "0", "weekIndex": "0", "status": "2", "homeTeam": "A", "awayTeam": "B", "homeScore": "7", "awayScore": "0"},
            {"id": "regular", "seasonIndex": "0", "stageIndex": "1", "weekIndex": "0", "status": "2", "homeTeam": "A", "awayTeam": "B", "homeScore": "14", "awayScore": "7"},
            {"id": "week18", "seasonIndex": "0", "stageIndex": "1", "weekIndex": "17", "status": "1", "homeTeam": "B", "awayTeam": "A", "homeScore": "0", "awayScore": "0"},
            {"id": "post", "seasonIndex": "0", "stageIndex": "2", "weekIndex": "18", "status": "2", "homeTeam": "A", "awayTeam": "B", "homeScore": "0", "awayScore": "28"},
            {"id": "other-season", "seasonIndex": "1", "stageIndex": "1", "weekIndex": "0", "status": "2", "homeTeam": "B", "awayTeam": "A", "homeScore": "35", "awayScore": "0"},
        ]
        with tempfile.TemporaryDirectory() as temp:
            games_path = Path(temp) / "MEGA_games.csv"
            with games_path.open("w", newline="", encoding="utf-8") as stream:
                writer = csv.DictWriter(stream, fieldnames=FIELDS)
                writer.writeheader()
                writer.writerows(rows)

            games = load_games(season_index=0, csv_path=games_path)

        self.assertEqual([game["id"] for game in games], ["regular", "week18"])
        week18 = [game for game in games if game["week"] == 17 and not game["completed"]]
        self.assertEqual([game["id"] for game in week18], ["week18"])

        teams = {
            "A": {"conference": "AFC", "division": "East"},
            "B": {"conference": "AFC", "division": "East"},
        }
        stats = calculate_team_stats(teams, games)
        self.assertEqual((stats["A"]["W"], stats["A"]["L"], stats["A"]["T"]), (1, 0, 0))
        self.assertEqual((stats["B"]["W"], stats["B"]["L"], stats["B"]["T"]), (0, 1, 0))


if __name__ == "__main__":
    unittest.main()
