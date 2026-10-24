"""An empty or partially imported cycle must not publish misleading results."""
import contextlib
import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts import generate_index
from scripts.cycle_context import canonical_input_sha256


class EmptyCycleIndexTests(unittest.TestCase):
    def test_missing_exports_do_not_run_aggregation_or_link_dashboards(self):
        for present_inputs in ((), ('MEGA_teams.csv', 'MEGA_games.csv')):
            with self.subTest(present_inputs=present_inputs), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                docs = root / 'docs'
                docs.mkdir()
                (docs / 'team_stats_explorer.html').write_text('reusable dashboard')
                for name in present_inputs:
                    (root / name).write_text('header\n')
                with patch.object(generate_index, 'ROOT_DIR', root), \
                     patch.object(generate_index, 'DOCS_DIR', docs), \
                     patch.object(generate_index, 'SITE_MANIFEST_PATH', docs / 'site_manifest.json'), \
                     patch.object(generate_index, 'BUILD_MANIFEST_PATH', root / 'output' / 'build_manifest.json'), \
                     contextlib.redirect_stdout(io.StringIO()):
                    generate_index.main()
                page = (root / 'index.html').read_text()
                self.assertIn('Madden 27 — awaiting league data', page)
                self.assertIn('archive/madden-26/README.md', page)
                self.assertNotIn('href="docs/team_stats_explorer.html"', page)
                self.assertFalse((root / 'output').exists())

    def test_declared_page_inventory_requires_artifact_from_active_snapshot(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            docs = root / 'docs'
            data = docs / 'data'
            output = root / 'output'
            data.mkdir(parents=True)
            output.mkdir()
            (docs / 'source.html').write_text('source')
            (docs / 'report.html').write_text('generated')
            artifact = output / 'ready.csv'
            artifact.write_text('value\n1\n')
            digest = hashlib.sha256(artifact.read_bytes()).hexdigest()
            (root / 'MEGA_teams.csv').write_text('displayName\nAlpha\n')
            (root / 'mega_elo.csv').write_text('Team,Week 8+\nAlpha,1000\n')
            metadata = {
                'game': 'Madden 27', 'seasonIndex': 0, 'seasonNumber': 1,
                'calendarYear': 2026, 'completedThroughWeek': 12,
                'exportWeekIndex': 12, 'nextScheduledWeek': 13,
                'eloSourceWeek': 8, 'snapshotId': 'fixture-snapshot',
                'hashContractVersion': 3, 'hashNormalization': 'newline-lf-v1',
                'inputs': [
                    {'path': 'MEGA_teams.csv', 'canonicalSha256': canonical_input_sha256((root / 'MEGA_teams.csv').read_bytes())},
                    {'path': 'mega_elo.csv', 'canonicalSha256': canonical_input_sha256((root / 'mega_elo.csv').read_bytes())},
                ], 'enabledFeatures': [],
            }
            (data / 'import_metadata.json').write_text(json.dumps(metadata))
            (docs / 'site_manifest.json').write_text(json.dumps({
                'pages': [
                    {'path': 'source.html', 'kind': 'source'},
                    {'path': 'report.html', 'kind': 'generated', 'requires': ['output/ready.csv']},
                ],
            }))
            (output / 'build_manifest.json').write_text(json.dumps({
                'snapshotId': 'fixture-snapshot', 'artifacts': {'output/ready.csv': digest},
            }))

            with patch.object(generate_index, 'ROOT_DIR', root), \
                 patch.object(generate_index, 'DOCS_DIR', docs), \
                 patch.object(generate_index, 'SITE_MANIFEST_PATH', docs / 'site_manifest.json'), \
                 patch.object(generate_index, 'BUILD_MANIFEST_PATH', output / 'build_manifest.json'):
                self.assertEqual(generate_index.categorize_files()['Reports & Visualizations'], ['report.html', 'source.html'])

                artifact.write_text('tampered\n')
                self.assertEqual(generate_index.categorize_files()['Reports & Visualizations'], ['source.html'])

    def test_rendering_navigation_does_not_run_aggregators(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            docs = root / 'docs'
            docs.mkdir()
            for name in ('MEGA_teams.csv', 'MEGA_games.csv', 'MEGA_players.csv'):
                (root / name).write_text('header\n')
            page = docs / 'stats_dashboard.html'
            page.write_text('dashboard')

            with patch.object(generate_index, 'ROOT_DIR', root), \
                 patch.object(generate_index, 'DOCS_DIR', docs), \
                 patch.object(generate_index, 'SITE_MANIFEST_PATH', docs / 'site_manifest.json'), \
                 patch.object(generate_index, 'BUILD_MANIFEST_PATH', root / 'output' / 'build_manifest.json'), \
                 patch('subprocess.run', side_effect=AssertionError('index rendering must not run subprocesses')), \
                 contextlib.redirect_stdout(io.StringIO()):
                generate_index.main()

            self.assertTrue((root / 'index.html').is_file())
            self.assertFalse((root / 'output').exists())


if __name__ == '__main__':
    unittest.main()
