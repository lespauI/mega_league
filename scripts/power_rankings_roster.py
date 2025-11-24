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
import math
import os
import statistics as st
import sys
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

    out: dict = {
        "team_abbrev": team_abbrev,
        "team_name": team_name,
        "player_id": player_id,
        "player_name": player_name,
        "position": position,
        "normalized_pos": normalized_pos,
        "ovr": int(ovr) if ovr is not None else 0,
        "dev": dev,
    }

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


def _player_unit_score(player: dict, dev_multipliers: dict | None = None) -> float:
    ovr = safe_int(player.get("ovr"), 0) or 0
    dev = str(player.get("dev") or "0")
    bonus = _dev_multiplier(ovr, dev, overrides=dev_multipliers)
    # Scale OVR by (1 + bonus); low-OVR devs get 0 bonus.
    return float(ovr) * (1.0 + bonus)


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
        help="(Unused in Phase 1) Output HTML report path",
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

    return 0


if __name__ == "__main__":  # pragma: no cover - CLI entry
    raise SystemExit(main())
