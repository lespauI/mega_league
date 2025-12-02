#!/usr/bin/env python3
"""
Verify Salary Cap math parity with docs/roster_cap_tool/js/capMath.js.

Produces a machine-readable report at output/cap_tool_verification.json that
summarizes scenario simulations (release, trade quick, extension, conversion,
signing) and basic invariants on cap deltas.

Defaults:
  - Teams CSV: docs/roster_cap_tool/data/MEGA_teams.csv (falls back to MEGA_teams.csv)
  - Players CSV: docs/roster_cap_tool/data/MEGA_players.csv (falls back to MEGA_players.csv)
  - Fixtures: scripts/fixtures/cap_scenarios.json (auto-generates if missing)
  - Output JSON: output/cap_tool_verification.json

Additionally, generates output/tiny_teams.csv if it does not exist by copying
the first few rows from the teams CSV for tiny tests.

Usage:
  python3 scripts/verify_cap_math.py \
      --teams docs/roster_cap_tool/data/MEGA_teams.csv \
      --players docs/roster_cap_tool/data/MEGA_players.csv \
      --fixtures scripts/fixtures/cap_scenarios.json \
      --out output/cap_tool_verification.json
"""
from __future__ import annotations

import argparse
import csv
import dataclasses as dc
import datetime as dt
import json
import math
import os
import sys
from typing import Any, Dict, List, Optional


MADDEN_BONUS_PRORATION_MAX_YEARS = 5


def to_float(v: Any, default: float = 0.0) -> float:
    try:
        if v is None:
            return default
        if isinstance(v, (int, float)):
            return float(v)
        s = str(v).strip()
        if not s:
            return default
        return float(s)
    except Exception:
        return default


def to_int(v: Any, default: int = 0) -> int:
    try:
        if v is None:
            return default
        if isinstance(v, int):
            return v
        if isinstance(v, float):
            return int(v)
        s = str(v).strip()
        if not s:
            return default
        if "." in s:
            return int(float(s))
        return int(s)
    except Exception:
        return default


def to_bool(v: Any) -> bool:
    if isinstance(v, bool):
        return v
    s = (str(v) or "").strip().lower()
    return s in {"1", "true", "t", "yes", "y"}


def proration_years(years: Any) -> int:
    y = max(1, to_int(years, 1))
    return max(1, min(MADDEN_BONUS_PRORATION_MAX_YEARS, y))


@dc.dataclass
class Team:
    abbrName: str
    displayName: str
    capRoom: float
    capSpent: float
    capAvailable: float
    seasonIndex: int
    weekIndex: int


@dc.dataclass
class Player:
    id: str
    firstName: str
    lastName: str
    position: str
    team: str | None
    isFreeAgent: bool
    capHit: float
    capReleaseNetSavings: Optional[float]
    capReleasePenalty: Optional[float]
    contractSalary: Optional[float]
    contractBonus: Optional[float]
    contractLength: Optional[int]
    contractYearsLeft: Optional[int]
    desiredSalary: Optional[float]
    desiredBonus: Optional[float]
    desiredLength: Optional[int]


@dc.dataclass
class CapSnapshot:
    capRoom: float
    capSpent: float
    capAvailable: float
    deadMoney: float
    baselineAvailable: float
    deltaAvailable: float


def read_csv(path: str) -> list[dict]:
    with open(path, newline="", encoding="utf-8-sig") as fh:
        return list(csv.DictReader(fh))


def load_teams(path: str) -> list[Team]:
    rows = read_csv(path)
    out: list[Team] = []
    for r in rows:
        out.append(
            Team(
                abbrName=str(r.get("abbrName") or r.get("teamAbbrev") or r.get("abbr") or "").strip(),
                displayName=str(r.get("displayName") or r.get("teamName") or "").strip(),
                capRoom=to_float(r.get("capRoom")),
                capSpent=to_float(r.get("capSpent")),
                capAvailable=to_float(r.get("capAvailable")),
                seasonIndex=to_int(r.get("seasonIndex"), 0),
                weekIndex=to_int(r.get("weekIndex"), 0),
            )
        )
    return [t for t in out if t.abbrName]


