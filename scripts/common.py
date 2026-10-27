"""Compatibility module for shared ELO and identity helpers."""

from pathlib import Path
import sys

if not __package__:
    repository_root = str(Path(__file__).resolve().parents[1])
    if repository_root not in sys.path:
        sys.path.insert(0, repository_root)

from mega.inputs import elo as _implementation

# Use one module instance for legacy imports, including existing monkeypatches.
sys.modules[__name__] = _implementation
