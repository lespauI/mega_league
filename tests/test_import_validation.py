"""Isolated ZIP validation and transactional activation checks."""

import csv
import io
import json
import os
from pathlib import Path
import tempfile
import zipfile
import unittest

from scripts.validate_import import BASIC_FILES, STATS_FILES, activate_snapshot, main, validate_snapshot
from scripts.cycle_context import CycleContext


def csv_bytes(fields, rows):
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=fields, lineterminator="\r\n")
    writer.writeheader()
    writer.writerows(rows)
    return buffer.getvalue().encode("utf-8")


def make_export_zips(directory: Path):
    basic = {
        "MEGA_teams.csv": csv_bytes(
            ["displayName", "userName", "seasonIndex", "weekIndex", "calendarYear"],
            [{"displayName": "Alpha", "userName": "alpha-user", "seasonIndex": 0, "weekIndex": 12, "calendarYear": 2026},
             {"displayName": "Beta", "userName": "beta-user", "seasonIndex": 0, "weekIndex": 12, "calendarYear": 2026}],
        ),
        "MEGA_games.csv": csv_bytes(
            ["gameId", "homeTeam", "awayTeam", "homeScore", "awayScore", "status", "seasonIndex", "stageIndex", "weekIndex"],
            [{"gameId": "g1", "homeTeam": "Alpha", "awayTeam": "Beta", "homeScore": 10, "awayScore": 7,
              "status": 2, "seasonIndex": 0, "stageIndex": 1, "weekIndex": 0}],
        ),
        "MEGA_players.csv": csv_bytes(
            ["id", "rosterId", "team", "fullName", "position"],
            [{"id": "p1", "rosterId": "r1", "team": "AA", "fullName": "Player One", "position": "QB"}],
        ),
        "MEGA_rankings.csv": csv_bytes(
            ["team", "seasonIndex", "stageIndex", "weekIndex", "rank"],
            [{"team": "Alpha", "seasonIndex": 0, "stageIndex": 1, "weekIndex": 12, "rank": 1},
             {"team": "Beta", "seasonIndex": 0, "stageIndex": 1, "weekIndex": 12, "rank": 2}],
        ),
        "MEGA_draft.csv": csv_bytes(["Year", "Round", "Pick"], [{"Year": 2026, "Round": 1, "Pick": 1}]),
        "MEGA_trades.csv": csv_bytes(["tradeId", "teamA", "teamB"], []),
    }
    stats = {}
    for name, required in STATS_FILES.items():
        fields = sorted(required)
        row = {field: "" for field in fields}
        row["team__displayName"] = "Alpha"
        row["player__rosterId"] = "r1"
        row["gamesPlayed"] = "1"
        stats[name] = csv_bytes(fields, [row])
    stats["MEGA_passing.csv"] = csv_bytes(
        sorted(STATS_FILES["MEGA_passing.csv"]),
        [{"player__rosterId": "r1", "team__displayName": "Alpha", "gamesPlayed": "1", "passTotalYds": "100"}],
    )

    basic_zip = directory / "basic.zip"
    stats_zip = directory / "stats.zip"
    with zipfile.ZipFile(basic_zip, "w") as archive:
        for name, data in basic.items():
            archive.writestr(f"export/{name}", data)
    with zipfile.ZipFile(stats_zip, "w") as archive:
        for name, data in stats.items():
            archive.writestr(f"export/{name}", data)
    elo = directory / "mega_elo.csv"
    elo.write_bytes(csv_bytes(["#", "Team", "GM", "Week 8+", "Week 12+"],
                              [{"#": 1, "Team": "Alpha", "GM": "GM A", "Week 8+": 1000, "Week 12+": 1200},
                               {"#": 2, "Team": "Beta", "GM": "GM B", "Week 8+": 1001, "Week 12+": 1201}]))
    users = directory / "MEGA_users.csv"
    users.write_bytes(csv_bytes(["Team", "GM", "neonsportzUserName", "sourceWeek"],
                                [{"Team": "Alpha", "GM": "GM A", "neonsportzUserName": "alpha-user", "sourceWeek": 8},
                                 {"Team": "Beta", "GM": "GM B", "neonsportzUserName": "beta-user", "sourceWeek": 8}]))
    return basic_zip, stats_zip, elo, users


