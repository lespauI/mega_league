"""Static browser inventory, link, and local-module path checks."""

from __future__ import annotations

from html.parser import HTMLParser
import json
from pathlib import Path
import re
import unittest
from urllib.parse import urlsplit

from scripts.pipeline_tasks import is_owned_artifact

ROOT = Path(__file__).resolve().parents[1]


class AssetParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.paths = []
        self.module_entries = []

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        if tag == "script" and values.get("src"):
            self.paths.append(values["src"])
            if values.get("type") == "module":
                self.module_entries.append(values["src"])
        elif tag in {"a", "link", "img", "iframe", "source"}:
            key = "href" if tag in {"a", "link"} else "src"
            if values.get(key):
                self.paths.append(values[key])


def local_target(base: Path, reference: str) -> Path | None:
    parsed = urlsplit(reference.strip())
    if not parsed.path or parsed.scheme or parsed.netloc:
        return None
    return (base / parsed.path.split("?", 1)[0]).resolve()


def module_imports(source: str) -> list[str]:
    pattern = re.compile(r"(?:\bimport\s*(?:[^'\"]*?\s+from\s*)?|\bexport\s+[^'\"]*?\s+from\s*)['\"]([^'\"]+)['\"]")
    dynamic = re.compile(r"\bimport\s*\(\s*['\"]([^'\"]+)['\"]\s*\)")
    return pattern.findall(source) + dynamic.findall(source)


class SiteManifestTests(unittest.TestCase):
    def test_declared_pages_and_local_html_assets_exist(self):
        manifest = json.loads((ROOT / "docs/site_manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["schemaVersion"], 1)
        for entry in manifest["pages"]:
            page = ROOT / "docs" / entry["path"]
            if entry.get("kind") == "generated" and not page.is_file():
                self.assertTrue(is_owned_artifact(f"docs/{entry['path']}"),
                                f"generated site page has no pipeline owner: {entry['path']}")
                continue
            self.assertTrue(page.is_file(), f"site manifest page is missing: {entry['path']}")
            if page.suffix.lower() not in {".html", ".htm"}:
                continue
            parser = AssetParser()
            parser.feed(page.read_text(encoding="utf-8"))
            for reference in parser.paths:
                target = local_target(page.parent, reference)
                if target is None:
                    continue
                if target.is_file():
                    continue
                rel = target.relative_to(ROOT).as_posix() if target.is_relative_to(ROOT) else ""
                self.assertTrue(is_owned_artifact(rel), f"broken local link in {page.relative_to(ROOT)}: {reference}")

    def test_local_frontend_module_imports_resolve(self):
        manifest = json.loads((ROOT / "docs/site_manifest.json").read_text(encoding="utf-8"))
        pending = []
        for entry in manifest["pages"]:
            page = ROOT / "docs" / entry["path"]
            if not page.is_file() and entry.get("kind") == "generated":
                continue
            if page.suffix.lower() not in {".html", ".htm"}:
                continue
            page_source = page.read_text(encoding="utf-8")
            parser = AssetParser()
            parser.feed(page_source)
            for module in parser.module_entries:
                target = local_target(page.parent, module)
                if target and target.suffix == ".js":
                    pending.append(target)
            pending.extend(
                (page.parent / imported).resolve()
                for imported in module_imports(page_source)
                if imported.startswith(".")
            )

        seen = set()
        while pending:
            module = pending.pop()
            if module in seen or not module.is_file():
                continue
            seen.add(module)
            for imported in module_imports(module.read_text(encoding="utf-8")):
                if not imported.startswith("."):
                    continue
                target = (module.parent / imported).resolve()
                self.assertTrue(target.is_file(), f"module import missing from {module.relative_to(ROOT)}: {imported}")
                if target.suffix == ".js":
                    pending.append(target)


if __name__ == "__main__":
    unittest.main()
