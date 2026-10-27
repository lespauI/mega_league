"""Read-only checks for the assembled, active static site."""

from __future__ import annotations

import hashlib
import json
import re
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit

from mega.inputs.cycle import CycleContext


class _Assets(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.references = []

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        attribute = "href" if tag in {"a", "link"} else "src"
        if tag in {"a", "link", "script", "img", "iframe", "source"} and values.get(attribute):
            self.references.append(values[attribute])


def _local_path(root: Path, parent: Path, reference: str) -> Path | None:
    parsed = urlsplit(reference)
    if parsed.scheme or parsed.netloc or not parsed.path:
        return None
    path = unquote(parsed.path)
    target = (root / path.lstrip("/") if path.startswith("/") else parent / path).resolve()
    if not target.is_relative_to(root):
        raise ValueError(f"Local URL leaves the publication root: {reference}")
    if target.is_dir():
        target /= "index.html"
    return target


def _module_imports(source: str) -> list[str]:
    static = re.compile(r"(?:\bimport\s*(?:[^'\"]*?\s+from\s*)?|\bexport\s+[^'\"]*?\s+from\s*)['\"]([^'\"]+)['\"]")
    dynamic = re.compile(r"\bimport\s*\(\s*['\"]([^'\"]+)['\"]\s*\)")
    return [name for name in static.findall(source) + dynamic.findall(source) if name.startswith(".")]


def validate_site(root: Path, *, context: CycleContext | None = None) -> list[str]:
    """Check enabled pages, browser inputs, build hashes, and local dependencies.

    Historical season pages and disabled integrations are excluded. A declared
    current page must have all its data, even when navigation would hide it.
    No files are written and no remote resources are requested.
    """
    from mega.pipeline.manifests import validate_browser_data

    root = Path(root).resolve()
    errors = []
    try:
        context = context or CycleContext.from_file(root / "docs/data/import_metadata.json", root)
        inventory = json.loads((root / "docs/site_manifest.json").read_text(encoding="utf-8"))
        build = json.loads((root / "output/build_manifest.json").read_text(encoding="utf-8"))
        if not isinstance(inventory, dict) or not isinstance(build, dict):
            raise ValueError("Site and build manifests must be JSON objects")
        if inventory.get("schemaVersion") != 1 or not isinstance(inventory.get("pages"), list):
            raise ValueError("Unsupported site inventory")
        if not isinstance(build.get("artifacts"), dict):
            raise ValueError("Build manifest is missing its artifact map")
        browser_build = json.loads((root / "docs/data/build_manifest.json").read_text(encoding="utf-8"))
        if browser_build != build:
            raise ValueError("Browser and pipeline build manifests disagree")
        if any(not isinstance(entry, dict) for entry in inventory["pages"]):
            raise ValueError("Site inventory pages must be objects")
        if build.get("complete") is not True or build.get("snapshotId") != context.snapshot_id:
            raise ValueError("Site requires a complete build for the active input snapshot")
        browser_data = validate_browser_data(root, context)
    except (OSError, ValueError, TypeError, KeyError) as exc:
        return [str(exc)]

    artifacts = build.get("artifacts", {})
    for name, digest in artifacts.items():
        path = (root / name).resolve()
        if not path.is_relative_to(root) or not path.is_file():
            errors.append(f"Missing or unsafe build artifact: {name}")
        elif hashlib.sha256(path.read_bytes()).hexdigest() != digest:
            errors.append(f"Build artifact changed: {name}")

    pending = [root / "index.html"]
    for entry in inventory["pages"]:
        if entry.get("feature") and entry["feature"] not in context.enabled_features:
            continue
        if entry.get("seasonScoped"):
            season = re.search(r"season(\d+)", entry.get("path", ""))
            if not season or int(season.group(1)) != context.display_season:
                continue
        page = (root / "docs" / entry.get("path", "")).resolve()
        if not page.is_relative_to(root / "docs") or not page.is_file():
            errors.append(f"Missing or unsafe active page: {entry.get('path')}")
            continue
        pending.append(page)
        for name in entry.get("requires", []):
            if name not in artifacts:
                errors.append(f"Page {entry['path']} requires an artifact outside the build: {name}")
        for key in entry.get("requiresData", []):
            if key not in browser_data.get("data", {}):
                errors.append(f"Page {entry['path']} requires an undeclared browser dataset: {key}")

    visited = set()
    while pending:
        path = pending.pop()
        if path in visited:
            continue
        visited.add(path)
        if not path.is_file():
            errors.append(f"Missing site file: {path.relative_to(root)}")
            continue
        if path.suffix not in {".html", ".js", ".css"}:
            continue
        source = path.read_text(encoding="utf-8")
        references = []
        if path.suffix == ".html":
            parser = _Assets()
            parser.feed(source)
            references.extend(parser.references)
        if path.suffix in {".html", ".js"}:
            references.extend(_module_imports(source))
        for reference in references:
            try:
                target = _local_path(root, path.parent, reference)
            except ValueError as exc:
                errors.append(f"{path.relative_to(root)}: {exc}")
                continue
            if target is None:
                continue
            if not target.is_file():
                errors.append(f"Broken local dependency in {path.relative_to(root)}: {reference}")
            elif target.suffix in {".js", ".css"}:
                pending.append(target)
    return sorted(set(errors))
