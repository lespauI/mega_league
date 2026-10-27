"""Build and browser-data manifests for one validated input snapshot."""

from __future__ import annotations

import json
import platform
from pathlib import Path

from mega.inputs.cycle import CycleContext

from .artifacts import BROWSER_DATA, is_owned_artifact, task_output_paths
from .staging import normalize_owned_text_artifacts, protected_hashes, sha256_file


DATA_MANIFEST_SCHEMA_VERSION = 1
BUILD_MANIFEST_SCHEMA_VERSION = 2


def browser_data_urls(context: CycleContext) -> dict[str, str]:
    return {
        key: artifact.resolved(context.display_season)[1]
        for key, artifact in BROWSER_DATA.items()
    }


def _browser_cycle(context: CycleContext) -> dict[str, int | str]:
    return {
        "edition": context.edition,
        "csvSeasonIndex": context.csv_season_index,
        "displaySeason": context.display_season,
        "calendarYear": context.calendar_year,
        "completedThroughWeek": context.completed_through_week,
        "exportWeekIndex": context.export_week_index,
        "eloSourceWeek": context.elo_source_week,
    }


def _browser_required_paths(root: Path, context: CycleContext) -> list[str]:
    return [
        artifact.resolved(context.display_season)[0]
        for artifact in BROWSER_DATA.values()
        if not (Path(root) / artifact.resolved(context.display_season)[0]).is_file()
    ]


def validate_browser_data(root: Path, context: CycleContext | None = None) -> dict:
    """Validate the browser manifest, its active snapshot, URLs, and source files.

    Community prediction storage is intentionally absent from the browser data
    registry; it remains an optional site feature outside this required contract.
    """
    root = Path(root)
    if context is None:
        context = CycleContext.from_file(root / "docs" / "data" / "import_metadata.json", root)

    path = root / "docs" / "data" / "data_manifest.json"
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"Cannot read browser data manifest {path}: {exc}") from exc
    if not isinstance(manifest, dict):
        raise ValueError("Browser data manifest must be a JSON object")
    if manifest.get("schemaVersion") != DATA_MANIFEST_SCHEMA_VERSION:
        raise ValueError("Unsupported browser data manifest schemaVersion")
    if manifest.get("snapshotId") != context.snapshot_id:
        raise ValueError("Browser data manifest belongs to a different input snapshot")
    if manifest.get("cycle") != _browser_cycle(context):
        raise ValueError("Browser data manifest cycle does not match active cycle metadata")
    if manifest.get("data") != browser_data_urls(context):
        raise ValueError("Browser data manifest URLs do not match the registered browser data contract")

    missing = _browser_required_paths(root, context)
    if missing:
        raise FileNotFoundError("Required browser data files are missing: " + ", ".join(missing))
    return manifest


def write_data_manifest(root: Path, context: CycleContext) -> dict:
    """Write the browser data contract, then validate its referenced files."""
    root = Path(root)
    missing = _browser_required_paths(root, context)
    if missing:
        raise FileNotFoundError("Required browser data files are missing: " + ", ".join(missing))
    manifest = {
        "schemaVersion": DATA_MANIFEST_SCHEMA_VERSION,
        "snapshotId": context.snapshot_id,
        "cycle": _browser_cycle(context),
        "data": browser_data_urls(context),
    }
    path = root / "docs" / "data" / "data_manifest.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    return validate_browser_data(root, context)


def _read_build_manifest(root: Path) -> dict | None:
    path = Path(root) / "output" / "build_manifest.json"
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return value if isinstance(value, dict) else None


def _task_regenerates_path(relative: str, task_ids: list[str], display_season: int) -> bool:
    path = Path(relative).as_posix()
    for task_id in task_ids:
        if path in task_output_paths(task_id, display_season):
            return True
        if task_id == "roster_rankings" and path.startswith("output/team_rosters/"):
            return True
    return False


