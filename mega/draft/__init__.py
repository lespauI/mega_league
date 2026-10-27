"""Draft class normalization, analytics, and reporting API."""
from __future__ import annotations

from importlib import import_module

from .analytics import (
    DEV_LABELS,
    _boolish,
    _normalize_player_name_for_match,
    _normalize_pos_for_mapping,
    _pos_key,
    _grade_for_ovr,
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

_LAZY_EXPORTS = {
    "render_round1_recap": ("mega.reporting.draft_class", "render_round1_recap"),
    "badge_for_dev": ("mega.reporting.draft_class", "badge_for_dev"),
    "generate_html": ("mega.reporting.draft_class", "generate_html"),
    "main": ("mega.draft.cli", "main"),
}


def __getattr__(name: str):
    try:
        module_name, attribute = _LAZY_EXPORTS[name]
    except KeyError as exc:
        raise AttributeError(name) from exc
    return getattr(import_module(module_name), attribute)


__all__ = [name for name in globals() if not name.startswith("_") and name != "import_module"] + list(_LAZY_EXPORTS)
