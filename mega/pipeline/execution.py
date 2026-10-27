"""Single dependency graph shared by the supported pipeline runners.

Public names from the artifact package remain re-exported here for compatibility
with existing runners, tests, and local tooling.
"""

from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from mega.inputs.cycle import CycleContext
from mega.pipeline.runtime import ScriptResult, ScriptStatus, publish_browser_data, run_command

from .artifacts import (
    BROWSER_DATA,
    GENERATED_BROWSER_DATA,
    GENERATED_DOC_PAGES,
    PROTECTED_OUTPUT_FILES,
    TASK_OUTPUTS,
    clear_owned_artifacts,
    is_owned_artifact,
    task_output_paths,
)
from .manifests import _read_build_manifest, validate_browser_data, write_build_manifest
from .publication import publish_staged_changes
from .staging import _protected_hashes, _sha256, create_staging_workspace


PIPELINE_SIMULATION_SEED = 0


@dataclass(frozen=True)
class Task:
    task_id: str
    description: str
    script: str | None = None
    arguments: tuple[str, ...] = ()
    dependencies: tuple[str, ...] = ()
    optional: bool = False
    action: str | None = None


TASKS: dict[str, Task] = {
    "stints": Task("stints", "Player/team stints", "stats_scripts/build_player_team_stints.py"),
    "team_stats": Task("team_stats", "Team statistics", "stats_scripts/aggregate_team_stats.py", dependencies=("stints",)),
    "usage": Task("usage", "Player usage", "stats_scripts/aggregate_player_usage.py", dependencies=("stints", "team_stats")),
    "rankings_stats": Task("rankings_stats", "Rankings statistics", "stats_scripts/aggregate_rankings_stats.py", dependencies=("stints", "team_stats")),
    "trade_verify": Task("trade_verify", "Trade-aware stats verification", "scripts/verify_trade_stats.py", dependencies=("stints", "team_stats")),
    "sos_elo": Task("sos_elo", "ELO strength of schedule", "scripts/calc_sos_elo.py", dependencies=("inputs",)),
    "verify_sos_elo": Task("verify_sos_elo", "Verify ELO schedules and SoS", "scripts/verify_sos_elo.py", dependencies=("sos_elo",)),
    "sos_rankings": Task("sos_rankings", "Rankings strength of schedule", "scripts/calc_sos_by_rankings.py", dependencies=("inputs",)),
    "scenarios": Task("scenarios", "Playoff scenario simulation", "scripts/generate_all_team_scenarios.py", dependencies=("sos_rankings", "verify_sos_elo")),
    "week18_simulator": Task("week18_simulator", "Week 18 playoff simulator", "scripts/week18_simulator.py", dependencies=("inputs",)),
    "playoff_table": Task("playoff_table", "Playoff race table", "scripts/playoff_race_table.py", dependencies=("scenarios",)),
    "playoff_html": Task("playoff_html", "Playoff race report", "scripts/playoff_race_html.py", dependencies=("playoff_table",)),
    "scenario_html": Task("scenario_html", "Team scenario viewer", "scripts/generate_team_scenario_html.py", dependencies=("scenarios",)),
    "draft_race": Task("draft_race", "Draft pick race analysis", "scripts/top_pick_race_analysis.py", optional=True, dependencies=("scenarios",)),
    "roster_rankings": Task("roster_rankings", "Roster power rankings", "scripts/power_rankings_roster.py", dependencies=("inputs",)),
    "publish_browser_data": Task("publish_browser_data", "Browser data publication", dependencies=("verify_sos_elo", "sos_rankings", "scenarios"), action="publish"),
    "index": Task("index", "Navigation page generation", "scripts/generate_index.py"),
}

