"""Compatibility imports; implementation lives in the mega package."""

from pathlib import Path
import sys

# Existing direct-script commands also work outside the repository directory.
if not __package__:
    repository_root = str(Path(__file__).resolve().parents[1])
    if repository_root not in sys.path:
        sys.path.insert(0, repository_root)

from mega.inputs.cycle import (
    CycleContext,
    HASH_CONTRACT_VERSION,
    canonical_input_bytes,
    canonical_input_sha256,
    _validate_elo_bytes,
)

__all__ = ['CycleContext', 'HASH_CONTRACT_VERSION', 'canonical_input_bytes', 'canonical_input_sha256']
