"""The assembled site must include all current-page inputs and dependencies."""

import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from mega.inputs.cycle import CycleContext
from mega.site import validate_site

CONTEXT = CycleContext("Madden 27", 0, 1, 2026, 12, 12, 13, 8, "fixture-snapshot", ())


class SiteValidationTests(unittest.TestCase):
    def fixture(self, root, pages):
        (root / "docs").mkdir()
        (root / "docs/data").mkdir()
        (root / "output").mkdir()
        (root / "index.html").write_text('<a href="docs/dashboard.html">Dashboard</a>')
        (root / "docs/dashboard.html").write_text('<script type="module" src="app.js"></script>')
        (root / "docs/app.js").write_text('import "./format.js";')
        (root / "docs/format.js").write_text('export const label = "Team";')
        (root / "docs/site_manifest.json").write_text(json.dumps({"schemaVersion": 1, "pages": pages}))
        (root / "output/stats.csv").write_text("team,value\nAlpha,1\n")
        build = {"complete": True, "snapshotId": CONTEXT.snapshot_id, "artifacts": {
            "output/stats.csv": hashlib.sha256((root / "output/stats.csv").read_bytes()).hexdigest(),
        }}
        (root / "output/build_manifest.json").write_text(json.dumps(build))
        (root / "docs/data/build_manifest.json").write_text(json.dumps(build))

    def test_complete_site_checks_nested_module_imports_and_current_data(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.fixture(root, [{"path": "dashboard.html", "requires": ["output/stats.csv"], "requiresData": ["team_stats"]}])
            with patch("mega.pipeline.manifests.validate_browser_data", return_value={"data": {"team_stats": "stats.csv"}}):
                self.assertEqual(validate_site(root, context=CONTEXT), [])
                (root / "docs/format.js").unlink()
                self.assertTrue(any("format.js" in error for error in validate_site(root, context=CONTEXT)))

    def test_current_page_cannot_hide_missing_inputs_behind_navigation_filtering(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.fixture(root, [{"path": "dashboard.html", "requires": ["output/missing.csv"], "requiresData": ["missing_key"]}])
            with patch("mega.pipeline.manifests.validate_browser_data", return_value={"data": {}}):
                errors = validate_site(root, context=CONTEXT)
            self.assertTrue(any("output/missing.csv" in error for error in errors))
            self.assertTrue(any("missing_key" in error for error in errors))

    def test_disabled_integration_and_other_season_pages_are_not_required(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.fixture(root, [
                {"path": "dashboard.html"},
                {"path": "missing-integration.html", "feature": "community_predictions"},
                {"path": "sos_season3.html", "seasonScoped": True},
            ])
            with patch("mega.pipeline.manifests.validate_browser_data", return_value={"data": {}}):
                self.assertEqual(validate_site(root, context=CONTEXT), [])

    def test_changed_artifact_fails_even_when_page_and_csv_still_exist(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.fixture(root, [{"path": "dashboard.html"}])
            (root / "output/stats.csv").write_text("stale\n")
            with patch("mega.pipeline.manifests.validate_browser_data", return_value={"data": {}}):
                self.assertIn("Build artifact changed: output/stats.csv", validate_site(root, context=CONTEXT))


if __name__ == "__main__":
    unittest.main()
