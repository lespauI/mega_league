#!/usr/bin/env python3
"""
Generate an analytics-focused HTML page for a given draft class.

Focus:
- Show explicit dev trait tiers in UI (XF/SS/Star/Normal)
- Team draft analytics (who picked best OVR, how many rookies, counts by dev)
- Position strength analytics (counts by Non‑Normal/Normal, avg OVR)

Usage:
  python3 scripts/generate_draft_class_analytics.py --year 2026 \
      --players MEGA_players.csv --teams MEGA_teams.csv \
      --out docs/draft_class_2026.html
"""
from __future__ import annotations

import argparse
import json
import csv
import html
import os
import re
import sys
import statistics as st
from collections import Counter


# Internal dev labels (raw).
DEV_LABELS = {"3": "X-Factor", "2": "Superstar", "1": "Star", "0": "Normal"}


def grade_badge(tier: str, pct: float, target: float) -> tuple[str, str]:
    """Return (label, css_class) for KPI grading badges.

    - css_class in {'grade-on','grade-near','grade-below'}
    - On-target: pct >= target
    - Near-target: pct >= 0.75 * target
    - Below-target: otherwise
    """
    try:
        p = float(pct)
        tgt = float(target)
    except Exception:
        p = 0.0
        tgt = 0.0
    if tgt <= 0:
        return ("On-target", "grade-on")
    if p >= tgt:
        return ("On-target", "grade-on")
    if p >= 0.75 * tgt:
        return ("Near-target", "grade-near")
    # Below-target: will be hidden in UI per KPI changes
    return ("Below-target", "grade-below")


def read_csv(path: str) -> list[dict]:
    """Read a CSV file returning a list of dict rows.

    - Uses utf-8-sig to tolerate BOMs
    - Raises a clear error message on failure
    """
    try:
        with open(path, newline="", encoding="utf-8-sig") as fh:
            reader = csv.DictReader(fh)
            return list(reader)
    except FileNotFoundError:
        print(f"error: file not found: {path}", file=sys.stderr)
        sys.exit(2)
    except Exception as e:
        print(f"error: failed to read CSV '{path}': {e}", file=sys.stderr)
        sys.exit(2)


def read_section_intros(path: str | None) -> dict:
    """Load optional section intros JSON mapping.

    Expected keys (all optional): 'kpis', 'elites', 'team_quality', 'positions', 'round1'.
    Values should be strings; lists will be joined by newlines. Other types are
    coerced to strings. On any error, returns an empty mapping without exiting.
    """
    mapping: dict[str, str] = {}
    if not path:
        return mapping
    try:
        if not os.path.exists(path):
            print(f"warn: section intros file not found: {path}", file=sys.stderr)
            return mapping
        with open(path, 'r', encoding='utf-8') as fh:
            data = json.load(fh)
        if not isinstance(data, dict):
            print("warn: section intros JSON is not an object; ignoring", file=sys.stderr)
            return mapping
        for k in ('kpis', 'elites', 'team_quality', 'positions', 'round1'):
            if k not in data:
                continue
            v = data.get(k)
            if isinstance(v, list):
                v = "\n".join(str(x) for x in v)
            elif not isinstance(v, str):
                v = str(v)
            mapping[k] = v
    except Exception as e:
        print(f"warn: failed to read section intros: {e}", file=sys.stderr)
        return {}
    return mapping


def warn_missing_columns(rows: list[dict], required: list[str], context: str) -> None:
    """Warn about missing columns but do not fail.

    Gathers headers from first few rows to detect likely schema issues.
    """
    try:
        headers: set[str] = set()
        for r in rows[:5]:
            headers.update(r.keys())
        missing = [c for c in required if c not in headers]
        if missing:
            print(
                f"warn: {context}: missing column(s): {', '.join(missing)} — using safe fallbacks",
                file=sys.stderr,
            )
    except Exception:
        # Best-effort only; never crash on warnings path
        pass


def safe_int(v, default=None):
    """Best-effort parse of an int value.

    Accepts strings and numeric types; returns default on failure.
    """
    try:
        if v is None:
            return default
        if isinstance(v, int):
            return v
        s = str(v).strip()
        if s == "":
            return default
        # handle floats encoded as strings like "69.0"
        if "." in s:
            return int(float(s))
        return int(s)
    except Exception:
        return default


def build_team_logo_map(teams_rows: list[dict]) -> dict:
    """Build a mapping of team names to logoId.

    Maps any of displayName, nickName, or teamName to the team's logoId.
    - Trims whitespace, skips empty/zero logoIds
    - Adds case-insensitive variants to increase match likelihood
    """
    mapping: dict[str, str] = {}
    if not teams_rows:
        return mapping

    for r in teams_rows:
        lid = str(r.get('logoId') or '').strip()
        # Allow '0' as a valid logoId (e.g., Bears => 0.png)
        if lid == '':
            continue

        for key in ('displayName', 'nickName', 'teamName'):
            name = (r.get(key) or '').strip()
            if not name:
                continue
            # Store several variants to be resilient to case/spacing differences
            for variant in {name, name.lower(), name.upper()}:
                mapping[variant] = lid

    return mapping


def gather_rookies(players: list[dict], year: int) -> list[dict]:
    """Filter rookies by year and normalize core fields for analytics.

    Normalization rules:
    - name: fullName > cleanName > firstName + lastName; trimmed
    - team: trimmed; default 'FA' when missing/blank
    - position: trimmed; default '?' when missing/blank
    - ovr: prefer playerBestOvr, then playerSchemeOvr; default 0
    - dev: keep as string in {'3','2','1','0'}; map unknowns to '0'
    - draftRound/draftPick: parsed to ints when available (used in Elites Spotlight)
    - age: parsed to int when available; used on elite cards
    - college: if present, used in the meta line instead of current team
    """
    out = []
    for r in players:
        if str(r.get('rookieYear', '')).strip() != str(year):
            continue

        # Overall rating with fallback
        ovr = safe_int(r.get('playerBestOvr'), None)
        if ovr is None:
            ovr = safe_int(r.get('playerSchemeOvr'), 0)
        if ovr is None:
            ovr = 0

        # Dev trait mapping (unknown -> '0')
        dev_raw = r.get('devTrait', '0')
        dev = str(dev_raw).strip() if dev_raw is not None else '0'
        if dev not in DEV_LABELS:
            dev = '0'

        # Name derivation and trimming
        fn = (r.get('fullName') or '').strip()
        cn = (r.get('cleanName') or '').strip()
        first = (r.get('firstName') or '').strip()
        last = (r.get('lastName') or '').strip()
        name = fn or cn or (f"{first} {last}".strip())

        # Team, college, and position normalization
        team = (r.get('team') or '').strip() or 'FA'
        college = (r.get('college') or '').strip()
        pos = (r.get('position') or '').strip() or '?'

        out.append({
            'id': r.get('id'),
            'name': name,
            'team': team,
            'position': pos,
            'ovr': int(ovr),
            'dev': dev,
            'draft_round': safe_int(r.get('draftRound'), None),
            'draft_pick': safe_int(r.get('draftPick'), None),
            # Optional portrait identifier (used for Round 1 recap photos)
            'portrait_id': (lambda v: (str(v) if v is not None else None))(safe_int(r.get('portraitId'), None)),
            'college': college,
            'age': safe_int(r.get('age'), None),
        })
    # Deterministic sorting: OVR desc, then name asc
    out.sort(key=lambda x: (-x['ovr'], x['name']))
    return out


def _normalize_pos_for_mapping(pos: str) -> str:
    """Normalize a raw position into a mapping class for attrs/traits.

    Groups logical equivalents (e.g., LE/RE -> DE, LT/RT/LG/RG/C -> OL, FS/SS -> S).
    """
    p = (pos or '').strip().upper()
    if not p:
        return '?'
    # Offense
    if p in {'HB', 'RB'}:
        return 'RB'
    if p == 'FB':
        return 'FB'
    if p == 'WR':
        return 'WR'
    if p == 'TE':
        return 'TE'
    if p in {'LT', 'RT', 'LG', 'RG', 'C', 'OL', 'T', 'G'}:
        return 'OL'
    if p == 'QB':
        return 'QB'
    if p in {'K', 'P'}:
        return p
    # Defense
    if p in {'LE', 'RE', 'DE'}:
        return 'DE'
    if p in {'DT'}:
        return 'DT'
    if p in {'MLB', 'LOLB', 'ROLB', 'OLB', 'LB'}:
        return 'LB'
    if p in {'FS', 'SS'}:
        return 'S'
    if p in {'CB'}:
        return 'CB'
    # Fallback
    return p


