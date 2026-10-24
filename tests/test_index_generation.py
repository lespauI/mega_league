"""An empty or partially imported cycle must not publish misleading results."""
import contextlib
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts import generate_index


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
                     patch.object(generate_index, 'run_aggregation_script') as aggregate, \
                     contextlib.redirect_stdout(io.StringIO()):
                    generate_index.main()
                aggregate.assert_not_called()
                page = (root / 'index.html').read_text()
                self.assertIn('Madden 27 — awaiting league data', page)
                self.assertIn('archive/madden-26/README.md', page)
                self.assertNotIn('href="docs/team_stats_explorer.html"', page)
                self.assertFalse((root / 'output').exists())


if __name__ == '__main__':
    unittest.main()