def load_players(path: str) -> list[Player]:
    rows = read_csv(path)
    out: list[Player] = []
    for r in rows:
        out.append(
            Player(
                id=str(r.get("id") or r.get("playerId") or r.get("rosterId") or "").strip(),
                firstName=str(r.get("firstName") or r.get("fname") or "").strip(),
                lastName=str(r.get("lastName") or r.get("lname") or "").strip(),
                position=str(r.get("position") or r.get("pos") or "").strip(),
                team=(str(r.get("team") or r.get("abbrName") or "").strip() or None),
                isFreeAgent=to_bool(r.get("isFreeAgent")),
                capHit=to_float(r.get("capHit")),
                capReleaseNetSavings=(
                    to_float(r.get("capReleaseNetSavings")) if r.get("capReleaseNetSavings") not in (None, "") else None
                ),
                capReleasePenalty=(
                    to_float(r.get("capReleasePenalty")) if r.get("capReleasePenalty") not in (None, "") else None
                ),
                contractSalary=(
                    to_float(r.get("contractSalary")) if r.get("contractSalary") not in (None, "") else None
                ),
                contractBonus=(
                    to_float(r.get("contractBonus")) if r.get("contractBonus") not in (None, "") else None
                ),
                contractLength=(
                    to_int(r.get("contractLength"), 0) if r.get("contractLength") not in (None, "") else None
                ),
                contractYearsLeft=(
                    to_int(r.get("contractYearsLeft"), 0) if r.get("contractYearsLeft") not in (None, "") else None
                ),
                desiredSalary=(
                    to_float(r.get("desiredSalary")) if r.get("desiredSalary") not in (None, "") else None
                ),
                desiredBonus=(
                    to_float(r.get("desiredBonus")) if r.get("desiredBonus") not in (None, "") else None
                ),
                desiredLength=(
                    to_int(r.get("desiredLength"), 0) if r.get("desiredLength") not in (None, "") else None
                ),
            )
        )
    # Filter obviously malformed rows
    return [p for p in out if p.id and p.firstName and p.lastName and p.position and math.isfinite(p.capHit)]


# --- Cap Math (Python parity with js/capMath.js) ---


def calc_cap_summary(team: Team, moves: list[dict]) -> CapSnapshot:
    cap_room = float(team.capRoom)
    base_spent = float(team.capSpent)
    base_avail = float(team.capAvailable)

    delta_spent = 0.0
    dead_money = 0.0

    for mv in moves or []:
        t = mv.get("type")
        if t == "release":
            savings = to_float(mv.get("savings"))
            delta_spent -= savings
            dead_money += to_float(mv.get("penalty"))
        elif t == "tradeQuick":
            savings = to_float(mv.get("savings"))
            delta_spent -= savings
            dead_money += to_float(mv.get("penalty"))
        elif t in {"extend", "convert"}:
            delta_spent += to_float(mv.get("capHitDelta"))
        elif t == "sign":
            delta_spent += to_float(mv.get("year1CapHit"))

    cap_spent = base_spent + delta_spent
    cap_avail = base_avail - delta_spent
    return CapSnapshot(
        capRoom=cap_room,
        capSpent=cap_spent,
        capAvailable=cap_avail,
        deadMoney=dead_money,
        baselineAvailable=base_avail,
        deltaAvailable=cap_avail - base_avail,
    )


def simulate_release(team: Team, player: Player) -> dict:
    savings = float(player.capReleaseNetSavings or 0.0)
    penalty_total = max(0.0, float(player.capReleasePenalty or 0.0))
    years_left = max(0, int(player.contractYearsLeft or 0))

    penalty_current = penalty_total
    penalty_next = 0.0
    if penalty_total > 0 and years_left >= 2:
        # Mirror JS: ~60% current year, ~40% next year
        penalty_next = round(penalty_total * 0.4)
        penalty_current = penalty_total - penalty_next

    new_cap_space = float(team.capAvailable) + savings
    move = {
        "type": "release",
        "playerId": player.id,
        "penalty": penalty_current,
        "savings": savings,
        "at": int(dt.datetime.now().timestamp() * 1000),
    }
    return {
        "savings": savings,
        "penaltyTotal": penalty_total,
        "penaltyCurrentYear": penalty_current,
        "penaltyNextYear": penalty_next,
        "newCapSpace": new_cap_space,
        "move": move,
    }


def simulate_trade_quick(team: Team, player: Player) -> dict:
    res = simulate_release(team, player)
    res["move"]["type"] = "tradeQuick"
    return res


def simulate_extension(player: Player, years: int, total_salary: float, signing_bonus: float) -> dict:
    y = max(1, int(years))
    total = max(0.0, float(total_salary))
    bonus = max(0.0, float(signing_bonus))
    new_cap_hit = (total + bonus) / y
    cap_hit_delta = new_cap_hit - float(player.capHit)
    move = {
        "type": "extend",
        "playerId": player.id,
        "years": y,
        "salary": total,
        "bonus": bonus,
        "capHitDelta": cap_hit_delta,
        "at": int(dt.datetime.now().timestamp() * 1000),
    }
    return {"newCapHit": new_cap_hit, "capHitDelta": cap_hit_delta, "move": move}