def get_attr_keys_for_pos(pos: str) -> list[str]:
    """Return up to ~10 key rating fields to display for a given position.

    Keys match columns in MEGA_players.csv. Missing columns/values should be
    skipped by callers. Order expresses priority.
    """
    p = _normalize_pos_for_mapping(pos)
    mapping = {
        # QB passing, pressure, mobility, awareness
        'QB': [
            'throwAccShortRating', 'throwAccMidRating', 'throwAccDeepRating',
            'throwPowerRating', 'throwUnderPressureRating', 'throwOnRunRating',
            'playActionRating', 'awareRating', 'speedRating', 'breakSackRating',
        ],
        # RB/HB elusiveness + carrying/vision + receiving
        'RB': [
            'speedRating', 'accelRating', 'agilityRating',
            'breakTackleRating', 'truckRating', 'jukeMoveRating', 'spinMoveRating',
            'stiffArmRating', 'carryRating', 'catchRating', 'bCVRating',
        ],
        # FB blocking + strength + short-yardage
        'FB': [
            'runBlockRating', 'leadBlockRating', 'impactBlockRating',
            'strengthRating', 'truckRating', 'catchRating',
        ],
        # WR receiving, route running, release, agility
        'WR': [
            'catchRating', 'cITRating', 'routeRunShortRating', 'routeRunMedRating',
            'routeRunDeepRating', 'speedRating', 'releaseRating', 'agilityRating',
            'changeOfDirectionRating',
        ],
        # TE balanced catching + blocking + strength
        'TE': [
            'catchRating', 'cITRating', 'runBlockRating', 'passBlockRating',
            'speedRating', 'routeRunShortRating', 'routeRunMedRating',
            'strengthRating', 'specCatchRating',
        ],
        # Offensive Line (T/G/C): pass/run, power/finesse + strength/awareness/impact
        'OL': [
            'passBlockRating', 'passBlockPowerRating', 'passBlockFinesseRating',
            'runBlockRating', 'runBlockPowerRating', 'runBlockFinesseRating',
            'strengthRating', 'awareRating', 'impactBlockRating',
        ],
        # Edge rushers: moves + shed + pursuit + tackle + speed
        'DE': [
            'powerMovesRating', 'finesseMovesRating', 'blockShedRating',
            'pursuitRating', 'tackleRating', 'strengthRating', 'speedRating', 'hitPowerRating',
        ],
        # Interior DL: power + shed + strength + tackle + pursuit + hit power
        'DT': [
            'powerMovesRating', 'blockShedRating', 'strengthRating',
            'tackleRating', 'pursuitRating', 'hitPowerRating',
        ],
        # Linebackers: tackle + pursuit + hit + shed + recognition + coverage + speed
        'LB': [
            'tackleRating', 'pursuitRating', 'hitPowerRating', 'blockShedRating',
            'playRecRating', 'zoneCoverRating', 'manCoverRating', 'speedRating', 'awareRating',
        ],
        # Cornerbacks: man/zone + speed/accel/agility + press + recognition + ball skills
        'CB': [
            'manCoverRating', 'zoneCoverRating', 'speedRating', 'accelRating',
            'agilityRating', 'pressRating', 'playRecRating', 'catchRating', 'changeOfDirectionRating',
        ],
        # Safeties: zone + tackle + hit + speed + recognition + pursuit + man + awareness + hands
        'S': [
            'zoneCoverRating', 'tackleRating', 'hitPowerRating', 'speedRating',
            'playRecRating', 'pursuitRating', 'manCoverRating', 'awareRating', 'catchRating',
        ],
        # Specialists
        'K': ['kickPowerRating', 'kickAccRating'],
        'P': ['kickPowerRating', 'kickAccRating'],
    }
    return mapping.get(p, [])


def get_trait_keys_for_pos(pos: str) -> list[str]:
    """Return a list of trait fields to display for a given position.

    Uses role-based groupings per spec; skips missing fields gracefully downstream.
    """
    p = _normalize_pos_for_mapping(pos)
    # Core groups
    qb_traits = ['clutchTrait', 'sensePressureTrait', 'throwAwayTrait', 'tightSpiralTrait', 'forcePassTrait']
    ball_carrier_traits = ['coverBallTrait', 'fightForYardsTrait', 'runStyle']
    receiver_traits = ['feetInBoundsTrait', 'posCatchTrait', 'yACCatchTrait', 'dropOpenPassTrait']  # 'specCatchTrait' not present in CSV
    defender_core = ['bigHitTrait', 'stripBallTrait', 'playBallTrait']
    dl_moves = ['dLBullRushTrait', 'dLSpinTrait', 'dLSwimTrait']

    if p == 'QB':
        return qb_traits
    if p in {'RB', 'FB'}:
        return ball_carrier_traits
    if p in {'WR', 'TE'}:
        return receiver_traits
    if p in {'DE', 'DT'}:
        return dl_moves + defender_core
    if p in {'LB', 'CB', 'S'}:
        return defender_core
    return []


def compute_analytics(rows: list[dict]):
    """Compute draft class analytics aggregates.

    KPIs:
    - total rookies
    - avg overall (2 decimals)
    - dev distribution (keys '3','2','1','0')
    - elites (XF+SS) absolute and share percentage

    Aggregates:
    - per team: count, avg_ovr, best_ovr, dev distribution
    - per position: count, avg_ovr, dev distribution

    Sorting rules are applied downstream during rendering, but we also return
    pre-sorted helper lists to make consumption straightforward if needed.
    """
    total = len(rows)

    # Dev distribution normalized to expected keys
    raw_dev_counts = Counter(r['dev'] for r in rows)
    dev_counts = {k: raw_dev_counts.get(k, 0) for k in ('3', '2', '1', '0')}

    ovrs = [r['ovr'] for r in rows]
    avg_ovr = round(st.mean(ovrs), 2) if ovrs else 0.0

    # Team aggregates
    teams: dict[str, dict] = {}
    for r in rows:
        team = r['team']
        t = teams.setdefault(team, {'count': 0, 'sum_ovr': 0, 'best_ovr': 0, 'dev': Counter()})
        t['count'] += 1
        t['sum_ovr'] += r['ovr']
        if r['ovr'] > t['best_ovr']:
            t['best_ovr'] = r['ovr']
        t['dev'][r['dev']] += 1
    for team, t in teams.items():
        t['avg_ovr'] = round((t['sum_ovr'] / t['count']) if t['count'] else 0.0, 2)
        # normalize dev dict to all expected keys
        t['dev'] = {k: t['dev'].get(k, 0) for k in ('3', '2', '1', '0')}
        # drop helper
        del t['sum_ovr']

    # Position aggregates
    positions: dict[str, dict] = {}
    for r in rows:
        pos = r['position']
        p = positions.setdefault(pos, {'count': 0, 'sum_ovr': 0, 'dev': Counter()})
        p['count'] += 1
        p['sum_ovr'] += r['ovr']
        p['dev'][r['dev']] += 1
    for pos, p in positions.items():
        p['avg_ovr'] = round((p['sum_ovr'] / p['count']) if p['count'] else 0.0, 2)
        p['dev'] = {k: p['dev'].get(k, 0) for k in ('3', '2', '1', '0')}
        del p['sum_ovr']

    # Elites spotlight (data only; HTML cards built in renderer)
    elites = sorted(
        (r for r in rows if r['dev'] in ('3', '2')),
        key=lambda r: (-int(r['dev']), -int(r['ovr']), r['name'])
    )
    elites_count = dev_counts['3'] + dev_counts['2']
    elite_share_pct = round((100.0 * elites_count / total), 1) if total else 0.0

    # Percentages by tier
    def pct(v: int, denom: int) -> float:
        return round(100.0 * v / denom, 1) if denom else 0.0

    xf_pct = pct(dev_counts['3'], total)
    ss_pct = pct(dev_counts['2'], total)
    star_pct = pct(dev_counts['1'], total)
    norm_pct = pct(dev_counts['0'], total)

    # Grading (targets: XF ≥10%, SS ≥15%)
    xf_grade_label, xf_grade_class = grade_badge('xf', xf_pct, 10.0)
    ss_grade_label, ss_grade_class = grade_badge('ss', ss_pct, 15.0)

    # Pre-sorted helper views (not strictly required by renderer)
    teams_sorted = sorted(teams.items(), key=lambda kv: (-kv[1]['avg_ovr'], kv[0]))
    positions_sorted = sorted(positions.items(), key=lambda kv: (-kv[1]['avg_ovr'], -kv[1]['count'], kv[0]))

    # Per-team per-round hits/misses
    # Only include rows with a known draft_round
    rounds_present: set[int] = set()
    team_rounds: dict[str, dict[int, dict[str, int]]] = {}
    team_rounds_elites: dict[str, dict[int, dict[str, int]]] = {}
    for r in rows:
        rd = r.get('draft_round')
        if rd is None:
            continue
        try:
            rdv = int(rd)
        except Exception:
            continue
        rounds_present.add(rdv)
        team = r['team']
        cell = team_rounds.setdefault(team, {}).setdefault(rdv, {'hit': 0, 'total': 0})
        cell['total'] += 1
        if r['dev'] in ('3', '2', '1'):
            cell['hit'] += 1
        # elites-only aggregation mirrors totals, counts hits for XF/SS only
        cell_e = team_rounds_elites.setdefault(team, {}).setdefault(rdv, {'hit': 0, 'total': 0})
        cell_e['total'] += 1
        if r['dev'] in ('3', '2'):
            cell_e['hit'] += 1
    rounds_sorted = sorted(rounds_present)

    return {
        'total': total,
        'avg_ovr': avg_ovr,
        'dev_counts': raw_dev_counts,  # keep Counter for compatibility in renderer
        'dev_counts_norm': dev_counts,  # normalized dict if needed elsewhere
        'elite_count': elites_count,
        'elite_share_pct': elite_share_pct,
        'elites': elites,
        # KPI percentages
        'xf_pct': xf_pct,
        'ss_pct': ss_pct,
        'star_pct': star_pct,
        'norm_pct': norm_pct,
        # Grades
        'xf_grade': 'on' if xf_grade_class.endswith('on') else ('near' if xf_grade_class.endswith('near') else 'below'),
        'ss_grade': 'on' if ss_grade_class.endswith('on') else ('near' if ss_grade_class.endswith('near') else 'below'),
        'xf_grade_label': xf_grade_label,
        'ss_grade_label': ss_grade_label,
        'xf_grade_class': xf_grade_class,
        'ss_grade_class': ss_grade_class,
        'teams': teams,
        'teams_sorted': teams_sorted,
        'positions': positions,
        'positions_sorted': positions_sorted,
        'team_rounds': team_rounds,
        'team_rounds_elites': team_rounds_elites,
        'rounds_sorted': rounds_sorted,
    }


