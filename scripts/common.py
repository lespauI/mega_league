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
    """Read team -> ELO map from mega_elo.csv (comma delimiter, dot decimal)."""
    elo_map: Dict[str, float] = {}
    with open(elo_csv, "r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter=",")
        for row in reader:
            team_raw = row.get("Team")
            start_raw = row.get("Week 14+")
            if not team_raw or not start_raw:
                continue
            key = normalize_team_name(team_raw)
            try:
                elo = float(start_raw)
            except ValueError:
                logging.warning(
                    "Skipping ELO row with invalid Week 14+: team=%r Week 14+=%r",
                    team_raw,
                    start_raw,
                )
                continue
            elo_map[key] = elo
    logging.info("Loaded ELO map: %d teams from %s", len(elo_map), elo_csv)
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
