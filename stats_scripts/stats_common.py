#!/usr/bin/env python3
"""
Shared helper utilities for stats scripts.
"""

import csv
import sys
from pathlib import Path
from typing import List, Dict, Any


def load_csv(filepath: Path) -> List[Dict[str, Any]]:
    """Load a CSV file into a list of dicts with basic error handling."""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            return list(reader)
    except Exception as e:
        print(f"Error loading {filepath}: {e}", file=sys.stderr)
        return []


def safe_float(value, default: float = 0.0) -> float:
    """Safely convert a value to float, returning a default on error."""
    try:
        return float(value) if value not in (None, "") else default
    except (ValueError, TypeError):
        return default


def normalize_team_display(name: str) -> str:
    """
    Normalize team display names to a canonical form.

    - Strips surrounding whitespace.
    - Removes any leading numeric index and colon, e.g. "11:Browns" -> "Browns".
    """
    if not name:
        return ""

    text = str(name).strip()
    if not text:
        return ""

    if ":" in text:
        prefix, rest = text.split(":", 1)
        if prefix.isdigit():
            return rest.strip()

    return text

