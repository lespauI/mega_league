#!/usr/bin/env python3
"""Roster-based power rankings – roster exports and unit scoring.

This script currently implements:
- Phase 1: data loading and per-team full roster exports.
- Phase 2: unit (Offense/Defense/Special Teams) assignment, basic
  starter selection heuristics, and unit/overall scoring with
  normalized 0–100 scores written to ``output/power_rankings_roster.csv``.

Usage (from project root):
    python3 scripts/power_rankings_roster.py \
        --players MEGA_players.csv --teams MEGA_teams.csv
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import os
import statistics as st
import sys
from html import escape
from typing import Iterable


###############################################################################
# Basic CSV utilities
###############################################################################


def read_csv(path: str) -> list[dict]:
    """Read a CSV file returning a list of dict rows.

    Uses utf-8-sig to tolerate BOMs and exits with a clear message on failure.
    """

    try:
        with open(path, newline="", encoding="utf-8-sig") as fh:
            reader = csv.DictReader(fh)
            return list(reader)
    except FileNotFoundError:
        print(f"error: file not found: {path}", file=sys.stderr)
        sys.exit(2)
    except Exception as exc:  # pragma: no cover - defensive path
        print(f"error: failed to read CSV '{path}': {exc}", file=sys.stderr)
        sys.exit(2)


def warn_missing_columns(rows: list[dict], required: Iterable[str], context: str) -> None:
    """Warn about missing columns but do not fail.

    Gathers headers from the first few rows to detect likely schema issues.
    """

    try:
        headers: set[str] = set()
        for r in rows[:5]:
            headers.update(r.keys())
        missing = [c for c in required if c not in headers]
        if missing:
            cols = ", ".join(missing)
            print(
                f"warn: {context}: missing column(s): {cols} — using safe fallbacks",
                file=sys.stderr,
            )
    except Exception:
        # Best-effort only; never crash due to warning code.
        return


def safe_int(value, default: int | None = None) -> int | None:
    """Best-effort parse of an int value.

    Accepts strings and numeric types; returns *default* on failure.
    """

    try:
        if value is None:
            return default
        if isinstance(value, int):
            return value
        s = str(value).strip()
        if s == "":
            return default
        if "." in s:
            return int(float(s))
        return int(s)
    except Exception:
        return default


def safe_float(value, default: float | None = None) -> float | None:
    """Best-effort parse of a float value.

    Accepts strings and numeric types; returns *default* on failure.
    """

    try:
        if value is None:
            return default
        if isinstance(value, (int, float)):
            return float(value)
        s = str(value).strip()
        if s == "":
            return default
        return float(s)
    except Exception:
        return default


###############################################################################
# Team loading and indexing
###############################################################################


def read_teams(path: str) -> list[dict]:
    """Read and lightly normalize team rows from MEGA_teams.csv.

    Returns a list of dict rows with convenient normalized keys:
    - team_id: from teamId (falls back to id)
    - team_name: displayName > teamName > nickName
    - abbrev: uppercased abbrName/abbrev
    - logo_id: from logoId when present
    """

    rows = read_csv(path)
    warn_missing_columns(
        rows,
        required=("teamId", "displayName", "teamName", "nickName", "abbrev", "abbrName"),
        context="read_teams",
    )

    out: list[dict] = []
    for raw in rows:
        team_id = raw.get("teamId") or raw.get("id")
        team_name = (raw.get("displayName") or raw.get("teamName") or raw.get("nickName") or "").strip()
        abbrev = (raw.get("abbrev") or raw.get("abbrName") or "").strip().upper()
        logo_id = (raw.get("logoId") or "").strip()

        norm = dict(raw)
        if team_id is not None:
            norm["team_id"] = str(team_id)
        norm["team_name"] = team_name
        norm["abbrev"] = abbrev
        norm["logo_id"] = logo_id
        out.append(norm)

    return out


def build_team_index(teams: list[dict]) -> dict[str, dict]:
    """Build a lookup index for teams.

    The returned mapping is keyed by several identifiers to make matching
    robust:
    - team abbrev (e.g., "BUF")
    - team_name (e.g., "Bills")
    - lowercase / uppercase variants of the above
    - cityName from the raw row when present (e.g., "Buffalo")

    Values are the normalized team dicts produced by :func:`read_teams`.
    """

    index: dict[str, dict] = {}
    for row in teams:
        abbrev = (row.get("abbrev") or "").strip()
        team_name = (row.get("team_name") or row.get("displayName") or row.get("teamName") or "").strip()
        city = (row.get("cityName") or "").strip()

        keys: set[str] = set()
        if abbrev:
            keys.add(abbrev)
            keys.add(abbrev.upper())
        if team_name:
            keys.add(team_name)
            keys.add(team_name.lower())
            keys.add(team_name.upper())
        if city:
            keys.add(city)
            keys.add(city.lower())
            keys.add(city.upper())

        for k in keys:
            if not k:
                continue
            # Do not overwrite an existing mapping; first wins.
            index.setdefault(k, row)

    return index


###############################################################################
# Player normalization
###############################################################################


def read_players(path: str) -> list[dict]:
    """Read raw player rows from MEGA_players.csv.

    This function only performs CSV parsing and basic column presence
    checks. Per-player normalization (including OVR, dev, and team
    resolution) is handled by :func:`normalize_player_row`.
    """

    rows = read_csv(path)
    warn_missing_columns(
        rows,
        required=(
            "id",
            "team",
            "position",
            "playerBestOvr",
            "playerSchemeOvr",
            "devTrait",
            "fullName",
            "cleanName",
            "firstName",
            "lastName",
        ),
        context="read_players",
    )
    return rows


def _normalize_pos_for_mapping(pos: str) -> str:
    """Normalize raw position labels into broader classes.

    This mirrors the mapping used in draft analytics:
    - LE/RE -> DE; LT/RT/LG/RG/C/OL/T/G -> OL; FS/SS -> S; MLB/LOLB/ROLB/OLB/LB -> LB.
    """

    p = (pos or "").strip().upper()
    if not p:
        return "?"
    # Offense
    if p in {"HB", "RB"}:
        return "RB"
    if p == "FB":
        return "FB"
    if p == "WR":
        return "WR"
    if p == "TE":
        return "TE"
    if p in {"LT", "RT", "LG", "RG", "C", "OL", "T", "G"}:
        return "OL"
    if p == "QB":
        return "QB"
    if p in {"K", "P"}:
        return p
    # Defense
    if p in {"LE", "RE", "DE", "LEDGE", "REDGE"}:
        return "DE"
    if p in {"DT"}:
        return "DT"
    if p in {"MLB", "LOLB", "ROLB", "OLB", "LB", "WILL", "SAM", "MIKE"}:
        return "LB"
    if p in {"FS", "SS"}:
        return "S"
    if p in {"CB"}:
        return "CB"
    # Fallback
    return p


def get_attr_keys_for_pos(pos: str) -> list[str]:
    """Return key rating fields to use for a position.

    This mirrors the attribute selections used in the draft class
    analytics for highlighting strengths by position. Keys correspond to
    columns in MEGA_players.csv; missing fields are simply skipped by
    callers.
    """

    p = _normalize_pos_for_mapping(pos)
    mapping = {
        # QB passing, pressure, mobility, awareness
        "QB": [
            "throwAccShortRating",
            "throwAccMidRating",
            "throwAccDeepRating",
            "throwPowerRating",
            "throwUnderPressureRating",
            "throwOnRunRating",
            "playActionRating",
            "awareRating",
            "speedRating",
            "breakSackRating",
        ],
        # RB/HB elusiveness + carrying/vision + receiving
        "RB": [
            "speedRating",
            "accelRating",
            "agilityRating",
            "breakTackleRating",
            "truckRating",
            "jukeMoveRating",
            "spinMoveRating",
            "stiffArmRating",
            "carryRating",
            "catchRating",
            "bCVRating",
        ],
        # FB blocking + strength + short-yardage
        "FB": [
            "runBlockRating",
            "leadBlockRating",
            "impactBlockRating",
            "strengthRating",
            "truckRating",
            "catchRating",
        ],
        # WR receiving, route running, release, agility
        "WR": [
            "catchRating",
            "cITRating",
            "routeRunShortRating",
            "routeRunMedRating",
            "routeRunDeepRating",
            "speedRating",
            "releaseRating",
            "agilityRating",
            "changeOfDirectionRating",
        ],
        # TE balanced catching + blocking + strength
        "TE": [
            "catchRating",
            "cITRating",
            "runBlockRating",
            "passBlockRating",
            "speedRating",
            "routeRunShortRating",
            "routeRunMedRating",
            "strengthRating",
            "specCatchRating",
        ],
        # Offensive Line: pass/run, power/finesse + strength/awareness/impact
        "OL": [
            "passBlockRating",
            "passBlockPowerRating",
            "passBlockFinesseRating",
            "runBlockRating",
            "runBlockPowerRating",
            "runBlockFinesseRating",
            "strengthRating",
            "awareRating",
            "impactBlockRating",
        ],
        # Edge rushers: moves + shed + pursuit + tackle + speed
        "DE": [
            "powerMovesRating",
            "finesseMovesRating",
            "blockShedRating",
            "pursuitRating",
            "tackleRating",
            "strengthRating",
            "speedRating",
            "hitPowerRating",
        ],
        # Interior DL: power + shed + strength + tackle + pursuit + hit power
        "DT": [
            "powerMovesRating",
            "blockShedRating",
            "strengthRating",
            "tackleRating",
            "pursuitRating",
            "hitPowerRating",
        ],
        # Linebackers: tackle + pursuit + hit + shed + recognition + coverage + speed
        "LB": [
            "tackleRating",
            "pursuitRating",
            "hitPowerRating",
            "blockShedRating",
            "playRecRating",
            "zoneCoverRating",
            "manCoverRating",
            "speedRating",
            "awareRating",
        ],
        # Cornerbacks: man/zone + speed/accel/agility + press + recognition + ball skills
        "CB": [
            "manCoverRating",
            "zoneCoverRating",
            "speedRating",
            "accelRating",
            "agilityRating",
            "pressRating",
            "playRecRating",
            "catchRating",
            "changeOfDirectionRating",
        ],
        # Safeties: zone + tackle + hit + speed + recognition + pursuit + man + awareness + hands
        "S": [
            "zoneCoverRating",
            "tackleRating",
            "hitPowerRating",
            "speedRating",
            "playRecRating",
            "pursuitRating",
            "manCoverRating",
            "awareRating",
            "catchRating",
        ],
    }
    return mapping.get(p, [])


def get_top_attrs_for_player(player: dict, limit: int = 4) -> list[dict]:
    """Return the strongest rating attributes for a player.

    The result is a list of small dicts of the form
    ``{"key": rating_name, "value": rating_value}`` ordered by
    descending value. Only attributes that participate in the scoring
    for the player's position are considered.
    """

    pos = player.get("position") or player.get("normalized_pos") or ""
    keys = get_attr_keys_for_pos(str(pos))
    values: list[tuple[str, float]] = []
    for key in keys:
        val = safe_float(player.get(key), None)
        if val is None:
            continue
        values.append((key, float(val)))

    if not values:
        return []

    values.sort(key=lambda kv: -kv[1])
    top = values[: max(0, int(limit))]
    return [{"key": k, "value": round(v, 1)} for k, v in top]


def normalize_player_row(raw: dict, team_index: dict[str, dict] | None = None) -> dict:
    """Normalize a raw player row into the canonical internal format.

    Output fields (Phase 1 subset):
    - team_abbrev: team short code from teams CSV (or "FA" when unknown).
    - team_name: display name from teams CSV when resolvable.
    - player_id: MEGA player id.
    - player_name: best-effort full name.
    - position: raw position.
    - normalized_pos: grouped position (QB/RB/WR/TE/OL/DE/DT/LB/CB/S/K/P/other).
    - ovr: int OVR value used for scoring (best or scheme OVR).
    - dev: dev trait code as string in {"3","2","1","0"}.
    """

    # Start from the raw row so all rating attributes remain available to
    # downstream scoring logic.
    out: dict = dict(raw)

    # Player id
    player_id = (raw.get("id") or "").strip()

    # Name derivation and trimming
    fn = (raw.get("fullName") or "").strip()
    cn = (raw.get("cleanName") or "").strip()
    first = (raw.get("firstName") or "").strip()
    last = (raw.get("lastName") or "").strip()
    player_name = fn or cn or (f"{first} {last}".strip()) or "?"

    # Team resolution
    raw_team = (raw.get("team") or "").strip()
    team_abbrev = "FA"
    team_name = raw_team or "Free Agent"
    if team_index and raw_team:
        candidates = [raw_team, raw_team.upper(), raw_team.lower()]
        for key in candidates:
            team = team_index.get(key)
            if team:
                team_abbrev = (team.get("abbrev") or "FA").strip() or "FA"
                team_name = (team.get("team_name") or team.get("displayName") or raw_team).strip()
                break

    # Position and normalized position
    position = (raw.get("position") or "").strip() or "?"
    normalized_pos = _normalize_pos_for_mapping(position)

    # Overall rating from best OVR, falling back to scheme OVR
    ovr = safe_int(raw.get("playerBestOvr"), None)
    if ovr is None:
        ovr = safe_int(raw.get("playerSchemeOvr"), 0) or 0

    # Dev trait normalization
    dev_raw = raw.get("devTrait", "0")
    dev = str(dev_raw).strip() if dev_raw is not None else "0"
    if dev not in {"3", "2", "1", "0"}:
        dev = "0"

    out["team_abbrev"] = team_abbrev
    out["team_name"] = team_name
    out["player_id"] = player_id
    out["player_name"] = player_name
    out["position"] = position
    out["normalized_pos"] = normalized_pos
    out["ovr"] = int(ovr) if ovr is not None else 0
    out["dev"] = dev

    return out


###############################################################################
# Roster export
###############################################################################


def _collect_teams_by_abbrev(teams_index: dict[str, dict]) -> dict[str, dict]:
    """Return mapping of team abbrev -> team row from a team index.

    The *teams_index* map is keyed by multiple identifiers; this helper
    collapses that into a single mapping by official `abbrev`.
    """

    all_teams: dict[str, dict] = {}
    for team in teams_index.values():
        abbrev = (team.get("abbrev") or "").strip()
        if not abbrev:
            continue
        all_teams.setdefault(abbrev, team)
    return all_teams


def export_team_rosters(
    players: list[dict],
    teams_index: dict[str, dict],
    out_dir: str,
    split_units: bool = False,
    include_st: bool = False,  # kept for CLI compatibility; currently ignored
) -> None:
    """Export one full-roster CSV per team.

    Phase 1 behavior:
    - Groups players by team_abbrev (resolved via team_index).
    - Ensures *every* team from MEGA_teams.csv has a CSV, even if the
      roster is empty.
    - Writes output/team_rosters/<TEAM_ABBR>.csv using a shared schema
      across all teams. Additional fields present on player dicts are
      preserved as extra columns.

    When *split_units* is True, also writes split-unit CSVs per team:
    - <TEAM_ABBR>_Offense.csv – offensive players
    - <TEAM_ABBR>_Defense.csv – defensive players
    """

    # Derive the set of team abbrevs from the team index
    all_teams = _collect_teams_by_abbrev(teams_index)

    # Group players by team_abbrev
    grouped: dict[str, list[dict]] = {abbrev: [] for abbrev in all_teams.keys()}
    for p in players:
        team_abbrev = (p.get("team_abbrev") or "").strip()
        if not team_abbrev or team_abbrev == "FA":
            # Skip free agents / unassigned players for team exports.
            continue
        grouped.setdefault(team_abbrev, []).append(p)

    # Determine fieldnames: core fields plus any extras present.
    core_fields = [
        "team_abbrev",
        "team_name",
        "player_id",
        "player_name",
        "position",
        "normalized_pos",
        "ovr",
        "dev",
    ]
    extra_fields: list[str] = []
    seen: set[str] = set(core_fields)
    for p in players:
        for k in p.keys():
            if k not in seen:
                seen.add(k)
                extra_fields.append(k)
    fieldnames = core_fields + extra_fields

    os.makedirs(out_dir, exist_ok=True)

    # Write one CSV per team; always emit a header even when no players.
    total_players = 0
    for abbrev, team in sorted(all_teams.items(), key=lambda kv: kv[0]):
        team_players = grouped.get(abbrev, [])
        total_players += len(team_players)

        path = os.path.join(out_dir, f"{abbrev}.csv")
        with open(path, "w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=fieldnames)
            writer.writeheader()
            for p in team_players:
                writer.writerow(p)

        if split_units and team_players:
            offense: list[dict] = []
            defense: list[dict] = []
            for p in team_players:
                unit = assign_unit(p.get("position", ""))
                if unit == "Offense":
                    offense.append(p)
                elif unit == "Defense":
                    defense.append(p)

            if offense:
                o_path = os.path.join(out_dir, f"{abbrev}_Offense.csv")
                with open(o_path, "w", newline="", encoding="utf-8") as fh_o:
                    writer_o = csv.DictWriter(fh_o, fieldnames=fieldnames)
                    writer_o.writeheader()
                    for p in offense:
                        writer_o.writerow(p)

            if defense:
                d_path = os.path.join(out_dir, f"{abbrev}_Defense.csv")
                with open(d_path, "w", newline="", encoding="utf-8") as fh_d:
                    writer_d = csv.DictWriter(fh_d, fieldnames=fieldnames)
                    writer_d.writeheader()
                    for p in defense:
                        writer_d.writerow(p)

    print(
        f"exported {total_players} players across {len(all_teams)} teams to {out_dir}",
        file=sys.stdout,
    )


###############################################################################
# Unit assignment and starter selection
###############################################################################


def assign_unit(position: str, side_hint: str | None = None) -> str:
    """Assign a position to a high-level unit.

    Returns one of "Offense", "Defense", or "?" when the unit cannot
    be determined.
    """

    p = _normalize_pos_for_mapping(position)
    if p in {"QB", "RB", "FB", "WR", "TE", "OL"}:
        return "Offense"
    if p in {"DE", "DT", "LB", "CB", "S"}:
        return "Defense"
    # K/P and any other unrecognized positions are not scored in
    # offense/defense units.
    return side_hint or "?"


# Starter / rotation target counts per unit and normalized position.
UNIT_ROLE_COUNTS: dict[str, dict[str, int]] = {
    # Passing: QB + 2 WR + TE + RB, behind 5 OL.
    "off_pass": {"QB": 1, "WR": 2, "TE": 1, "RB": 1, "OL": 5},
    # Rushing: RB + FB + 2 blocking TEs + 5 OL.
    "off_run": {"RB": 1, "TE": 2, "FB": 1, "OL": 5},
    "def_coverage": {"CB": 3, "S": 2, "LB": 2},
    "pass_rush": {"DE": 2, "DT": 2, "LB": 2},
    "run_defense": {"DE": 2, "DT": 2, "LB": 3, "S": 1},
}


def _group_by_normalized_pos(players: list[dict]) -> dict[str, list[dict]]:
    grouped: dict[str, list[dict]] = {}
    for p in players:
        pos = p.get("normalized_pos") or _normalize_pos_for_mapping(p.get("position", ""))
        grouped.setdefault(pos, []).append(p)
    for lst in grouped.values():
        lst.sort(key=lambda r: -safe_int(r.get("ovr"), 0) or 0)
    return grouped


def select_unit_starters(players: list[dict], unit_type: str) -> dict[str, list[dict]]:
    """Select starters/rotation players for a given unit.

    Returns mapping from normalized position -> list of selected players.
    """

    roles = UNIT_ROLE_COUNTS.get(unit_type, {})
    grouped = _group_by_normalized_pos(players)
    selected: dict[str, list[dict]] = {}
    for pos, count in roles.items():
        pool = grouped.get(pos, [])
        if not pool:
            # No players at this position; leave empty to reflect a weakness.
            selected[pos] = []
            continue
        selected[pos] = pool[: max(0, int(count))]
    return selected


###############################################################################
# Scoring
###############################################################################


# Position importance weights per unit; values are normalized internally.
UNIT_POSITION_WEIGHTS: dict[str, dict[str, float]] = {
    "off_pass": {"QB": 0.45, "WR": 0.30, "TE": 0.10, "OL": 0.15},
    "off_run": {"RB": 0.35, "OL": 0.40, "TE": 0.15, "FB": 0.10},
    "def_coverage": {"CB": 0.50, "S": 0.30, "LB": 0.20},
    "pass_rush": {"DE": 0.40, "DT": 0.30, "LB": 0.30},
    "run_defense": {"DT": 0.35, "DE": 0.25, "LB": 0.30, "S": 0.10},
    "special": {"K": 0.50, "P": 0.50},
}


# Dev trait multipliers by dev tier and OVR band.
DEFAULT_DEV_MULTIPLIERS: dict[str, list[tuple[int, float]]] = {
    # X-Factor
    "3": [(85, 0.10), (80, 0.05)],
    # Superstar
    "2": [(85, 0.07), (80, 0.03)],
    # Star / Normal: no bonus by default
    "1": [],
    "0": [],
}


# Overall unit weights used when composing the final power score from
# normalized unit scores. Exposed as a constant so the HTML report can
# document the actual configuration in use.
DEFAULT_OVERALL_UNIT_WEIGHTS: dict[str, float] = {
    "off_pass": 0.30,
    "off_run": 0.20,
    "def_coverage": 0.30,
    "pass_rush": 0.20,
}


def _dev_multiplier(ovr: int, dev: str, overrides: dict | None = None) -> float:
    tiers = overrides or DEFAULT_DEV_MULTIPLIERS
    ladder = tiers.get(str(dev), [])
    for threshold, bonus in ladder:
        if ovr >= threshold:
            return float(bonus)
    return 0.0


def _player_base_attr_score(player: dict) -> float:
    """Compute a base score from key attributes for the player's position.

    Falls back to overall rating when attribute fields are missing.
    """

    pos = player.get("position") or player.get("normalized_pos") or ""
    keys = get_attr_keys_for_pos(str(pos))
    values: list[float] = []
    for key in keys:
        val = safe_float(player.get(key), None)
        if val is not None:
            values.append(val)
    if values:
        return float(sum(values) / len(values))

    # Fallback: use overall rating if no attribute data is available.
    return float(safe_int(player.get("ovr"), 0) or 0)


def _player_unit_score(player: dict, dev_multipliers: dict | None = None) -> float:
    base = _player_base_attr_score(player)
    dev = str(player.get("dev") or "0")
    ovr_for_band = safe_int(player.get("ovr"), 0) or 0
    bonus = _dev_multiplier(ovr_for_band, dev, overrides=dev_multipliers)
    # Scale attribute-based score by (1 + bonus); low-OVR devs get 0 bonus.
    return float(base) * (1.0 + bonus)


def _score_unit_with_breakdown(
    players: list[dict],
    unit_type: str,
    weights: dict | None = None,
    dev_multipliers: dict | None = None,
) -> tuple[float, dict]:
    """Compute a raw unit score plus a per-position breakdown.

    The score matches :func:`score_unit`. The breakdown dictionary has
    the shape::

        {
            "positions": [
                {
                    "pos": "QB",
                    "weight": 0.45,
                    "weight_share": 0.45,
                    "avg_unit_score": 92.3,
                    "contribution": 41.5,
                    "contribution_share": 0.34,
                    "players": [
                        {"player_id": "123", "unit_score": 95.1},
                        ...,
                    ],
                },
                ...,
            ],
            "total_weight": 1.0,
        }
    """

    if not players:
        return 0.0, {"positions": [], "total_weight": 0.0}

    pos_weights = dict(UNIT_POSITION_WEIGHTS.get(unit_type, {}))
    if weights:
        # Allow overriding or extending the default position weights.
        pos_weights.update({k: float(v) for k, v in weights.items()})

    total_w = sum(v for v in pos_weights.values() if v > 0)
    if total_w <= 0:
        return 0.0, {"positions": [], "total_weight": 0.0}

    starters_by_pos = select_unit_starters(players, unit_type)

    score = 0.0
    breakdown_positions: list[dict] = []

    for pos, w in pos_weights.items():
        if w <= 0:
            continue
        chosen = starters_by_pos.get(pos, [])
        if not chosen:
            continue

        player_entries: list[dict] = []
        for p in chosen:
            pid = p.get("player_id") or p.get("id") or ""
            unit_val = _player_unit_score(p, dev_multipliers=dev_multipliers)
            player_entries.append(
                {
                    "player_id": str(pid),
                    "unit_score": round(float(unit_val), 1),
                }
            )

        if not player_entries:
            continue

        avg = sum(e["unit_score"] for e in player_entries) / len(player_entries)
        contrib = (w / total_w) * avg
        score += contrib

        breakdown_positions.append(
            {
                "pos": pos,
                "weight": float(w),
                "weight_share": float(w / total_w),
                "avg_unit_score": round(float(avg), 1),
                "contribution": round(float(contrib), 2),
                # contribution_share is filled once final score is known.
                "players": player_entries,
            }
        )

    if score > 0 and breakdown_positions:
        for entry in breakdown_positions:
            contrib = float(entry.get("contribution") or 0.0)
            entry["contribution_share"] = float(contrib / score)
    else:
        for entry in breakdown_positions:
            entry["contribution_share"] = 0.0

    details = {"positions": breakdown_positions, "total_weight": float(total_w)}
    return float(score), details


def score_unit(
    players: list[dict],
    unit_type: str,
    weights: dict | None = None,
    dev_multipliers: dict | None = None,
) -> float:
    """Compute a raw (unnormalized) score for a unit.

    The score is a weighted average of position-group scores, where each
    group's score is the average of selected starters' attribute-driven
    ratings adjusted by dev-trait multipliers.
    """

    score, _ = _score_unit_with_breakdown(
        players,
        unit_type,
        weights=weights,
        dev_multipliers=dev_multipliers,
    )
    return score


def normalize_unit_scores(
    raw_scores: dict[str, float],
    method: str = "zscore",
) -> dict[str, float]:
    """Normalize raw unit scores into 0–100 scale.

    Supported methods:
    - "zscore": mean→50, +/−1 std dev → ~65/35, clipped to [0, 100].
    - "minmax": min→0, max→100 (degenerates to 50 when all equal).
    """

    if not raw_scores:
        return {}

    values = list(raw_scores.values())
    if all(not math.isfinite(v) for v in values):
        return {k: 0.0 for k in raw_scores.keys()}

    if method == "minmax":
        v_min = min(values)
        v_max = max(values)
        if math.isclose(v_min, v_max):
            return {k: 50.0 for k in raw_scores.keys()}
        span = v_max - v_min
        return {k: max(0.0, min(100.0, (v - v_min) * 100.0 / span)) for k, v in raw_scores.items()}

    # Default: z-score with 50-point mean, 15-point stddev.
    mean = st.mean(values)
    try:
        sigma = st.pstdev(values)
    except Exception:
        sigma = 0.0
    if sigma <= 1e-9:
        return {k: 50.0 for k in raw_scores.keys()}

    norm: dict[str, float] = {}
    for k, v in raw_scores.items():
        z = (v - mean) / sigma
        score = 50.0 + 15.0 * z
        score = max(0.0, min(100.0, score))
        norm[k] = score
    return norm


def compute_overall_score(units: dict[str, float], weights: dict[str, float] | None = None) -> float:
    """Compute overall power score from normalized unit scores.

    Default composite (passing-era emphasis):
    - 30% Off Pass, 20% Off Run, 30% Pass Coverage, 20% Pass Rush.
    Run Defense and Special Teams can be folded in via *weights*.
    """

    default_weights = dict(DEFAULT_OVERALL_UNIT_WEIGHTS)
    if weights:
        default_weights.update({k: float(v) for k, v in weights.items()})

    usable_items = [
        (k, default_weights[k])
        for k in default_weights.keys()
        if k in units and default_weights[k] > 0
    ]
    total_w = sum(w for _, w in usable_items)
    if total_w <= 0:
        return 0.0

    score = 0.0
    for k, w in usable_items:
        score += units.get(k, 0.0) * (w / total_w)
    return score


###############################################################################
# Metrics assembly and CSV output
###############################################################################


DEV_LABELS = {"3": "X-Factor", "2": "Superstar", "1": "Star", "0": "Normal"}


def _compute_ranks(values: dict[str, float]) -> dict[str, int]:
    """Return rank mapping (1 = best) for numeric values by key."""

    ordered = sorted(values.items(), key=lambda kv: kv[1], reverse=True)
    ranks: dict[str, int] = {}
    rank = 1
    for key, _ in ordered:
        ranks[key] = rank
        rank += 1
    return ranks


def build_team_metrics(
    players: list[dict],
    teams_index: dict[str, dict],
    *,
    include_st: bool = False,
    normalization: str = "zscore",
    overall_weights: dict[str, float] | None = None,
    dev_multipliers: dict | None = None,
) -> list[dict]:
    """Compute per-team unit and overall metrics.

    Returns a list of dicts, one per team, suitable for CSV/HTML output.
    """

    all_teams = _collect_teams_by_abbrev(teams_index)

    players_by_team: dict[str, list[dict]] = {abbrev: [] for abbrev in all_teams.keys()}
    for p in players:
        team_abbrev = (p.get("team_abbrev") or "").strip()
        if team_abbrev in players_by_team:
            players_by_team[team_abbrev].append(p)

    unit_keys = ["off_pass", "off_run", "def_coverage", "pass_rush", "run_defense"]

    raw_scores_by_unit: dict[str, dict[str, float]] = {u: {} for u in unit_keys}

    dev_counts_by_team: dict[str, dict[str, int]] = {}

    for abbrev, team in all_teams.items():
        team_players = players_by_team.get(abbrev, [])
        offense = [p for p in team_players if assign_unit(p.get("position", "")) == "Offense"]
        defense = [p for p in team_players if assign_unit(p.get("position", "")) == "Defense"]

        raw_scores_by_unit["off_pass"][abbrev] = score_unit(
            offense,
            "off_pass",
            dev_multipliers=dev_multipliers,
        )
        raw_scores_by_unit["off_run"][abbrev] = score_unit(
            offense,
            "off_run",
            dev_multipliers=dev_multipliers,
        )
        raw_scores_by_unit["def_coverage"][abbrev] = score_unit(
            defense,
            "def_coverage",
            dev_multipliers=dev_multipliers,
        )
        raw_scores_by_unit["pass_rush"][abbrev] = score_unit(
            defense,
            "pass_rush",
            dev_multipliers=dev_multipliers,
        )
        raw_scores_by_unit["run_defense"][abbrev] = score_unit(
            defense,
            "run_defense",
            dev_multipliers=dev_multipliers,
        )

        # Dev trait counts per team
        dev_counts = {"3": 0, "2": 0, "1": 0, "0": 0}
        for p in team_players:
            d = str(p.get("dev") or "0")
            if d not in dev_counts:
                d = "0"
            dev_counts[d] += 1
        dev_counts_by_team[abbrev] = dev_counts

    # Normalize unit scores to 0–100.
    norm_scores_by_unit: dict[str, dict[str, float]] = {}
    for unit_key, mapping in raw_scores_by_unit.items():
        norm_scores_by_unit[unit_key] = normalize_unit_scores(mapping, method=normalization)

    # Overall scores and ranks.
    overall_scores: dict[str, float] = {}
    for abbrev in all_teams.keys():
        unit_scores_for_team = {
            unit_key: norm_scores_by_unit[unit_key].get(abbrev, 0.0)
            for unit_key in norm_scores_by_unit.keys()
        }
        overall_scores[abbrev] = compute_overall_score(
            unit_scores_for_team,
            weights=overall_weights,
        )

    # Build ranks for overall and each unit.
    overall_ranks = _compute_ranks(overall_scores)
    unit_ranks: dict[str, dict[str, int]] = {}
    for unit_key, norm_scores in norm_scores_by_unit.items():
        unit_ranks[unit_key] = _compute_ranks(norm_scores)

    # Assemble metrics list.
    metrics: list[dict] = []
    for abbrev, team in sorted(all_teams.items(), key=lambda kv: kv[0]):
        team_name = (team.get("team_name") or team.get("displayName") or abbrev).strip()
        dev_counts = dev_counts_by_team.get(abbrev, {"3": 0, "2": 0, "1": 0, "0": 0})

        # Compact top contributors string: top 3 OVR players.
        team_players = players_by_team.get(abbrev, [])
        top_players = sorted(
            team_players,
            key=lambda p: (-safe_int(p.get("ovr"), 0) or 0, p.get("player_name", "")),
        )[:3]
        contrib_parts: list[str] = []
        for p in top_players:
            dev_label = DEV_LABELS.get(str(p.get("dev") or "0"), "Normal")
            contrib_parts.append(
                f"{p.get('position','?')} {p.get('player_name','?')} "
                f"({safe_int(p.get('ovr'), 0) or 0}, {dev_label})"
            )
        top_contributors = "; ".join(contrib_parts)

        row: dict[str, object] = {
            "team_abbrev": abbrev,
            "team_name": team_name,
            "overall_score": round(overall_scores.get(abbrev, 0.0), 1),
            "overall_rank": overall_ranks.get(abbrev, 0),
            "off_pass_score": round(norm_scores_by_unit["off_pass"].get(abbrev, 0.0), 1),
            "off_pass_rank": unit_ranks["off_pass"].get(abbrev, 0),
            "off_run_score": round(norm_scores_by_unit["off_run"].get(abbrev, 0.0), 1),
            "off_run_rank": unit_ranks["off_run"].get(abbrev, 0),
            "def_cover_score": round(norm_scores_by_unit["def_coverage"].get(abbrev, 0.0), 1),
            "def_cover_rank": unit_ranks["def_coverage"].get(abbrev, 0),
            "def_pass_rush_score": round(norm_scores_by_unit["pass_rush"].get(abbrev, 0.0), 1),
            "def_pass_rush_rank": unit_ranks["pass_rush"].get(abbrev, 0),
            "def_run_score": round(norm_scores_by_unit["run_defense"].get(abbrev, 0.0), 1),
            "def_run_rank": unit_ranks["run_defense"].get(abbrev, 0),
            "dev_xf": dev_counts.get("3", 0),
            "dev_ss": dev_counts.get("2", 0),
            "dev_star": dev_counts.get("1", 0),
            "dev_normal": dev_counts.get("0", 0),
            "top_contributors": top_contributors,
        }

        metrics.append(row)

    # Sort by overall_rank ascending for convenience.
    metrics.sort(key=lambda r: int(r.get("overall_rank", 0) or 0))
    return metrics


def write_power_rankings_csv(path: str, teams_metrics: list[dict]) -> None:
    """Write power rankings metrics CSV to *path*."""

    if not teams_metrics:
        print("warn: no team metrics to write", file=sys.stderr)
        return

    fieldnames = [
        "team_abbrev",
        "team_name",
        "overall_score",
        "overall_rank",
        "off_pass_score",
        "off_pass_rank",
        "off_run_score",
        "off_run_rank",
        "def_cover_score",
        "def_cover_rank",
        "def_pass_rush_score",
        "def_pass_rush_rank",
        "def_run_score",
        "def_run_rank",
        "dev_xf",
        "dev_ss",
        "dev_star",
        "dev_normal",
        "top_contributors",
    ]

    out_dir = os.path.dirname(path)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)

    with open(path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        for row in teams_metrics:
            writer.writerow(row)

    print(f"wrote power rankings CSV for {len(teams_metrics)} teams to {path}", file=sys.stdout)


###############################################################################
# League context and HTML report rendering (Phase 3)
###############################################################################


def compute_league_context(teams_metrics: list[dict]) -> dict:
    """Compute simple league-wide context statistics for key metrics.

    Returns a mapping of metric name -> summary stats, where each summary
    contains avg/min/max and 25th/50th/75th percentiles. This is intended
    both for display in the HTML report and for narrative helpers in
    later phases.
    """

    def _metric_stats(key: str) -> dict:
        vals: list[float] = []
        for row in teams_metrics:
            v = row.get(key)
            if v is None or v == "":
                continue
            try:
                vals.append(float(v))
            except Exception:
                continue
        if not vals:
            return {}
        vals.sort()
        n = len(vals)

        def pct(p: float) -> float:
            if n == 1:
                return vals[0]
            # Simple nearest-rank percentile.
            idx = int(round((p / 100.0) * (n - 1)))
            if idx < 0:
                idx = 0
            if idx >= n:
                idx = n - 1
            return vals[idx]

        avg = sum(vals) / n
        return {
            "avg": avg,
            "min": vals[0],
            "max": vals[-1],
            "p25": pct(25.0),
            "p50": pct(50.0),
            "p75": pct(75.0),
        }

    metrics = {
        "overall_score": _metric_stats("overall_score"),
        "off_pass_score": _metric_stats("off_pass_score"),
        "off_run_score": _metric_stats("off_run_score"),
        "def_cover_score": _metric_stats("def_cover_score"),
        "def_pass_rush_score": _metric_stats("def_pass_rush_score"),
        "def_run_score": _metric_stats("def_run_score"),
    }

    # Filter out completely empty entries.
    return {k: v for k, v in metrics.items() if v}


def generate_team_narrative(team_metrics: dict, league_context: dict) -> dict[str, str]:
    """Generate narrative text describing a team's strengths and weaknesses.

    The output dict contains ``strengths``, ``weaknesses``, and ``summary``
    keys. The content is heuristic but grounded in the same metrics that
    feed the CSV/HTML report.
    """

    # Core unit keys and human labels.
    unit_keys = [
        ("off_pass_score", "Off Pass"),
        ("off_run_score", "Off Run"),
        ("def_cover_score", "Pass Coverage"),
        ("def_pass_rush_score", "Pass Rush"),
        ("def_run_score", "Run Defense"),
    ]

    scores: dict[str, float] = {}
    for key, _ in unit_keys:
        try:
            scores[key] = float(team_metrics.get(key) or 0.0)
        except Exception:
            scores[key] = 0.0

    def _ctx(key: str) -> dict:
        if isinstance(league_context, dict):
            return league_context.get(key, {})
        return {}

    strengths: list[str] = []
    weaknesses: list[str] = []

    # Strong if >= 75th percentile, weak if <= 25th.
    for key, label in unit_keys:
        ctx = _ctx(key)
        score = scores.get(key, 0.0)
        if ctx:
            high = ctx.get("p75", ctx.get("p50", 0.0))
            low = ctx.get("p25", ctx.get("p50", 0.0))
        else:
            high = 70.0
            low = 40.0

        if score >= high:
            strengths.append(f"{label} unit grades as a clear strength ({score:.1f}).")
        elif score <= low:
            weaknesses.append(f"{label} unit looks like a liability ({score:.1f}).")

    # Ensure at least one strength/weakness.
    if not strengths and scores:
        best_key = max(scores, key=scores.get)
        best_label = dict(unit_keys).get(best_key, best_key)
        strengths.append(f"{best_label} is the most reliable unit on this roster.")

    if not weaknesses and scores:
        worst_key = min(scores, key=scores.get)
        worst_label = dict(unit_keys).get(worst_key, worst_key)
        weaknesses.append(f"{worst_label} lags behind the rest of the build.")

    dev_xf = int(team_metrics.get("dev_xf") or 0)
    dev_ss = int(team_metrics.get("dev_ss") or 0)
    dev_star = int(team_metrics.get("dev_star") or 0)
    dev_norm = int(team_metrics.get("dev_normal") or 0)
    total_premium = dev_xf + dev_ss
    total_dev = total_premium + dev_star + dev_norm

    dev_phrase = ""
    if total_premium >= 6:
        dev_phrase = f" built around {total_premium} X-Factor/Superstar pieces"
    elif total_premium >= 3:
        dev_phrase = " with a solid premium dev core"

    top_contrib_str = str(team_metrics.get("top_contributors") or "")
    top_contrib = ""
    if top_contrib_str:
        first = top_contrib_str.split(";")[0].strip()
        if first:
            top_contrib = first

    team_name = str(
        team_metrics.get("team_name") or team_metrics.get("team_abbrev") or ""
    ).strip()
    overall_rank = int(team_metrics.get("overall_rank") or 0)

    primary_strength = strengths[0] if strengths else ""
    primary_weakness = weaknesses[0] if weaknesses else ""

    summary_parts: list[str] = []
    if team_name:
        if overall_rank:
            summary_parts.append(
                f"{team_name} currently grades #{overall_rank} in roster power"
            )
        else:
            summary_parts.append(
                f"{team_name} sits in the middle of the roster power pack"
            )
    if dev_phrase:
        summary_parts.append(dev_phrase)
    if top_contrib:
        summary_parts.append(f" headlined by {top_contrib}")

    summary = ""
    if summary_parts:
        summary = "".join(summary_parts) + "."
        if primary_strength or primary_weakness:
            summary += " " + " ".join(
                s for s in [primary_strength, primary_weakness] if s
            )

    return {
        "strengths": " ".join(strengths) if strengths else primary_strength,
        "weaknesses": " ".join(weaknesses) if weaknesses else primary_weakness,
        "summary": summary,
    }


def render_html_report(
    path: str,
    teams_metrics: list[dict],
    config: dict | None = None,
    league_context: dict | None = None,
    players_by_team: dict[str, list[dict]] | None = None,
) -> None:
    """Render a basic HTML report for roster-based power rankings.

    Phase 3 scope focuses on a league-wide sortable/searchable table and
    simple bar-style charts, while keeping the layout visually aligned
    with existing docs pages such as draft_class_2026 and
    rankings_explorer.
    """

    if not teams_metrics:
        print("warn: render_html_report called with no team metrics; skipping HTML output", file=sys.stderr)
        return

    cfg = dict(config or {})
    league_ctx = dict(league_context or {})

    # Prepare compact JS data blob.
    js_teams: list[dict] = []
    for row in teams_metrics:
        js_teams.append(
            {
                "team_abbrev": row.get("team_abbrev"),
                "team_name": row.get("team_name"),
                "overall_score": row.get("overall_score"),
                "overall_rank": row.get("overall_rank"),
                "off_pass_score": row.get("off_pass_score"),
                "off_run_score": row.get("off_run_score"),
                "def_cover_score": row.get("def_cover_score"),
                "def_pass_rush_score": row.get("def_pass_rush_score"),
                "def_run_score": row.get("def_run_score"),
                "dev_xf": row.get("dev_xf"),
                "dev_ss": row.get("dev_ss"),
                "dev_star": row.get("dev_star"),
                "dev_normal": row.get("dev_normal"),
            }
        )

    # Optional per-team roster + unit breakdown data for team detail pages.
    rosters_payload: dict[str, list[dict]] = {}
    unit_breakdowns: dict[str, dict] = {}

    if players_by_team:
        # Use the same dev multipliers that drove scoring so that
        # per-unit breakdowns line up with the main grades.
        dev_cfg = cfg.get("dev_multipliers") or DEFAULT_DEV_MULTIPLIERS

        unit_labels = {
            "off_pass": "Off Pass",
            "off_run": "Off Run",
            "def_coverage": "Pass Coverage",
            "pass_rush": "Pass Rush",
            "run_defense": "Run Defense",
        }

        score_key_map = {
            "off_pass": "off_pass_score",
            "off_run": "off_run_score",
            "def_coverage": "def_cover_score",
            "pass_rush": "def_pass_rush_score",
            "run_defense": "def_run_score",
        }

        # Build payloads keyed by team abbrev so JS can quickly map
        # from a clicked team to its roster and unit breakdown.
        for row in teams_metrics:
            team_abbrev = str(row.get("team_abbrev") or "").strip()
            if not team_abbrev:
                continue

            team_players = list(players_by_team.get(team_abbrev, []))
            if team_players:
                # Sort by OVR descending for a nicer default ordering.
                team_players.sort(
                    key=lambda p: (-safe_int(p.get("ovr"), 0) or 0, p.get("player_name", "")),
                )

            roster_rows: list[dict] = []
            for p in team_players:
                dev = str(p.get("dev") or "0")
                roster_rows.append(
                    {
                        "player_id": str(p.get("player_id") or p.get("id") or ""),
                        "name": p.get("player_name") or p.get("fullName") or "?",
                        "position": p.get("position") or "?",
                        "normalized_pos": p.get("normalized_pos") or _normalize_pos_for_mapping(p.get("position", "")),
                        "ovr": safe_int(p.get("ovr"), 0) or 0,
                        "dev": dev,
                        "dev_label": DEV_LABELS.get(dev, "Normal"),
                        "top_attrs": get_top_attrs_for_player(p),
                    }
                )

            if roster_rows:
                rosters_payload[team_abbrev] = roster_rows

            if team_players:
                offense = [
                    p
                    for p in team_players
                    if assign_unit(p.get("position", "")) == "Offense"
                ]
                defense = [
                    p
                    for p in team_players
                    if assign_unit(p.get("position", "")) == "Defense"
                ]

                unit_details: dict[str, dict] = {}
                for unit_key in [
                    "off_pass",
                    "off_run",
                    "def_coverage",
                    "pass_rush",
                    "run_defense",
                ]:
                    pool = offense if unit_key.startswith("off_") else defense
                    raw_score, breakdown = _score_unit_with_breakdown(
                        pool,
                        unit_key,
                        dev_multipliers=dev_cfg,
                    )
                    norm_key = score_key_map.get(unit_key)
                    norm_val = row.get(norm_key) if norm_key else None
                    try:
                        norm_score = (float(norm_val) if norm_val is not None else None)
                    except Exception:
                        norm_score = None

                    unit_details[unit_key] = {
                        "label": unit_labels.get(unit_key, unit_key),
                        "raw_score": round(float(raw_score), 2),
                        "norm_score": norm_score,
                        "positions": breakdown.get("positions", []),
                    }

                unit_breakdowns[team_abbrev] = unit_details

    data_dict: dict[str, object] = {
        "teams": js_teams,
        "config": cfg,
        "league": league_ctx,
    }
    if rosters_payload:
        data_dict["rosters"] = rosters_payload
    if unit_breakdowns:
        data_dict["unit_breakdowns"] = unit_breakdowns

    data_blob = json.dumps(data_dict, ensure_ascii=False)

    normalization = cfg.get("normalization", "zscore")

    title = "Roster Power Rankings — Roster Analytics"
    subtitle = f"League-wide roster strength overview (normalization: {normalization})"

    # Small helper for per-team radar / spider-style visualization.
    def _radar_svg(team_row: dict) -> str:
        metrics = [
            ("off_pass_score", "OP"),
            ("off_run_score", "OR"),
            ("def_cover_score", "Cov"),
            ("def_pass_rush_score", "Rush"),
            ("def_run_score", "Run"),
        ]
        cx, cy, radius = 60.0, 60.0, 42.0

        # Background polygon at ~70% radius for visual context.
        bg_pts: list[str] = []
        for idx, _ in enumerate(metrics):
            angle = -math.pi / 2.0 + (2.0 * math.pi * idx) / len(metrics)
            r_bg = radius * 0.7
            x = cx + r_bg * math.cos(angle)
            y = cy + r_bg * math.sin(angle)
            bg_pts.append(f"{x:.1f},{y:.1f}")

        # Data polygon from unit scores.
        data_pts: list[tuple[float, float]] = []
        for idx, (key, _label) in enumerate(metrics):
            try:
                score = float(team_row.get(key) or 0.0)
            except Exception:
                score = 0.0
            score = max(0.0, min(100.0, score))
            angle = -math.pi / 2.0 + (2.0 * math.pi * idx) / len(metrics)
            r = radius * (score / 100.0)
            x = cx + r * math.cos(angle)
            y = cy + r * math.sin(angle)
            data_pts.append((x, y))

        poly_pts = " ".join(f"{x:.1f},{y:.1f}" for x, y in data_pts)

        abbr = str(team_row.get("team_abbrev") or "")

        svg_parts: list[str] = []
        svg_parts.append(
            '<svg class="radar-chart" viewBox="0 0 120 120" '
            f'data-team-abbr="{escape(abbr)}">'
        )
        svg_parts.append('<g class="radar-bg"><polygon points="' + " ".join(bg_pts) + '"/></g>')
        svg_parts.append('<g class="radar-axes">')
        for idx, _ in enumerate(metrics):
            angle = -math.pi / 2.0 + (2.0 * math.pi * idx) / len(metrics)
            x2 = cx + radius * math.cos(angle)
            y2 = cy + radius * math.sin(angle)
            svg_parts.append(
                '<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}"/>'.format(
                    x1=cx,
                    y1=cy,
                    x2=x2,
                    y2=y2,
                )
            )
        svg_parts.append("</g>")
        svg_parts.append('<polygon class="radar-poly" points="' + poly_pts + '"/>')
        for x, y in data_pts:
            svg_parts.append(
                '<circle class="radar-point" cx="{x:.1f}" cy="{y:.1f}" r="2"/>'.format(
                    x=x,
                    y=y,
                )
            )
        svg_parts.append("</svg>")
        return "".join(svg_parts)

    # Build HTML structure. Keep the style and table sorter closely
    # aligned with draft_class_2026.html for visual consistency.
    parts: list[str] = []
    parts.append("<!DOCTYPE html>")
    parts.append("<html lang=\"en\">")
    parts.append("<head>")
    parts.append("  <meta charset=\"utf-8\" />")
    parts.append("  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />")
    parts.append(f"  <title>{escape(title)}</title>")
    parts.append("  <style>")
    parts.append("    :root { --text:#0f172a; --sub:#64748b; --muted:#94a3b8; --grid:#e2e8f0; --bg:#f7f7f7; --card:#ffffff; --accent:#3b82f6; }")
    parts.append("    body { margin:16px; font-family: system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial, sans-serif; color:var(--text); background:var(--bg); }")
    parts.append("    .topbar { max-width: 1200px; margin: 0 auto 10px; display:flex; align-items:center; gap:10px; }")
    parts.append("    .back { display:inline-flex; align-items:center; gap:8px; font-size:13px; color:#1e293b; text-decoration:none; background:#fff; border:1px solid #e5e7eb; padding:6px 10px; border-radius:8px; box-shadow:0 1px 2px rgba(0,0,0,.05); }")
    parts.append("    .back:hover { background:#f8fafc; }")
    parts.append("    .container { max-width: 1200px; margin: 0 auto; background: var(--card); border: 1px solid #e5e7eb; border-radius: 12px; box-shadow: 0 1px 3px rgba(0,0,0,.06); overflow:hidden; }")
    parts.append("    header { padding: 18px 20px 10px; border-bottom: 1px solid #ececec; background:linear-gradient(180deg,#ffffff 0%,#fafafa 100%); }")
    parts.append("    h1 { margin:0; font-size: 22px; }")
    parts.append("    .subtitle { color: var(--sub); margin:8px 0 4px; font-size: 13px; }")
    parts.append("    .pill { display:inline-block; margin-left:8px; padding:2px 8px; border-radius:999px; border:1px solid #bfdbfe; background:#dbeafe; color:#1e3a8a; font-size:12px; }")
    parts.append("    .panel { padding: 14px 18px; border-bottom: 1px solid #f0f0f0; }")
    parts.append("    .section-title { font-size: 14px; font-weight: 700; margin: 0 0 10px; border-left:3px solid var(--accent); padding-left:8px; }")
    parts.append("    .section-intro { white-space: pre-wrap; color: #334155; font-size: 13px; margin: 4px 0 10px; }")
    parts.append("    .kpis { display:grid; grid-template-columns: repeat(3, minmax(0,1fr)); gap:10px; }")
    parts.append("    .kpi { background:#f8fafc; padding: 10px 12px; border: 1px solid #e5e7eb; border-radius: 10px; }")
    parts.append("    .kpi b { display:block; font-size: 12px; color:#0f172a; }")
    parts.append("    .kpi span { color:#334155; font-size: 18px; font-weight: 700; }")
    parts.append("    .kpi .gbar { margin-top:6px; height:6px; background:#e5e7eb; border-radius:999px; overflow:hidden; }")
    parts.append("    .kpi .gbar .fill { height:100%; background: linear-gradient(90deg, #60a5fa, #22c55e); }")
    parts.append("    .controls { display:flex; flex-wrap:wrap; align-items:center; gap:10px; font-size:13px; }")
    parts.append("    .controls label { font-weight:500; color:#475569; }")
    parts.append("    .controls input[type='search'] { padding:6px 8px; border-radius:8px; border:1px solid #e5e7eb; min-width: 220px; font-size:13px; }")
    parts.append("    .controls select { padding:6px 8px; border-radius:8px; border:1px solid #e5e7eb; font-size:13px; }")
    parts.append("    .table-wrap { margin-top:10px; border:1px solid #e5e7eb; border-radius:10px; overflow:auto; }")
    parts.append("    table { width:100%; border-collapse:collapse; font-size:12px; }")
    parts.append("    thead { background:#f8fafc; position:sticky; top:0; z-index:1; }")
    parts.append("    th, td { padding:6px 8px; border-bottom:1px solid #e5e7eb; text-align:left; }")
    parts.append("    th { font-weight:600; color:#475569; cursor:pointer; white-space:nowrap; }")
    parts.append("    tr:nth-child(even) { background:#f9fafb; }")
    parts.append("    tr:hover { background:#eef2ff; }")
    parts.append("    .num { text-align:right; font-variant-numeric: tabular-nums; }")
    parts.append("    .rank-cell { font-weight:700; }")
    parts.append("    .team-cell { display:flex; align-items:center; gap:6px; }")
    parts.append("    .team-tag { display:inline-flex; align-items:center; gap:4px; font-weight:600; }")
    parts.append("    .team-tag span { font-size:11px; color:#64748b; }")
    parts.append("    .metric { display:flex; flex-direction:column; gap:2px; }")
    parts.append("    .metric-value { font-weight:600; }")
    parts.append("    .metric-bar { height:6px; background:#e5e7eb; border-radius:999px; overflow:hidden; }")
    parts.append("    .metric-bar-fill { height:100%; background:linear-gradient(90deg,#3b82f6,#22c55e); }")
    parts.append("    .dev-chips { display:flex; flex-wrap:wrap; gap:4px; }")
    parts.append("    .chip { padding:2px 6px; border-radius:999px; border:1px solid #e5e7eb; font-size:11px; background:#f9fafb; }")
    parts.append("    .chip-xf { border-color:#fecaca; background:#fee2e2; color:#b91c1c; }")
    parts.append("    .chip-ss { border-color:#facc15; background:#fef9c3; color:#854d0e; }")
    parts.append("    .chip-star { border-color:#d4d4d8; background:#e4e4e7; color:#27272a; }")
    parts.append("    .chip-norm { border-color:#c4b5fd; background:#e0e7ff; color:#3730a3; }")
    parts.append("    .chart-strip { margin-top:8px; display:flex; flex-wrap:wrap; gap:4px; }")
    parts.append("    .chart-bar { flex:1 1 40px; min-width:40px; height:36px; background:#f8fafc; border:1px solid #e5e7eb; border-radius:6px; position:relative; overflow:hidden; }")
    parts.append("    .chart-bar-fill { position:absolute; left:0; top:0; bottom:0; background:linear-gradient(90deg,#22c55e,#16a34a); opacity:0.3; }")
    parts.append("    .chart-bar-label { position:relative; z-index:1; padding:4px 6px; font-size:11px; display:flex; flex-direction:column; justify-content:center; }")
    parts.append("    .chart-bar-label b { font-size:12px; }")
    parts.append("    .methodology-grid { display:grid; grid-template-columns: repeat(3, minmax(0,1fr)); gap:12px; margin-top:8px; font-size:12px; color:#111827; }")
    parts.append("    .methodology-col { background:#f8fafc; border:1px solid #e5e7eb; border-radius:10px; padding:10px 12px; }")
    parts.append("    .methodology-col h3 { margin:0 0 6px; font-size:12px; text-transform:uppercase; letter-spacing:0.03em; color:#6b7280; }")
    parts.append("    .methodology-list { margin:0; padding-left:16px; }")
    parts.append("    .methodology-list li { margin:2px 0; }")
    parts.append("    .team-grid { display:grid; grid-template-columns: repeat(2, minmax(0,1fr)); gap:12px; }")
    parts.append("    .team-card { border:1px solid #e5e7eb; border-radius:10px; padding:10px 12px; background:#f9fafb; display:flex; flex-direction:column; gap:8px; }")
    parts.append("    .team-card-header { display:flex; justify-content:space-between; align-items:baseline; gap:8px; }")
    parts.append("    .team-card-title { font-size:13px; font-weight:600; color:#0f172a; }")
    parts.append("    .team-card-sub { font-size:11px; color:#6b7280; }")
    parts.append("    .team-card-dev { font-size:11px; color:#4b5563; }")
    parts.append("    .team-card-dev strong { font-weight:600; }")
    parts.append("    .team-card-dev span { margin-right:6px; }")
    parts.append("    .team-card.dev-elite { border-color:#f97316; box-shadow:0 0 0 1px rgba(249,115,22,0.35); }")
    parts.append("    .team-card-body { display:flex; gap:10px; align-items:stretch; }")
    parts.append("    .radar-shell { flex:0 0 120px; display:flex; flex-direction:column; align-items:center; justify-content:center; }")
    parts.append("    .radar-chart { width:120px; height:120px; }")
    parts.append("    .radar-bg polygon { fill:#eff6ff; stroke:#dbeafe; stroke-width:1; }")
    parts.append("    .radar-axes line { stroke:#e5e7eb; stroke-width:1; }")
    parts.append("    .radar-poly { fill:rgba(59,130,246,0.3); stroke:#2563eb; stroke-width:1.5; }")
    parts.append("    .radar-point { fill:#1d4ed8; stroke:#eff6ff; stroke-width:1; r:2; }")
    parts.append("    .radar-labels { display:flex; flex-wrap:wrap; gap:4px; justify-content:center; margin-top:4px; font-size:10px; color:#6b7280; }")
    parts.append("    .radar-labels span { padding:1px 4px; border-radius:999px; background:#e5e7eb; }")
    parts.append("    .team-narrative { flex:1 1 auto; font-size:12px; color:#111827; display:flex; flex-direction:column; gap:4px; }")
    parts.append("    .team-narrative p { margin:0; }")
    parts.append("    .team-narrative strong { color:#0f172a; }")
    parts.append("    .team-narrative .label { text-transform:uppercase; font-size:11px; letter-spacing:0.04em; color:#6b7280; }")
    parts.append("    #teams-table tbody tr, .team-card { cursor:pointer; }")
    parts.append("    .team-detail-overlay { position:fixed; inset:0; display:none; align-items:flex-start; justify-content:center; padding:40px 12px; z-index:40; }")
    parts.append("    .team-detail-overlay.visible { display:flex; }")
    parts.append("    .team-detail-backdrop { position:absolute; inset:0; background:rgba(15,23,42,0.55); }")
    parts.append("    .team-detail-panel { position:relative; max-width:980px; width:100%; max-height:100%; background:#ffffff; border-radius:12px; box-shadow:0 22px 45px rgba(15,23,42,0.45); padding:16px 18px 18px; overflow:auto; }")
    parts.append("    .team-detail-close { position:absolute; top:8px; right:10px; border:none; background:transparent; font-size:18px; cursor:pointer; color:#64748b; }")
    parts.append("    .team-detail-header h2 { margin:0; font-size:18px; }")
    parts.append("    .team-detail-sub { margin:2px 0 10px; font-size:12px; color:#6b7280; }")
    parts.append("    .team-detail-body { font-size:11px; color:#111827; }")
    parts.append("    .team-detail-columns { display:grid; grid-template-columns: minmax(0,1.4fr) minmax(0,1.1fr); gap:12px; }")
    parts.append("    .team-detail-col h3 { margin:0 0 6px; font-size:13px; }")
    parts.append("    .team-detail-table { width:100%; border-collapse:collapse; font-size:11px; }")
    parts.append("    .team-detail-table th, .team-detail-table td { padding:4px 6px; border-bottom:1px solid #e5e7eb; text-align:left; }")
    parts.append("    .team-detail-table th { font-weight:600; color:#475569; background:#f9fafb; position:sticky; top:0; z-index:1; }")
    parts.append("    .team-detail-table .num { text-align:right; font-variant-numeric:tabular-nums; }")
    parts.append("    .team-detail-attr { font-variant-numeric:tabular-nums; }")
    parts.append("    .team-detail-breakdown { font-size:11px; display:flex; flex-direction:column; gap:6px; }")
    parts.append("    .team-detail-breakdown-unit { border:1px solid #e5e7eb; border-radius:8px; padding:6px 8px; background:#f8fafc; }")
    parts.append("    .team-detail-breakdown-unit h4 { margin:0 0 4px; font-size:12px; }")
    parts.append("    .team-detail-breakdown-unit table { width:100%; border-collapse:collapse; font-size:11px; }")
    parts.append("    .team-detail-breakdown-unit th, .team-detail-breakdown-unit td { padding:2px 4px; text-align:left; }")
    parts.append("    .team-detail-breakdown-unit th { color:#6b7280; font-weight:500; }")
    parts.append("    @media (max-width: 900px) { .kpis { grid-template-columns: repeat(2, minmax(0,1fr)); } .team-grid { grid-template-columns: 1fr; } }")
    parts.append("    @media (max-width: 600px) { .kpis { grid-template-columns: 1fr; } th:nth-child(4), td:nth-child(4), th:nth-child(5), td:nth-child(5), th:nth-child(6), td:nth-child(6) { display:none; } .team-card-body { flex-direction:column; } .team-detail-columns { grid-template-columns: 1fr; } .team-detail-panel { padding:12px 10px 14px; } }")
    parts.append("  </style>")
    parts.append("  <script>")
    parts.append("  (function() {")
    parts.append("    function getData() {")
    parts.append("      const el = document.getElementById('teams-data');")
    parts.append("      if (!el) return null;")
    parts.append("      try { return JSON.parse(el.textContent || '{}'); } catch (e) { return null; }")
    parts.append("    }")
    parts.append("    function closeTeamDetail() {")
    parts.append("      const overlay = document.getElementById('team-detail-overlay');")
    parts.append("      if (!overlay) return;")
    parts.append("      overlay.classList.remove('visible');")
    parts.append("      overlay.setAttribute('aria-hidden', 'true');")
    parts.append("    }")
    parts.append("    function openTeamDetail(abbr, DATA) {")
    parts.append("      if (!DATA || !DATA.rosters) return;")
    parts.append("      const rosterMap = DATA.rosters || {};")
    parts.append("      const unitsMap = DATA.unit_breakdowns || {};")
    parts.append("      const roster = rosterMap[abbr];")
    parts.append("      if (!roster || !roster.length) return;")
    parts.append("      const overlay = document.getElementById('team-detail-overlay');")
    parts.append("      if (!overlay) return;")
    parts.append("      const teamMeta = (DATA.teams || []).find(function(t) { return String(t.team_abbrev || '') === String(abbr || ''); });")
    parts.append("      const titleEl = document.getElementById('team-detail-title');")
    parts.append("      const subEl = document.getElementById('team-detail-subtitle');")
    parts.append("      const rosterTable = document.getElementById('team-detail-roster');")
    parts.append("      const breakdownRoot = document.getElementById('team-detail-breakdown');")
    parts.append("      if (!rosterTable || !breakdownRoot) return;")
    parts.append("      const name = teamMeta && (teamMeta.team_name || teamMeta.team_abbrev || abbr) || abbr;")
    parts.append("      const rank = teamMeta && teamMeta.overall_rank;")
    parts.append("      const overall = teamMeta && teamMeta.overall_score;")
    parts.append("      if (titleEl) { titleEl.textContent = name + ' (' + abbr + ')'; }")
    parts.append("      if (subEl) {")
    parts.append("        const bits = [];")
    parts.append("        if (typeof rank === 'number' && rank) bits.push('#' + rank + ' overall roster grade');")
    parts.append("        if (typeof overall === 'number') bits.push('Overall ' + overall.toFixed(1));")
    parts.append("        subEl.textContent = bits.join(' • ');")
    parts.append("      }")
    parts.append("      const byId = {};")
    parts.append("      roster.forEach(function(p) { if (p && p.player_id != null) byId[String(p.player_id)] = p; });")
    parts.append("      rosterTable.innerHTML = '';")
    parts.append("      const thead = document.createElement('thead');")
    parts.append("      thead.innerHTML = '<tr><th>Pos</th><th>Player</th><th class=num>OVR</th><th>Dev</th><th>Top attributes</th></tr>';")
    parts.append("      rosterTable.appendChild(thead);")
    parts.append("      const tbody = document.createElement('tbody');")
    parts.append("      roster.forEach(function(p) {")
    parts.append("        const tr = document.createElement('tr');")
    parts.append("        const attrs = (p.top_attrs || []).map(function(a) { return a.key + ': ' + a.value; }).join(', ');")
    parts.append("        tr.innerHTML = '<td>' + (p.position || '') + '</td>' +")
    parts.append("          '<td>' + (p.name || '') + '</td>' +")
    parts.append("          '<td class=num>' + (p.ovr != null ? p.ovr : '') + '</td>' +")
    parts.append("          '<td>' + (p.dev_label || '') + '</td>' +")
    parts.append("          '<td class=team-detail-attr>' + attrs + '</td>';")
    parts.append("        tbody.appendChild(tr);")
    parts.append("      });")
    parts.append("      rosterTable.appendChild(tbody);")
    parts.append("      breakdownRoot.innerHTML = '';")
    parts.append("      const allUnits = ['off_pass','off_run','def_coverage','pass_rush','run_defense'];")
    parts.append("      const labels = { off_pass: 'Off Pass', off_run: 'Off Run', def_coverage: 'Pass Coverage', pass_rush: 'Pass Rush', run_defense: 'Run Defense' };")
    parts.append("      const teamUnits = unitsMap && unitsMap[abbr];")
    parts.append("      if (teamUnits) {")
    parts.append("        allUnits.forEach(function(key) {")
    parts.append("          const u = teamUnits[key];")
    parts.append("          if (!u) return;")
    parts.append("          const card = document.createElement('div');")
    parts.append("          card.className = 'team-detail-breakdown-unit';")
    parts.append("          const h = document.createElement('h4');")
    parts.append("          const label = (u.label || labels[key] || key);")
    parts.append("          let grade = '';")
    parts.append("          if (typeof u.norm_score === 'number') grade = ' — grade ' + u.norm_score.toFixed(1);")
    parts.append("          h.textContent = label + grade;")
    parts.append("          card.appendChild(h);")
    parts.append("          if (typeof u.raw_score === 'number') {")
    parts.append("            const p = document.createElement('p');")
    parts.append("            p.textContent = 'Raw starter blend: ' + u.raw_score.toFixed(1);")
    parts.append("            card.appendChild(p);")
    parts.append("          }")
    parts.append("          const tbl = document.createElement('table');")
    parts.append("          const th = document.createElement('thead');")
    parts.append("          th.innerHTML = '<tr><th>Pos</th><th class=num>Wt%</th><th class=num>Pos score</th><th>Starters used</th></tr>';")
    parts.append("          tbl.appendChild(th);")
    parts.append("          const tb = document.createElement('tbody');")
    parts.append("          (u.positions || []).forEach(function(posInfo) {")
    parts.append("            const tr = document.createElement('tr');")
    parts.append("            const wtPct = (posInfo.weight_share != null ? (posInfo.weight_share * 100).toFixed(0) : '');")
    parts.append("            const posScore = (posInfo.avg_unit_score != null ? posInfo.avg_unit_score.toFixed(1) : '');")
    parts.append("            const starters = (posInfo.players || []).map(function(pl) {")
    parts.append("              const pid = pl.player_id != null ? String(pl.player_id) : '';")
    parts.append("              const base = pid && byId[pid] ? byId[pid] : null;")
    parts.append("              if (!base) return '';")
    parts.append("              const tag = (base.position || '') + ' ' + (base.name || '');")
    parts.append("              const ovr = base.ovr != null ? base.ovr : '';")
    parts.append("              const dev = base.dev_label || '';")
    parts.append("              const parts = [tag];")
    parts.append("              if (ovr !== '') parts.push(String(ovr));")
    parts.append("              if (dev) parts.push(dev);")
    parts.append("              return parts.join(' ');")
    parts.append("            }).filter(Boolean).join('; ');")
    parts.append("            tr.innerHTML = '<td>' + (posInfo.pos || '') + '</td>' +")
    parts.append("              '<td class=num>' + wtPct + '</td>' +")
    parts.append("              '<td class=num>' + posScore + '</td>' +")
    parts.append("              '<td>' + starters + '</td>';")
    parts.append("            tb.appendChild(tr);")
    parts.append("          });")
    parts.append("          tbl.appendChild(tb);")
    parts.append("          card.appendChild(tbl);")
    parts.append("          breakdownRoot.appendChild(card);")
    parts.append("        });")
    parts.append("      }")
    parts.append("      overlay.classList.add('visible');")
    parts.append("      overlay.setAttribute('aria-hidden', 'false');")
    parts.append("    }")
    parts.append("    function attachTeamDetailHandlers() {")
    parts.append("      const DATA = getData();")
    parts.append("      if (!DATA) return;")
    parts.append("      const rows = document.querySelectorAll('#teams-table tbody tr[data-team-abbr]');")
    parts.append("      rows.forEach(function(tr) {")
    parts.append("        tr.addEventListener('click', function() {")
    parts.append("          const abbr = tr.getAttribute('data-team-abbr');")
    parts.append("          if (abbr) openTeamDetail(abbr, DATA);")
    parts.append("        });")
    parts.append("      });")
    parts.append("      const cards = document.querySelectorAll('.team-card[data-team-abbr]');")
    parts.append("      cards.forEach(function(card) {")
    parts.append("        card.addEventListener('click', function() {")
    parts.append("          const abbr = card.getAttribute('data-team-abbr');")
    parts.append("          if (abbr) openTeamDetail(abbr, DATA);")
    parts.append("        });")
    parts.append("      });")
    parts.append("      const overlay = document.getElementById('team-detail-overlay');")
    parts.append("      if (overlay) {")
    parts.append("        const closeBtn = overlay.querySelector('.team-detail-close');")
    parts.append("        const backdrop = overlay.querySelector('.team-detail-backdrop');")
    parts.append("        if (closeBtn) closeBtn.addEventListener('click', closeTeamDetail);")
    parts.append("        if (backdrop) backdrop.addEventListener('click', closeTeamDetail);")
    parts.append("      }")
    parts.append("      document.addEventListener('keydown', function(ev) { if (ev.key === 'Escape') closeTeamDetail(); });")
    parts.append("    }")
    parts.append("    if (document.readyState === 'loading') {")
    parts.append("      document.addEventListener('DOMContentLoaded', attachTeamDetailHandlers);")
    parts.append("    } else {")
    parts.append("      attachTeamDetailHandlers();")
    parts.append("    }")
    parts.append("  })();")
    parts.append("  </script>")
    parts.append("</head>")
    parts.append("<body>")
    parts.append("  <div class=\"topbar\"><a class=\"back\" href=\"../index.html\" title=\"Back to index\">&#8592; Back to Index</a></div>")
    parts.append("  <div class=\"container\">")
    parts.append("    <header>")
    parts.append(f"      <h1>{escape(title)} <span class=\"pill\">Roster-based</span></h1>")
    parts.append(f"      <div class=\"subtitle\">{escape(subtitle)}</div>")
    parts.append(
        "      <div class=\"subtitle\">"
        "For X/Y roster unit comparison charts (Off vs Def, Pass vs Run, coverage vs pass rush), "
        "open the <a href='power_rankings_roster_charts.html'>Roster Power Explorer</a>."
        "</div>"
    )
    parts.append("    </header>")

    # Overview KPIs: overall average and simple context for a couple of units.
    parts.append("    <section class=\"panel\" id=\"overview\">")
    parts.append("      <div class=\"section-title\">League Overview</div>")
    parts.append("      <div class=\"section-intro\">Roster-based power rankings derived from unit strength scores. Higher scores reflect stronger starters and premium dev traits at key positions.</div>")
    parts.append("      <div class=\"kpis\">")

    def _fmt(val: float | None) -> str:
        try:
            if val is None:
                return "—"
            return f"{val:.1f}"
        except Exception:
            return "—"

    ov = league_ctx.get("overall_score") or {}
    parts.append("        <div class=\"kpi\"><b>Avg overall score</b><span>" + escape(_fmt(ov.get("avg"))) + "</span>"
                 "<div class=\"gbar\"><div class=\"fill\" style=\"width: " + escape(_fmt(ov.get("avg"))) + "%\"></div></div></div>")

    offp = league_ctx.get("off_pass_score") or {}
    parts.append("        <div class=\"kpi\"><b>Avg Off Pass</b><span>" + escape(_fmt(offp.get("avg"))) + "</span>"
                 "<div class=\"gbar\"><div class=\"fill\" style=\"width: " + escape(_fmt(offp.get("avg"))) + "%\"></div></div></div>")

    defc = league_ctx.get("def_cover_score") or {}
    parts.append("        <div class=\"kpi\"><b>Avg Coverage</b><span>" + escape(_fmt(defc.get("avg"))) + "</span>"
                 "<div class=\"gbar\"><div class=\"fill\" style=\"width: " + escape(_fmt(defc.get("avg"))) + "%\"></div></div></div>")

    parts.append("      </div>")
    parts.append("      <div class=\"chart-strip\" id=\"overall-chart\"></div>")
    parts.append("    </section>")

    # Methodology / configuration overview.
    parts.append("    <section class=\"panel\" id=\"methodology\">")
    parts.append("      <div class=\"section-title\">Methodology &amp; Config</div>")

    norm_text = "z-score (mean ~50, spread by standard deviation)"
    if normalization == "minmax":
        norm_text = "min–max to [0,100] across teams"

    parts.append(
        '      <div class="section-intro">'
        + escape(
            "Each unit score is a position-weighted blend of starter-quality ratings, "
            "boosted by premium dev traits at high OVR bands and then normalized to a 0–100 scale ("
            + norm_text
            + ")."
        )
        + "</div>"
    )

    # Unit position weighting lines (always based on the position-level
    # weights baked into this script so that readers can see which
    # positions drive each unit, regardless of overall unit weight
    # tweaks).
    unit_weight_lines: list[str] = []
    unit_labels = {
        "off_pass": "Off Pass (QB/WR/TE/OL)",
        "off_run": "Off Run (RB/FB/TE/OL)",
        "def_coverage": "Pass Coverage (CB/S/LB)",
        "pass_rush": "Pass Rush (DE/DT/LB)",
        "run_defense": "Run Defense (DE/DT/LB/S)",
    }
    for key in ["off_pass", "off_run", "def_coverage", "pass_rush", "run_defense"]:
        weights = UNIT_POSITION_WEIGHTS.get(key, {})
        if not weights:
            continue
        total = sum(v for v in weights.values() if v > 0)
        if total <= 0:
            continue
        parts_line: list[str] = []
        for pos, w in sorted(weights.items(), key=lambda kv: -kv[1]):
            if w <= 0:
                continue
            pct = (w / total) * 100.0
            parts_line.append(f"{pos} {pct:.0f}%")
        if parts_line:
            unit_label = unit_labels.get(key, key)
            unit_weight_lines.append(f"{unit_label}: " + ", ".join(parts_line))

    # Dev trait ladder description. Prefer any runtime configuration
    # provided via the CLI, falling back to defaults.
    dev_cfg = cfg.get("dev_multipliers") or DEFAULT_DEV_MULTIPLIERS
    dev_lines: list[str] = []
    for dev_code, label in DEV_LABELS.items():
        ladder = dev_cfg.get(dev_code) or DEFAULT_DEV_MULTIPLIERS.get(dev_code, [])
        if not ladder:
            dev_lines.append(f"{label}: baseline impact only (no extra multiplier by default).")
            continue
        parts_line = []
        for threshold, bonus in ladder:
            parts_line.append(f"+{bonus * 100:.0f}% above {threshold} OVR")
        dev_lines.append(f"{label}: " + ", ".join(parts_line))

    # Overall weighting text. Prefer runtime-configured overall unit
    # weights so the explanation matches the actual composite score.
    overall_cfg = cfg.get("overall_unit_weights") or DEFAULT_OVERALL_UNIT_WEIGHTS
    overall_parts: list[str] = []
    for key, label in [
        ("off_pass", "Off Pass"),
        ("off_run", "Off Run"),
        ("def_coverage", "Pass Coverage"),
        ("pass_rush", "Pass Rush"),
    ]:
        w = (overall_cfg.get(key) if isinstance(overall_cfg, dict) else None)
        if w is None or w <= 0:
            continue
        overall_parts.append(f"{label} {w * 100:.0f}%")
    overall_text = " + ".join(overall_parts)

    parts.append("      <div class=\"methodology-grid\">")
    parts.append("        <div class=\"methodology-col\">")
    parts.append("          <h3>Units &amp; position weighting</h3>")
    parts.append("          <ul class=\"methodology-list\">")
    for line in unit_weight_lines:
        parts.append("            <li>" + escape(line) + "</li>")
    parts.append("          </ul>")
    parts.append("        </div>")

    parts.append("        <div class=\"methodology-col\">")
    parts.append("          <h3>Dev traits impact</h3>")
    parts.append("          <ul class=\"methodology-list\">")
    for line in dev_lines:
        parts.append("            <li>" + escape(line) + "</li>")
    parts.append("          </ul>")
    parts.append("        </div>")

    parts.append("        <div class=\"methodology-col\">")
    parts.append("          <h3>Normalization &amp; overall score</h3>")
    if overall_text:
        parts.append(
            "          <p>" + escape(
                "Overall roster power combines normalized unit scores using: "
                + overall_text
                + ". Run Defense is shown as its own unit but not currently weighted into the composite score by default."
            )
            + "</p>"
        )
    parts.append(
        "          <p>" + escape(
            "Normalization method: " + normalization + " (" + norm_text + ")."
        )
        + "</p>"
    )
    parts.append("        </div>")
    parts.append("      </div>")
    parts.append("    </section>")

    # Controls + league-wide table.
    parts.append("    <section class=\"panel\" id=\"teams\">")
    parts.append("      <div class=\"section-title\">Teams – Roster Power Table</div>")
    parts.append("      <div class=\"controls\">")
    parts.append("        <label for=\"team-search\">Search team:</label>")
    parts.append("        <input id=\"team-search\" type=\"search\" placeholder=\"Filter by team or abbrev...\" />")
    parts.append("        <span style=\"flex:1 0 auto\"></span>")
    parts.append("        <span>Tip: click column headers to sort (overall or any unit).</span>")
    parts.append("      </div>")
    parts.append("      <div class=\"table-wrap\">")
    parts.append("        <table class=\"sortable\" id=\"teams-table\">")
    parts.append("          <thead><tr>"
                 "<th>Rank</th>"
                 "<th>Team</th>"
                 "<th>Overall</th>"
                 "<th>Off Pass</th>"
                 "<th>Off Run</th>"
                 "<th>Def Coverage</th>"
                 "<th>Pass Rush</th>"
                 "<th>Run Def</th>"
                 "<th>Dev traits</th>"
                 "<th>Top contributors</th>"
                 "</tr></thead>")
    parts.append("          <tbody>")

    for row in teams_metrics:
        team_abbrev = str(row.get("team_abbrev") or "")
        team_name = str(row.get("team_name") or team_abbrev)
        overall_score = float(row.get("overall_score") or 0.0)
        off_pass_score = float(row.get("off_pass_score") or 0.0)
        off_run_score = float(row.get("off_run_score") or 0.0)
        def_cover_score = float(row.get("def_cover_score") or 0.0)
        def_pr_score = float(row.get("def_pass_rush_score") or 0.0)
        def_run_score = float(row.get("def_run_score") or 0.0)
        overall_rank = int(row.get("overall_rank") or 0)
        dev_xf = int(row.get("dev_xf") or 0)
        dev_ss = int(row.get("dev_ss") or 0)
        dev_star = int(row.get("dev_star") or 0)
        dev_norm = int(row.get("dev_normal") or 0)
        contrib = str(row.get("top_contributors") or "")

        parts.append(
            "            <tr data-team-abbr=\""
            + escape(team_abbrev)
            + "\" data-team-name=\""
            + escape(team_name)
            + "\">"
        )
        parts.append(
            "              <td class=\"num rank-cell\" data-sort=\""
            + escape(str(overall_rank))
            + "\">"
            + escape(str(overall_rank))
            + "</td>"
        )
        parts.append(
            "              <td><div class=\"team-cell\"><span class=\"team-tag\">"
            + escape(team_name)
            + "<span>"
            + escape(team_abbrev)
            + "</span></span></div></td>"
        )

        def _metric_cell(val: float) -> str:
            pct = max(0.0, min(100.0, float(val)))
            return (
                "<td class=\"num\" data-sort=\""
                + escape(f"{val:.1f}")
                + "\"><div class=\"metric\"><span class=\"metric-value\">"
                + escape(f"{val:.1f}")
                + "</span><div class=\"metric-bar\"><div class=\"metric-bar-fill\" style=\"width: "
                + escape(f"{pct:.1f}")
                + "%\"></div></div></div></td>"
            )

        parts.append("              " + _metric_cell(overall_score))
        parts.append("              " + _metric_cell(off_pass_score))
        parts.append("              " + _metric_cell(off_run_score))
        parts.append("              " + _metric_cell(def_cover_score))
        parts.append("              " + _metric_cell(def_pr_score))
        parts.append("              " + _metric_cell(def_run_score))

        dev_html = [
            f"<span class=\"chip chip-xf\">XF {dev_xf}</span>",
            f"<span class=\"chip chip-ss\">SS {dev_ss}</span>",
            f"<span class=\"chip chip-star\">Star {dev_star}</span>",
            f"<span class=\"chip chip-norm\">Norm {dev_norm}</span>",
        ]
        parts.append(
            "              <td><div class=\"dev-chips\">"
            + "".join(dev_html)
            + "</div></td>"
        )

        parts.append("              <td>" + escape(contrib) + "</td>")
        parts.append("            </tr>")

    parts.append("          </tbody>")
    parts.append("        </table>")
    parts.append("      </div>")
    parts.append("    </section>")

    # Team-level cards with radar-style unit overview and narrative.
    parts.append("    <section class=\"panel\" id=\"team-insights\">")
    parts.append("      <div class=\"section-title\">Team Unit Profiles &amp; Narratives</div>")
    parts.append(
        '      <div class="section-intro">'
        + escape(
            "Per-team view of unit balance, dev-trait composition, and roster storylines. "
            "Use alongside the table above when scouting matchups or trade targets."
        )
        + "</div>"
    )
    parts.append("      <div class=\"team-grid\">")

    for row in teams_metrics:
        team_abbrev = str(row.get("team_abbrev") or "")
        team_name = str(row.get("team_name") or team_abbrev)
        overall_score = float(row.get("overall_score") or 0.0)
        overall_rank = int(row.get("overall_rank") or 0)
        dev_xf = int(row.get("dev_xf") or 0)
        dev_ss = int(row.get("dev_ss") or 0)
        dev_star = int(row.get("dev_star") or 0)
        dev_norm = int(row.get("dev_normal") or 0)

        premium_dev = dev_xf + dev_ss
        card_classes = ["team-card"]
        if premium_dev >= 6:
            card_classes.append("dev-elite")
        card_class = " ".join(card_classes)

        narrative = generate_team_narrative(row, league_ctx)
        strengths_text = str(narrative.get("strengths") or "").strip()
        weaknesses_text = str(narrative.get("weaknesses") or "").strip()
        summary_text = str(narrative.get("summary") or "").strip()

        parts.append(
            "        <article class=\""
            + card_class
            + "\" data-team-abbr=\""
            + escape(team_abbrev)
            + "\">"
        )
        parts.append("          <div class=\"team-card-header\">")
        parts.append("            <div>")
        parts.append(
            '              <div class="team-card-title">'
            + escape(team_name)
            + " <span>("
            + escape(team_abbrev)
            + ")</span></div>"
        )
        parts.append(
            '              <div class="team-card-sub">Overall '
            + escape(f"{overall_score:.1f}")
            + " (rank "
            + escape(str(overall_rank))
            + ")</div>"
        )
        parts.append("            </div>")
        parts.append("            <div class=\"team-card-dev\">")
        parts.append(
            "              <strong>Dev traits:</strong> "
            + "<span>XF "
            + escape(str(dev_xf))
            + "</span><span>SS "
            + escape(str(dev_ss))
            + "</span><span>Star "
            + escape(str(dev_star))
            + "</span><span>Norm "
            + escape(str(dev_norm))
            + "</span>"
        )
        parts.append("            </div>")
        parts.append("          </div>")

        radar_html = _radar_svg(row)

        parts.append("          <div class=\"team-card-body\">")
        parts.append("            <div class=\"radar-shell\">")
        parts.append("              " + radar_html)
        parts.append(
            '              <div class="radar-labels"><span>OP</span><span>OR</span><span>Cov</span><span>Rush</span><span>Run</span></div>'
        )
        parts.append("            </div>")

        parts.append(
            '            <div class="team-narrative" data-team-abbr="'
            + escape(team_abbrev)
            + "\">"
        )
        if summary_text:
            parts.append("              <p class=\"label\">Summary</p>")
            parts.append("              <p>" + escape(summary_text) + "</p>")
        if strengths_text:
            parts.append("              <p class=\"label\">Strengths</p>")
            parts.append("              <p>" + escape(strengths_text) + "</p>")
        if weaknesses_text:
            parts.append("              <p class=\"label\">Weaknesses</p>")
            parts.append("              <p>" + escape(weaknesses_text) + "</p>")
        parts.append("            </div>")
        parts.append("          </div>")
        parts.append("        </article>")

    parts.append("      </div>")
    parts.append("    </section>")

    # Team detail overlay used as an in-page "team page". Clicking a
    # row in the table or a team card opens this panel and shows the
    # full roster plus a per-unit scoring breakdown for that team.
    parts.append("    <div id=\"team-detail-overlay\" class=\"team-detail-overlay\" aria-hidden=\"true\">")
    parts.append("      <div class=\"team-detail-backdrop\"></div>")
    parts.append("      <div class=\"team-detail-panel\">")
    parts.append("        <button type=\"button\" class=\"team-detail-close\" aria-label=\"Close team detail\">&#x00D7;</button>")
    parts.append("        <div class=\"team-detail-header\">")
    parts.append("          <h2 id=\"team-detail-title\"></h2>")
    parts.append("          <p id=\"team-detail-subtitle\" class=\"team-detail-sub\"></p>")
    parts.append("        </div>")
    parts.append("        <div class=\"team-detail-body\">")
    parts.append("          <div class=\"team-detail-columns\">")
    parts.append("            <section class=\"team-detail-col\">")
    parts.append("              <h3>Roster overview (OVR &amp; key attributes)</h3>")
    parts.append("              <table id=\"team-detail-roster\" class=\"team-detail-table\"></table>")
    parts.append("            </section>")
    parts.append("            <section class=\"team-detail-col\">")
    parts.append("              <h3>Unit strength breakdown</h3>")
    parts.append("              <div id=\"team-detail-breakdown\" class=\"team-detail-breakdown\"></div>")
    parts.append("            </section>")
    parts.append("          </div>")
    parts.append("        </div>")
    parts.append("      </div>")
    parts.append("    </div>")

    parts.append("  </div>")
    parts.append("  <script id=\"teams-data\" type=\"application/json\">")
    parts.append(data_blob)
    parts.append("  </script>")
    parts.append("</body>")
    parts.append("</html>")

    html_out = "\n".join(parts)
    out_dir = os.path.dirname(path)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(html_out)

    print(f"wrote power rankings HTML report to {path}", file=sys.stdout)


###############################################################################
# CLI
###############################################################################


def _load_json_spec(spec: str, *, label: str) -> dict:
    """Load a JSON mapping from a file path or inline JSON string.

    The *spec* value may be either a path to a JSON file or a literal
    JSON object string. This helper is used for configuration flags like
    ``--weights-json`` and ``--dev-multipliers-json`` so that callers
    can keep small configs inline or in separate files.
    """

    if not spec:
        return {}

    # Prefer treating *spec* as a file path when it exists on disk.
    if os.path.exists(spec):
        try:
            with open(spec, "r", encoding="utf-8") as fh:
                data = json.load(fh)
        except Exception as exc:  # pragma: no cover - defensive
            print(
                f"error: failed to load {label} JSON from file {spec}: {exc}",
                file=sys.stderr,
            )
            sys.exit(2)
    else:
        try:
            data = json.loads(spec)
        except Exception as exc:  # pragma: no cover - defensive
            print(
                f"error: failed to parse {label} JSON value: {exc}",
                file=sys.stderr,
            )
            sys.exit(2)

    if not isinstance(data, dict):
        print(
            f"error: {label} JSON must be a mapping/object (got {type(data).__name__})",
            file=sys.stderr,
        )
        sys.exit(2)

    return data


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Roster-based power rankings: roster exports and unit scoring"
        )
    )

    parser.add_argument(
        "--players",
        default="MEGA_players.csv",
        help="Path to MEGA_players.csv (default: MEGA_players.csv)",
    )
    parser.add_argument(
        "--teams",
        default="MEGA_teams.csv",
        help="Path to MEGA_teams.csv (default: MEGA_teams.csv)",
    )
    parser.add_argument(
        "--rosters-dir",
        default=os.path.join("output", "team_rosters"),
        help="Directory for per-team roster CSVs (default: output/team_rosters)",
    )

    # Roster export on by default; allow explicit opt-out.
    parser.add_argument(
        "--export-rosters",
        dest="export_rosters",
        action="store_true",
        help="Export per-team roster CSVs (default)",
    )
    parser.add_argument(
        "--no-export-rosters",
        dest="export_rosters",
        action="store_false",
        help="Skip per-team roster CSV export",
    )
    parser.set_defaults(export_rosters=True)

    parser.add_argument(
        "--out-csv",
        default=os.path.join("output", "power_rankings_roster.csv"),
        help="Output CSV for power rankings (default: output/power_rankings_roster.csv)",
    )
    parser.add_argument(
        "--out-html",
        default=os.path.join("docs", "power_rankings_roster.html"),
        help="Output HTML report path (default: docs/power_rankings_roster.html)",
    )
    parser.add_argument(
        "--include-st",
        action="store_true",
        help="Include Special Teams unit in exports and scoring",
    )
    parser.add_argument(
        "--weights-json",
        help=(
            "JSON mapping for overall unit weights (path to file or inline JSON). "
            "Example: '{\"off_pass\": 0.35, \"off_run\": 0.15, "
            "\"def_coverage\": 0.30, \"pass_rush\": 0.20}'."
        ),
    )
    parser.add_argument(
        "--dev-multipliers-json",
        help=(
            "JSON mapping for dev multipliers by dev tier and OVR band "
            "(path to file or inline JSON). Keys are devTrait codes "
            "('3' X-Factor, '2' Superstar, '1' Star, '0' Normal) and values "
            "are [ovr_threshold, bonus] pairs; e.g. '{\"3\": [[90, 0.15], [85, 0.10]]}'."
        ),
    )
    parser.add_argument(
        "--normalization",
        choices=["zscore", "minmax"],
        default="zscore",
        help="Normalization method for unit scores (default: zscore)",
    )
    parser.add_argument(
        "--no-clobber",
        action="store_true",
        help=(
            "Fail if target outputs already exist instead of overwriting "
            "(applies to CSV/HTML and roster CSVs)."
        ),
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose logging",
    )

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    # Optional JSON-based configuration for overall unit weights and
    # dev multipliers. These override the hard-coded defaults when
    # provided, enabling experimentation without code changes.
    overall_weights: dict[str, float] | None = None
    dev_multipliers: dict | None = None

    if getattr(args, "weights_json", None):
        raw = _load_json_spec(args.weights_json, label="weights")
        # Cast values to float defensively.
        overall_weights = {str(k): float(v) for k, v in raw.items()}

    if getattr(args, "dev_multipliers_json", None):
        dev_multipliers = _load_json_spec(args.dev_multipliers_json, label="dev-multipliers")

    # Respect --no-clobber by refusing to overwrite existing primary
    # outputs (CSV/HTML and roster CSVs).
    if getattr(args, "no_clobber", False):
        existing: list[str] = []
        if os.path.exists(args.out_csv):
            existing.append(args.out_csv)
        if os.path.exists(args.out_html):
            existing.append(args.out_html)
        if args.export_rosters and os.path.isdir(args.rosters_dir):
            for name in os.listdir(args.rosters_dir):
                if name.lower().endswith(".csv"):
                    existing.append(os.path.join(args.rosters_dir, name))
                    break
        if existing:
            print(
                "error: --no-clobber specified and one or more outputs already exist: "
                + ", ".join(existing),
                file=sys.stderr,
            )
            return 1

    if args.verbose:
        print(
            f"info: loading teams from {args.teams} and players from {args.players}",
            file=sys.stderr,
        )

    teams = read_teams(args.teams)
    team_index = build_team_index(teams)

    players_raw = read_players(args.players)
    players: list[dict] = [normalize_player_row(r, team_index) for r in players_raw]

    # Pre-compute players grouped by team abbrev so both the scoring
    # pipeline and HTML renderer can reason about per-team rosters
    # without re-deriving this mapping.
    players_by_team: dict[str, list[dict]] = {}
    for p in players:
        abbr = (p.get("team_abbrev") or "").strip()
        if not abbr or abbr == "FA":
            continue
        players_by_team.setdefault(abbr, []).append(p)

    if args.export_rosters:
        if args.verbose:
            print(
                f"info: exporting team rosters to {args.rosters_dir}",
                file=sys.stderr,
            )
        export_team_rosters(
            players,
            team_index,
            args.rosters_dir,
            split_units=True,
            include_st=args.include_st,
        )
    else:
        if args.verbose:
            print("info: --no-export-rosters specified; skipping roster export", file=sys.stderr)

    # Phase 2: compute unit scores and overall power rankings CSV.
    if args.verbose:
        print(
            "info: computing unit scores and overall power rankings",
            file=sys.stderr,
        )

    teams_metrics = build_team_metrics(
        players,
        team_index,
        include_st=args.include_st,
        normalization=args.normalization,
        overall_weights=overall_weights,
        dev_multipliers=dev_multipliers,
    )
    write_power_rankings_csv(args.out_csv, teams_metrics)

    # Phase 3: HTML report generation.
    league_ctx = compute_league_context(teams_metrics)
    html_config = {
        "normalization": args.normalization,
        "include_st": bool(args.include_st),
        "overall_unit_weights": overall_weights or DEFAULT_OVERALL_UNIT_WEIGHTS,
        "dev_multipliers": dev_multipliers or DEFAULT_DEV_MULTIPLIERS,
    }
    if args.verbose:
        print(
            f"info: rendering HTML report to {args.out_html}",
            file=sys.stderr,
        )
    render_html_report(
        args.out_html,
        teams_metrics,
        config=html_config,
        league_context=league_ctx,
        players_by_team=players_by_team,
    )

    return 0


if __name__ == "__main__":  # pragma: no cover - CLI entry
    raise SystemExit(main())
