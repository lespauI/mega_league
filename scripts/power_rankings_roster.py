#!/usr/bin/env python3
"""Roster-based power rankings – Phase 1 pipeline.

This script implements the Phase 1 data-loading and per-team roster
export pipeline for roster-based power rankings.

Scope for Phase 1:
- Read MEGA_players.csv and MEGA_teams.csv.
- Normalize players into a canonical representation.
- Associate players with teams via a team index.
- Export one full-roster CSV per team to output/team_rosters/<TEAM_ABBR>.csv.

No unit (O/D/ST) splits or scoring are performed yet.

Usage (from project root):
    python3 scripts/power_rankings_roster.py \
        --players MEGA_players.csv --teams MEGA_teams.csv --export-rosters
"""
from __future__ import annotations

import argparse
import csv
import os
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
    if p in {"LE", "RE", "DE"}:
        return "DE"
    if p in {"DT"}:
        return "DT"
    if p in {"MLB", "LOLB", "ROLB", "OLB", "LB"}:
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


def export_team_rosters(
    players: list[dict],
    teams_index: dict[str, dict],
    out_dir: str,
    split_units: bool = False,  # noqa: ARG001 - reserved for Phase 2
) -> None:
    """Export one full-roster CSV per team.

    Phase 1 behavior:
    - Groups players by team_abbrev (resolved via team_index).
    - Ensures *every* team from MEGA_teams.csv has a CSV, even if the
      roster is empty.
    - Writes output/team_rosters/<TEAM_ABBR>.csv using a shared schema
      across all teams. Additional fields present on player dicts are
      preserved as extra columns.

    The *split_units* flag is accepted for forward compatibility but is
    ignored in this phase.
    """

    # Derive the set of team abbrevs from the team index
    all_teams: dict[str, dict] = {}
    for team in teams_index.values():
        abbrev = (team.get("abbrev") or "").strip()
        if not abbrev:
            continue
        all_teams.setdefault(abbrev, team)

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

    print(
        f"exported {total_players} players across {len(all_teams)} teams to {out_dir}",
        file=sys.stdout,
    )


###############################################################################
# CLI
###############################################################################


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Roster-based power rankings – Phase 1: data loading and "
            "per-team roster export"
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

    # Placeholder options for later phases; accepted but unused for now so
    # the CLI contract is stable across phases.
    parser.add_argument(
        "--out-csv",
        default=os.path.join("output", "power_rankings_roster.csv"),
        help="(Unused in Phase 1) Output CSV for power rankings",
    )
    parser.add_argument(
        "--out-html",
        default=os.path.join("docs", "power_rankings_roster.html"),
        help="(Unused in Phase 1) Output HTML report path",
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
        export_team_rosters(players, team_index, args.rosters_dir, split_units=False)
    else:
        if args.verbose:
            print("info: --no-export-rosters specified; skipping roster export", file=sys.stderr)

    return 0


if __name__ == "__main__":  # pragma: no cover - CLI entry
    raise SystemExit(main())