def _pos_key(pos: str) -> str:
    try:
        return (pos or '').strip().upper()
    except Exception:
        return ''


def get_attr_keys_for_pos(pos: str) -> list[str]:
    """Return ordered attribute keys for a given position.

    Uses a curated set based on Madden attribute names. Missing keys are skipped
    at render time; this helper only provides the order of preference.
    """
    p = _pos_key(pos)
    # QB
    if p == 'QB':
        return [
            'throwAccShort','throwAccMid','throwAccDeep','throwPower',
            'throwUnderPressure','throwOnRun','playAction','awareRating',
            'speedRating','breakSackRating',
        ]
    # RB/HB archetype (ball carrier)
    if p in {'HB','RB'}:
        return [
            'speedRating','accelRating','agilityRating','breakTackleRating',
            'truckRating','jukeMoveRating','spinMoveRating','stiffArmRating',
            'carryRating','catchRating','bCVRating',
        ]
    if p == 'FB':
        return ['runBlockRating','leadBlockRating','impactBlockRating','strengthRating','truckRating','catchRating']
    if p == 'WR':
        return ['catchRating','specCatchRating','cITRating','speedRating','routeRunShort','routeRunMed','routeRunDeep','releaseRating','agilityRating','changeOfDirectionRating']
    if p == 'TE':
        return ['catchRating','cITRating','runBlockRating','passBlockRating','speedRating','routeRunShort','routeRunMed','strengthRating','specCatchRating']
    if p in {'LT','LG','RT','RG','T','G','C','OL'}:
        return ['passBlockRating','passBlockPower','passBlockFinesse','runBlockRating','runBlockPower','runBlockFinesse','strengthRating','awareRating','impactBlockRating']
    if p in {'LE','RE','DE'}:
        return ['powerMovesRating','finesseMovesRating','blockShedRating','pursuitRating','tackleRating','strengthRating','speedRating','hitPowerRating']
    if p == 'DT':
        return ['powerMovesRating','blockShedRating','strengthRating','tackleRating','pursuitRating','hitPowerRating']
    if p in {'MLB','LOLB','ROLB','OLB','LB'}:
        return ['tackleRating','pursuitRating','hitPowerRating','blockShedRating','playRecRating','zoneCoverRating','manCoverRating','speedRating','awareRating']
    if p == 'CB':
        return ['manCoverRating','zoneCoverRating','speedRating','accelRating','agilityRating','pressRating','playRecRating','catchRating','changeOfDirectionRating']
    if p in {'FS','SS','S'}:
        return ['zoneCoverRating','tackleRating','hitPowerRating','speedRating','playRecRating','pursuitRating','manCoverRating','awareRating','catchRating']
    if p == 'K' or p == 'P':
        return ['kickPowerRating','kickAccRating']
    # Default: show common overall-relevant metrics if present
    return ['speedRating','strengthRating','agilityRating','awareRating']


def get_trait_keys_for_pos(pos: str) -> list[str]:
    """Return ordered trait keys for a position.

    Traits are boolean-ish fields in CSV (e.g., 'True', 'Yes', '1').
    """
    base_qb = ['clutchTrait','sensePressureTrait','throwAwayTrait','tightSpiralTrait','forcePassTrait']
    base_ball = ['coverBallTrait','fightForYardsTrait','runStyle']
    base_rec = ['feetInBoundsTrait','specCatchTrait','posCatchTrait','yACCatchTrait','dropOpenPassTrait']
    base_def = ['bigHitTrait','stripBallTrait','playBallTrait']
    base_dl = ['dLBullRushTrait','dLSpinTrait','dLSwimTrait']
    p = _pos_key(pos)
    if p == 'QB':
        return base_qb
    if p in {'HB','RB','FB'}:
        return base_ball
    if p in {'WR','TE'}:
        return base_rec
    if p in {'LE','RE','DE','DT'}:
        return base_def + base_dl
    if p in {'MLB','LOLB','ROLB','OLB','LB','CB','FS','SS','S'}:
        return base_def
    return base_qb[:2] + base_def[:1]


def _boolish(v) -> bool:
    if v is None:
        return False
    s = str(v).strip().lower()
    return s in {'1','true','yes','y','t'}


def build_round1_entries(players_rows: list[dict], team_logo_map: dict, *, year: int | None = None) -> list[dict]:
    """Select Round 1 rookies and build card data entries.

    - Filters by rookieYear if year is provided.
    - Sorts by draftPick ascending.
    - Attaches team logoId, photo URL (if portraitId), attributes and traits.
    """
    entries: list[dict] = []
    for r in players_rows:
        if year is not None and str(r.get('rookieYear', '')).strip() != str(year):
            continue
        rd = safe_int(r.get('draftRound'), None)
        pk = safe_int(r.get('draftPick'), None)
        if rd != 1 or pk is None:
            continue

        # Name derivation mirrors gather_rookies
        fn = (r.get('fullName') or '').strip()
        cn = (r.get('cleanName') or '').strip()
        first = (r.get('firstName') or '').strip()
        last = (r.get('lastName') or '').strip()
        name = fn or cn or (f"{first} {last}".strip())

        team = (r.get('team') or '').strip() or 'FA'
        pos = (r.get('position') or '').strip() or '?'
        ovr = safe_int(r.get('playerBestOvr'), None)
        if ovr is None:
            ovr = safe_int(r.get('playerSchemeOvr'), 0) or 0
        dev = str(r.get('devTrait') or '0').strip()
        portrait_id = (r.get('portraitId') or '').strip()

        # Team logo mapping -> URL fragment
        lid = team_logo_map.get(team) or team_logo_map.get(team.lower()) or team_logo_map.get(team.upper())
        logo_url = f"https://cdn.neonsportz.com/teamlogos/256/{lid}.png" if lid not in (None, '') else ''

        # Attribute grid
        attr_keys = get_attr_keys_for_pos(pos)
        attrs = []
        for k in attr_keys:
            if k in r and str(r.get(k) or '').strip() != '':
                try:
                    val = int(float(str(r[k]).strip()))
                except Exception:
                    continue
                attrs.append((k, val))
        # Trait badges
        trait_keys = get_trait_keys_for_pos(pos)
        traits = []
        for k in trait_keys:
            if _boolish(r.get(k)):
                traits.append(k)

        photo_url = ''
        if portrait_id.isdigit():
            photo_url = f"https://ratings-images-prod.pulse.ea.com/madden-nfl-26/portraits/{portrait_id}.png"

        entries.append({
            'pick': pk,
            'team': team,
            'team_logo': logo_url,
            'name': name,
            'position': pos,
            'ovr': int(ovr),
            'dev': dev,
            'photo': photo_url,
            'attrs': attrs,
            'traits': traits,
        })

    entries.sort(key=lambda e: (e['pick'] if e['pick'] is not None else 999))
    return entries


def _grade_for_ovr(ovr: int) -> tuple[str, str]:
    """Return (label, css_class) for a simple pick grade derived from OVR.

    - A (grade-on): 78+
    - B (grade-near): 72–77
    - C (grade-below): <72
    """
    try:
        o = int(ovr)
    except Exception:
        o = 0
    if o >= 78:
        return ('A', 'grade-on')
    if o >= 72:
        return ('B', 'grade-near')
    return ('C', 'grade-below')


def _normalize_player_name_for_match(name: str) -> str:
    """Normalize player name to match against mock draft markdown names.

    - Strips Markdown emphasis (** **)
    - Truncates at first ' (' to remove variant notes like '(вариант 1)'
    - Trims whitespace
    """
    s = (name or '').strip()
    # Remove variant suffix in parentheses first
    if ' (' in s:
        s = s.split(' (', 1)[0]
    # Remove Markdown bold markers if present on either side
    if s.startswith('**'):
        s = s[2:]
    if s.endswith('**'):
        s = s[:-2]
    return s.strip()