def simulate_conversion(player: Player, convert_amount: float, years_remaining: int) -> dict:
    y_rem = max(1, int(years_remaining))
    p_years = proration_years(y_rem)

    total_bonus = float(player.contractBonus or 0.0)
    length = max(1, int(player.contractLength or 1))
    prorate_years = min(length, MADDEN_BONUS_PRORATION_MAX_YEARS)
    bonus_per_year = (total_bonus / prorate_years) if total_bonus else 0.0

    current_cap_hit = float(player.capHit)
    approx_base_salary = max(0.0, current_cap_hit - bonus_per_year)

    convert = max(0.0, float(convert_amount))
    convert = min(convert, approx_base_salary)

    per_year_proration = convert / p_years
    new_current_year_cap_hit = current_cap_hit - convert + per_year_proration
    cap_hit_delta = new_current_year_cap_hit - current_cap_hit

    future_years = [per_year_proration for _ in range(max(0, p_years - 1))]
    move = {
        "type": "convert",
        "playerId": player.id,
        "convertAmount": convert,
        "yearsRemaining": y_rem,
        "capHitDelta": cap_hit_delta,
        "at": int(dt.datetime.now().timestamp() * 1000),
    }
    return {
        "newCurrentYearCapHit": new_current_year_cap_hit,
        "perYearProration": per_year_proration,
        "capHitDelta": cap_hit_delta,
        "futureYears": future_years,
        "move": move,
    }


def simulate_signing(team: Team, player: Player, years: int, salary: float, bonus: float) -> dict:
    y = max(1, int(years))
    s = max(0.0, float(salary))
    b = max(0.0, float(bonus))
    p_years = proration_years(y)
    year1_cap_hit = s + (b / p_years)
    remaining_after = float(team.capAvailable) - year1_cap_hit

    # lowball warning if any offered dimension < 90% of desired
    ds = player.desiredSalary if player.desiredSalary is not None else None
    db = player.desiredBonus if player.desiredBonus is not None else None
    dl = player.desiredLength if player.desiredLength is not None else None
    salary_ok = True if (ds is None or ds == 0) else s >= 0.9 * ds
    bonus_ok = True if (db is None or db == 0) else b >= 0.9 * db
    years_ok = True if (dl is None or dl == 0) else y >= int(math.floor(0.9 * dl))
    warn_lowball = not (salary_ok and bonus_ok and years_ok)

    move = {
        "type": "sign",
        "playerId": player.id,
        "years": y,
        "salary": s,
        "bonus": b,
        "year1CapHit": year1_cap_hit,
        "at": int(dt.datetime.now().timestamp() * 1000),
    }
    return {
        "year1CapHit": year1_cap_hit,
        "remainingCapAfter": remaining_after,
        "warnLowball": warn_lowball,
        "canSign": remaining_after >= 0,
        "move": move,
    }


# --- Scenario runner ---


def find_team(teams: list[Team], abbr: str) -> Optional[Team]:
    for t in teams:
        if t.abbrName == abbr:
            return t
    return None


def pick_player_for_release(players: list[Player], team_aliases: list[str]) -> Optional[Player]:
    candidates = [
        p
        for p in players
        if (not p.isFreeAgent) and (p.team in team_aliases) and (p.capReleaseNetSavings is not None)
    ]
    # Prefer those with both savings and penalty present
    candidates.sort(key=lambda p: (0 if (p.capReleaseNetSavings and p.capReleasePenalty) else 1, -p.capHit))
    return candidates[0] if candidates else None


def pick_player_for_extension(players: list[Player], team_aliases: list[str]) -> Optional[Player]:
    candidates = [p for p in players if (not p.isFreeAgent) and (p.team in team_aliases) and math.isfinite(p.capHit)]
    candidates.sort(key=lambda p: -p.capHit)
    return candidates[0] if candidates else None


def pick_player_for_conversion(players: list[Player], team_aliases: list[str]) -> Optional[Player]:
    candidates = [p for p in players if (not p.isFreeAgent) and (p.team in team_aliases) and math.isfinite(p.capHit)]
    # Prefer those with contractBonus/Length to exercise bonus-per-year logic
    candidates.sort(key=lambda p: (0 if (p.contractBonus and p.contractLength) else 1, -p.capHit))
    return candidates[0] if candidates else None