class ImportValidationTests(unittest.TestCase):
    def test_valid_fixture_creates_separate_source_and_working_hashes(self):
        with tempfile.TemporaryDirectory() as temp:
            basic_zip, stats_zip, elo, users = make_export_zips(Path(temp))
            working, metadata = validate_snapshot(basic_zip, stats_zip, elo, users, season_index=0, elo_source_week=8)
            self.assertEqual(len(working), len(BASIC_FILES) + len(STATS_FILES) + 2)
            self.assertEqual(metadata["completedThroughWeek"], 1)
            self.assertEqual(metadata["exportWeekIndex"], 12)
            self.assertNotEqual(metadata["inputs"][0]["sourceSha256"], "")
            self.assertNotEqual(metadata["inputs"][0]["workingSha256"], "")
            self.assertEqual(metadata["hashContractVersion"], 3)
            with zipfile.ZipFile(basic_zip) as archive:
                self.assertNotIn("MEGA_users.csv", [Path(name).name for name in archive.namelist()])
            self.assertEqual(metadata["independentSourceFiles"]["usersCsv"]["path"], "MEGA_users.csv")
            self.assertIn("Week 12+", working["mega_elo.csv"].decode("utf-8"))

    def test_invalid_import_does_not_change_active_files(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            basic_zip = root / "bad-basic.zip"
            stats_zip = root / "bad-stats.zip"
            with zipfile.ZipFile(basic_zip, "w") as archive:
                archive.writestr("MEGA_teams.csv", "displayName,seasonIndex\nAlpha,0\n")
            with zipfile.ZipFile(stats_zip, "w") as archive:
                archive.writestr("MEGA_passing.csv", "team__displayName\nAlpha\n")
            elo = root / "elo.csv"
            elo.write_text("Team,GM,Week 8+\nAlpha,GM A,1000\n", encoding="utf-8")
            (root / "MEGA_teams.csv").write_text("keep active\n", encoding="utf-8")

            users = root / "users.csv"
            users.write_text("Team,GM,neonsportzUserName,sourceWeek\nAlpha,GM A,alpha-user,8\n", encoding="utf-8")
            result = main(["--basic-info-zip", str(basic_zip), "--stats-zip", str(stats_zip),
                           "--elo-csv", str(elo), "--users-csv", str(users), "--season-index", "0", "--elo-source-week", "8",
                           "--root", str(root), "--activate"])

            self.assertEqual(result, 1)
            self.assertEqual((root / "MEGA_teams.csv").read_text(encoding="utf-8"), "keep active\n")
            self.assertFalse((root / "MEGA_players.csv").exists())

    def test_activation_writes_hash_checked_cycle_metadata(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            basic_zip, stats_zip, elo, users = make_export_zips(root)
            working, metadata = validate_snapshot(basic_zip, stats_zip, elo, users, season_index=0, elo_source_week=8)
            activate_snapshot(root, working, metadata)
            active_metadata = root / "docs" / "data" / "import_metadata.json"
            context = CycleContext.from_file(active_metadata, root)
            self.assertEqual(context.csv_season_index, 0)
            self.assertEqual(context.display_season, 1)
            self.assertEqual(context.elo_source_week, 8)
            self.assertEqual(context.completed_through_week, 1)
            self.assertEqual(context.snapshot_id, metadata["snapshotId"][:16])

    def test_declared_week_flows_from_multi_column_import_to_both_playoff_loaders(self):
        from scripts.calc_playoff_probabilities import load_data
        from scripts.playoff_race_table import load_elo_data as load_table_elo
        from scripts.run_utils import publish_browser_data

        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            basic_zip, stats_zip, elo, users = make_export_zips(base)
            working, metadata = validate_snapshot(
                basic_zip, stats_zip, elo, users, season_index=0, elo_source_week=8
            )
            active = base / "active"
            active.mkdir()
            activate_snapshot(active, working, metadata)
            output = active / "output"
            output.mkdir()
            with (output / "ranked_sos_by_conference.csv").open("w", newline="", encoding="utf-8") as stream:
                writer = csv.DictWriter(stream, fieldnames=["team", "past_ranked_sos_avg"])
                writer.writeheader()
                writer.writerows([
                    {"team": "Alpha", "past_ranked_sos_avg": "0.5"},
                    {"team": "Beta", "past_ranked_sos_avg": "0.5"},
                ])
            (output / "playoff_probabilities.json").write_text("{}", encoding="utf-8")
            sos_dir = output / "sos"
            sos_dir.mkdir()
            (sos_dir / "season1_elo.csv").write_text("team\nAlpha\n", encoding="utf-8")
            schedule_dir = output / "schedules" / "season1"
            schedule_dir.mkdir(parents=True)
            (schedule_dir / "all_schedules.json").write_text("{}", encoding="utf-8")
            publish_browser_data(0, root=active)

            with (active / "docs/data/current_elo.csv").open(newline="", encoding="utf-8") as stream:
                browser_rows = list(csv.DictReader(stream))
            self.assertEqual([row["ELO"] for row in browser_rows], ["1000", "1001"])
            self.assertEqual([row["sourceWeek"] for row in browser_rows], ["8", "8"])
            self.assertIn("Week 12+", (active / "docs/data/mega_elo.csv").read_text(encoding="utf-8"))

            previous = Path.cwd()
            try:
                os.chdir(active)
                teams_info, _, _ = load_data(season_index=0)
            finally:
                os.chdir(previous)

            self.assertEqual(teams_info["Alpha"]["elo"], 1000.0)
            self.assertEqual(teams_info["Beta"]["elo"], 1001.0)
            self.assertEqual(load_table_elo(root=active, season_index=0), {
                "alpha": 1000.0,
                "beta": 1001.0,
            })

    def test_nonfinite_and_nonnumeric_elo_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            basic_zip, stats_zip, elo, users = make_export_zips(root)
            for value in ("NaN", "Infinity", "not-a-number"):
                elo.write_bytes(csv_bytes(["#", "Team", "GM", "Week 8+"],
                                          [{"#": 1, "Team": "Alpha", "GM": "GM A", "Week 8+": value},
                                           {"#": 2, "Team": "Beta", "GM": "GM B", "Week 8+": 1001}]))
                with self.subTest(value=value), self.assertRaisesRegex(ValueError, "ELO row"):
                    validate_snapshot(basic_zip, stats_zip, elo, users, season_index=0, elo_source_week=8)

                active = root / "active"
                active.mkdir(exist_ok=True)
                (active / "MEGA_teams.csv").write_text("leave active bytes untouched\n", encoding="utf-8")
                result = main(["--basic-info-zip", str(basic_zip), "--stats-zip", str(stats_zip),
                               "--elo-csv", str(elo), "--users-csv", str(users), "--season-index", "0",
                               "--elo-source-week", "8", "--root", str(active), "--activate"])
                self.assertEqual(result, 1)
                self.assertEqual((active / "MEGA_teams.csv").read_text(encoding="utf-8"),
                                 "leave active bytes untouched\n")
                self.assertFalse((active / "docs" / "data" / "import_metadata.json").exists())

    def test_source_week_after_export_fails_cycle_preflight(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            basic_zip, stats_zip, elo, users = make_export_zips(root)
            elo.write_bytes(csv_bytes(["#", "Team", "GM", "Week 8+", "Week 13+"],
                                      [{"#": 1, "Team": "Alpha", "GM": "GM A", "Week 8+": 1000, "Week 13+": 1100},
                                       {"#": 2, "Team": "Beta", "GM": "GM B", "Week 8+": 1001, "Week 13+": 1101}]))
            users.write_bytes(csv_bytes(["Team", "GM", "neonsportzUserName", "sourceWeek"],
                                        [{"Team": "Alpha", "GM": "GM A", "neonsportzUserName": "alpha-user", "sourceWeek": 13},
                                         {"Team": "Beta", "GM": "GM B", "neonsportzUserName": "beta-user", "sourceWeek": 13}]))
            with self.assertRaisesRegex(ValueError, "ELO source week cannot be later"):
                validate_snapshot(basic_zip, stats_zip, elo, users, season_index=0, elo_source_week=13)

    def test_inconsistent_cycle_metadata_is_rejected_before_activation(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            basic_zip, stats_zip, elo, users = make_export_zips(root)
            working, metadata = validate_snapshot(basic_zip, stats_zip, elo, users, season_index=0, elo_source_week=8)
            (root / "MEGA_teams.csv").write_text("leave this untouched\n", encoding="utf-8")
            metadata["eloSourceWeek"] = 13
            with self.assertRaisesRegex(ValueError, "ELO source week cannot be later"):
                activate_snapshot(root, working, metadata)
            self.assertEqual((root / "MEGA_teams.csv").read_text(encoding="utf-8"), "leave this untouched\n")
            self.assertFalse((root / "docs" / "data" / "import_metadata.json").exists())

    def test_canonical_hash_accepts_lf_and_crlf_but_rejects_content_edits(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            basic_zip, stats_zip, elo, users = make_export_zips(base)
            working, metadata = validate_snapshot(basic_zip, stats_zip, elo, users, season_index=0, elo_source_week=8)
            lf_root = base / "lf"
            crlf_root = base / "crlf"
            for root in (lf_root, crlf_root):
                root.mkdir()
                for name, data in working.items():
                    target_data = data if root == lf_root else data.replace(b"\n", b"\r\n")
                    (root / name).parent.mkdir(parents=True, exist_ok=True)
                    (root / name).write_bytes(target_data)
                metadata_path = root / "docs" / "data" / "import_metadata.json"
                metadata_path.parent.mkdir(parents=True, exist_ok=True)
                metadata_path.write_text(json.dumps(metadata), encoding="utf-8")
            self.assertEqual(CycleContext.from_file(lf_root / "docs/data/import_metadata.json", lf_root).snapshot_id,
                             CycleContext.from_file(crlf_root / "docs/data/import_metadata.json", crlf_root).snapshot_id)
            (crlf_root / "MEGA_teams.csv").write_bytes((crlf_root / "MEGA_teams.csv").read_bytes().replace(b"Alpha", b"Omega", 1))
            with self.assertRaisesRegex(ValueError, "Canonical-file hash mismatch"):
                CycleContext.from_file(crlf_root / "docs/data/import_metadata.json", crlf_root)


if __name__ == "__main__":
    unittest.main()