def read_mock_draft_md(path: str | None) -> dict:
    """Parse docs/draft_mock.md table into lookup maps.

    Returns a dict with:
      - 'by_pick': {int: [notes, ...]}
      - 'by_player': {norm_name: [notes, ...]}
      - 'team_by_pick': {int: team}
      - 'team_by_player': {norm_name: team}
      - 'player_by_pick': {int: [player_norm, ...]}

    Safe on errors/missing file; returns empty maps.
    """
    out = {
        'by_pick': {},
        'by_player': {},
        'team_by_pick': {},
        'team_by_player': {},
        'player_by_pick': {},
    }
    if not path:
        return out
    try:
        if not os.path.exists(path):
            return out
        with open(path, 'r', encoding='utf-8') as fh:
            lines = fh.read().splitlines()
        # Find the markdown table (lines starting with '|') under "Первый Раунд"
        in_table = False
        for ln in lines:
            if ln.strip().startswith('|'):
                in_table = True
                # Skip header and alignment rows
                # Detect alignment by pattern like |:---|
                parts = [p.strip() for p in ln.strip().strip('|').split('|')]
                if len(parts) < 5:
                    continue
                # Heuristic: skip header (contains non-numeric in 1st col and typically words)
                if parts[0] and not parts[0].isdigit():
                    continue
                if parts[1].lower().startswith('---') or parts[0].lower().startswith('---'):
                    continue
                # Data row: Pick | Player | Pos | Team | Notes
                pick_raw, player_raw, pos_raw, team_raw, notes_raw = parts[:5]
                # Clean fields
                try:
                    pick = int(float(pick_raw))
                except Exception:
                    # If pick is not parseable, try to match by player name only
                    pick = None
                player = player_raw.strip()
                player_norm = _normalize_player_name_for_match(player)
                notes = notes_raw.strip()
                team_proj = team_raw.strip()
                if notes:
                    if pick is not None:
                        out['by_pick'].setdefault(pick, []).append(notes)
                    if player_norm:
                        out['by_player'].setdefault(player_norm, []).append(notes)
                # Team projections
                if team_proj:
                    if pick is not None and team_proj:
                        out['team_by_pick'].setdefault(pick, team_proj)
                    if player_norm:
                        out['team_by_player'].setdefault(player_norm, team_proj)
                # Projected player(s) per pick (allow variants)
                if pick is not None and player_norm:
                    lst = out['player_by_pick'].setdefault(pick, [])
                    if player_norm not in lst:
                        lst.append(player_norm)
            else:
                if in_table and ln.strip() == '':
                    # End of contiguous table block
                    in_table = False
        return out
    except Exception:
        return {
            'by_pick': {},
            'by_player': {},
            'team_by_pick': {},
            'team_by_player': {},
            'player_by_pick': {},
        }


def render_round1_recap(entries: list[dict], mock_lookup: dict | None = None) -> str:
    """Render HTML for Round 1 recap cards.

    Produces a responsive grid of cards with player photo header, pick number,
    team logo pinned at top-right, name/pos, grade badge, attributes grid,
    trait badges, analytics notes (expanded), and projection deltas.
    """
    if not entries:
        return "<div class='muted'>No Round 1 picks found.</div>"

    def esc(s: str) -> str:
        return html.escape(str(s))
    def _norm_team(val: str | None) -> str:
        if not val:
            return ''
        s = str(val).strip()
        # Lower, remove extra spaces
        s = ' '.join(s.split()).lower()
        # Take mascot/last token to align "Pittsburgh Steelers" with "Steelers"
        parts = [p for p in re.split(r"[\s\t]+", s) if p]
        return parts[-1] if parts else s

    cards = []
    mock_by_pick = (mock_lookup or {}).get('by_pick', {})
    mock_by_player = (mock_lookup or {}).get('by_player', {})
    team_by_pick = (mock_lookup or {}).get('team_by_pick', {})
    team_by_player = (mock_lookup or {}).get('team_by_player', {})
    player_by_pick = (mock_lookup or {}).get('player_by_pick', {})
    for e in entries:
        grade_label, grade_cls = _grade_for_ovr(e.get('ovr', 0))
        # Add '+' to grade for Superstar/X-Factor devs
        try:
            if str(e.get('dev')) in ('2','3'):
                grade_label = f"{grade_label}+"
        except Exception:
            pass
        # Team logo in the top-right corner
        logo_img = f"<img class=\"team-logo\" src=\"{esc(e['team_logo'])}\" alt=\"{esc(e['team'])}\" />" if e.get('team_logo') else ''
        photo = e.get('photo')
        # Prominent player photo in header
        photo_html = f"<img class=\"r1-photo\" src=\"{esc(photo)}\" alt=\"{esc(e['name'])}\" />" if photo else ''

        # Attributes grid (limit to 8-10 entries)
        attr_lines = []
        for k, v in (e.get('attrs') or [])[:10]:
            attr_lines.append(f"<div class=\"attr\"><span class=\"k\">{esc(k)}</span><span class=\"v\">{int(v)}</span></div>")
        attrs_html = ''.join(attr_lines) if attr_lines else "<div class='muted' style='grid-column:1/-1;'>No attributes.</div>"

        # Trait badges
        trait_lines = []
        for t in (e.get('traits') or []):
            trait_lines.append(f"<span class=\"trait\">{esc(t)}</span>")
        traits_html = ''.join(trait_lines)

        # Build projection deltas and analytics notes together inside one block
        notes_html = ''
        proj_html = ''
        try:
            pick = e.get('pick')
            actual_team = e.get('team')
            player_norm = _normalize_player_name_for_match(e.get('name', ''))

            # Collect projection messages
            msgs = []
            team_proj_player = team_by_player.get(player_norm)
            if team_proj_player and _norm_team(team_proj_player) != _norm_team(actual_team):
                msgs.append(f"Прогнозируемая команда: {esc(team_proj_player)} → выбран {esc(actual_team)}")
            if isinstance(pick, int) and pick in team_by_pick:
                team_proj_pick = team_by_pick.get(pick)
                if team_proj_pick and _norm_team(team_proj_pick) != _norm_team(actual_team):
                    msgs.append(f"У прогноза на пик #{pick}: {esc(team_proj_pick)} → фактически {esc(actual_team)}")
            if isinstance(pick, int) and pick in player_by_pick:
                projected_players = [p for p in player_by_pick.get(pick, []) if p]
                if projected_players and player_norm not in projected_players:
                    msgs.append(f"Прогноз игрока на этот пик: {esc(projected_players[0])}")
            if msgs:
                proj_html = "<div class=\"proj\">" + "<br/>".join(msgs) + "</div>"

            # Gather analytics notes
            notes_list = []
            if player_norm and player_norm in mock_by_player:
                notes_list = list(mock_by_player.get(player_norm, []))
            elif isinstance(pick, int) and pick in mock_by_pick:
                notes_list = list(mock_by_pick.get(pick, []))

            # Render section only if we have projections or notes
            if msgs or notes_list:
                parts = []
                if proj_html:
                    parts.append(proj_html)
                if notes_list:
                    joined = '\n\n'.join(notes_list)
                    parts.append(f"<div class=\"mock-notes\">{esc(joined)}</div>")
                notes_html = (
                    "<div class=\"mock-notes-block\">"
                    "  <div class=\"mock-notes-title\">Что говорили аналитики</div>"
                    + ''.join(parts) +
                    "</div>"
                )
        except Exception:
            notes_html = ''

        # Real pick evaluation section (always shown)
        # Dev badge
        dev_badge = badge_for_dev(e.get('dev', '0'))
        real_eval_html = (
            "<div class=\"real-eval-block\">"
            "  <div class=\"real-eval-title\">Оценка реального пика</div>"
            f"  <div class=\"real-eval\">Оценка: <span class=\"grade {esc(grade_cls)}\">{esc(grade_label)}</span></div>"
            f"  <div class=\"real-eval\">OVR: <span class=\"ovr-badge\">{int(e.get('ovr',0))}</span></div>"
            f"  <div class=\"real-eval\">DevTrait: {dev_badge}</div>"
            "</div>"
        )

        cards.append(
            (
                "<div class=\"r1-card\">"
                f"  {logo_img}"
                f"  <div class=\"head\">{photo_html}<div class=\"pick\">Pick {esc(e.get('pick',''))}</div></div>"
                f"  <div class=\"name\"><b>{esc(e['name'])}</b> <span class=\"pos\">{esc(e['position'])}</span> <span class=\"grade {esc(grade_cls)}\">{esc(grade_label)}</span></div>"
                f"  <div class=\"meta\">Team: {esc(e['team'])} &nbsp; • &nbsp; OVR {int(e.get('ovr',0))}</div>"
                f"  <div class=\"attrs\">{attrs_html}</div>"
                f"  <div class=\"traits\">{traits_html}</div>"
                f"  {notes_html}"
                f"  {real_eval_html}"
                "</div>"
            )
        )
    return '<div class="r1-list">' + '\n'.join(cards) + '</div>'


def badge_for_dev(dev: str) -> str:
    # Render explicit dev tiers
    mapping = {
        '3': ('X-Factor', 'dev-xf'),
        '2': ('Superstar', 'dev-ss'),
        '1': ('Star', 'dev-star'),
        '0': ('Normal', 'dev-norm'),
    }
    label, cls = mapping.get(str(dev), ('Normal', 'dev-norm'))
    return f'<span class="dev-badge {cls}">{html.escape(label)}</span>'


