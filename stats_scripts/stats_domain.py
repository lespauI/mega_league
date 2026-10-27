"""Compatibility imports; implementation lives in the mega package."""

from pathlib import Path
import sys

# Existing direct-script commands also work outside the repository directory.
if not __package__:
    repository_root = str(Path(__file__).resolve().parents[1])
    if repository_root not in sys.path:
        sys.path.insert(0, repository_root)

from mega.inputs.identity import (
    safe_float,
    normalize_team_display,
)

__all__ = ['safe_float', 'normalize_team_display']
