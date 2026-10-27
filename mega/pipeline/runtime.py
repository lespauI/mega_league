"""Reusable process execution and browser-data publication functions."""

from __future__ import annotations

import csv
import shutil
import subprocess
import sys
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from mega.inputs.cycle import CycleContext
from mega.inputs.elo import normalize_team_name, read_elo_map
from .manifests import write_data_manifest


class ScriptStatus(str, Enum):
    SUCCEEDED = "succeeded"
    SKIPPED = "skipped"
    FAILED = "failed"


@dataclass(frozen=True)
class ScriptResult:
    status: ScriptStatus
    description: str
    returncode: int | None = None
    error: str | None = None


def season_start_row(season_index, games_csv="MEGA_games.csv"):
    """Locate the requested CSV season without legacy export row offsets."""
    with open(games_csv, newline="", encoding="utf-8") as stream:
        for index, row in enumerate(csv.DictReader(stream), 1):
            if row.get("seasonIndex") == str(season_index) and row.get("stageIndex") == "1":
                return index
    raise ValueError(f"No regular-season games for seasonIndex={season_index}")


def publish_browser_data(season_index, root=Path(".")):
    """Copy a complete current data set to the browser paths and publish its contract."""
    root = Path(root)
    destination = root / "docs/data"
    destination.mkdir(parents=True, exist_ok=True)
    season = season_index + 1
    sources = {
        "MEGA_teams.csv": "MEGA_teams.csv",
        "MEGA_users.csv": "MEGA_users.csv",
        "mega_elo.csv": "mega_elo.csv",
        "output/playoff_probabilities.json": "playoff_probabilities.json",
        f"output/sos/season{season}_elo.csv": f"season{season}_elo.csv",
        f"output/schedules/season{season}/all_schedules.json": f"schedules_season{season}.json",
        "output/ranked_sos_by_conference.csv": f"ranked_sos_by_conference_season{season}.csv",
    }
    resolved_sources = {source: root / source for source in sources}
    missing = [path for path in resolved_sources.values() if not path.is_file()]
    if missing:
        raise FileNotFoundError("Required browser artifacts are missing: " + ", ".join(map(str, missing)))
    for source, name in sources.items():
        shutil.copyfile(resolved_sources[source], destination / name)

    context = CycleContext.from_file(destination / "import_metadata.json", root)
    if context.csv_season_index != season_index:
        raise ValueError(
            f"browser data seasonIndex={season_index} does not match cycle metadata "
            f"seasonIndex={context.csv_season_index}"
        )
    source_week = context.elo_source_week
    ratings = read_elo_map(
        str(root / "mega_elo.csv"), source_week=source_week,
        root=root, season_index=season_index,
    )
    with (root / "mega_elo.csv").open("r", newline="", encoding="utf-8-sig") as source_stream:
        source_rows = csv.DictReader(source_stream)
        with (destination / "current_elo.csv").open("w", newline="", encoding="utf-8") as output_stream:
            writer = csv.writer(output_stream, lineterminator="\n")
            writer.writerow(("Team", "GM", "ELO", "sourceWeek"))
            for row in source_rows:
                team = (row.get("Team") or "").strip()
                rating = ratings.get(normalize_team_name(team))
                if rating is None:
                    raise ValueError(f"No Week {source_week}+ ELO rating for {team!r}")
                writer.writerow((team, (row.get("GM") or "").strip(), f"{rating:g}", source_week))

    write_data_manifest(root, context)


def run_command(script_name, description, optional=False, extra_args=None, enabled=True, working_directory=None):
    """Run a script and distinguish disabled, failed, and successful states."""
    print("\n" + "=" * 80)
    print(f"Running: {description}")
    if optional:
        print("(Optional feature)")
    print("=" * 80)

    if not enabled:
        print(f"↷ {description} disabled by configuration")
        return ScriptResult(ScriptStatus.SKIPPED, description)

    try:
        cwd = Path(working_directory) if working_directory is not None else Path(__file__).resolve().parents[2]
        script_path = Path(script_name)
        if not script_path.is_absolute():
            script_path = cwd / script_path
        cmd = [sys.executable, str(script_path)]
        if extra_args:
            cmd.extend(extra_args)
        result = subprocess.run(cmd, cwd=str(cwd), capture_output=False, text=True)
        if result.returncode == 0:
            print(f"✓ {description} completed successfully")
            return ScriptResult(ScriptStatus.SUCCEEDED, description, result.returncode)
        print(f"✗ {description} failed with exit code {result.returncode}")
        return ScriptResult(ScriptStatus.FAILED, description, result.returncode)
    except Exception as exc:
        print(f"✗ Error running {description}: {str(exc)}")
        return ScriptResult(ScriptStatus.FAILED, description, error=str(exc))


def run_script(script_name, description, optional=False, extra_args=None):
    """Compatibility helper that returns a boolean for older runners."""
    result = run_command(script_name, description, optional, extra_args)
    return result.status == ScriptStatus.SUCCEEDED
