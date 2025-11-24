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


def score_unit(
    players: list[dict],
    unit_type: str,
    weights: dict | None = None,
    dev_multipliers: dict | None = None,
) -> float:
    """Compute a raw (unnormalized) score for a unit.

    The score is a weighted average of position-group scores, where each
    group's score is the average of selected starters' OVRs adjusted by
    dev-trait multipliers.
    """

    if not players:
        return 0.0

    pos_weights = dict(UNIT_POSITION_WEIGHTS.get(unit_type, {}))
    if weights:
        # Allow overriding or extending the default position weights.
        pos_weights.update({k: float(v) for k, v in weights.items()})

    total_w = sum(v for v in pos_weights.values() if v > 0)
    if total_w <= 0:
        return 0.0

    starters_by_pos = select_unit_starters(players, unit_type)
    score = 0.0
    for pos, w in pos_weights.items():
        if w <= 0:
            continue
        chosen = starters_by_pos.get(pos, [])
        if not chosen:
            continue
        vals = [_player_unit_score(p, dev_multipliers=dev_multipliers) for p in chosen]
        if not vals:
            continue
        avg = sum(vals) / len(vals)
        score += (w / total_w) * avg

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

    default_weights = {
        "off_pass": 0.30,
        "off_run": 0.20,
        "def_coverage": 0.30,
        "pass_rush": 0.20,
    }
    if weights:
        default_weights.update({k: float(v) for k, v in weights.items()})

    usable_items = [(k, default_weights[k]) for k in default_weights.keys() if k in units and default_weights[k] > 0]
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


