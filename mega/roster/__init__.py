"""Roster power ranking input, scoring, and reporting API."""
from __future__ import annotations

from importlib import import_module

from .inputs import (
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
from .scoring import (
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

_LAZY_EXPORTS = {
    "compute_league_context": ("mega.reporting.roster_power", "compute_league_context"),
    "generate_team_narrative": ("mega.reporting.roster_power", "generate_team_narrative"),
    "render_html_report": ("mega.reporting.roster_power", "render_html_report"),
    "_load_json_spec": ("mega.roster.cli", "_load_json_spec"),
    "build_arg_parser": ("mega.roster.cli", "build_arg_parser"),
    "main": ("mega.roster.cli", "main"),
}


def __getattr__(name: str):
    """Load CLI and reporting exports only when requested to avoid import cycles."""

    try:
        module_name, attribute = _LAZY_EXPORTS[name]
    except KeyError as exc:
        raise AttributeError(name) from exc
    return getattr(import_module(module_name), attribute)


__all__ = [
    name for name in globals()
    if not name.startswith("_") and name != "import_module"
] + list(_LAZY_EXPORTS)