def generate_html(
    year: int,
    rows: list[dict],
    analytics: dict,
    team_logo_map: dict,
    *,
    title_suffix: str | None = None,
    title_override: str | None = None,
    section_intros: dict | None = None,
    intro_default: str | None = None,
    round1_entries: list[dict] | None = None,
    round1_mock: dict | None = None,
) -> str:
    elites = [r for r in rows if r['dev'] in ('3','2')]
    # Order cards by draft pick: round asc, pick asc; missing picks last
    def elite_sort_key(r: dict):
        rd = r.get('draft_round')
        pk = r.get('draft_pick')
        missing = 0 if (rd is not None and pk is not None) else 1
        rdv = int(rd) if rd is not None else 999
        pkv = int(pk) if pk is not None else 999
        return (missing, rdv, pkv, -int(r['ovr']), r['name'])
    elites.sort(key=elite_sort_key)

    def logo_img(team: str) -> str:
        # Try exact then case-insensitive lookup
        lid = team_logo_map.get(team) or team_logo_map.get(team.lower()) or team_logo_map.get(team.upper())
        if not lid:
            return ''
        return f'<img class="logo" src="https://cdn.neonsportz.com/teamlogos/256/{lid}.png" alt="{html.escape(team)}" />'

    # Small, colorful position chip
    def pos_chip(pos: str) -> str:
        p = (pos or '?').upper()
        # Group common positions into color families for consistent styling
        if p in {'LT','LG','RT','RG','T','G','C','OL'}:
            cls = 'OL'
        elif p in {'DE','DT','RE','LE','DL'}:
            cls = 'DL'
        elif p in {'MLB','LOLB','ROLB','OLB','LB'}:
            cls = 'LB'
        elif p in {'CB','FS','SS','DB'}:
            cls = 'DB'
        elif p in {'HB','RB','FB','WR','TE'}:
            cls = p  # direct mapping available in CSS rules
        elif p in {'QB','K','P'}:
            cls = p
        elif p == '?':
            cls = '?'
        else:
            cls = 'UNK'
        return f'<span class="pos-chip pos-{html.escape(cls)}">{html.escape(p)}</span>'

    elite_cards = []
    for r in elites:
        # Round.pick badge when both are present (e.g., 1.7)
        rd = r.get('draft_round')
        pk = r.get('draft_pick')
        pick_badge = f"<span class=\"pick-badge\">{int(rd)}.{int(pk)}</span>" if (rd is not None and pk is not None) else ""
        ovr_badge = f"<span class=\"ovr-badge\">OVR {int(r['ovr'])}</span>"
        school = (r.get('college') or '').strip() or r['team']
        age = r.get('age')
        age_txt = f"{int(age)}" if isinstance(age, int) else ""

        elite_cards.append(
            (
                '<div class="player">'
                f"<div class=\"hdr\">{logo_img(r['team'])}<div class=\"tags\">{ovr_badge}{pick_badge}</div></div>"
                f"<div class=\"nm\">{html.escape(r['name'])}, {html.escape(str(r['position']))}, {age_txt}</div>"
                f"<div class=\"meta\">{html.escape(school)}</div>"
                f"<div class=\"dev\">{badge_for_dev(r['dev'])}</div>"
                '</div>'
            )
        )
    elite_cards_html = '\n'.join(elite_cards) if elite_cards else "<div class='muted'>No X-Factor or Superstar rookies.</div>"

    # Teams tables
    team_rows = []
    for team, stats in sorted(analytics['teams'].items(), key=lambda kv: (-kv[1]['avg_ovr'], kv[0])):
        dev = stats['dev']
        xf = dev.get('3', 0)
        ss = dev.get('2', 0)
        star = dev.get('1', 0)
        normal = dev.get('0', 0)
        team_rows.append(
            (
                '<tr>'
                f"<td class='team'>{logo_img(team)}<span>{html.escape(team)}</span></td>"
                f"<td class='num'>{xf}</td>"
                f"<td class='num'>{ss}</td>"
                f"<td class='num'>{star}</td>"
                f"<td class='num'>{normal}</td>"
                f"<td class='num'>{stats['count']}</td>"
                f"<td class='num'>{stats['avg_ovr']:.2f}</td>"
                f"<td class='num'>{stats['best_ovr']}</td>"
                '</tr>'
            )
        )
    team_table_html = '\n'.join(team_rows)

    # Most elites: XF + SS
    team_hidden_rows = []
    for team, stats in sorted(
        analytics['teams'].items(),
        key=lambda kv: (-(kv[1]['dev'].get('3', 0) + kv[1]['dev'].get('2', 0)), kv[0])
    ):
        elites = stats['dev'].get('3', 0) + stats['dev'].get('2', 0)
        team_hidden_rows.append(
            f"<tr><td class='team'>{logo_img(team)}<span>{html.escape(team)}</span></td><td class='num'>{elites}</td><td class='num'>{stats['count']}</td><td class='num'>{stats['avg_ovr']:.2f}</td></tr>"
        )
    team_hiddens_html = '\n'.join(team_hidden_rows)

    # Positions table
    pos_rows = []
    for pos, stats in sorted(analytics['positions'].items(), key=lambda kv: (-kv[1]['avg_ovr'], -kv[1]['count'], kv[0])):
        dev = stats['dev']
        xf = dev.get('3', 0)
        ss = dev.get('2', 0)
        star = dev.get('1', 0)
        normal = dev.get('0', 0)
        pos_rows.append(
            (
                '<tr>'
                f"<td>{html.escape(pos)}</td>"
                f"<td class='num'>{xf}</td>"
                f"<td class='num'>{ss}</td>"
                f"<td class='num'>{star}</td>"
                f"<td class='num'>{normal}</td>"
                f"<td class='num'>{stats['count']}</td>"
                f"<td class='num'>{stats['avg_ovr']:.2f}</td>"
                '</tr>'
            )
        )
    pos_table_html = '\n'.join(pos_rows)

    total = analytics['total'] or 1
    xf_total = analytics['dev_counts'].get('3',0)
    ss_total = analytics['dev_counts'].get('2',0)
    star_total = analytics['dev_counts'].get('1',0)
    norm_total = analytics['dev_counts'].get('0',0)
    elites_total = xf_total + ss_total

    # Elite-heavy positions summary (show XF and SS separately)
    pos_elite_sorted = []
    for p in analytics['positions']:
        d = analytics['positions'][p]['dev']
        xf_c = d.get('3',0)
        ss_c = d.get('2',0)
        star_c = d.get('1',0)
        pos_elite_sorted.append((p, xf_c, ss_c, star_c, xf_c+ss_c))
    pos_elite_sorted.sort(key=lambda x: (-x[4], -x[3], x[0]))
    top_pos_lines = []
    for p, xf_c, ss_c, star_c, elite_total in pos_elite_sorted[:6]:
        non_normal = xf_c + ss_c + star_c
        top_pos_lines.append(f"<li><b>{html.escape(p)}</b>: {non_normal} non-normal</li>")
    top_pos_html = '\n'.join(top_pos_lines)

    html_out = """<!DOCTYPE html>
<html lang=\"en\">
<head>
  <meta charset=\"utf-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
  <title>__PAGE_TITLE__</title>
  <style>
    :root { --text:#0f172a; --sub:#64748b; --muted:#94a3b8; --grid:#e2e8f0; --bg:#f7f7f7; --card:#ffffff; --accent:#3b82f6; }
    body { margin:16px; font-family: system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial, sans-serif; color:var(--text); background:var(--bg); }
    .topbar { max-width: 1200px; margin: 0 auto 10px; display:flex; align-items:center; gap:10px; }
    .back { display:inline-flex; align-items:center; gap:8px; font-size:13px; color:#1e293b; text-decoration:none; background:#fff; border:1px solid #e5e7eb; padding:6px 10px; border-radius:8px; box-shadow:0 1px 2px rgba(0,0,0,.05); }
    .back:hover { background:#f8fafc; }
    .container { max-width: 1200px; margin: 0 auto; background: var(--card); border: 1px solid #e5e7eb; border-radius: 12px; box-shadow: 0 1px 3px rgba(0,0,0,.06); overflow:hidden; }
    header { padding: 18px 20px 8px; border-bottom: 1px solid #ececec; background:linear-gradient(180deg,#ffffff 0%,#fafafa 100%); }
    h1 { margin:0; font-size: 22px; }
    .subtitle { color: var(--sub); margin:8px 0 6px; font-size: 13px; }
    .pill { display:inline-block; margin-left:8px; padding:2px 8px; border-radius:999px; border:1px solid #bfdbfe; background:#dbeafe; color:#1e3a8a; font-size:12px; }
    .section-intro { white-space: pre-wrap; color: #334155; font-size: 13px; margin: 8px 0 12px; }

    .panel { padding: 14px 18px; border-bottom: 1px solid #f0f0f0; }
    .kpis { display: grid; grid-template-columns: repeat(6, minmax(0,1fr)); gap: 10px; }
    .kpi { background:#f8fafc; padding: 10px 12px; border: 1px solid #e5e7eb; border-radius: 10px; transition: box-shadow .15s ease; }
    .kpi:hover { box-shadow:0 2px 6px rgba(0,0,0,.06); }
    .kpi b { display:block; font-size: 12px; color:#0f172a; }
    .kpi span { color:#334155; font-size: 18px; font-weight: 700; }
    .kpi .gbar { margin-top:6px; height:6px; background:#e5e7eb; border-radius:999px; overflow:hidden; }
    .kpi .gbar .fill { height:100%; background: linear-gradient(90deg, #60a5fa, #22c55e); }
    .kpi-large { grid-column: span 4; }
    /* Stacked distribution bar */
    .stackbar { margin-top:6px; height:10px; display:flex; border-radius:999px; overflow:hidden; border:1px solid #e5e7eb; background:#f3f4f6; }
    .stackbar .seg { height:100%; }
    .stackbar .seg-xf { background:#ef4444; }
    .stackbar .seg-ss { background:#d4af37; }
    .stackbar .seg-star { background:#c0c0c0; }
    .stackbar .seg-norm { background:#cd7f32; }

    .section-title { font-size: 14px; font-weight: 700; margin: 0 0 10px; border-left:3px solid var(--accent); padding-left:8px; }
    .grid { display:grid; grid-template-columns: 1.7fr 1.3fr; gap: 12px; }
    .card { background:#fff; border: 1px solid #e5e7eb; border-radius: 10px; padding: 12px; }
    .card h3 { margin: 0 0 8px; font-size: 14px; color:#0f172a; }

    .players { display:grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 10px; }
    .player { border:1px solid var(--grid); border-radius:10px; padding:10px; background:#fff; transition: transform .12s ease, box-shadow .12s ease; }
    .player:hover { transform: translateY(-2px); box-shadow: 0 3px 10px rgba(0,0,0,.06); }
    .player .hdr { display:flex; align-items:center; }
    .player .logo { width:22px; height:22px; border-radius:4px; box-shadow:0 0 0 1px rgba(0,0,0,.06); }
    .player .tags { margin-left:auto; display:flex; align-items:center; gap:6px; }
    .player .nm { font-weight: 600; margin-top: 2px; display:flex; align-items:center; gap:6px; flex-wrap:wrap; }
    .player .meta { color:#475569; font-size: 12px; margin-top: 2px; display:flex; align-items:center; gap:8px; }
    .player .ovr { display:none; }
    .player .dev { margin-top: 4px; }
    .player .pick-badge { display:inline-block; padding:2px 7px; border-radius:999px; font-size:11px; font-weight:700; background:#e0f2fe; color:#075985; border:1px solid #bae6fd; }
    .player .ovr-badge { display:inline-block; padding:2px 7px; border-radius:999px; font-size:11px; font-weight:700; background:#dcfce7; color:#166534; border:1px solid #bbf7d0; }
    .muted { color: var(--muted); }
    .pos-chip { display:inline-block; padding:2px 7px; border-radius:999px; font-size:11px; font-weight:700; border:1px solid transparent; }
    .pos-QB { background:#fee2e2; color:#991b1b; border-color:#fecaca; }
    .pos-HB, .pos-RB, .pos-FB, .pos-WR, .pos-TE { background:#dbeafe; color:#1e3a8a; border-color:#bfdbfe; }
    .pos-T, .pos-G, .pos-C, .pos-OL { background:#ede9fe; color:#5b21b6; border-color:#ddd6fe; }
    .pos-DE, .pos-DT, .pos-DL { background:#fef3c7; color:#92400e; border-color:#fde68a; }
    .pos-MLB, .pos-LOLB, .pos-ROLB, .pos-LB { background:#dcfce7; color:#166534; border-color:#bbf7d0; }
    .pos-CB, .pos-FS, .pos-SS, .pos-DB { background:#e0f2fe; color:#075985; border-color:#bae6fd; }
    .pos-K, .pos-P { background:#f1f5f9; color:#0f172a; border-color:#e2e8f0; }
    .pos-UNK, .pos-? { background:#e5e7eb; color:#374151; border-color:#d1d5db; }

    table { width:100%; border-collapse: collapse; }
    thead tr { background:#fafafa; }
    tbody tr:nth-child(odd) { background: #fcfcfd; }
    tbody tr:hover { background:#f6faff; }
    th, td { padding: 8px 8px; border-bottom: 1px solid var(--grid); font-size: 13px; text-align:center; }
    th { color:#475569; font-size:12px; user-select:none; }
    table.sortable th { cursor:pointer; }
    td.num { text-align:center; font-variant-numeric: tabular-nums; }
    td.team { display:flex; align-items:center; justify-content:center; gap:8px; }
    td.team img.logo { width:18px; height:18px; border-radius:4px; box-shadow:0 0 0 1px rgba(0,0,0,.05); }

    .dev-badge { display:inline-block; padding:3px 8px; border-radius:999px; font-size:11px; font-weight:600; }
    .dev-xf { background:#fee2e2; color:#991b1b; border:1px solid #fecaca; }
    .dev-ss { background:#dbeafe; color:#1e3a8a; border:1px solid #bfdbfe; }
    .dev-star { background:#fef3c7; color:#92400e; border:1px solid #fde68a; }
    .dev-norm { background:#e5e7eb; color:#374151; border:1px solid #d1d5db; }
    /* Grade badges */
    .grade { display:inline-block; margin-left:6px; padding:2px 7px; border-radius:999px; font-size:11px; font-weight:700; border:1px solid transparent; }
    .grade-on { background:#dcfce7; color:#166534; border-color:#bbf7d0; }
    .grade-near { background:#fef3c7; color:#92400e; border-color:#fde68a; }
    .grade-below { background:#fee2e2; color:#991b1b; border-color:#fecaca; }
    .grade.hidden { display:none; }

    /* Round hit/miss visualization */
    .rounds-table th.rcol { text-align:center; }
    .round-cell { width: 60px; height: 16px; position: relative; background:#f3f4f6; border:1px solid #e5e7eb; border-radius:6px; overflow:hidden; }
    .round-cell .hit { height:100%; background:#86efac; }
    .round-cell.low .hit { background:#fcd34d; }
    .round-cell.med .hit { background:#a3e635; }
    .round-cell.high .hit { background:#22c55e; }
    .round-cell.zero .hit { background:#e5e7eb; }
    .round-cell .label { position:absolute; inset:0; display:flex; align-items:center; justify-content:center; font-size:11px; color:#334155; }
    .rounds-table td.empty { background:#fafafa; }

    /* Sticky sub-nav */
    .subnav { position: sticky; top: 0; z-index: 20; background: rgba(255,255,255,.92); backdrop-filter: saturate(120%) blur(6px); border-bottom: 1px solid #eef2f7; padding: 8px 12px; display:flex; flex-wrap:wrap; gap: 8px; }
    .subnav a { text-decoration:none; font-size:12px; color:#0f172a; background:#f1f5f9; border:1px solid #e2e8f0; padding:6px 10px; border-radius:999px; }
    .subnav a:hover { background:#e2e8f0; }

    /* Round 1 recap cards */
    .r1-list { display:grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 12px; }
    .r1-card { border:1px solid var(--grid); border-radius:10px; padding:12px; background:#fff; position:relative; }
    .r1-card .head { display:flex; align-items:center; gap:8px; justify-content:space-between; }
    .r1-card .head img.r1-photo { width:56px; height:56px; border-radius:8px; object-fit:cover; box-shadow:0 2px 6px rgba(0,0,0,.08); }
    .r1-card img.team-logo { position:absolute; top:10px; right:10px; width:24px; height:24px; border-radius:6px; box-shadow:0 0 0 1px rgba(0,0,0,.08); }
    .r1-card .pick { margin-left:auto; font-weight:700; font-size:12px; color:#0f172a; background:#f1f5f9; border:1px solid #e2e8f0; padding:2px 8px; border-radius:999px; }
    .r1-card .name { margin-top:4px; }
    .r1-card .name .pos { color:#475569; font-weight:600; }
    .r1-card .name .grade { margin-left:6px; padding:1px 6px; border-radius:999px; font-size:11px; border:1px solid #e5e7eb; }
    .r1-card .name .grade.grade-on { background:#dcfce7; color:#166534; border-color:#bbf7d0; }
    .r1-card .name .grade.grade-near { background:#fef9c3; color:#92400e; border-color:#fde68a; }
    .r1-card .name .grade.grade-below { background:#fee2e2; color:#991b1b; border-color:#fecaca; }
    .r1-card .meta { color:#64748b; font-size:12px; margin-top:2px; }
    .r1-card .attrs { margin-top:6px; display:grid; grid-template-columns: repeat(2, minmax(0,1fr)); gap:6px; }
    .r1-card .attr { display:flex; justify-content:space-between; gap:8px; background:#f8fafc; border:1px solid #e5e7eb; border-radius:8px; padding:6px 8px; font-size:12px; }
    .r1-card .traits { margin-top:8px; display:flex; flex-wrap:wrap; gap:6px; }
    .r1-card .trait { display:inline-block; padding:2px 8px; border-radius:999px; font-size:11px; background:#eef2ff; color:#3730a3; border:1px solid #e0e7ff; }
    .proj { color:#0f172a; font-size:12px; margin-top:6px; background:#fff7ed; border:1px solid #fde68a; border-radius:8px; padding:6px 8px; }
    .mock-notes-block { margin-top:8px; }
    .mock-notes-title { cursor:default; color:#475569; font-weight:600; }
    .mock-notes { white-space: pre-wrap; color:#475569; font-size:12px; margin-top:6px; }
    /* Real pick evaluation */
    .real-eval-block { margin-top:8px; }
    .real-eval-title { color:#475569; font-weight:600; }
    .real-eval { color:#475569; font-size:12px; margin-top:6px; }
    .ovr-badge { display:inline-block; padding:2px 7px; border-radius:999px; font-size:11px; font-weight:700; background:#dcfce7; color:#166534; border:1px solid #bbf7d0; }

    /* Responsive tweaks */
    @media (max-width: 1100px) {
      .players { grid-template-columns: repeat(3, minmax(0,1fr)); }
    }
    @media (max-width: 800px) {
      .grid { grid-template-columns: 1fr; }
      .players { grid-template-columns: repeat(2, minmax(0,1fr)); }
      .kpis { grid-template-columns: repeat(3, minmax(0,1fr)); }
    }
    @media (max-width: 520px) {
      .players { grid-template-columns: 1fr; }
      .kpis { grid-template-columns: repeat(2, minmax(0,1fr)); }
    }
  </style>
  <script>
  // Simple table sorter: click any <th> in a .sortable table to sort by that column
  (function() {
    function getCellValue(tr, idx) {
      const td = tr.children[idx];
      if (!td) return '';
      // Prefer data-sort attribute when provided
      const ds = td.getAttribute('data-sort');
      const txt = ds != null ? ds : td.textContent || '';
      return txt.trim();
    }

    function asNumber(v) {
      if (v === '' || v == null) return NaN;
      const n = parseFloat(v.replace(/[,\s]/g, ''));
      return isNaN(n) ? NaN : n;
    }

    function makeComparer(idx, asc) {
      return function(a, b) {
        const va = getCellValue(a, idx);
        const vb = getCellValue(b, idx);
        const na = asNumber(va);
        const nb = asNumber(vb);
        let cmp;
        if (!isNaN(na) && !isNaN(nb)) {
          cmp = na - nb;
        } else {
          cmp = va.localeCompare(vb, undefined, {numeric:true, sensitivity:'base'});
        }
        return asc ? cmp : -cmp;
      }
    }

    function initSortableTables() {
      document.querySelectorAll('table.sortable').forEach(function(table) {
        const thead = table.tHead;
        if (!thead) return;
        const headers = thead.rows[0]?.cells || [];
        Array.from(headers).forEach(function(th, idx) {
          th.addEventListener('click', function() {
            const tbody = table.tBodies[0];
            if (!tbody) return;
            const rows = Array.from(tbody.rows);
            const current = th.getAttribute('data-sort-dir') || 'desc';
            const nextDir = current === 'asc' ? 'desc' : 'asc';
            rows.sort(makeComparer(idx, nextDir === 'asc'));
            // Update attributes for visual state (optional)
            Array.from(headers).forEach(h => h.removeAttribute('data-sort-dir'));
            th.setAttribute('data-sort-dir', nextDir);
            // Re-append rows
            rows.forEach(r => tbody.appendChild(r));
          });
        });
      });
    }

    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', initSortableTables);
    } else {
      initSortableTables();
    }
  })();
  </script>
</head>
<body>
  <div class=\"topbar\"><a class=\"back\" href=\"../index.html\" title=\"Back to index\">&#8592; Back to Index</a></div>
  <div class=\"container\"> 
    <header>
      <h1>Draft Class __YEAR__ — Analytics Report <span class=\"pill\">__YEAR__</span></h1>
      <div class=\"subtitle\">Elites spotlight + team and position strength analytics</div>
    </header>

    <nav class=\"subnav\">
      <a href=\"#kpis\">KPIs</a>
      <a href=\"#spotlight\">Spotlight</a>
      <a href=\"#teams\">Teams</a>
      <a href=\"#rounds\">Rounds</a>
      <a href=\"#round1\">Round 1</a>
      <a href=\"#positions\">Positions</a>
    </nav>

    <section id=\"kpis\" class=\"panel\"> 
      __INTRO_KPIS__
      <div class=\"kpis\"> 
        <div class=\"kpi\"><b>Total rookies</b><span>__TOTAL__</span></div>
        <div class=\"kpi\"><b>Avg overall</b><span>__AVG_OVR__</span></div>
        <div class=\"kpi\"><b>XF</b><span>__XF__ (__XF_PCT__%) <span class=\"grade __XF_GRADE_CLASS__\">__XF_GRADE_LABEL__</span></span></div>
        <div class=\"kpi\"><b>SS</b><span>__SS__ (__SS_PCT__%) <span class=\"grade __SS_GRADE_CLASS__\">__SS_GRADE_LABEL__</span></span></div>
        <div class=\"kpi\"><b>Star</b><span>__STAR__ (__STAR_PCT__%)</span></div>
        <div class=\"kpi\"><b>Normal</b><span>__NORMAL__ (__NORM_PCT__%)</span></div>
        <div class=\"kpi kpi-large\"><b>Dev distribution</b>
          <span>__XF_PCT__% / __SS_PCT__% / __STAR_PCT__% / __NORM_PCT__%</span>
          <div class=\"stackbar\">
            <div class=\"seg seg-xf\" style=\"width: __XF_PCT__%\"></div>
            <div class=\"seg seg-ss\" style=\"width: __SS_PCT__%\"></div>
            <div class=\"seg seg-star\" style=\"width: __STAR_PCT__%\"></div>
            <div class=\"seg seg-norm\" style=\"width: __NORM_PCT__%\"></div>
          </div>
        </div>
      </div>
    </section>

    <section id=\"round1\" class=\"panel\"> 
      <div class=\"section-title\">Round 1 Recap</div>
      __INTRO_ROUND1__
      <div class=\"card\"> 
        __ROUND1_HTML__
        <p class=\"muted\" style=\"margin-top:6px;\">__ROUND1_NOTE__</p>
      </div>
    </section>

    <section id=\"spotlight\" class=\"panel\"> 
      <div class=\"section-title\">Elites Spotlight</div>
      __INTRO_ELITES__
      <div class=\"players\">__ELITE_CARDS__</div>
    </section>

    <section id=\"teams\" class=\"panel\"> 
      <div class=\"grid\"> 
        <div class=\"card\"> 
          <h3>Team draft quality — by Avg OVR</h3>
          __INTRO_TEAM_QUALITY__
          <table class=\"sortable\">
            <thead><tr><th>Team</th><th>XF</th><th>SS</th><th>Star</th><th>Normal</th><th>#</th><th>Avg OVR</th><th>Best OVR</th></tr></thead>
            <tbody>__TEAM_TABLE__</tbody>
          </table>
        </div>
        <div class=\"card\"> 
          <h3>Most elites (XF+SS) — by team</h3>
          <table class=\"sortable\">
            <thead><tr><th>Team</th><th>Elites</th><th>#</th><th>Avg OVR</th></tr></thead>
            <tbody>__TEAM_HIDDENS__</tbody>
          </table>
          <p class=\"muted\" style=\"margin-top:6px;\">Note: based on current team on roster.</p>
        </div>
      </div>
    </section>

    <section id=\"rounds\" class=\"panel\">
      <div class=\"card\">
        <h3>Per-Round Hits by Team — Hit = XF/SS/Star</h3>
        <table class=\"rounds-table\">
          <thead>
            <tr>
              <th>Team</th>
              __ROUND_HEADERS__
            </tr>
          </thead>
          <tbody>
            __ROUND_ROWS__
          </tbody>
        </table>
        <p class=\"muted\" style=\"margin-top:6px;\">Hit counts include XF/SS/Star (non-Normal). Cells show Hit/Total with a bar; empty = no picks.</p>
      </div>
      <div class=\"card\" style=\"margin-top:16px;\">\n        <h3>Per-Round Hits by Team — Hit = Elites (XF/SS)</h3>\n        <table class=\"rounds-table\">\n          <thead>\n            <tr>\n              <th>Team</th>\n              __ROUND_HEADERS__\n            </tr>\n          </thead>\n          <tbody>\n            __ROUND_ROWS_ELITES__\n          </tbody>\n        </table>\n        <p class=\"muted\" style=\"margin-top:6px;\">Elites include only X-Factor and Superstar devs. Cells show Hit/Total with a bar; empty = no picks.</p>\n      </div>
    </section>

    <section id=\"positions\" class=\"panel\"> 
      __INTRO_POSITIONS__
      <div class=\"grid\"> 
        <div class=\"card\"> 
          <h3>Position strength</h3>
          <table class=\"sortable\">
            <thead><tr><th>Position</th><th>XF</th><th>SS</th><th>Star</th><th>Normal</th><th>Total</th><th>Avg OVR</th></tr></thead>
            <tbody>__POS_TABLE__</tbody>
          </table>
        </div>
        <div class=\"card\"> 
          <h3>Non‑Normal‑heavy positions</h3>
          <ul>__TOP_POS__</ul>
          <p class=\"muted\" style=\"margin-top:6px;\">Non‑Normal = X‑Factor + Superstar + Star</p>
        </div>
      </div>
    </section>

  </div>
</body>
</html>
"""
    # Page title computation with optional branding (safe for verifier)
    if title_override:
        page_title = title_override
    else:
        page_title = f"Draft Class {year} — Analytics"
        if title_suffix:
            page_title = f"{page_title} — {title_suffix}"

    # Inject values
    html_out = html_out.replace('__PAGE_TITLE__', html.escape(page_title))
    html_out = html_out.replace('__YEAR__', str(year))
    html_out = html_out.replace('__TOTAL__', str(total))
    html_out = html_out.replace('__AVG_OVR__', str(analytics['avg_ovr']))
    # KPI numbers and percentages
    html_out = html_out.replace('__XF__', str(xf_total))
    html_out = html_out.replace('__SS__', str(ss_total))
    html_out = html_out.replace('__STAR__', str(star_total))
    html_out = html_out.replace('__NORMAL__', str(norm_total))
    html_out = html_out.replace('__XF_PCT__', str(analytics.get('xf_pct', 0.0)))
    html_out = html_out.replace('__SS_PCT__', str(analytics.get('ss_pct', 0.0)))
    html_out = html_out.replace('__STAR_PCT__', str(analytics.get('star_pct', 0.0)))
    html_out = html_out.replace('__NORM_PCT__', str(analytics.get('norm_pct', 0.0)))
    # Grades: hide below-target badge (no badge shown)
    xf_label = analytics.get('xf_grade_label', '')
    xf_class = analytics.get('xf_grade_class', '')
    ss_label = analytics.get('ss_grade_label', '')
    ss_class = analytics.get('ss_grade_class', '')
    if xf_class == 'grade-below':
        xf_label_render, xf_class_render = '', 'hidden'
    else:
        xf_label_render, xf_class_render = xf_label, xf_class
    if ss_class == 'grade-below':
        ss_label_render, ss_class_render = '', 'hidden'
    else:
        ss_label_render, ss_class_render = ss_label, ss_class
    html_out = html_out.replace('__XF_GRADE_LABEL__', html.escape(xf_label_render))
    html_out = html_out.replace('__SS_GRADE_LABEL__', html.escape(ss_label_render))
    html_out = html_out.replace('__XF_GRADE_CLASS__', html.escape(xf_class_render))
    html_out = html_out.replace('__SS_GRADE_CLASS__', html.escape(ss_class_render))
    # Section intros
    section_intros = section_intros or {}
    def render_intro(key: str) -> str:
        txt = section_intros.get(key)
        if txt is None:
            txt = intro_default or ''
        txt = (txt or '').strip()
        if not txt:
            return ''
        return f'<div class="section-intro">{html.escape(txt)}</div>'

    html_out = html_out.replace('__INTRO_KPIS__', render_intro('kpis'))
    html_out = html_out.replace('__INTRO_ELITES__', render_intro('elites'))
    html_out = html_out.replace('__INTRO_TEAM_QUALITY__', render_intro('team_quality'))
    html_out = html_out.replace('__INTRO_POSITIONS__', render_intro('positions'))

    html_out = html_out.replace('__ELITE_CARDS__', elite_cards_html)
    html_out = html_out.replace('__TEAM_TABLE__', team_table_html)
    html_out = html_out.replace('__TEAM_HIDDENS__', team_hiddens_html)
    html_out = html_out.replace('__POS_TABLE__', pos_table_html)
    html_out = html_out.replace('__TOP_POS__', top_pos_html)
    # Round 1 recap injection
    r1_entries = round1_entries or []
    r1_html = render_round1_recap(r1_entries, round1_mock)
    r1_note = ''
    try:
        n = len(r1_entries)
        if n and n < 32:
            r1_note = f"Showing {n} of 32 picks"
    except Exception:
        r1_note = ''
    html_out = html_out.replace('__ROUND1_HTML__', r1_html)
    html_out = html_out.replace('__ROUND1_NOTE__', html.escape(r1_note))
    html_out = html_out.replace('__INTRO_ROUND1__', render_intro('round1'))

    # Round-by-team hidden/miss table injection
    rounds = analytics.get('rounds_sorted', [])
    # Limit the number of columns to keep layout sane (e.g., first 7 rounds)
    rounds = [r for r in rounds if isinstance(r, int)]
    rounds = sorted(rounds)[:10]
    if rounds:
        hdr_cells = ''.join([f"<th class='rcol'>R{int(r)}</th>" for r in rounds])
    else:
        hdr_cells = "<th class='rcol'>R1</th>"
    html_out = html_out.replace('__ROUND_HEADERS__', hdr_cells)

    team_rounds = analytics.get('team_rounds', {})
    round_rows = []
    # Keep team ordering similar to overall team table (by avg OVR desc)
    for team, stats in sorted(analytics['teams'].items(), key=lambda kv: (-kv[1]['avg_ovr'], kv[0])):
        cells = []
        per_team = team_rounds.get(team, {})
        for r in rounds:
            cell = per_team.get(r)
            if not cell:
                cells.append("<td class='empty' title='No pick'></td>")
                continue
            hit = int(cell.get('hit', 0))
            total = int(cell.get('total', 0))
            pct = int(round(100.0 * hit / total)) if total else 0
            rate_cls = 'high' if pct >= 75 else ('med' if pct >= 40 else ('low' if pct > 0 else 'zero'))
            bar = (
                f"<div class='round-cell {rate_cls}' title='Hit {hit} of {total}'>"
                f"<div class='hit' style='width:{pct}%'></div>"
                f"<div class='label'>{hit}/{total}</div>"
                f"</div>"
            )
            cells.append(f"<td>{bar}</td>")
        row_html = f"<tr><td class='team'>{logo_img(team)}<span>{html.escape(team)}</span></td>{''.join(cells)}</tr>"
        round_rows.append(row_html)
    html_out = html_out.replace('__ROUND_ROWS__', '\n'.join(round_rows))
    # Elites-only round table rows
    team_rounds_elites = analytics.get('team_rounds_elites', {})
    round_rows_elites = []
    for team, stats in sorted(analytics['teams'].items(), key=lambda kv: (-kv[1]['avg_ovr'], kv[0])):
        cells = []
        per_team = team_rounds_elites.get(team, {})
        for r in rounds:
            cell = per_team.get(r)
            if not cell:
                cells.append("<td class='empty' title='No pick'></td>")
                continue
            hit = int(cell.get('hit', 0))
            total = int(cell.get('total', 0))
            pct = int(round(100.0 * hit / total)) if total else 0
            rate_cls = 'high' if pct >= 75 else ('med' if pct >= 40 else ('low' if pct > 0 else 'zero'))
            bar = (
                f"<div class='round-cell {rate_cls}' title='Elites {hit} of {total}'>"
                f"<div class='hit' style='width:{pct}%'></div>"
                f"<div class='label'>{hit}/{total}</div>"
                f"</div>"
            )
            cells.append(f"<td>{bar}</td>")
        row_html = f"<tr><td class='team'>{logo_img(team)}<span>{html.escape(team)}</span></td>{''.join(cells)}</tr>"
        round_rows_elites.append(row_html)
    html_out = html_out.replace('__ROUND_ROWS_ELITES__', '\n'.join(round_rows_elites))
    return html_out


