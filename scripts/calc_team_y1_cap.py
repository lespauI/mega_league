#!/usr/bin/env python3
"""
Compute Year+1 cap projection for a given team from MEGA CSVs.

- Per-player Y+1 = base_per_year (or inferred) + bonus_per_year if proration remains
- Mirrors docs/roster_cap_tool/js/capMath.js projectPlayerCapHits() logic

Usage:
  python3 scripts/calc_team_y1_cap.py --team DAL \
      --players MEGA_players.csv \
      --teams MEGA_teams.csv \
      [--growth 0.09] [--rookie-reserve 0] [--baseline-dead-next 0] [--resign-factor 0.4]

Prints a sorted breakdown and totals for roster-only Y+1 spend, then adds
rookie reserve, baseline next-year dead money, and a re-sign reserve estimate.
"""
import argparse, csv, math, sys

MADDEN_BONUS_PRORATION_MAX_YEARS = 5

def to_float(s, default=0.0):
    try:
        v = float(s)
        if math.isfinite(v):
            return v
        return default
    except Exception:
        return default

def to_int(s, default=0):
    try:
        v = int(float(s))
        return v
    except Exception:
        return default

def to_bool(s):
    return str(s).strip().lower() in ("1","true","yes","y")

BASE_SALARY_WEIGHTS = {
    2: [48.7, 51.3],
    3: [31.7, 33.3, 35.0],
    4: [23.2, 24.3, 25.5, 27.0],
    5: [18.0, 19.0, 20.0, 21.0, 22.0],
    6: [14.7, 15.4, 16.2, 17.0, 17.9, 18.8],
    7: [12.3, 12.9, 13.5, 14.2, 14.9, 15.7, 16.5],
}

def build_base_schedule(total_salary: float, length: int):
    if length <= 0:
        return []
    w = BASE_SALARY_WEIGHTS.get(length)
    if not w or len(w) != length:
        per = total_salary / length if length else 0.0
        return [per] * length
    s = sum(w) or 1.0
    out = []
    acc = 0.0
    for i, pct in enumerate(w):
        if i == length - 1:
            out.append(max(0.0, total_salary - acc))
        else:
            v = total_salary * (pct / s)
            out.append(v)
            acc += v
    return out

def project_player_y1(p):
    """Return (y1_cap, base_component, bonus_component, meta) for a player row."""
    capHit = to_float(p.get('capHit', 0.0), 0.0)
    length = to_int(p.get('contractLength', 0), 0)
    yearsLeft = to_int(p.get('contractYearsLeft', 0), 0)
    if length <= 0:
        length = max(1, yearsLeft if yearsLeft > 0 else 1)
    yearsElapsed = max(0, min(length, length - yearsLeft))
    prorateYears = min(length, MADDEN_BONUS_PRORATION_MAX_YEARS)

    # Bonus total: prefer contractBonus else derive from capReleasePenalty
    bonusTotal = to_float(p.get('contractBonus', 0.0), 0.0)
    remainingProrationNow = max(0, prorateYears - yearsElapsed)
    if bonusTotal <= 0:
        pen = to_float(p.get('capReleasePenalty', 0.0), 0.0)
        if pen > 0 and remainingProrationNow > 0:
            bonusTotal = pen * (prorateYears / remainingProrationNow)
    bonusPerYear = (bonusTotal / prorateYears) if (bonusTotal > 0 and prorateYears > 0) else 0.0

    # Base per year: prefer contractSalary/length else infer from capHit minus proration
    contractSalary = to_float(p.get('contractSalary', 0.0), 0.0)
    baseSchedule = build_base_schedule(contractSalary, length) if contractSalary > 0 else None
    inferredBasePerYear = max(0.0, capHit - (bonusPerYear if remainingProrationNow > 0 else 0.0))

    i = 1  # Y+1
    withinContract = i < yearsLeft
    hasProration = i < remainingProrationNow
    if withinContract:
        idx = yearsElapsed + i
        base = baseSchedule[idx] if baseSchedule and idx < len(baseSchedule) else inferredBasePerYear
    else:
        base = 0.0
    pr = bonusPerYear if hasProration else 0.0
    meta = {
        'length': length,
        'yearsLeft': yearsLeft,
        'yearsElapsed': yearsElapsed,
        'prorateYears': prorateYears,
        'bonusTotal': bonusTotal,
        'bonusPerYear': bonusPerYear,
        'basePerYear': (baseSchedule[yearsElapsed] if baseSchedule and yearsElapsed < len(baseSchedule) else inferredBasePerYear),
    }
    return base + pr, base, pr, meta

