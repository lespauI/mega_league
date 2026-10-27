"""Public import and CLI compatibility after moving reusable code into mega."""

from pathlib import Path
import contextlib
import io
import os
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from mega.inputs.csv import load_csv
from mega.inputs.cycle import CycleContext
from mega.inputs.identity import normalize_team_display
from mega.standings.records import calculate_team_stats
from scripts import cycle_context, standings_domain
from stats_scripts import csv_io, stats_domain

ROOT = Path(__file__).resolve().parents[1]


class PackageCompatibilityTests(unittest.TestCase):
    def test_old_imports_share_the_same_implementation(self):
        self.assertIs(cycle_context.CycleContext, CycleContext)
        self.assertIs(csv_io.load_csv, load_csv)
        self.assertIs(stats_domain.normalize_team_display, normalize_team_display)
        self.assertIs(standings_domain.calculate_team_stats, calculate_team_stats)

    def test_pipeline_public_exports_exist(self):
        from scripts import pipeline_tasks
        for name in pipeline_tasks.__all__:
            with self.subTest(name=name):
                self.assertTrue(hasattr(pipeline_tasks, name))

    def test_failed_pipeline_preflight_preserves_callers_working_directory(self):
        from mega.pipeline.execution import run_pipeline
        previous = Path.cwd()
        with tempfile.TemporaryDirectory() as directory:
            try:
                os.chdir(directory)
                with patch('mega.pipeline.execution.Path.is_file', return_value=False), contextlib.redirect_stdout(io.StringIO()):
                    results = run_pipeline('full', staged=False)
                self.assertEqual(Path.cwd(), Path(directory).resolve())
                self.assertEqual(results[0].status.value, 'failed')
            finally:
                os.chdir(previous)

    def test_commands_load_from_an_unrelated_working_directory(self):
        environment = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}
        with tempfile.TemporaryDirectory() as directory:
            for command in ("power_rankings_roster.py", "run_all.py", "verify_site.py", "check.py"):
                with self.subTest(command=command):
                    result = subprocess.run(
                        [sys.executable, str(ROOT / "scripts" / command), "--help"],
                        cwd=directory, env=environment, capture_output=True, text=True,
                    )
                    self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(list(Path(directory).iterdir()), [])


if __name__ == "__main__":
    unittest.main()
