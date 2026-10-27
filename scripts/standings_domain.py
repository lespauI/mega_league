"""Compatibility imports; implementation lives in the mega package."""

from pathlib import Path
import sys

# Existing direct-script commands also work outside the repository directory.
if not __package__:
    repository_root = str(Path(__file__).resolve().parents[1])
    if repository_root not in sys.path:
        sys.path.insert(0, repository_root)

from mega.standings.records import (
    calculate_team_stats,
)

__all__ = ['calculate_team_stats']
