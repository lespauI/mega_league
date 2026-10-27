#!/usr/bin/env python3
"""Backward-compatible facade for roster-based power rankings.

The implementation lives in :mod:`mega.roster` and :mod:`mega.reporting`.
"""
from __future__ import annotations

# Retain the historical import surface for callers that imported these names
# from this script. Add the repository root only for direct script execution,
# where Python otherwise places ``scripts/`` (rather than its parent) on the
# module search path. Importing the module never changes the working directory.
import argparse
import csv
import json
import math
import os
import statistics as st
import sys
from html import escape
from typing import Iterable

if __package__ in (None, ""):
    _PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if _PROJECT_ROOT not in sys.path:
        sys.path.insert(0, _PROJECT_ROOT)

from mega.reporting.roster_power import compute_league_context, generate_team_narrative, render_html_report
from mega.roster.cli import _load_json_spec, build_arg_parser, main
from mega.roster.inputs import (
    UNIT_ROLE_COUNTS,
    _collect_teams_by_abbrev,
    _group_by_normalized_pos,
    _normalize_pos_for_mapping,
    assign_unit,
    build_team_index,
    export_team_rosters,
    get_attr_keys_for_pos,
    get_top_attrs_for_player,
    normalize_player_row,
    read_csv,
    read_players,
    read_teams,
    safe_float,
    safe_int,
    select_unit_starters,
    warn_missing_columns,
)
from mega.roster.scoring import (
    DEFAULT_DEV_MULTIPLIERS,
    DEFAULT_OVERALL_UNIT_WEIGHTS,
    DEV_LABELS,
    UNIT_POSITION_WEIGHTS,
    _compute_ranks,
    _dev_multiplier,
    _player_base_attr_score,
    _player_unit_score,
    _score_unit_with_breakdown,
    build_team_metrics,
    compute_overall_score,
    normalize_unit_scores,
    score_unit,
    write_power_rankings_csv,
)

if __name__ == "__main__":  # pragma: no cover - CLI entry
    raise SystemExit(main())
