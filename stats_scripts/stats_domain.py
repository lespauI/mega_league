#!/usr/bin/env python3
"""Pure scalar and identity helpers shared by stats calculations."""


def safe_float(value, default: float = 0.0) -> float:
    """Safely convert a value to float, returning a default on error."""
    try:
        return float(value) if value not in (None, "") else default
    except (ValueError, TypeError):
        return default


def normalize_team_display(name: str) -> str:
    """Normalize display names by trimming whitespace and numeric prefixes."""
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
