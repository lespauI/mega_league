#!/usr/bin/env python3
"""
Shared utility functions for scripts/.

Mirrors the pattern established by stats_scripts/stats_common.py.
"""

from __future__ import annotations

import csv
import logging
import math
from pathlib import Path
from typing import Any, Dict


def to_int(val, default=None):
    try:
        return int(val)
    except Exception:
        return default


def norm_rank(rank):
    if rank is None or rank <= 0:
        return None
    return (33 - rank) / 32.0


def mean_safe(values):
    vals = [v for v in values if v is not None]
    if not vals:
        return None
    return sum(vals) / len(vals)


def normalize_team_name(name: str) -> str:
    """Normalize team names for consistent joins across files."""
    if name is None:
        return ""
    s = name.strip().lower()
    for ch in ["'", "\"", ".", ",", "-", "_", "(", ")", "/", "\\", "&", "  "]:
        s = s.replace(ch, " ")
    s = "".join(ch for ch in s if ch.isalnum())
    return s


def latest_elo_column(fieldnames):
    """Select the newest supplied Week N+ rating column by numeric week."""
    columns = []
    for name in fieldnames or []:
        value = (name or '').strip()
        if value.lower().startswith('week ') and value.endswith('+'):
            try:
                columns.append((int(value[5:-1].strip()), name))
            except ValueError:
                continue
    if not columns:
        raise ValueError('No Week N+ ELO column found')
    return max(columns)[1]


def declared_elo_source_week(root: str | Path = ".", season_index: int | None = None) -> int | None:
    """Return the validated active ELO week, or ``None`` without cycle metadata."""
    root = Path(root)
    metadata_path = root / "docs" / "data" / "import_metadata.json"
    if not metadata_path.is_file():
        return None
    try:
        from cycle_context import CycleContext
    except ImportError:
        from scripts.cycle_context import CycleContext
    context = CycleContext.from_file(metadata_path, root)
    if season_index is not None and context.csv_season_index != season_index:
        raise ValueError(
            f"requested seasonIndex={season_index} does not match active snapshot "
            f"seasonIndex={context.csv_season_index}"
        )
    return context.elo_source_week


def read_elo_map(
    elo_csv: str,
    source_week: int | None = None,
    *,
    root: str | Path | None = None,
    season_index: int | None = None,
) -> Dict[str, float]:
    """Read team -> ELO map from MEGA_elo.csv (comma delimiter, dot decimal).

    When ``source_week`` is provided, read exactly that declared snapshot
    column. The latest-column fallback remains for legacy standalone callers.
    """
    elo_path = Path(elo_csv)
    if root is not None and not elo_path.is_absolute():
        elo_path = Path(root) / elo_path
    cycle_root = Path(root) if root is not None else elo_path.resolve().parent
    declared_week = declared_elo_source_week(cycle_root, season_index)
    if source_week is None:
        source_week = declared_week
    elif declared_week is not None and source_week != declared_week:
        raise ValueError(
            f"requested ELO source week {source_week} does not match active cycle Week {declared_week}"
        )

    elo_map: Dict[str, float] = {}
    with elo_path.open("r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter=",", strict=True)
        fieldnames = reader.fieldnames or []
        if source_week is None:
            elo_col = latest_elo_column(fieldnames)
        else:
            elo_col = next((name for name in fieldnames if (name or "").strip() == f"Week {source_week}+"), None)
            if elo_col is None:
                raise ValueError(f"ELO file {elo_path} does not contain declared source column Week {source_week}+")

        for line_number, row in enumerate(reader, start=2):
            team_raw = (row.get("Team") or "").strip()
            start_raw = (row.get(elo_col) or "").strip()
            if not team_raw:
                raise ValueError(f"ELO row {line_number} has no Team value")
            if not start_raw:
                raise ValueError(f"ELO row {line_number} has no {elo_col} rating")
            key = normalize_team_name(team_raw)
            try:
                elo = float(start_raw)
            except ValueError:
                raise ValueError(f"ELO row {line_number} has nonnumeric {elo_col}: {start_raw!r}")
            if not math.isfinite(elo):
                raise ValueError(f"ELO row {line_number} has nonfinite {elo_col}: {start_raw!r}")
            if not key or key in elo_map:
                raise ValueError(f"ELO row {line_number} has an invalid or duplicate team: {team_raw!r}")
            elo_map[key] = elo
    if not elo_map:
        raise ValueError(f"ELO file {elo_path} contains no team ratings")
    logging.info("Loaded ELO map: %d teams from %s (col=%s)", len(elo_map), elo_path, elo_col)
    return elo_map


def read_team_meta(teams_csv: str) -> Dict[str, Dict[str, Any]]:
    """Read team metadata (conference, division, logoId) from MEGA_teams.csv."""
    meta: Dict[str, Dict[str, Any]] = {}
    with open(teams_csv, "r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            name = (row.get("teamName") or row.get("displayName") or "").strip()
            if not name:
                continue
            key = normalize_team_name(name)
            meta[key] = {
                "teamName": name,
                "conference": (row.get("conferenceName") or "").strip() or None,
                "division": (row.get("divName") or "").strip() or None,
                "logoId": (row.get("logoId") or "").strip() or None,
            }
    logging.info("Loaded team metadata: %d teams from %s", len(meta), teams_csv)
    return meta
