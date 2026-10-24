#!/usr/bin/env python3
"""Validate and optionally activate a matched pair of NeonSportz exports.

Validation always happens in memory before any active file is changed. Use
``--activate`` only after the report confirms the intended season and ELO week.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import os
import shutil
import sys
import tempfile
import zipfile
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "stats_scripts"))
try:
    from csv_io import REQUIRED_HEADERS_BY_NAME  # noqa: E402
    from stats_domain import normalize_team_display  # noqa: E402
except ImportError:  # package imports used by unit tests
    from stats_scripts.csv_io import REQUIRED_HEADERS_BY_NAME  # noqa: E402
    from stats_scripts.stats_domain import normalize_team_display  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import normalize_team_name  # noqa: E402
from cycle_context import CycleContext, HASH_CONTRACT_VERSION, canonical_input_sha256  # noqa: E402


BASIC_FILES = {
    "MEGA_teams.csv": {"displayName", "userName", "seasonIndex", "weekIndex", "calendarYear"},
    "MEGA_games.csv": {"gameId", "homeTeam", "awayTeam", "homeScore", "awayScore", "status", "seasonIndex", "stageIndex", "weekIndex"},
    "MEGA_players.csv": {"id", "rosterId", "team", "fullName", "position"},
    "MEGA_rankings.csv": {"team", "seasonIndex", "stageIndex", "weekIndex", "rank"},
    "MEGA_draft.csv": {"Year", "Round", "Pick"},
    "MEGA_trades.csv": {"tradeId", "teamA", "teamB"},
}
USERS_HEADERS = {"Team", "GM", "neonsportzUserName", "sourceWeek"}
STATS_FILES = {
    "MEGA_passing.csv": REQUIRED_HEADERS_BY_NAME["MEGA_passing.csv"],
    "MEGA_rushing.csv": REQUIRED_HEADERS_BY_NAME["MEGA_rushing.csv"],
    "MEGA_receiving.csv": REQUIRED_HEADERS_BY_NAME["MEGA_receiving.csv"],
    "MEGA_defense.csv": REQUIRED_HEADERS_BY_NAME["MEGA_defense.csv"],
    "MEGA_punting.csv": REQUIRED_HEADERS_BY_NAME["MEGA_punting.csv"],
    "MEGA_kicking.csv": REQUIRED_HEADERS_BY_NAME["MEGA_kicking.csv"],
}


def _parse_csv(data: bytes, label: str) -> tuple[list[str], list[dict[str, str]]]:
    try:
        text = data.decode("utf-8-sig")
        reader = csv.DictReader(io.StringIO(text, newline=""), strict=True)
        fields = reader.fieldnames or []
        if not fields or any(not field or not field.strip() for field in fields):
            raise ValueError("missing or blank header")
        if len(set(fields)) != len(fields):
            raise ValueError("duplicate headers")
        rows = []
        for line, row in enumerate(reader, start=2):
            if None in row or any(value is None for value in row.values()):
                raise ValueError(f"row {line} has a different field count from the header")
            rows.append(row)
        return fields, rows
    except (UnicodeDecodeError, csv.Error, ValueError) as exc:
        raise ValueError(f"Invalid CSV {label}: {exc}") from exc


def _read_zip(path: Path) -> tuple[dict[str, bytes], str]:
    try:
        archive_bytes = path.read_bytes()
        with zipfile.ZipFile(io.BytesIO(archive_bytes)) as archive:
            files: dict[str, bytes] = {}
            for member in archive.infolist():
                if member.is_dir() or not member.filename.lower().endswith(".csv"):
                    continue
                name = Path(member.filename).name
                data = archive.read(member)
                if name in files and files[name] != data:
                    raise ValueError(f"ZIP contains conflicting files named {name}: {path}")
                files[name] = data
        return files, hashlib.sha256(archive_bytes).hexdigest()
    except (OSError, zipfile.BadZipFile) as exc:
        raise ValueError(f"Cannot read export ZIP {path}: {exc}") from exc


def _canonical_csv(fields: list[str], rows: list[dict[str, str]]) -> bytes:
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n", extrasaction="raise")
    writer.writeheader()
    writer.writerows(rows)
    return stream.getvalue().encode("utf-8")


def _required(value: str, label: str) -> str:
    result = (value or "").strip()
    if not result:
        raise ValueError(f"Missing required {label}")
    return result


def validate_snapshot(
    basic_zip: Path,
    stats_zip: Path,
    elo_csv: Path,
    users_csv: Path,
    *,
    season_index: int,
    elo_source_week: int,
    edition: str = "Madden 27",
) -> tuple[dict[str, bytes], dict[str, Any]]:
    if season_index < 0 or elo_source_week < 0:
        raise ValueError("season index and ELO source week must be zero or greater")
    basic_files, basic_archive_hash = _read_zip(Path(basic_zip))
    stats_files, stats_archive_hash = _read_zip(Path(stats_zip))
    merged: dict[str, bytes] = {}
    for collection in (basic_files, stats_files):
        for name, data in collection.items():
            if name in merged and merged[name] != data:
                raise ValueError(f"Basic Info and Stats ZIPs contain conflicting {name}")
            merged[name] = data

    required = {**BASIC_FILES, **STATS_FILES}
    missing = sorted(set(required) - set(merged))
    if missing:
        raise ValueError("Export ZIPs are incomplete; missing " + ", ".join(missing))

    parsed: dict[str, tuple[list[str], list[dict[str, str]]]] = {}
    working: dict[str, bytes] = {}
    source_hashes: dict[str, str] = {}
    working_hashes: dict[str, str] = {}
    for name, expected_headers in required.items():
        source_hashes[name] = hashlib.sha256(merged[name]).hexdigest()
        fields, rows = _parse_csv(merged[name], name)
        absent = sorted(expected_headers - set(fields))
        if absent:
            raise ValueError(f"{name} is missing required columns: {', '.join(absent)}")
        parsed[name] = (fields, rows)
        if not rows and name not in {"MEGA_trades.csv", "MEGA_draft.csv"}:
            raise ValueError(f"Required export {name} contains a header only")
        working[name] = _canonical_csv(fields, rows)
        working_hashes[name] = hashlib.sha256(working[name]).hexdigest()

    users_path = Path(users_csv)
    users_bytes = users_path.read_bytes()
    user_fields, user_rows = _parse_csv(users_bytes, str(users_path))
    absent_user_headers = sorted(USERS_HEADERS - set(user_fields))
    if absent_user_headers:
        raise ValueError(f"Independent user map is missing required columns: {', '.join(absent_user_headers)}")
    users_working = _canonical_csv(user_fields, user_rows)
    working["MEGA_users.csv"] = users_working
    source_hashes["MEGA_users.csv"] = hashlib.sha256(users_bytes).hexdigest()
    working_hashes["MEGA_users.csv"] = hashlib.sha256(users_working).hexdigest()

    elo_bytes = Path(elo_csv).read_bytes()
    elo_fields, elo_rows = _parse_csv(elo_bytes, str(elo_csv))
    elo_column = f"Week {elo_source_week}+"
    if not {"Team", "GM", elo_column}.issubset(set(elo_fields)):
        raise ValueError(f"ELO file must include Team, GM and {elo_column}")
    elo_source_hash = hashlib.sha256(elo_bytes).hexdigest()
    working["mega_elo.csv"] = _canonical_csv(elo_fields, elo_rows)
    source_hashes["mega_elo.csv"] = elo_source_hash
    working_hashes["mega_elo.csv"] = hashlib.sha256(working["mega_elo.csv"]).hexdigest()

    team_fields, team_rows = parsed["MEGA_teams.csv"]
    del team_fields
    team_rows = [row for row in team_rows if (row.get("seasonIndex") or "").strip() == str(season_index)]
    if not team_rows:
        raise ValueError(f"MEGA_teams.csv contains no teams for seasonIndex={season_index}")
    teams_by_key: dict[str, str] = {}
    team_rows_by_key: dict[str, dict[str, str]] = {}
    calendar_years: set[str] = set()
    export_weeks: set[str] = set()
    for row in team_rows:
        name = normalize_team_display(row.get("displayName", ""))
        key = normalize_team_name(name)
        if not key or key in teams_by_key:
            raise ValueError(f"Duplicate or invalid team identity in target season: {name!r}")
        teams_by_key[key] = name
        team_rows_by_key[key] = row
        calendar_years.add(_required(row.get("calendarYear", ""), "team calendarYear"))
        export_weeks.add(_required(row.get("weekIndex", ""), "team weekIndex"))
    if len(calendar_years) != 1 or len(export_weeks) != 1:
        raise ValueError("Target team rows disagree on calendarYear or export weekIndex")

    game_fields, game_rows = parsed["MEGA_games.csv"]
    del game_fields
    selected_games = [row for row in game_rows
                      if row.get("seasonIndex", "").strip() == str(season_index)
                      and row.get("stageIndex", "").strip() == "1"]
    if not selected_games:
        raise ValueError(f"MEGA_games.csv contains no regular-season games for seasonIndex={season_index}")
    ids: set[str] = set()
    max_completed_display_week = 0
    for row in selected_games:
        game_id = _required(row.get("gameId", ""), "gameId")
        if game_id in ids:
            raise ValueError(f"Duplicate gameId in target regular season: {game_id}")
        ids.add(game_id)
        for field in ("homeTeam", "awayTeam"):
            key = normalize_team_name(normalize_team_display(row.get(field, "")))
            if key not in teams_by_key:
                raise ValueError(f"Game {game_id} has unknown {field} team {row.get(field)!r}")
        try:
            week_index = int(row.get("weekIndex", ""))
            status = int(row.get("status", ""))
        except (TypeError, ValueError) as exc:
            raise ValueError(f"Game {game_id} has invalid weekIndex or status") from exc
        if status in (2, 3, 4):
            max_completed_display_week = max(max_completed_display_week, week_index + 1)

    ranking_rows = parsed["MEGA_rankings.csv"][1]
    selected_rankings = [row for row in ranking_rows
                         if row.get("seasonIndex", "").strip() == str(season_index)
                         and row.get("stageIndex", "").strip() == "1"]
    if not selected_rankings:
        raise ValueError(f"MEGA_rankings.csv contains no regular-season rows for seasonIndex={season_index}")
    for row in selected_rankings:
        key = normalize_team_name(normalize_team_display(row.get("team", "")))
        if key not in teams_by_key:
            raise ValueError(f"Ranking row references unknown team {row.get('team')!r}")
    try:
        latest_ranking_week = max(int(row.get("weekIndex", "-1")) for row in selected_rankings)
    except (TypeError, ValueError) as exc:
        raise ValueError("Rankings contain an invalid weekIndex") from exc
    if str(latest_ranking_week) not in export_weeks:
        raise ValueError("Latest rankings weekIndex does not match the target team export week")
    selected_rankings = [row for row in selected_rankings
                         if int(row.get("weekIndex", "-1")) == latest_ranking_week]

    for name in STATS_FILES:
        for row in parsed[name][1]:
            team_name = normalize_team_display(row.get("team__displayName", ""))
            if team_name and normalize_team_name(team_name) not in teams_by_key:
                raise ValueError(f"{name} references unknown team {team_name!r}")

    users = user_rows
    user_teams: set[str] = set()
    users_by_team: dict[str, dict[str, str]] = {}
    exported_users_by_team = {key: (row.get("userName") or "").strip() for key, row in team_rows_by_key.items()}
    for row in users:
        team = _required(row.get("Team", ""), "user Team")
        key = normalize_team_name(normalize_team_display(team))
        if key not in teams_by_key:
            raise ValueError(f"MEGA_users.csv references unknown team {team!r}")
        if key in users_by_team:
            raise ValueError(f"MEGA_users.csv has a duplicate team mapping: {team!r}")
        username = _required(row.get("neonsportzUserName", ""), f"{team} exported username")
        gm_label = _required(row.get("GM", ""), f"{team} GM label")
        source_week = _required(row.get("sourceWeek", ""), f"{team} user-map sourceWeek")
        if source_week != str(elo_source_week):
            raise ValueError(f"MEGA_users.csv sourceWeek for {team} does not match the selected ELO week")
        exported_username = exported_users_by_team[key]
        if username != exported_username:
            raise ValueError(f"MEGA_users.csv username for {team} does not match the exported team userName")
        users_by_team[key] = row
        user_teams.add(key)
    if user_teams != set(teams_by_key):
        raise ValueError("MEGA_users.csv does not map every target team")

    elo_data = _parse_csv(working["mega_elo.csv"], "normalized mega_elo.csv")[1]
    elo_teams: set[str] = set()
    for row in elo_data:
        team = (row.get("Team") or "").strip()
        if not team:
            continue
        key = normalize_team_name(team)
        if key in elo_teams:
            raise ValueError(f"Duplicate team in ELO file: {team}")
        elo_teams.add(key)
        _required(row.get(elo_column, ""), f"{team} {elo_column}")
        mapped_user = users_by_team.get(key)
        if mapped_user and (row.get("GM") or "").strip() != (mapped_user.get("GM") or "").strip():
            raise ValueError(f"ELO GM label for {team} does not match the independently maintained user map")
    if elo_teams != set(teams_by_key):
        missing_elo = sorted(teams_by_key[key] for key in set(teams_by_key) - elo_teams)
        extra_elo = sorted(elo_teams - set(teams_by_key))
        raise ValueError(f"ELO team mapping mismatch (missing={missing_elo}, extra keys={extra_elo})")

    try:
        calendar_year = int(next(iter(calendar_years)))
        export_week_index = int(next(iter(export_weeks)))
    except ValueError as exc:
        raise ValueError("calendarYear and export weekIndex must be integers") from exc
    snapshot_basis = {
        "basicInfoZipSha256": basic_archive_hash,
        "statsZipSha256": stats_archive_hash,
        "inputSourceSha256": source_hashes,
        "eloSourceWeek": elo_source_week,
        "seasonIndex": season_index,
    }
    snapshot_id = hashlib.sha256(json.dumps(snapshot_basis, sort_keys=True, separators=(",", ":")).encode()).hexdigest()[:16]
    metadata = {
        "game": edition,
        "seasonIndex": season_index,
        "seasonNumber": season_index + 1,
        "calendarYear": calendar_year,
        "completedThroughWeek": max_completed_display_week,
        "exportWeekIndex": export_week_index,
        "nextScheduledWeek": max_completed_display_week + 1,
        "eloSourceWeek": elo_source_week,
        "eloUsage": f"Week {elo_source_week} ELO ratings used with the validated export snapshot",
        "snapshotId": snapshot_id,
        "hashContractVersion": HASH_CONTRACT_VERSION,
        "hashNormalization": "newline-lf-v1",
        "sourceArchives": {"basicInfoZipSha256": basic_archive_hash, "statsZipSha256": stats_archive_hash},
        "independentSourceFiles": {
            "usersCsv": {"path": users_path.name, "sha256": source_hashes["MEGA_users.csv"]},
            "eloCsv": {"path": Path(elo_csv).name, "sha256": elo_source_hash},
        },
        "inputs": [
            {
                "path": name,
                "sourceSha256": source_hashes[name],
                "workingSha256": working_hashes[name],
                "canonicalSha256": canonical_input_sha256(working[name]),
            }
            for name in sorted(working)
        ],
    }
    CycleContext.from_metadata(metadata, Path.cwd(), input_bytes=working)
    return working, metadata


def activate_snapshot(root: Path, working: dict[str, bytes], metadata: dict[str, Any]) -> None:
    """Replace all active CSVs and metadata with rollback on a failed replace."""
    root = Path(root)
    CycleContext.from_metadata(metadata, root, input_bytes=working)
    metadata_path = Path("docs/data/import_metadata.json")
    targets = {root / name: content for name, content in working.items()}
    targets[root / metadata_path] = (json.dumps(metadata, indent=2, ensure_ascii=False) + "\n").encode("utf-8")
    staged = Path(tempfile.mkdtemp(prefix=".mega-import-", dir=root))
    backups: dict[Path, Path | None] = {}
    replaced: list[Path] = []
    try:
        staged_targets = {}
        for index, (target, content) in enumerate(targets.items()):
            staged_path = staged / "new" / str(index)
            staged_path.parent.mkdir(parents=True, exist_ok=True)
            staged_path.write_bytes(content)
            staged_targets[target] = staged_path
            if target.exists():
                backup = staged / "backup" / str(index)
                backup.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(target, backup)
                backups[target] = backup
            else:
                backups[target] = None
        for target, staged_path in staged_targets.items():
            target.parent.mkdir(parents=True, exist_ok=True)
            os.replace(staged_path, target)
            replaced.append(target)
    except Exception:
        for target in reversed(replaced):
            backup = backups[target]
            if backup is None:
                target.unlink(missing_ok=True)
            else:
                os.replace(backup, target)
        raise
    finally:
        shutil.rmtree(staged, ignore_errors=True)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate matched NeonSportz export ZIPs and ELO inputs")
    parser.add_argument("--basic-info-zip", type=Path, required=True)
    parser.add_argument("--stats-zip", type=Path, required=True)
    parser.add_argument("--elo-csv", type=Path, required=True)
    parser.add_argument("--users-csv", type=Path, required=True,
                        help="Independent GM-label/exported-username mapping; it is not part of the NeonSportz ZIPs")
    parser.add_argument("--season-index", type=int, required=True, help="Zero-based CSV seasonIndex")
    parser.add_argument("--elo-source-week", type=int, required=True)
    parser.add_argument("--edition", default="Madden 27", help="Game edition label in import metadata")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent.parent)
    parser.add_argument("--activate", action="store_true", help="Replace active CSVs only after all checks pass")
    args = parser.parse_args(argv)
    try:
        working, metadata = validate_snapshot(
            args.basic_info_zip, args.stats_zip, args.elo_csv, args.users_csv,
            season_index=args.season_index, elo_source_week=args.elo_source_week, edition=args.edition,
        )
        print(f"Snapshot {metadata['snapshotId']} valid: Madden 27 season {metadata['seasonNumber']}, "
              f"week {metadata['completedThroughWeek']} results, Week {metadata['eloSourceWeek']} ELO, "
              f"{len(working)} CSV files.")
        if args.activate:
            activate_snapshot(args.root, working, metadata)
            print(f"Activated validated snapshot under {args.root}")
        else:
            print("Validation only; active files were not changed. Re-run with --activate to install this snapshot.")
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(f"Import validation failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
