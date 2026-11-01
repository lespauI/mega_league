"""Explicit routing for performance consumers; official readers keep raw inputs."""
import json
import hashlib
from pathlib import Path

from mega.inputs.csv import load_csv as load_raw_csv
from mega.inputs.evidence_bundle import verify_bundle


def enabled(root):
    return (Path(root) / "spec" / "performance_policy.json").is_file()


def analytics_path(path):
    path = Path(path)
    root = path.parent
    if path.name.startswith("MEGA_") and enabled(root):
        manifest = root / "output" / "performance" / "manifest.json"
        if not manifest.is_file():
            raise ValueError("Performance inputs are missing; run the performance pipeline stage first")
        metadata = json.loads(manifest.read_text())
        if metadata.get("complete") is not True:
            raise ValueError("Performance inputs are incomplete")
        verify_bundle(root)
        for relative, expected in (("spec/performance_policy.json", metadata["policyHash"]),
                                   ("data/performance_evidence/manifest.json", metadata["evidenceManifestHash"])):
            if hashlib.sha256((root / relative).read_bytes()).hexdigest() != expected:
                raise ValueError("Performance policy or evidence changed; rebuild performance inputs")
        for name, expected in metadata["inputHashes"].items():
            if hashlib.sha256((root / name).read_bytes()).hexdigest() != expected:
                raise ValueError(f"Performance inputs are stale for {name}; rebuild performance inputs")
        path = root / ".cache" / "performance" / "inputs" / path.name
        relative = path.relative_to(root).as_posix()
        if hashlib.sha256(path.read_bytes()).hexdigest() != metadata["outputHashes"][relative]:
            raise ValueError("Adjusted performance input hash mismatch")
    return path


def load_csv(path):
    return load_raw_csv(analytics_path(path))


def excluded_game(row):
    from mega.inputs.games import flag
    return any([flag(row.get("home_fw", "False")), flag(row.get("away_fw", "False"))])
