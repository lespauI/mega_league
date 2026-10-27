"""Transactional publication of manifest-owned staged artifacts."""

from __future__ import annotations

import os
import shutil
from pathlib import Path
from typing import Callable

from .artifacts import is_owned_artifact
from .manifests import BUILD_MANIFEST_SCHEMA_VERSION, _read_build_manifest
from .staging import sha256_file


def publish_staged_changes(
    workspace: Path,
    repository_root: Path,
    temporary_root: Path,
    group: str,
    *,
    replace_func: Callable | None = None,
) -> list[str]:
    """Publish manifest-owned files transactionally, rolling back on error.

    Obsolete files are removed only when a complete same-snapshot manifest
    previously owned them. Across snapshots, old generated paths are retained
    because they may be historical links or results.
    """
    workspace = Path(workspace)
    repository_root = Path(repository_root)
    temporary_root = Path(temporary_root)
    manifest = _read_build_manifest(workspace)
    if not manifest or manifest.get("schemaVersion") != BUILD_MANIFEST_SCHEMA_VERSION or manifest.get("complete") is not True:
        raise ValueError("Cannot publish without a complete artifact-ownership manifest")
    artifacts = manifest.get("artifacts", {})
    candidates: set[Path] = set()
    for relative, digest in artifacts.items():
        rel_path = Path(relative)
        if not is_owned_artifact(relative) or rel_path.is_absolute() or ".." in rel_path.parts:
            raise ValueError(f"Manifest contains an unowned or unsafe artifact: {relative}")
        source = workspace / rel_path
        if not source.is_file() or sha256_file(source) != digest:
            raise ValueError(f"Manifest-owned staged artifact is missing or changed: {relative}")
        candidates.add(rel_path)
    candidates.update({Path("output/build_manifest.json"), Path("docs/data/build_manifest.json")})

    previous = _read_build_manifest(repository_root)
    obsolete: set[Path] = set()
    if (previous and previous.get("schemaVersion") == BUILD_MANIFEST_SCHEMA_VERSION
            and previous.get("complete") is True
            and previous.get("snapshotId") == manifest.get("snapshotId")):
        for relative in set(previous.get("artifacts", {})) - set(artifacts):
            if is_owned_artifact(relative):
                obsolete.add(Path(relative))

    if (workspace / "index.html").is_file():
        candidates.add(Path("index.html"))

    backups: dict[Path, Path | None] = {}
    replaced: list[Path] = []
    replace = replace_func or os.replace
    try:
        for index, relative in enumerate(sorted(candidates | obsolete, key=lambda item: item.as_posix())):
            if "archive" in relative.parts or relative.is_absolute() or ".." in relative.parts:
                raise ValueError(f"Refusing to publish a protected path: {relative}")
            target = repository_root / relative
            if target.exists():
                backup = temporary_root / "backup" / str(index)
                backup.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(target, backup)
                backups[target] = backup
            else:
                backups[target] = None
            if relative in obsolete:
                target.unlink(missing_ok=True)
                replaced.append(target)
                continue
            source = workspace / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            staged_copy = temporary_root / "publish" / str(index)
            staged_copy.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, staged_copy)
            replace(staged_copy, target)
            replaced.append(target)
    except Exception:
        for target in reversed(replaced):
            backup = backups[target]
            if backup is None:
                target.unlink(missing_ok=True)
            else:
                rollback = temporary_root / "rollback" / str(len(replaced))
                rollback.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(backup, rollback)
                replace(rollback, target)
        raise
    published = candidates | obsolete
    return [path.as_posix() for path in sorted(published, key=lambda item: item.as_posix())]
