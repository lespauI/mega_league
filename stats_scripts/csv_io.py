"""Compatibility imports; implementation lives in the mega package."""

from pathlib import Path
import sys

# Existing direct-script commands also work outside the repository directory.
if not __package__:
    repository_root = str(Path(__file__).resolve().parents[1])
    if repository_root not in sys.path:
        sys.path.insert(0, repository_root)

from mega.inputs.csv import (
    REQUIRED_HEADERS_BY_NAME,
    load_csv,
)

__all__ = ['REQUIRED_HEADERS_BY_NAME', 'load_csv']
