#!/usr/bin/env python3
"""
Shared utility functions for scripts/.

Mirrors the pattern established by stats_scripts/stats_common.py.
"""

from __future__ import annotations

import csv
import logging
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


def read_elo_map(elo_csv: str) -> Dict[str, float]:
    """Read team -> ELO map from MEGA_elo.csv (comma delimiter, dot decimal).

    The ELO column name follows the pattern ``Week N+`` (e.g. ``Week 14+``,
    ``Week 16+``, ``Week 18+``) and changes as the screenshot cutover is
    updated. Auto-detect the highest ``Week N+`` column so we don't have
    to edit code each time the source export rolls forward.
    """
    elo_map: Dict[str, float] = {}
    with open(elo_csv, "r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter=",")
        fieldnames = reader.fieldnames or []
        elo_col = None
        best_week = -1
        for name in fieldnames:
            if not name:
                continue
            stripped = name.strip()
            if stripped.lower().startswith("week ") and stripped.endswith("+"):
                try:
                    wk = int(stripped[5:-1].strip())
                except ValueError:
                    continue
                if wk > best_week:
                    best_week = wk
                    elo_col = name
        if elo_col is None:
            logging.error("No 'Week N+' column found in %s (fields=%r)", elo_csv, fieldnames)
            return elo_map

        for row in reader:
            team_raw = row.get("Team")
            start_raw = row.get(elo_col)
            if not team_raw or not start_raw:
                continue
            key = normalize_team_name(team_raw)
            try:
                elo = float(start_raw)
            except ValueError:
                logging.warning(
                    "Skipping ELO row with invalid %s: team=%r %s=%r",
                    elo_col,
                    team_raw,
                    elo_col,
                    start_raw,
                )
                continue
            elo_map[key] = elo
    logging.info("Loaded ELO map: %d teams from %s (col=%s)", len(elo_map), elo_csv, elo_col)
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
