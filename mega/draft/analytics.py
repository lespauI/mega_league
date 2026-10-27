"""Draft class input normalization and analytics calculations."""
from __future__ import annotations

import csv
import json
import os
import statistics as st
import sys
from collections import Counter

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

    Keys correspond to CSV column names. For readability on cards, labels will
    have the trailing 'Rating' removed at render time (e.g., speedRating → speed).
    """
    p = _pos_key(pos)
    # QB
    if p == 'QB':
        return [
            'throwAccShortRating','throwAccMidRating','throwAccDeepRating','throwPowerRating',
            'throwUnderPressureRating','throwOnRunRating','playActionRating','awareRating',
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
        return [
            'catchRating','specCatchRating','cITRating','speedRating',
            'routeRunShortRating','routeRunMedRating','routeRunDeepRating',
            'releaseRating','agilityRating','changeOfDirectionRating'
        ]
    if p == 'TE':
        return [
            'catchRating','cITRating','runBlockRating','passBlockRating',
            'speedRating','routeRunShortRating','routeRunMedRating','strengthRating','specCatchRating'
        ]
    if p in {'LT','LG','RT','RG','T','G','C','OL'}:
        return [
            'passBlockRating','passBlockPowerRating','passBlockFinesseRating',
            'runBlockRating','runBlockPowerRating','runBlockFinesseRating',
            'strengthRating','awareRating','impactBlockRating'
        ]
    if p in {'LE','RE','DE','LEDGE','REDGE'}:
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
    if p in {'LE','RE','DE','DT','LEDGE','REDGE'}:
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
        # Include Round 1 + Round 2 Pick 1 (hack for 2.1)
        if pk is None:
            continue
        if rd == 1:
            pass  # include all R1
        elif rd == 2 and pk == 1:
            pass  # include R2 pick 1 only
        else:
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

        # Calculate overall pick number (32 picks per round)
        overall_pick = ((rd - 1) * 32) + pk if rd and pk else pk

        entries.append({
            'pick': overall_pick,
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


def _grade_for_ovr(ovr: int, dev: str = '0') -> tuple[str, str]:
    """Return (label, css_class) for a pick grade derived from OVR + dev trait.

    Elite day-1 impact requires BOTH high OVR and a Superstar/X-Factor dev tier.
    Normal/Star dev caps the grade regardless of OVR.

    - A  (grade-on):    OVR >= 80 AND dev in {SS, XF}
    - B  (grade-near):  (OVR >= 78 AND dev in {SS, XF}) OR OVR >= 82
    - C  (grade-near):  OVR >= 78 OR (dev in {SS, XF} AND OVR >= 72)
    - D  (grade-below): OVR >= 72
    - F  (grade-below): OVR < 72
    """
    try:
        o = int(ovr)
    except Exception:
        o = 0
    elite = str(dev) in ('2', '3')  # Superstar or X-Factor
    if o >= 80 and elite:
        return ('A', 'grade-on')
    if (o >= 78 and elite) or o >= 82:
        return ('B', 'grade-near')
    if o >= 78 or (elite and o >= 72):
        return ('C', 'grade-near')
    if o >= 72:
        return ('D', 'grade-below')
    return ('F', 'grade-below')


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
