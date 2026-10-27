"""CSV input, normalization, and per-team roster export helpers."""
from __future__ import annotations

import csv
import os
import sys
from typing import Iterable


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

    def _display_name(attr_key: str) -> str:
        # Strip generic "Rating" suffix so labels match the shorter
        # style used elsewhere (e.g. accelRating -> accel,
        # finesseMovesRating -> finesseMoves).
        if attr_key.endswith("Rating"):
            return attr_key[: -len("Rating")]
        return attr_key

    return [{"key": _display_name(k), "value": round(v, 1)} for k, v in top]


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