def write_build_manifest(
    workspace: Path,
    repository_root: Path,
    group: str,
    context: CycleContext,
    task_ids: list[str],
    *,
    include_index: bool = True,
) -> dict:
    """Write a manifest from owned, staged outputs and verified subset inputs."""
    workspace = Path(workspace)
    repository_root = Path(repository_root)
    previous = _read_build_manifest(repository_root)
    if group != "full":
        if not previous or previous.get("complete") is not True:
            raise ValueError("A subset build needs a successful full-build manifest first")
        if previous.get("schemaVersion") != BUILD_MANIFEST_SCHEMA_VERSION:
            raise ValueError("Existing build manifest predates artifact ownership; run a full build before a subset build")
        if previous.get("snapshotId") != context.snapshot_id:
            raise ValueError("A subset build cannot mix artifacts from a different input snapshot; run the full pipeline")

    artifacts: dict[str, str] = {}
    if group != "full" and previous:
        for relative, digest in previous.get("artifacts", {}).items():
            if not is_owned_artifact(relative):
                raise ValueError(f"Previous manifest claims an unowned artifact: {relative}")
            if relative == "index.html" and not include_index:
                continue
            path = workspace / relative
            if path.is_file() and sha256_file(path) == digest:
                artifacts[relative] = digest
            elif not _task_regenerates_path(relative, task_ids, context.display_season):
                raise ValueError(f"Subset build lost a required same-snapshot artifact: {relative}")

    # Verify carried-forward files against their previous raw hashes first,
    # then canonicalize before recording this build's hashes. This also lets a
    # subset build migrate an older CRLF manifest without touching repository
    # files or changing task output outside the staged workspace.
    normalize_owned_text_artifacts(workspace)

    output_root = workspace / "output"
    for path in output_root.rglob("*"):
        if not path.is_file():
            continue
        relative = path.relative_to(workspace).as_posix()
        if relative == "output/build_manifest.json":
            continue
        if relative in protected_hashes(workspace):
            continue
        if not is_owned_artifact(relative):
            raise ValueError(f"Staged build produced an artifact without an owner: {relative}")
        artifacts[relative] = sha256_file(path)

    docs_root = workspace / "docs"
    for path in docs_root.rglob("*"):
        if not path.is_file():
            continue
        relative = path.relative_to(workspace).as_posix()
        if relative == "docs/data/build_manifest.json":
            continue
        if is_owned_artifact(relative):
            artifacts[relative] = sha256_file(path)
        else:
            source = repository_root / relative
            if not source.is_file() or sha256_file(source) != sha256_file(path):
                raise ValueError(f"Staged build changed maintained source without an artifact owner: {relative}")

    index_path = workspace / "index.html"
    if include_index and index_path.is_file():
        artifacts["index.html"] = sha256_file(index_path)
    else:
        artifacts.pop("index.html", None)

    if "publish_browser_data" in task_ids:
        validate_browser_data(workspace, context)
    elif group != "full" and "docs/data/data_manifest.json" not in artifacts:
        raise ValueError("Subset build is missing its same-snapshot browser data manifest")
    elif group != "full":
        validate_browser_data(workspace, context)

    previous_groups = set(previous.get("groups", [])) if previous and previous.get("snapshotId") == context.snapshot_id else set()
    previous_tasks = set(previous.get("taskIds", [])) if previous and previous.get("snapshotId") == context.snapshot_id else set()
    manifest = {
        "schemaVersion": BUILD_MANIFEST_SCHEMA_VERSION,
        "snapshotId": context.snapshot_id,
        "edition": context.edition,
        "csvSeasonIndex": context.csv_season_index,
        "displaySeason": context.display_season,
        "calendarYear": context.calendar_year,
        "completedThroughWeek": context.completed_through_week,
        "exportWeekIndex": context.export_week_index,
        "eloSourceWeek": context.elo_source_week,
        "pythonRuntime": platform.python_version(),
        "simulationSeed": (
            0 if {"scenarios", "playoff_table"} & (previous_tasks | set(task_ids)) else None
        ),
        "complete": group == "full" or bool(previous and previous.get("complete")),
        "groups": sorted(previous_groups | {group}),
        "taskIds": sorted(previous_tasks | set(task_ids)),
        "artifacts": dict(sorted(artifacts.items())),
    }
    encoded = json.dumps(manifest, indent=2, ensure_ascii=False, sort_keys=True) + "\n"
    output_root.mkdir(parents=True, exist_ok=True)
    (output_root / "build_manifest.json").write_text(encoded, encoding="utf-8")
    data_root = workspace / "docs" / "data"
    data_root.mkdir(parents=True, exist_ok=True)
    (data_root / "build_manifest.json").write_text(encoded, encoding="utf-8")
    return manifest
