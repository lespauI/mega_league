#!/usr/bin/env python3
"""Backward-compatible imports for the split stats IO and domain helpers."""

try:  # package import
    from .csv_io import REQUIRED_HEADERS_BY_NAME, load_csv
    from .stats_domain import normalize_team_display, safe_float
except ImportError:  # direct script import with stats_scripts on sys.path
    from csv_io import REQUIRED_HEADERS_BY_NAME, load_csv
    from stats_domain import normalize_team_display, safe_float

__all__ = [
    "REQUIRED_HEADERS_BY_NAME",
    "load_csv",
    "normalize_team_display",
    "safe_float",
]
