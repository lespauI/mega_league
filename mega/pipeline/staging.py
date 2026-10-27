"""Create clean, isolated workspaces for staged pipeline builds."""

from __future__ import annotations

import hashlib
import shutil
import tempfile
from pathlib import Path

from .artifacts import PROTECTED_OUTPUT_FILES, clear_owned_artifacts, is_owned_artifact


_TEXT_ARTIFACT_SUFFIXES = frozenset({".csv", ".json", ".html", ".md", ".js", ".css"})


def sha256_file(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def normalize_owned_text_artifacts(root: Path) -> None:
    """Give generated text files stable LF bytes before recording hashes.

    The registry excludes raw exports, maintained source pages, and protected
    formula/model files, so this only changes generated publication artifacts.
    """
    root = Path(root)
    candidates = [root / "index.html"]
    for directory in (root / "output", root / "docs"):
        if directory.is_dir():
            candidates.extend(directory.rglob("*"))
    for path in candidates:
        if not path.is_file() or path.suffix.lower() not in _TEXT_ARTIFACT_SUFFIXES:
            continue
        relative = path.relative_to(root).as_posix()
        if not is_owned_artifact(relative):
            continue
        original = path.read_bytes()
        normalized = original.replace(b"\r\n", b"\n").replace(b"\r", b"\n")
        if normalized != original:
            path.write_bytes(normalized)


def protected_output_files(root: Path) -> list[Path]:
    output = Path(root) / "output"
    files = [output / name for name in PROTECTED_OUTPUT_FILES if (output / name).is_file()]
    models = output / "trained_models"
    if models.is_dir():
        files.extend(path for path in models.rglob("*") if path.is_file())
    return sorted(files)


def protected_hashes(root: Path) -> dict[str, str]:
    return {path.relative_to(root).as_posix(): sha256_file(path) for path in protected_output_files(root)}


def create_staging_workspace(repository_root: Path) -> tuple[Path, Path, dict[str, str]]:
    """Copy maintained inputs/source and protected assets into a clean build tree."""
    repository_root = Path(repository_root).resolve()
    protected = protected_hashes(repository_root)
    temporary_root = Path(tempfile.mkdtemp(prefix=".mega-build-", dir=repository_root))
    workspace = temporary_root / "workspace"

    excluded = {
        ".git", "archive", "output", "node_modules", "__pycache__", ".pytest_cache",
        ".zenflow", ".idea", ".DS_Store", ".cache", "build", "dist", "myenv", ".venv",
        "test-results", "playwright-report", "playwright/.cache",
    }

    def ignore(directory: str, names: list[str]) -> set[str]:
        return {
            name for name in names
            if name in excluded or name.startswith(".mega-build-") or name.startswith(".mega-import-")
        }

    shutil.copytree(repository_root, workspace, ignore=ignore)
    staged_output = workspace / "output"
    staged_output.mkdir(parents=True, exist_ok=True)
    for relative in protected:
        source = repository_root / relative
        target = workspace / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)

    clear_owned_artifacts(workspace)

    if protected != protected_hashes(workspace):
        shutil.rmtree(temporary_root, ignore_errors=True)
        raise ValueError("Protected formula/model files changed while creating the staging workspace")
    return temporary_root, workspace, protected


# Compatibility aliases used by scripts.pipeline_tasks and older tooling.
_sha256 = sha256_file
_protected_hashes = protected_hashes
