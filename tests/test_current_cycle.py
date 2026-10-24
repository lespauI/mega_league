"""Regression checks for explicit cycle selection and shared pipeline tasks."""

import contextlib
import io
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import calc_playoff_probabilities as playoff  # noqa: E402
import common  # noqa: E402
import pipeline_tasks  # noqa: E402
import run_all  # noqa: E402
from run_utils import ScriptResult, ScriptStatus, season_start_row  # noqa: E402


class CurrentCycleTests(unittest.TestCase):
    def test_latest_elo_column_uses_numeric_week(self):
        self.assertEqual(common.latest_elo_column(["Team", "Week 8+", "Week 12+", "Week 2+"]), "Week 12+")
        with self.assertRaises(ValueError):
            common.latest_elo_column(["Team", "GM"])

    def test_playoff_loader_reads_supplied_week_instead_of_legacy_column(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "elo.csv"
            path.write_text(
                "Team,Week 2+,Week 8+\nChiefs,1001.0,1053.2\n49ers,999.0,946.0\n",
                encoding="utf-8",
            )
            with patch.object(common, "declared_elo_source_week", return_value=8):
                self.assertEqual(
                    playoff.load_elo_data(str(path), root=temp, season_index=0),
                    {"chiefs": 1053.2, "49ers": 946.0},
                )

    def test_default_rankings_select_season_zero(self):
        content = "team,seasonIndex,weekIndex,rank\nChiefs,3,18,32\nChiefs,0,3,7\nChiefs,0,12,1\n"
        with patch("builtins.open", return_value=io.StringIO(content)):
            self.assertEqual(playoff.load_rankings_data(), {"Chiefs": 1})

    def test_legacy_season_row_helper_still_locates_regular_season(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "games.csv"
            path.write_text("seasonIndex,stageIndex\n3,1\n0,0\n0,1\n", encoding="utf-8")
            self.assertEqual(season_start_row(0, path), 3)
            with self.assertRaises(ValueError):
                season_start_row(2, path)

    def test_shared_full_pipeline_order_and_current_cycle_arguments(self):
        from cycle_context import CycleContext

        task_ids = pipeline_tasks._resolve(pipeline_tasks.GROUPS["full"])
        context = CycleContext("Madden 27", 0, 1, 2026, 12, 12, 13, 8, "fixture-snapshot", ())
        self.assertEqual(task_ids[0], "stints")
        self.assertEqual(len(task_ids), len(set(task_ids)))
        self.assertEqual(
            pipeline_tasks.task_arguments("sos_elo", 0, context),
            ["--csv-season-index", "0", "--elo-source-week", "8"],
        )
        self.assertEqual(
            pipeline_tasks.task_arguments("scenarios", 0, context),
            ["--season-index", "0", "--elo-source-week", "8", "--seed", "0"],
        )
        self.assertEqual(
            pipeline_tasks.task_arguments("playoff_table", 0, context),
            ["--season-index", "0", "--elo-source-week", "8", "--seed", "0"],
        )
        self.assertEqual(pipeline_tasks.task_arguments("playoff_html", 0, context), ["--season-index", "0"])

    def test_failed_task_stops_before_publication(self):
        failure = ScriptResult(ScriptStatus.FAILED, "Player/team stints", 1)
        with patch.object(run_all, "run_command", return_value=failure) as runner, \
             patch.object(pipeline_tasks, "publish_browser_data") as publish, \
             patch.object(pipeline_tasks.os, "chdir"), \
             contextlib.redirect_stdout(io.StringIO()):
            with self.assertRaises(SystemExit):
                run_all.main(season_index=0, staged=False)
        runner.assert_called_once()
        publish.assert_not_called()


if __name__ == "__main__":
    unittest.main()