GROUPS: dict[str, tuple[str, ...]] = {
    "full": ("usage", "rankings_stats", "sos_elo", "verify_sos_elo", "sos_rankings", "playoff_table", "playoff_html", "scenario_html", "week18_simulator", "draft_race", "roster_rankings", "trade_verify", "publish_browser_data", "index"),
    "stats": ("usage", "rankings_stats", "trade_verify", "index"),
    "playoff": ("sos_elo", "verify_sos_elo", "sos_rankings", "scenarios", "playoff_table", "playoff_html", "scenario_html", "week18_simulator", "draft_race", "publish_browser_data", "index"),
}

def task_missing_outputs(workspace: Path, task_id: str, display_season: int) -> list[str]:
    missing = [rel for rel in task_output_paths(task_id, display_season) if not (workspace / rel).is_file()]
    if task_id == "roster_rankings":
        roster_dir = workspace / "output" / "team_rosters"
        main_rosters = []
        if roster_dir.is_dir():
            main_rosters = [path for path in roster_dir.glob("*.csv")
                            if not path.stem.endswith(("_Defense", "_Offense"))]
        if len(main_rosters) < 32:
            missing.append("output/team_rosters/<32 team roster CSVs>")
    return missing


def validate_task_result(result: ScriptResult, workspace: Path, task_id: str, display_season: int) -> ScriptResult:
    """Convert a zero-exit task into failure if its declared outputs are absent."""
    if result.status != ScriptStatus.SUCCEEDED:
        return result
    missing = task_missing_outputs(workspace, task_id, display_season)
    if not missing:
        return result
    return ScriptResult(
        ScriptStatus.FAILED,
        result.description,
        result.returncode,
        error="producer did not create required outputs: " + ", ".join(missing),
    )


def task_regenerates_path(relative: str, task_ids: list[str], display_season: int) -> bool:
    path = Path(relative).as_posix()
    for task_id in task_ids:
        if path in task_output_paths(task_id, display_season):
            return True
        if task_id == "roster_rankings" and path.startswith("output/team_rosters/"):
            return True
    return False


def task_arguments(task_id: str, season_index: int, context: CycleContext) -> list[str]:
    """Build the season and declared-ELO arguments for a task without running it."""
    task = TASKS[task_id]
    arguments = list(task.arguments)
    if task_id in {"sos_elo", "verify_sos_elo", "sos_rankings", "scenarios", "playoff_table", "playoff_html", "week18_simulator"}:
        if task_id == "sos_elo":
            arguments.extend(("--csv-season-index", str(season_index),
                              "--elo-source-week", str(context.elo_source_week)))
        elif task_id == "verify_sos_elo":
            arguments.extend(("--season-index", str(season_index + 1)))
        else:
            arguments.extend(("--season-index", str(season_index)))
    if task_id in {"scenarios", "playoff_table"}:
        arguments.extend(("--elo-source-week", str(context.elo_source_week)))
        arguments.extend(("--seed", str(PIPELINE_SIMULATION_SEED)))
    if task_id == "sos_rankings":
        arguments.extend(("--out-csv", "output/ranked_sos_by_conference.csv"))
    return arguments


def _resolve(selected: tuple[str, ...]) -> list[str]:
    ordered: list[str] = []
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(task_id: str) -> None:
        if task_id in visited or task_id == "inputs":
            return
        if task_id not in TASKS:
            raise ValueError(f"Unknown pipeline task or dependency: {task_id}")
        if task_id in visiting:
            raise ValueError(f"Pipeline dependency cycle includes {task_id}")
        visiting.add(task_id)
        for dependency in TASKS[task_id].dependencies:
            visit(dependency)
        visiting.remove(task_id)
        visited.add(task_id)
        ordered.append(task_id)

    for task_id in selected:
        visit(task_id)
    return ordered