def pick_free_agent(players: list[Player]) -> Optional[Player]:
    candidates = [p for p in players if p.isFreeAgent]
    # Prefer those with desired fields available
    def score(p: Player) -> int:
        have = 0
        if p.desiredSalary:
            have += 1
        if p.desiredBonus:
            have += 1
        if p.desiredLength:
            have += 1
        return -(have), -int(p.capHit)

    candidates.sort(key=score)
    return candidates[0] if candidates else None


def ensure_tiny_teams(teams_csv: str, out_path: str = os.path.join("output", "tiny_teams.csv")) -> None:
    if os.path.exists(out_path):
        return
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    rows = read_csv(teams_csv)
    if not rows:
        return
    # Copy header and up to 4 rows
    fieldnames = list(rows[0].keys())
    with open(out_path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fieldnames)
        w.writeheader()
        for r in rows[:4]:
            w.writerow({k: r.get(k, "") for k in fieldnames})


def main() -> None:
    ap = argparse.ArgumentParser(description="Verify cap math parity and produce a JSON report")
    ap.add_argument("--teams", default="docs/roster_cap_tool/data/MEGA_teams.csv", help="Teams CSV path")
    ap.add_argument("--players", default="docs/roster_cap_tool/data/MEGA_players.csv", help="Players CSV path")
    ap.add_argument("--fixtures", default="scripts/fixtures/cap_scenarios.json", help="Scenarios JSON path")
    ap.add_argument("--out", default="output/cap_tool_verification.json", help="Output JSON report path")
    args = ap.parse_args()

    teams_csv = args.teams if os.path.exists(args.teams) else "MEGA_teams.csv"
    players_csv = args.players if os.path.exists(args.players) else "MEGA_players.csv"

    teams = load_teams(teams_csv)
    players = load_players(players_csv)
    ensure_tiny_teams(teams_csv)

    # Load fixtures or create default
    if os.path.exists(args.fixtures):
        with open(args.fixtures, "r", encoding="utf-8") as fh:
            fixture = json.load(fh)
    else:
        # Create a minimal default fixture in-memory
        abbrs = [t.abbrName for t in teams[:2]] or ["SF", "CHI"]
        fixture = {
            "scenarios": [
                {"id": "basic_release_sign", "team": abbrs[0]},
                {"id": "extension_conversion", "team": abbrs[-1]},
                {"id": "trade_quick", "team": abbrs[0]},
            ]
        }

    # Prepare output
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    report: dict[str, Any] = {
        "generated_at": dt.datetime.now().isoformat(timespec="seconds"),
        "teams_csv": teams_csv,
        "players_csv": players_csv,
        "fixtures": args.fixtures if os.path.exists(args.fixtures) else "<in-memory default>",
        "scenarios": [],
        "assertions_passed": 0,
        "assertions_failed": 0,
    }

    def assert_eq(name: str, a: float, b: float, tol: float = 0.5) -> dict:
        ok = abs(a - b) <= tol
        if ok:
            report["assertions_passed"] += 1
        else:
            report["assertions_failed"] += 1
        return {"name": name, "pass": ok, "expected": round(b, 2), "actual": round(a, 2)}

    # Build alias map for players.team matching (players often store team "displayName")
    abbr_to_display = {t.abbrName: t.displayName for t in teams}

    for sc in fixture.get("scenarios", []):
        team_abbr = sc.get("team")
        team = find_team(teams, team_abbr) if team_abbr else None
        if not team:
            continue

        moves: list[dict] = []
        baseline = dc.asdict(calc_cap_summary(team, moves))
        prev_summary = baseline

        scenario_result = {
            "id": sc.get("id") or f"scenario_{team.abbrName}",
            "team": team.abbrName,
            "baseline": baseline,
            "ops": [],
            "final": None,
        }

        team_aliases = [team.abbrName]
        disp = abbr_to_display.get(team.abbrName)
        if disp:
            team_aliases.append(disp)

        # 1) Release
        p_rel = pick_player_for_release(players, team_aliases)
        if p_rel:
            rel = simulate_release(team, p_rel)
            moves.append(rel["move"])  # affects summary
            after = dc.asdict(calc_cap_summary(team, moves))
            scenario_result["ops"].append({
                "type": "release",
                "playerId": p_rel.id,
                "savings": rel["savings"],
                "penaltyCurrentYear": rel["penaltyCurrentYear"],
                "newCapSpacePreview": rel["newCapSpace"],
                "after": after,
                "assertions": [
                    assert_eq(
                        "capAvailable increased by savings",
                        a=after["capAvailable"] - prev_summary["capAvailable"],
                        b=rel["savings"],
                    )
                ],
            })
            prev_summary = after

        # 2) Quick trade
        p_tr = pick_player_for_release(players, team_aliases)  # similar requirements
        if p_tr:
            tr = simulate_trade_quick(team, p_tr)
            moves.append(tr["move"])  # affects summary
            after = dc.asdict(calc_cap_summary(team, moves))
            scenario_result["ops"].append({
                "type": "tradeQuick",
                "playerId": p_tr.id,
                "savings": tr["savings"],
                "penaltyCurrentYear": tr["penaltyCurrentYear"],
                "after": after,
                "assertions": [
                    assert_eq(
                        "capAvailable increased by savings (trade)",
                        a=after["capAvailable"] - prev_summary["capAvailable"],
                        b=tr["savings"],
                    )
                ],
            })
            prev_summary = after

        # 3) Extension
        p_ext = pick_player_for_extension(players, team_aliases)
        if p_ext:
            base_years = 4
            base_total = p_ext.contractSalary if (p_ext.contractSalary and p_ext.contractSalary > 0) else max(1.2 * p_ext.capHit * base_years, 1.0)
            base_bonus = p_ext.contractBonus if (p_ext.contractBonus and p_ext.contractBonus > 0) else 5_000_000.0
            ext = simulate_extension(p_ext, years=base_years, total_salary=base_total, signing_bonus=base_bonus)
            moves.append(ext["move"])  # affects summary
            after = dc.asdict(calc_cap_summary(team, moves))
            scenario_result["ops"].append({
                "type": "extend",
                "playerId": p_ext.id,
                "capHitDelta": ext["capHitDelta"],
                "after": after,
                "assertions": [
                    assert_eq(
                        "capAvailable changed by -capHitDelta (extension)",
                        a=after["capAvailable"] - prev_summary["capAvailable"],
                        b=-ext["capHitDelta"],
                    )
                ],
            })
            prev_summary = after

        # 4) Conversion
        p_conv = pick_player_for_conversion(players, team_aliases)
        if p_conv:
            convert_amt = max(0.3 * p_conv.capHit, 1_000_000.0)
            conv = simulate_conversion(p_conv, convert_amount=convert_amt, years_remaining=max(1, (p_conv.contractYearsLeft or 3)))
            moves.append(conv["move"])  # affects summary
            after = dc.asdict(calc_cap_summary(team, moves))
            scenario_result["ops"].append({
                "type": "convert",
                "playerId": p_conv.id,
                "capHitDelta": conv["capHitDelta"],
                "perYearProration": conv["perYearProration"],
                "after": after,
                "assertions": [
                    assert_eq(
                        "capAvailable changed by -capHitDelta (conversion)",
                        a=after["capAvailable"] - prev_summary["capAvailable"],
                        b=-conv["capHitDelta"],
                    )
                ],
            })
            prev_summary = after

        # 5) Signing
        p_fa = pick_free_agent(players)
        if p_fa:
            years = max(1, p_fa.desiredLength or 2)
            salary = max(1.0, (p_fa.desiredSalary or 3_000_000.0))
            bonus = max(0.0, (p_fa.desiredBonus or 1_000_000.0))
            sign = simulate_signing(team, p_fa, years=years, salary=salary, bonus=bonus)
            moves.append(sign["move"])  # affects summary
            after = dc.asdict(calc_cap_summary(team, moves))
            scenario_result["ops"].append({
                "type": "sign",
                "playerId": p_fa.id,
                "year1CapHit": sign["year1CapHit"],
                "warnLowball": sign["warnLowball"],
                "canSign": sign["canSign"],
                "after": after,
                "assertions": [
                    assert_eq(
                        "capAvailable decreased by year1CapHit (signing)",
                        a=after["capAvailable"] - prev_summary["capAvailable"],
                        b=-sign["year1CapHit"],
                    )
                ],
            })
            prev_summary = after

        scenario_result["final"] = prev_summary
        report["scenarios"].append(scenario_result)

    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=2)

    total_asserts = report["assertions_passed"] + report["assertions_failed"]
    print(
        f"Cap math verification complete: {report['assertions_passed']}/{total_asserts} assertions passed.\n"
        f"Report written to {args.out}"
    )

    if report["assertions_failed"] > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
