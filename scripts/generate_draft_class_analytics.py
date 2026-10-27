#!/usr/bin/env python3
"""Backward-compatible facade for draft class analytics."""
from __future__ import annotations

# Retain the historic imports along with all helper functions and constants.
# Add the repository root for direct script execution from any working folder.
import argparse
import csv
import html
import json
import os
import re
import statistics as st
import sys
from collections import Counter

if __package__ in (None, ""):
    _PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if _PROJECT_ROOT not in sys.path:
        sys.path.insert(0, _PROJECT_ROOT)

from mega.draft.analytics import (
    DEV_LABELS,
    _boolish,
    _grade_for_ovr,
    _normalize_player_name_for_match,
    _normalize_pos_for_mapping,
    _pos_key,
    build_round1_entries,
    build_team_logo_map,
    compute_analytics,
    gather_rookies,
    get_attr_keys_for_pos,
    get_trait_keys_for_pos,
    grade_badge,
    read_csv,
    read_mock_draft_md,
    read_section_intros,
    safe_int,
    warn_missing_columns,
)
from mega.draft.cli import main
from mega.reporting.draft_class import badge_for_dev, generate_html, render_round1_recap

if __name__ == "__main__":  # pragma: no cover - CLI entry
    main()