def run_pipeline(
    group: str,
    season_index: int = 0,
    *,
    executor: Callable[..., ScriptResult] = run_command,
    staged: bool = True,
    publish: bool = True,
    publish_browser_data_func=publish_browser_data,
    run_command_func=run_command,
) -> list[ScriptResult]:
    """Run one selection in an isolated workspace and publish only a valid build."""
    if group not in GROUPS:
        raise ValueError(f"Unknown pipeline group: {group}")
    if season_index < 0:
        raise ValueError("CSV season index must be zero or greater")

    repository_root = Path(__file__).resolve().parent.parent.parent
    results: list[ScriptResult] = []
    required_inputs = {
        "stats": (
            "MEGA_teams.csv", "MEGA_passing.csv", "MEGA_rushing.csv", "MEGA_receiving.csv",
            "MEGA_defense.csv", "MEGA_punting.csv", "MEGA_kicking.csv", "MEGA_rankings.csv",
        ),
        "playoff": (
            "MEGA_teams.csv", "MEGA_players.csv", "MEGA_games.csv", "MEGA_rankings.csv",
            "MEGA_users.csv", "mega_elo.csv",
        ),
        "full": (
            "MEGA_teams.csv", "MEGA_players.csv", "MEGA_games.csv", "MEGA_rankings.csv",
            "mega_elo.csv", "MEGA_users.csv", "MEGA_passing.csv", "MEGA_rushing.csv",
            "MEGA_receiving.csv", "MEGA_defense.csv", "MEGA_punting.csv", "MEGA_kicking.csv",
        ),
    }[group]
    missing_inputs = [name for name in required_inputs if not (repository_root / name).is_file()]
    if missing_inputs:
        print("Missing required current-cycle inputs: " + ", ".join(missing_inputs))
        return [ScriptResult(ScriptStatus.FAILED, "Input preflight", error="missing: " + ", ".join(missing_inputs))]
    task_ids = _resolve(GROUPS[group])

    metadata_path = repository_root / "docs" / "data" / "import_metadata.json"
    try:
        context = CycleContext.from_file(metadata_path, repository_root)
    except (OSError, ValueError) as exc:
        return [ScriptResult(ScriptStatus.FAILED, "Cycle metadata preflight", error=str(exc))]
    if context.csv_season_index != season_index:
        return [ScriptResult(
            ScriptStatus.FAILED, "Cycle metadata preflight",
            error=f"requested seasonIndex={season_index} does not match active snapshot seasonIndex={context.csv_season_index}",
        )]

    temporary_root = None
    workspace = repository_root
    protected_before = _protected_hashes(repository_root)
    if staged:
        if group != "full":
            previous = _read_build_manifest(repository_root)
            if not previous or previous.get("complete") is not True:
                return [ScriptResult(ScriptStatus.FAILED, "Build preflight", error="subset build requires a complete prior full-build manifest")]
            if previous.get("schemaVersion") != 2:
                return [ScriptResult(ScriptStatus.FAILED, "Build preflight", error="existing manifest has no explicit artifact ownership; run the full pipeline")]
            if previous.get("snapshotId") != context.snapshot_id:
                return [ScriptResult(ScriptStatus.FAILED, "Build preflight", error="existing artifacts belong to another snapshot; run the full pipeline")]
            if "docs/data/data_manifest.json" not in previous.get("artifacts", {}):
                return [ScriptResult(ScriptStatus.FAILED, "Build preflight", error="existing full build has no browser data manifest; run the full pipeline")]
            try:
                validate_browser_data(repository_root, context)
            except (OSError, ValueError) as exc:
                return [ScriptResult(ScriptStatus.FAILED, "Build preflight", error=f"browser data manifest preflight failed: {exc}")]
            for relative, digest in previous.get("artifacts", {}).items():
                if not is_owned_artifact(relative) or Path(relative).is_absolute() or ".." in Path(relative).parts:
                    return [ScriptResult(ScriptStatus.FAILED, "Build preflight", error=f"manifest contains an unowned or unsafe artifact: {relative}")]
                path = repository_root / relative
                if not path.is_file() or _sha256(path) != digest:
                    return [ScriptResult(ScriptStatus.FAILED, "Build preflight", error=f"manifest-owned artifact changed or is missing: {relative}")]
        try:
            temporary_root, workspace, protected_before = create_staging_workspace(repository_root)
            if group != "full":
                previous = _read_build_manifest(repository_root) or {}
                for relative in previous.get("artifacts", {}):
                    if task_regenerates_path(relative, task_ids, context.display_season):
                        continue
                    source = repository_root / relative
                    target = workspace / relative
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(source, target)
        except Exception as exc:
            if temporary_root:
                shutil.rmtree(temporary_root, ignore_errors=True)
            return [ScriptResult(ScriptStatus.FAILED, "Staging preflight", error=str(exc))]

    if staged:
        def staged_executor(script, description, optional=False, extra_args=None):
            return run_command_func(script, description, optional, extra_args, working_directory=workspace)
        task_executor = staged_executor
    else:
        task_executor = executor

    stopped = False
    index_deferred = False
    try:
        for task_id in task_ids:
            task = TASKS[task_id]
            if stopped:
                results.append(ScriptResult(ScriptStatus.SKIPPED, task.description, error="pipeline stopped after an earlier failure"))
                continue
            if staged and task_id == "index":
                index_deferred = True
                continue
            if task.action == "publish":
                try:
                    publish_browser_data_func(season_index, root=workspace)
                    missing = task_missing_outputs(workspace, task_id, context.display_season)
                    if missing:
                        raise ValueError("Producer did not create required browser outputs: " + ", ".join(missing))
                    results.append(ScriptResult(ScriptStatus.SUCCEEDED, task.description, 0))
                    print(f"✓ {task.description} completed successfully")
                except Exception as exc:
                    results.append(ScriptResult(ScriptStatus.FAILED, task.description, error=str(exc)))
                    print(f"✗ {task.description} failed: {exc}")
                    stopped = True
                continue

            arguments = task_arguments(task_id, season_index, context)

            result = task_executor(task.script, task.description, task.optional, arguments or None)
            if staged:
                result = validate_task_result(result, workspace, task_id, context.display_season)
            results.append(result)
            if result.status == ScriptStatus.FAILED:
                stopped = True

        if stopped:
            return results
        if not staged:
            return results

        write_build_manifest(workspace, repository_root, group, context, task_ids, include_index=False)
        results.append(ScriptResult(ScriptStatus.SUCCEEDED, "Snapshot manifest", 0))
        if index_deferred:
            index_result = task_executor("scripts/generate_index.py", "Navigation page generation", False, None)
            index_result = validate_task_result(index_result, workspace, "index", context.display_season)
            results.append(index_result)
            if index_result.status == ScriptStatus.FAILED:
                return results
            write_build_manifest(workspace, repository_root, group, context, task_ids, include_index=True)

        from mega.site import validate_site
        site_errors = validate_site(workspace, context=context)
        if site_errors:
            raise ValueError("Staged site validation failed: " + "; ".join(site_errors))

        if protected_before != _protected_hashes(workspace):
            raise ValueError("Protected formula/model files changed during the staged build")
        if not publish:
            results.append(ScriptResult(ScriptStatus.SUCCEEDED, "Staged build validation (not published)", 0))
            return results
        published = publish_staged_changes(workspace, repository_root, temporary_root, group)
        results.append(ScriptResult(ScriptStatus.SUCCEEDED, f"Published {len(published)} staged files", 0))
    except Exception as exc:
        results.append(ScriptResult(ScriptStatus.FAILED, "Staged build publication", error=str(exc)))
    finally:
        if temporary_root:
            shutil.rmtree(temporary_root, ignore_errors=True)

    print("\nPipeline summary")
    for result in results:
        if result.status == ScriptStatus.SUCCEEDED:
            status = "✓"
        elif result.status == ScriptStatus.SKIPPED:
            status = "↷"
        else:
            status = "✗"
        detail = f" ({result.error})" if result.error else ""
        print(f"{status} {result.description}{detail}")
    return results


def pipeline_succeeded(results: list[ScriptResult]) -> bool:
    return all(result.status != ScriptStatus.FAILED for result in results)
