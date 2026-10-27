"""Compatibility facade for the shared package pipeline executor."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Callable

try:
    from run_utils import ScriptResult, ScriptStatus, publish_browser_data, run_command
except ImportError:  # imported as scripts.pipeline_tasks
    from scripts.run_utils import ScriptResult, ScriptStatus, publish_browser_data, run_command

try:
    from mega.pipeline.execution import (
        BROWSER_DATA,
        GENERATED_BROWSER_DATA,
        GENERATED_DOC_PAGES,
        GROUPS,
        PIPELINE_SIMULATION_SEED,
        Task,
        PROTECTED_OUTPUT_FILES,
        TASKS,
        TASK_OUTPUTS,
        _protected_hashes,
        _read_build_manifest,
        _resolve,
        _sha256,
        clear_owned_artifacts,
        create_staging_workspace,
        is_owned_artifact,
        pipeline_succeeded,
        publish_staged_changes,
        task_arguments,
        task_missing_outputs,
        task_output_paths,
        task_regenerates_path,
        validate_browser_data,
        validate_task_result,
        write_build_manifest,
        run_pipeline as _run_pipeline,
    )
except ModuleNotFoundError:  # direct runner invocation puts scripts/ first on sys.path
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from mega.pipeline.execution import (
        BROWSER_DATA,
        GENERATED_BROWSER_DATA,
        GENERATED_DOC_PAGES,
        GROUPS,
        PIPELINE_SIMULATION_SEED,
        Task,
        PROTECTED_OUTPUT_FILES,
        TASKS,
        TASK_OUTPUTS,
        _protected_hashes,
        _read_build_manifest,
        _resolve,
        _sha256,
        clear_owned_artifacts,
        create_staging_workspace,
        is_owned_artifact,
        pipeline_succeeded,
        publish_staged_changes,
        task_arguments,
        task_missing_outputs,
        task_output_paths,
        task_regenerates_path,
        validate_browser_data,
        validate_task_result,
        write_build_manifest,
        run_pipeline as _run_pipeline,
    )


def run_pipeline(
    group: str,
    season_index: int = 0,
    *,
    executor: Callable[..., ScriptResult] = run_command,
    staged: bool = True,
    publish: bool = True,
) -> list[ScriptResult]:
    """Keep established monkeypatch points while delegating to the package."""
    return _run_pipeline(
        group,
        season_index,
        executor=executor,
        staged=staged,
        publish=publish,
        publish_browser_data_func=publish_browser_data,
        run_command_func=run_command,
    )


__all__ = [
    "BROWSER_DATA", "GENERATED_BROWSER_DATA", "GENERATED_DOC_PAGES", "GROUPS",
    "PIPELINE_SIMULATION_SEED", "PROTECTED_OUTPUT_FILES", "TASKS", "TASK_OUTPUTS", "Task", "clear_owned_artifacts",
    "create_staging_workspace", "is_owned_artifact", "pipeline_succeeded", "publish_browser_data",
    "publish_staged_changes", "run_pipeline", "task_arguments", "task_missing_outputs",
    "task_output_paths", "task_regenerates_path", "validate_browser_data", "validate_task_result",
    "write_build_manifest",
]