def main():
    ap = argparse.ArgumentParser(description='Generate Draft Class Analytics HTML')
    ap.add_argument('--year', type=int, required=True, help='Draft class year (e.g., 2026)')
    ap.add_argument('--players', default='MEGA_players.csv', help='Path to players CSV (default: MEGA_players.csv)')
    ap.add_argument('--teams', default='MEGA_teams.csv', help='Path to teams CSV (default: MEGA_teams.csv)')
    ap.add_argument('--out', default=None, help='Output HTML path (default: docs/draft_class_<year>.html)')
    ap.add_argument('--league-prefix', default='MEGA League', help='Optional league/brand suffix for <title>')
    ap.add_argument('--title', dest='title_override', default=None, help='Optional full page <title> override string')
    ap.add_argument('--section-intros', dest='section_intros', default=None, help='Path to JSON mapping for section intros')
    ap.add_argument('--intro-default', dest='intro_default', default=None, help='Default intro text used when a section is missing in mapping')
    ap.add_argument('--mock-md', dest='mock_md', default=None, help='Path to mock draft markdown (docs/draft_mock.md). If omitted and default exists, it will be used.')
    args = ap.parse_args()

    out_path = args.out or os.path.join('docs', f'draft_class_{args.year}.html')

    players = read_csv(args.players)
    # Non-fatal schema warnings for players CSV
    warn_missing_columns(
        players,
        required=['rookieYear', 'playerBestOvr', 'playerSchemeOvr', 'devTrait', 'fullName', 'team', 'position'],
        context='players CSV',
    )

    # Teams are optional; if missing, proceed without logos
    teams = []
    if os.path.exists(args.teams):
        try:
            teams = read_csv(args.teams)
        except SystemExit:
            # read_csv already handled printing; continue without logos
            teams = []
    else:
        print(f"warn: teams CSV not found: {args.teams} — continuing without logos", file=sys.stderr)
    team_logo_map = build_team_logo_map(teams)

    rookies = gather_rookies(players, args.year)
    analytics = compute_analytics(rookies)
    intros_map = read_section_intros(args.section_intros)
    # Mock draft notes (optional)
    mock_md_path = args.mock_md
    if not mock_md_path:
        default_md = os.path.join('docs', 'draft_mock.md')
        if os.path.exists(default_md):
            mock_md_path = default_md
    mock_lookup = read_mock_draft_md(mock_md_path)
    # Build round 1 entries from raw players to access full ratings/traits
    round1_entries = build_round1_entries(players, team_logo_map, year=args.year)
    html_out = generate_html(
        args.year, rookies, analytics, team_logo_map,
        title_suffix=args.league_prefix,
        title_override=args.title_override,
        section_intros=intros_map,
        intro_default=args.intro_default,
        round1_entries=round1_entries,
        round1_mock=mock_lookup,
    )

    out_dir = os.path.dirname(out_path)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
    try:
        with open(out_path, 'w', encoding='utf-8') as f:
            f.write(html_out)
    except Exception as e:
        print(f"error: failed to write output HTML '{out_path}': {e}", file=sys.stderr)
        sys.exit(2)

    print(f'Generated: {out_path}')
    print(f"Rookies: {analytics['total']} | Avg OVR: {analytics['avg_ovr']}")


if __name__ == '__main__':
    main()
