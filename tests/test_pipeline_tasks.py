"""Staging and rollback tests that write only inside temporary directories."""

import hashlib
import json
from pathlib import Path
import shutil
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
from mega.pipeline.artifacts import BROWSER_DATA
from mega.pipeline.manifests import validate_browser_data, write_data_manifest
from mega.pipeline.staging import sha256_file


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_browser_fixture(root: Path, context: CycleContext) -> dict:
    for artifact in BROWSER_DATA.values():
        source, _ = artifact.resolved(context.display_season)
        path = root / source
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("fixture\n", encoding="utf-8")
    return write_data_manifest(root, context)


class PipelineStagingTests(unittest.TestCase):
    def test_output_ownership_is_explicit_and_protects_models_and_formulas(self):
        self.assertTrue(is_owned_artifact("output/team_aggregated_stats.csv"))
        self.assertTrue(is_owned_artifact("output/team_rosters/BUF.csv"))
        self.assertFalse(is_owned_artifact("output/user_notes.csv"))
        self.assertFalse(is_owned_artifact("output/attributes.md"))
        self.assertFalse(is_owned_artifact("output/trained_models/model.pkl"))

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

    def test_browser_manifest_uses_registered_paths_and_rejects_missing_data(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "workspace"
            context = CycleContext("Madden 27", 0, 1, 2026, 12, 12, 13, 8, "fixture-snapshot", ())
            manifest = write_browser_fixture(root, context)

            self.assertEqual(manifest["schemaVersion"], 1)
            self.assertEqual(manifest["snapshotId"], context.snapshot_id)
            self.assertEqual(manifest["cycle"], {
                "edition": "Madden 27", "csvSeasonIndex": 0, "displaySeason": 1,
                "calendarYear": 2026, "completedThroughWeek": 12,
                "exportWeekIndex": 12, "eloSourceWeek": 8,
            })
            self.assertEqual(set(manifest["data"]), set(BROWSER_DATA))
            self.assertEqual(manifest["data"]["teams"], "../../MEGA_teams.csv")
            self.assertEqual(manifest["data"]["elo_sos"], "season1_elo.csv")
            self.assertEqual(manifest["data"]["schedules"], "schedules_season1.json")
            self.assertEqual(validate_browser_data(root, context), manifest)

            (root / "output" / "team_player_usage.csv").unlink()
            with self.assertRaisesRegex(FileNotFoundError, "team_player_usage.csv"):
                validate_browser_data(root, context)

    def test_full_manifest_survives_simulated_git_lf_checkout(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "repo"
            workspace = Path(temp) / "full-stage"
            context = CycleContext("Madden 27", 0, 1, 2026, 12, 12, 13, 8, "fixture-snapshot", ())
            write_browser_fixture(workspace, context)

            generated_csv = workspace / "output" / "team_aggregated_stats.csv"
            generated_csv.write_bytes(b"team\r\nAlpha\r\n")
            generated_json = workspace / "docs" / "data" / "schedules_season1.json"
            generated_json.write_bytes(b'{"schedule": []}\r\n')
            generated_html = workspace / "index.html"
            generated_html.write_bytes(b"<html>\r\n</html>\r\n")
            raw_input = workspace / "MEGA_teams.csv"
            raw_input.write_bytes(b"Team\r\nAlpha\r\n")
            protected_formula = workspace / "output" / "attributes.md"
            protected_formula.write_bytes(b"formula\r\n")

            manifest = write_build_manifest(
                workspace, root, "full", context, ["publish_browser_data"]
            )
            self.assertEqual(generated_csv.read_bytes(), b"team\nAlpha\n")
            self.assertEqual(generated_json.read_bytes(), b'{"schedule": []}\n')
            self.assertEqual(generated_html.read_bytes(), b"<html>\n</html>\n")
            self.assertEqual(raw_input.read_bytes(), b"Team\r\nAlpha\r\n")
            self.assertEqual(protected_formula.read_bytes(), b"formula\r\n")

            checkout = Path(temp) / "git-checkout"
            shutil.copytree(workspace, checkout)
            for relative in manifest["artifacts"]:
                path = checkout / relative
                if path.suffix.lower() in {".csv", ".json", ".html", ".md", ".js", ".css"}:
                    path.write_bytes(path.read_bytes().replace(b"\r\n", b"\n").replace(b"\r", b"\n"))
                self.assertEqual(sha256_file(path), manifest["artifacts"][relative], relative)
            self.assertEqual(validate_browser_data(checkout, context)["snapshotId"], context.snapshot_id)

    def test_same_snapshot_subset_manifest_preserves_browser_data_contract(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "repo"
            full_workspace = Path(temp) / "full-stage"
            context = CycleContext("Madden 27", 0, 1, 2026, 12, 12, 13, 8, "fixture-snapshot", ())
            write_browser_fixture(full_workspace, context)
            (full_workspace / "output" / "team_aggregated_stats.csv").write_bytes(b"team\r\nAlpha\r\n")

            full_manifest = write_build_manifest(full_workspace, root, "full", context, ["publish_browser_data"])
            self.assertEqual(
                (full_workspace / "output" / "team_aggregated_stats.csv").read_bytes(),
                b"team\nAlpha\n",
            )
            (root / "output").mkdir(parents=True, exist_ok=True)
            for key in ("teams", "players", "games"):
                source, _ = BROWSER_DATA[key].resolved(context.display_season)
                path = root / source
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("fixture\n", encoding="utf-8")
            for relative in full_manifest["artifacts"]:
                source = full_workspace / relative
                target = root / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, target)
            shutil.copy2(full_workspace / "output" / "build_manifest.json", root / "output" / "build_manifest.json")

            temporary_root, subset_workspace, _ = create_staging_workspace(root)
            try:
                for relative in full_manifest["artifacts"]:
                    source = root / relative
                    target = subset_workspace / relative
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(source, target)

                subset_manifest = write_build_manifest(
                    subset_workspace, root, "stats", context, ["team_stats"], include_index=False
                )
                self.assertEqual(
                    (subset_workspace / "output" / "team_aggregated_stats.csv").read_bytes(),
                    b"team\nAlpha\n",
                )
                self.assertEqual(
                    subset_manifest["artifacts"]["output/team_aggregated_stats.csv"],
                    sha256_file(subset_workspace / "output/team_aggregated_stats.csv"),
                )
                self.assertIn("docs/data/data_manifest.json", subset_manifest["artifacts"])
                self.assertEqual(
                    subset_manifest["artifacts"]["docs/data/data_manifest.json"],
                    sha256_file(subset_workspace / "docs/data/data_manifest.json"),
                )
                self.assertEqual(validate_browser_data(subset_workspace, context)["snapshotId"], context.snapshot_id)
            finally:
                shutil.rmtree(temporary_root, ignore_errors=True)

    def test_stage_excludes_old_generated_reports_but_preserves_unowned_page_data(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "repo"
            (root / "docs" / "data").mkdir(parents=True)
            (root / "docs" / "playoff_race.html").write_text("old snapshot report", encoding="utf-8")
            (root / "docs" / "data" / "playoff_dashboard.json").write_text("retained page data", encoding="utf-8")
            (root / "docs" / "data" / "data_manifest.json").write_text("old generated manifest", encoding="utf-8")
            (root / "docs" / "data" / "import_metadata.json").write_text("maintained import metadata", encoding="utf-8")
            (root / "docs" / "tools_guide.html").write_text("maintained source", encoding="utf-8")

            temporary_root, workspace, _ = create_staging_workspace(root)
            try:
                self.assertFalse((workspace / "docs" / "playoff_race.html").exists())
                self.assertFalse((workspace / "docs" / "data" / "data_manifest.json").exists())
                self.assertEqual((workspace / "docs" / "data" / "playoff_dashboard.json").read_text(), "retained page data")
                self.assertEqual((workspace / "docs" / "data" / "import_metadata.json").read_text(), "maintained import metadata")
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