def render_html_report(
    path: str,
    teams_metrics: list[dict],
    config: dict | None = None,
    league_context: dict | None = None,
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

    data_blob = json.dumps(
        {
            "teams": js_teams,
            "config": cfg,
            "league": league_ctx,
        },
        ensure_ascii=False,
    )

    normalization = cfg.get("normalization", "zscore")

    title = "Roster Power Rankings — Roster Analytics"
    subtitle = f"League-wide roster strength overview (normalization: {normalization})"

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
    parts.append("    @media (max-width: 900px) { .kpis { grid-template-columns: repeat(2, minmax(0,1fr)); } }")
    parts.append("    @media (max-width: 600px) { .kpis { grid-template-columns: 1fr; } th:nth-child(4), td:nth-child(4), th:nth-child(5), td:nth-child(5), th:nth-child(6), td:nth-child(6) { display:none; } }")
    parts.append("  </style>")
    parts.append("  <script>")
    parts.append("  // Simple table sorter: click any <th> in a .sortable table to sort by that column\n"  # noqa: E501
                 "  (function() {\n"  # noqa: E501
                 "    function getCellValue(tr, idx) {\n"
                 "      const td = tr.children[idx];\n"
                 "      if (!td) return '';\n"
                 "      const ds = td.getAttribute('data-sort');\n"
                 "      const txt = ds != null ? ds : (td.textContent || '');\n"
                 "      return txt.trim();\n"
                 "    }\n"
                 "    function asNumber(v) {\n"
                 "      if (v === '' || v == null) return NaN;\n"
                 "      const n = parseFloat(String(v).replace(/[,\\s]/g, ''));\n"
                 "      return isNaN(n) ? NaN : n;\n"
                 "    }\n"
                 "    function makeComparer(idx, asc) {\n"
                 "      return function(a, b) {\n"
                 "        const va = getCellValue(a, idx);\n"
                 "        const vb = getCellValue(b, idx);\n"
                 "        const na = asNumber(va);\n"
                 "        const nb = asNumber(vb);\n"
                 "        let cmp;\n"
                 "        if (!isNaN(na) && !isNaN(nb)) { cmp = na - nb; } else { cmp = va.localeCompare(vb, undefined, {numeric:true, sensitivity:'base'}); }\n"
                 "        return asc ? cmp : -cmp;\n"
                 "      }\n"
                 "    }\n"
                 "    function initSortableTables() {\n"
                 "      document.querySelectorAll('table.sortable').forEach(function(table) {\n"
                 "        const thead = table.tHead; if (!thead) return;\n"
                 "        const headers = thead.rows[0] ? thead.rows[0].cells : [];\n"
                 "        Array.from(headers).forEach(function(th, idx) {\n"
                 "          th.addEventListener('click', function() {\n"
                 "            const tbody = table.tBodies[0]; if (!tbody) return;\n"
                 "            const rows = Array.from(tbody.rows);\n"
                 "            const current = th.getAttribute('data-sort-dir') || 'asc';\n"
                 "            const nextDir = current === 'asc' ? 'desc' : 'asc';\n"
                 "            rows.sort(makeComparer(idx, nextDir === 'asc'));\n"
                 "            Array.from(headers).forEach(h => h.removeAttribute('data-sort-dir'));\n"
                 "            th.setAttribute('data-sort-dir', nextDir);\n"
                 "            rows.forEach(r => tbody.appendChild(r));\n"
                 "          });\n"
                 "        });\n"
                 "      });\n"
                 "    }\n"
                 "    function initSearchAndCharts() {\n"
                 "      const dataEl = document.getElementById('teams-data');\n"
                 "      let DATA = null;\n"
                 "      if (dataEl) {\n"
                 "        try { DATA = JSON.parse(dataEl.textContent || '{}'); } catch (e) { DATA = null; }\n"
                 "      }\n"
                 "      const search = document.getElementById('team-search');\n"
                 "      if (search) {\n"
                 "        search.addEventListener('input', function() {\n"
                 "          const q = (this.value || '').toLowerCase();\n"
                 "          const rows = document.querySelectorAll('#teams-table tbody tr');\n"
                 "          rows.forEach(function(tr) {\n"
                 "            const name = (tr.getAttribute('data-team-name') || '').toLowerCase();\n"
                 "            const abbr = (tr.getAttribute('data-team-abbr') || '').toLowerCase();\n"
                 "            const hay = name + ' ' + abbr;\n"
                 "            tr.style.display = hay.indexOf(q) === -1 ? 'none' : '';\n"
                 "          });\n"
                 "        });\n"
                 "      }\n"
                 "      function renderOverallChart() {\n"
                 "        if (!DATA || !DATA.teams) return;\n"
                 "        const wrap = document.getElementById('overall-chart');\n"
                 "        if (!wrap) return;\n"
                 "        const teams = Array.from(DATA.teams).sort((a,b) => (a.overall_rank||0) - (b.overall_rank||0));\n"
                 "        wrap.innerHTML = '';\n"
                 "        teams.forEach(function(t) {\n"
                 "          const score = typeof t.overall_score === 'number' ? t.overall_score : parseFloat(t.overall_score || '0');\n"
                 "          const pct = Math.max(0, Math.min(100, isNaN(score) ? 0 : score));\n"
                 "          const div = document.createElement('div');\n"
                 "          div.className = 'chart-bar';\n"
                 "          const fill = document.createElement('div');\n"
                 "          fill.className = 'chart-bar-fill';\n"
                 "          fill.style.width = pct + '%';\n"
                 "          const label = document.createElement('div');\n"
                 "          label.className = 'chart-bar-label';\n"
                 "          const name = (t.team_abbrev || '') + ' — ' + (t.team_name || '');\n"
                 "          label.innerHTML = '<b>' + name + '</b><span>Overall ' + (score || 0).toFixed ? (score || 0).toFixed(1) : score + '</span>';\n"
                 "          div.appendChild(fill);\n"
                 "          div.appendChild(label);\n"
                 "          wrap.appendChild(div);\n"
                 "        });\n"
                 "      }\n"
                 "      renderOverallChart();\n"
                 "    }\n"
                 "    if (document.readyState === 'loading') {\n"
                 "      document.addEventListener('DOMContentLoaded', function() { initSortableTables(); initSearchAndCharts(); });\n"
                 "    } else {\n"
                 "      initSortableTables(); initSearchAndCharts();\n"
                 "    }\n"
                 "  })();\n")
    parts.append("  </script>")
    parts.append("</head>")
    parts.append("<body>")
    parts.append("  <div class=\"topbar\"><a class=\"back\" href=\"../index.html\" title=\"Back to index\">&#8592; Back to Index</a></div>")
    parts.append("  <div class=\"container\">")
    parts.append("    <header>")
    parts.append(f"      <h1>{escape(title)} <span class=\"pill\">Roster-based</span></h1>")
    parts.append(f"      <div class=\"subtitle\">{escape(subtitle)}</div>")
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
        "--normalization",
        choices=["zscore", "minmax"],
        default="zscore",
        help="Normalization method for unit scores (default: zscore)",
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

    if args.verbose:
        print(
            f"info: loading teams from {args.teams} and players from {args.players}",
            file=sys.stderr,
        )

    teams = read_teams(args.teams)
    team_index = build_team_index(teams)

    players_raw = read_players(args.players)
    players: list[dict] = [normalize_player_row(r, team_index) for r in players_raw]

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
    )
    write_power_rankings_csv(args.out_csv, teams_metrics)

    # Phase 3: HTML report generation.
    league_ctx = compute_league_context(teams_metrics)
    html_config = {
        "normalization": args.normalization,
        "include_st": bool(args.include_st),
    }
    if args.verbose:
        print(
            f"info: rendering HTML report to {args.out_html}",
            file=sys.stderr,
        )
    render_html_report(args.out_html, teams_metrics, config=html_config, league_context=league_ctx)

    return 0


if __name__ == "__main__":  # pragma: no cover - CLI entry
    raise SystemExit(main())
