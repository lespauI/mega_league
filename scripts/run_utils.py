#!/usr/bin/env python3
"""Compatibility facade for shared pipeline runtime helpers."""

from __future__ import annotations

from pathlib import Path
import sys

if not __package__:
    repository_root = str(Path(__file__).resolve().parents[1])
    if repository_root not in sys.path:
        sys.path.insert(0, repository_root)

from mega.pipeline.runtime import (
    ScriptResult,
    ScriptStatus,
    publish_browser_data,
    run_command,
    season_start_row,
)


def run_script(script_name, description, optional=False, extra_args=None):
    """Compatibility wrapper returning a boolean for existing callers."""
    result = run_command(script_name, description, optional, extra_args)
    return result.status == ScriptStatus.SUCCEEDED


__all__ = [
    "ScriptResult", "ScriptStatus", "publish_browser_data", "run_command", "run_script",
    "season_start_row",
]
