"""Validated cycle metadata shared by pipeline and import tools."""

from __future__ import annotations

import csv
import hashlib
import io
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping


HASH_CONTRACT_VERSION = 3


def canonical_input_bytes(data: bytes) -> bytes:
    """Normalize line endings only; all other source bytes remain significant."""
    return data.replace(b"\r\n", b"\n").replace(b"\r", b"\n")


def canonical_input_sha256(data: bytes) -> str:
    return hashlib.sha256(canonical_input_bytes(data)).hexdigest()


@dataclass(frozen=True)
class CycleContext:
    edition: str
    csv_season_index: int
    display_season: int
    calendar_year: int
    completed_through_week: int
    export_week_index: int
    next_scheduled_week: int
    elo_source_week: int
    snapshot_id: str
    enabled_features: tuple[str, ...]

    @classmethod
    def from_file(cls, metadata_path: Path, root: Path | None = None) -> "CycleContext":
        metadata_path = Path(metadata_path)
        root = Path(root) if root is not None else metadata_path.parent.parent.parent
        try:
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ValueError(f"Cannot read cycle metadata {metadata_path}: {exc}") from exc
        return cls.from_metadata(metadata, root)

    @classmethod
    def from_metadata(
        cls,
        metadata: dict,
        root: Path,
        input_bytes: Mapping[str, bytes] | None = None,
    ) -> "CycleContext":
        """Validate metadata and its inputs before use or activation.

        ``input_bytes`` lets import validation apply the same checks to a
        candidate snapshot before any of those bytes are installed.
        """
        required = (
            "game", "seasonIndex", "seasonNumber", "calendarYear",
            "completedThroughWeek", "exportWeekIndex", "nextScheduledWeek",
            "eloSourceWeek", "inputs",
        )
        missing = [key for key in required if key not in metadata]
        if missing:
            raise ValueError(f"Cycle metadata is missing fields: {', '.join(missing)}")

        try:
            season_index = int(metadata["seasonIndex"])
            display_season = int(metadata["seasonNumber"])
            completed_week = int(metadata["completedThroughWeek"])
            export_week = int(metadata["exportWeekIndex"])
            next_week = int(metadata["nextScheduledWeek"])
            elo_week = int(metadata["eloSourceWeek"])
            calendar_year = int(metadata["calendarYear"])
        except (TypeError, ValueError) as exc:
            raise ValueError("Cycle metadata index/week/year fields must be integers") from exc

        if season_index < 0 or display_season != season_index + 1:
            raise ValueError("Display season must equal CSV seasonIndex + 1")
        if min(completed_week, export_week, next_week, elo_week) < 0:
            raise ValueError("Cycle weeks must be zero or greater")
        if next_week != completed_week + 1:
            raise ValueError("nextScheduledWeek must follow completedThroughWeek")
        # Games in the current zero-based export week may already be complete.
        if completed_week > export_week + 1:
            raise ValueError("completedThroughWeek cannot exceed the exported display week")
        if elo_week > export_week:
            raise ValueError("ELO source week cannot be later than the export week")
        if calendar_year < 1900:
            raise ValueError("calendarYear is outside the expected range")

        inputs = metadata["inputs"]
        if not isinstance(inputs, list) or not inputs:
            raise ValueError("Cycle metadata inputs must be a non-empty list")
        version = int(metadata.get("hashContractVersion", 1))
        if version < 1 or version > HASH_CONTRACT_VERSION:
            raise ValueError(f"Unsupported input hash contract version: {version}")
        if version >= 3 and metadata.get("hashNormalization") != "newline-lf-v1":
            raise ValueError("Hash contract v3 requires hashNormalization='newline-lf-v1'")
        overrides = input_bytes or {}
        seen_paths: set[str] = set()
        snapshot_basis = []
        resolved_inputs: dict[str, bytes] = {}
        for item in inputs:
            if not isinstance(item, dict) or not item.get("path"):
                raise ValueError("Each cycle input must include a path")
            relative = Path(str(item["path"]))
            if relative.is_absolute() or ".." in relative.parts:
                raise ValueError(f"Unsafe cycle input path: {relative}")
            name = relative.as_posix()
            if name in seen_paths:
                raise ValueError(f"Duplicate cycle input path: {name}")
            seen_paths.add(name)
            if name in overrides:
                data = overrides[name]
            else:
                try:
                    data = (Path(root) / relative).read_bytes()
                except OSError as exc:
                    raise ValueError(f"Cannot read cycle input {name}: {exc}") from exc

            canonical_digest = canonical_input_sha256(data)
            if version >= 3:
                expected = item.get("canonicalSha256")
                if not expected:
                    raise ValueError(f"Cycle input {name} is missing canonicalSha256 for hash contract v{version}")
                if canonical_digest != expected:
                    raise ValueError(f"Canonical-file hash mismatch for {name}: expected {expected}, got {canonical_digest}")
            else:
                expected = item.get("workingSha256", item.get("sha256"))
                if expected and hashlib.sha256(data).hexdigest() != expected:
                    raise ValueError(f"Working-file hash mismatch for {name}: expected {expected}, got {hashlib.sha256(data).hexdigest()}")

            resolved_inputs[name] = data
            snapshot_basis.append((name, item.get("sourceSha256", item.get("sha256")), canonical_digest))

        elo_path = next((name for name in resolved_inputs if Path(name).name == "mega_elo.csv"), None)
        if not elo_path:
            raise ValueError("Cycle metadata inputs must include mega_elo.csv")
        _validate_elo_bytes(resolved_inputs[elo_path], elo_week)

        canonical = json.dumps(snapshot_basis, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
        snapshot_id = str(metadata.get("snapshotId") or hashlib.sha256(canonical).hexdigest()[:16])
        features = metadata.get("enabledFeatures", ())
        if not isinstance(features, (list, tuple)):
            raise ValueError("enabledFeatures must be a list when supplied")
        return cls(
            edition=str(metadata["game"]),
            csv_season_index=season_index,
            display_season=display_season,
            calendar_year=calendar_year,
            completed_through_week=completed_week,
            export_week_index=export_week,
            next_scheduled_week=next_week,
            elo_source_week=elo_week,
            snapshot_id=snapshot_id,
            enabled_features=tuple(str(feature) for feature in features),
        )


def _validate_elo_bytes(data: bytes, source_week: int) -> str:
    try:
        text = data.decode("utf-8-sig")
        reader = csv.DictReader(io.StringIO(text, newline=""), strict=True)
        fields = reader.fieldnames or []
        elo_column = f"Week {source_week}+"
        if not {"Team", elo_column}.issubset(fields):
            raise ValueError(f"ELO file does not contain the declared source column {elo_column}")
        teams: set[str] = set()
        count = 0
        for line, row in enumerate(reader, start=2):
            team = (row.get("Team") or "").strip()
            if not team:
                raise ValueError(f"ELO row {line} has no team")
            if team in teams:
                raise ValueError(f"ELO file has a duplicate team: {team}")
            teams.add(team)
            raw = (row.get(elo_column) or "").strip()
            try:
                value = float(raw)
            except (TypeError, ValueError) as exc:
                raise ValueError(f"ELO row {line} has nonnumeric {elo_column}: {raw!r}") from exc
            if not math.isfinite(value):
                raise ValueError(f"ELO row {line} has nonfinite {elo_column}: {raw!r}")
            count += 1
        if not count:
            raise ValueError("ELO file contains no team ratings")
        return elo_column
    except (UnicodeDecodeError, csv.Error) as exc:
        raise ValueError(f"Invalid ELO CSV: {exc}") from exc
