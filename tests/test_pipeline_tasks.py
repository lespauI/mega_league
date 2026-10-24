"""Staging and rollback tests that write only inside temporary directories."""

import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from scripts.cycle_context import CycleContext
from scripts.pipeline_tasks import (
    create_staging_workspace,
    is_owned_artifact,
    publish_staged_changes,
    task_output_paths,
    task_missing_outputs,
    validate_task_result,
    write_build_manifest,
)
from scripts.run_utils import ScriptResult, ScriptStatus


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class PipelineStagingTests(unittest.TestCase):
    def test_week18_page_is_a_declared_pipeline_artifact(self):
        self.assertTrue(is_owned_artifact("docs/week18_simulator.html"))
        self.assertEqual(task_output_paths("week18_simulator", 1), ("docs/week18_simulator.html",))

    def test_clean_stage_copies_source_and_protected_assets_but_not_generated_output_or_archive(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "repo"
            root.mkdir()
            (root / "scripts").mkdir()
            (root / "scripts" / "source.py").write_text("source", encoding="utf-8")
            (root / "archive" / "madden-26").mkdir(parents=True)
            (root / "archive" / "madden-26" / "historical.csv").write_text("historical", encoding="utf-8")
            (root / "output" / "trained_models").mkdir(parents=True)
            (root / "output" / "attributes.md").write_text("protected attributes", encoding="utf-8")
            (root / "output" / "individual_position_formulas.txt").write_text("protected formulas", encoding="utf-8")
            (root / "output" / "trained_models" / "G.pkl").write_bytes(b"model-bytes")
            (root / "output" / "stale.csv").write_text("old generated data", encoding="utf-8")

            temporary_root, workspace, protected = create_staging_workspace(root)
            try:
                self.assertEqual((workspace / "scripts" / "source.py").read_text(), "source")
                self.assertFalse((workspace / "archive").exists())
                self.assertFalse((workspace / "output" / "stale.csv").exists())
                self.assertEqual(protected, {
                    "output/attributes.md": digest(root / "output" / "attributes.md"),
                    "output/individual_position_formulas.txt": digest(root / "output" / "individual_position_formulas.txt"),
                    "output/trained_models/G.pkl": digest(root / "output" / "trained_models" / "G.pkl"),
                })
                self.assertEqual(protected, {
                    path.relative_to(workspace).as_posix(): digest(path)
                    for path in [workspace / key for key in protected]
                })
            finally:
                import shutil
                shutil.rmtree(temporary_root, ignore_errors=True)

    def test_manifest_records_snapshot_and_generated_artifact_hashes(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "repo"
            workspace = root / ".stage"
            (root / "docs" / "data").mkdir(parents=True)
            (workspace / "docs" / "data").mkdir(parents=True)
            (workspace / "output").mkdir(parents=True)
            (workspace / "output" / "team_aggregated_stats.csv").write_text("team\nAlpha\n", encoding="utf-8")
            context = CycleContext("Madden 27", 0, 1, 2026, 12, 12, 13, 8, "fixture-snapshot", ())

            manifest = write_build_manifest(workspace, root, "full", context, ["team_stats"])

            self.assertTrue(manifest["complete"])
            self.assertEqual(manifest["snapshotId"], "fixture-snapshot")
            self.assertEqual(manifest["artifacts"]["output/team_aggregated_stats.csv"], digest(workspace / "output/team_aggregated_stats.csv"))
            self.assertTrue((workspace / "docs" / "data" / "build_manifest.json").is_file())

    def test_stage_excludes_old_generated_reports_but_preserves_unowned_page_data(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "repo"
            (root / "docs" / "data").mkdir(parents=True)
            (root / "docs" / "playoff_race.html").write_text("old snapshot report", encoding="utf-8")
            (root / "docs" / "data" / "playoff_dashboard.json").write_text("retained page data", encoding="utf-8")
            (root / "docs" / "tools_guide.html").write_text("maintained source", encoding="utf-8")

            temporary_root, workspace, _ = create_staging_workspace(root)
            try:
                self.assertFalse((workspace / "docs" / "playoff_race.html").exists())
                self.assertEqual((workspace / "docs" / "data" / "playoff_dashboard.json").read_text(), "retained page data")
                self.assertEqual((workspace / "docs" / "tools_guide.html").read_text(), "maintained source")
                context = CycleContext("Madden 27", 0, 1, 2026, 12, 12, 13, 8, "new-snapshot", ())
                manifest = write_build_manifest(workspace, root, "full", context, ["playoff_html"])
                self.assertNotIn("docs/playoff_race.html", manifest["artifacts"])
                self.assertNotIn("docs/data/playoff_dashboard.json", manifest["artifacts"])
                producer = ScriptResult(ScriptStatus.SUCCEEDED, "Playoff report", 0)
                checked = validate_task_result(producer, workspace, "playoff_html", 1)
                self.assertEqual(checked.status, ScriptStatus.FAILED)
                self.assertIn("docs/playoff_race.html", checked.error)
            finally:
                import shutil
                shutil.rmtree(temporary_root, ignore_errors=True)

    def test_injected_publish_failure_rolls_back_prior_replacements(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "repo"
            workspace = Path(temp) / "stage"
            temporary_root = Path(temp) / "tmp"
            for path in (root / "output", workspace / "output", root / "docs" / "data",
                         workspace / "docs" / "data", temporary_root):
                path.mkdir(parents=True, exist_ok=True)
            (root / "output" / "player_team_stints.csv").write_text("old A", encoding="utf-8")
            (root / "output" / "team_aggregated_stats.csv").write_text("old Z", encoding="utf-8")
            (workspace / "output" / "player_team_stints.csv").write_text("new A", encoding="utf-8")
            (workspace / "output" / "team_aggregated_stats.csv").write_text("new Z", encoding="utf-8")
            manifest = {
                "schemaVersion": 2,
                "snapshotId": "same-snapshot",
                "complete": True,
                "artifacts": {
                    "output/player_team_stints.csv": digest(workspace / "output" / "player_team_stints.csv"),
                    "output/team_aggregated_stats.csv": digest(workspace / "output" / "team_aggregated_stats.csv"),
                },
            }
            (workspace / "output" / "build_manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
            (workspace / "docs" / "data" / "build_manifest.json").write_text(json.dumps(manifest), encoding="utf-8")

            import os
            real_replace = os.replace

            def fail_on_second_publish(source, target):
                source_path = Path(source)
                target_path = Path(target)
                if target_path == root / "output" / "team_aggregated_stats.csv" and "publish" in source_path.parts:
                    raise OSError("injected replace failure")
                return real_replace(source, target)

            with self.assertRaisesRegex(OSError, "injected"):
                publish_staged_changes(workspace, root, temporary_root, "full", replace_func=fail_on_second_publish)

            self.assertEqual((root / "output" / "player_team_stints.csv").read_text(encoding="utf-8"), "old A")
            self.assertEqual((root / "output" / "team_aggregated_stats.csv").read_text(encoding="utf-8"), "old Z")


if __name__ == "__main__":
    unittest.main()
