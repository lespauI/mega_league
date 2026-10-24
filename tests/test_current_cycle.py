"""Regression checks for importing a new cycle without stale season/ELO data."""
import contextlib
import csv
import io
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import calc_playoff_probabilities as playoff
import common
import run_all
from run_utils import season_start_row


class CurrentCycleTests(unittest.TestCase):
    def test_latest_elo_column_uses_numeric_week(self):
        self.assertEqual(common.latest_elo_column(['Team', 'Week 8+', 'Week 12+', 'Week 2+']), 'Week 12+')
        with self.assertRaises(ValueError):
            common.latest_elo_column(['Team', 'GM'])

    def test_playoff_loader_reads_supplied_week_instead_of_legacy_column(self):
        with patch('builtins.open', return_value=io.StringIO('Team,Week 2+,Week 8+\nChiefs,1001.0,1053.2\n49ers,999.0,946.0\n')):
            self.assertEqual(playoff.load_elo_data(), {'Chiefs': 1053.2, '49ers': 946.0})

    def test_default_rankings_select_season_zero(self):
        content = 'team,seasonIndex,weekIndex,rank\nChiefs,3,18,32\nChiefs,0,3,7\nChiefs,0,12,1\n'
        with patch('builtins.open', return_value=io.StringIO(content)):
            self.assertEqual(playoff.load_rankings_data(), {'Chiefs': 1})

    def test_elo_slice_locates_requested_regular_season(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'games.csv'
            path.write_text('seasonIndex,stageIndex\n3,1\n0,0\n0,1\n')
            self.assertEqual(season_start_row(0, path), 3)
            with self.assertRaises(ValueError):
                season_start_row(2, path)

    def test_pipeline_builds_dependencies_before_consumers_and_passes_season(self):
        with patch.object(run_all, 'run_script', return_value=True) as runner, \
             patch.object(run_all, 'season_start_row', return_value=7), \
             patch.object(run_all, 'publish_browser_data') as publish, \
             patch.object(run_all.os, 'chdir'), \
             contextlib.redirect_stdout(io.StringIO()):
            run_all.main(season_index=0)
        calls = {c.args[0]: c.args for c in runner.call_args_list}
        self.assertEqual(runner.call_args_list[0].args[0], 'stats_scripts/build_player_team_stints.py')
        self.assertEqual(calls['scripts/calc_sos_elo.py'][3], ['--season-index', '1', '--start-row', '7'])
        for name in ['generate_all_team_scenarios.py', 'playoff_race_table.py', 'playoff_race_html.py']:
            self.assertEqual(calls['scripts/' + name][3], ['--season-index', '0'])
        publish.assert_called_once_with(0)


if __name__ == '__main__':
    unittest.main()