def estimate_resign_reserve(players, team_name, factor=0.4):
    """Sum desired Y1 cap for expiring/flagged players, scaled by factor."""
    total = 0.0
    cnt = 0
    for p in players:
        if p.get('team') != team_name or to_bool(p.get('isFreeAgent','false')):
            continue
        yl = to_int(p.get('contractYearsLeft', 0), 0)
        rs = to_int(p.get('reSignStatus', 0), 0)
        if yl <= 0 or rs != 0:
            ds = to_float(p.get('desiredSalary', 0.0), 0.0)
            db = to_float(p.get('desiredBonus', 0.0), 0.0)
            dl = to_int(p.get('desiredLength', 3), 3)
            pyears = max(1, min(5, dl))
            y1 = ds + (db / pyears)
            if y1 > 0:
                total += y1
                cnt += 1
    return total * max(0.0, min(1.0, factor)), cnt

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--team', required=True, help='Team abbr (e.g., DAL)')
    ap.add_argument('--players', default='MEGA_players.csv')
    ap.add_argument('--teams', default='MEGA_teams.csv')
    ap.add_argument('--growth', type=float, default=0.09, help='Cap growth rate for Y+1')
    ap.add_argument('--rookie-reserve', type=float, default=0.0)
    ap.add_argument('--baseline-dead-next', type=float, default=0.0)
    ap.add_argument('--resign-factor', type=float, default=0.4)
    args = ap.parse_args()

    # Load teams
    team_row = None
    with open(args.teams, newline='') as f:
        r = csv.DictReader(f)
        for row in r:
            if row.get('abbrName') == args.team:
                team_row = row
                break
    if not team_row:
        print(f"Team {args.team} not found in {args.teams}", file=sys.stderr)
        sys.exit(2)

    capRoom0 = to_float(team_row.get('capRoom', 0.0), 0.0)
    capRoom1 = capRoom0 * (1.0 + float(args.growth))
    team_name = team_row.get('displayName') or team_row.get('teamName') or args.team

    # Load players
    players = []
    with open(args.players, newline='') as f:
        players = list(csv.DictReader(f))

    # Collect team players by display name in players.csv
    # players.csv uses team full name (e.g., 'Cowboys') not abbr; map from teams.csv displayName
    roster_name = team_name
    roster = [p for p in players if p.get('team') == roster_name and not to_bool(p.get('isFreeAgent','false'))]

    rows = []
    total = 0.0
    for p in roster:
        y1, base, pr, meta = project_player_y1(p)
        total += y1
        rows.append({
            'name': f"{p.get('firstName','')} {p.get('lastName','')}",
            'pos': p.get('position',''),
            'capHit_now': to_float(p.get('capHit',0.0),0.0),
            'y1_cap': y1,
            'y1_base': base,
            'y1_bonus': pr,
            'yearsLeft': meta['yearsLeft'],
            'length': meta['length'],
        })

    rows.sort(key=lambda r: r['y1_cap'], reverse=True)

    # Estimate re-sign reserve
    resign_reserve, resign_count = estimate_resign_reserve(players, roster_name, args.resign_factor)

    print(f"Team: {args.team} ({roster_name})")
    print(f"Players counted: {len(rows)}")
    print(f"Cap Room Y0: ${capRoom0:,.0f}; Cap Room Y+1 (growth {args.growth:.0%}): ${capRoom1:,.0f}")
    print()
    print("Top 20 Y+1 cap hits (approx):")
    for r in rows[:20]:
        print(f"  {r['name']:<24} {r['pos']:<4}  Y1 ${r['y1_cap']:>10,.0f}  (base ${r['y1_base']:>10,.0f} + bonus ${r['y1_bonus']:>10,.0f})  L{r['length']}/YL{r['yearsLeft']}")

    print()
    print(f"Roster Y+1 total (approx): ${total:,.0f}")
    print(f"Add: Rookie Reserve (Y+1): ${float(args.rookie_reserve):,.0f}")
    print(f"Add: Baseline Dead Money (Y+1): ${float(args.baseline_dead_next):,.0f}")
    print(f"Add: Re-sign reserve (factor {args.resign_factor:.0%}, {resign_count} players): ${resign_reserve:,.0f}")
    grand = total + float(args.rookie_reserve) + float(args.baseline_dead_next) + resign_reserve
    print(f"Projected Y+1 spend (approx): ${grand:,.0f}")
    cap_space1 = capRoom1 - grand
    print(f"Projected Y+1 cap space: ${cap_space1:,.0f}")

if __name__ == '__main__':
    main()
