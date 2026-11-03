#!/usr/bin/env python3
"""Reproduce a leakage-aware review of archived MEGA game forecasts.

The script reads committed snapshots with ``git show`` and never checks out or
runs historical pipeline code. It writes only the requested match CSV and
summary report. Run from any directory with:

    python3 scripts/analyze_forecast_quality.py

By default, outputs go to ``analysis/forecast_quality/``.
"""

from __future__ import annotations

import argparse
import ast
import csv
import hashlib
import io
import json
import math
import random
import re
import subprocess
import sys
from collections import Counter, defaultdict
from datetime import date
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from mega.standings.records import calculate_team_stats

COMPLETE_STATUSES = {2, 3, 4}
REGULAR_SEASON_WEEKS = 18
TIE_EPSILON = 1e-9
BIN_EDGES = (0.5, 0.6, 0.7, 0.8, 0.9, 1.000000001)
# These are the exact M27 probability-source revisions inspected for this
# report. Unknown future formula hashes remain in the saved-forecast dataset
# but are not reconstructed until their logic is reviewed here.
SUPPORTED_MIXED_MODEL_VERSIONS = {
    "mixed-weekly-77272782dc82",
    "mixed-weekly-83eb8fb59b68",
    "mixed-weekly-d25866c15b30",
}


def git(*args: str, check: bool = True) -> bytes:
    result = subprocess.run(
        ["git", *args], cwd=ROOT, stdout=subprocess.PIPE,
        stderr=subprocess.PIPE, check=False,
    )
    if check and result.returncode:
        raise RuntimeError(result.stderr.decode("utf-8", "replace").strip())
    return result.stdout


@lru_cache(maxsize=4096)
def show(ref: str, path: str) -> bytes | None:
    result = git("show", f"{ref}:{path}", check=False)
    return result or None


@lru_cache(maxsize=4096)
def blob_id(ref: str, path: str) -> str:
    return git("rev-parse", f"{ref}:{path}", check=False).decode().strip()


@lru_cache(maxsize=1024)
def git_time(ref: str) -> str:
    return git("show", "-s", "--format=%cI", ref).decode().strip()


def rows_from_csv(raw: bytes | None) -> list[dict[str, str]]:
    if not raw:
        return []
    return list(csv.DictReader(io.StringIO(raw.decode("utf-8-sig"))))


def parse_json(raw: bytes | None) -> dict:
    return json.loads(raw.decode("utf-8-sig")) if raw else {}


def truth(value: object) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "y"}


def number(value: object, default: float | None = None) -> float | None:
    try:
        result = float(str(value).strip())
        return result if math.isfinite(result) else default
    except (TypeError, ValueError):
        return default


def source_default_season(source: bytes | None) -> int | None:
    if not source:
        return None
    try:
        tree = ast.parse(source.decode("utf-8"))
    except SyntaxError:
        return None
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) or node.name != "load_data":
            continue
        positional = list(node.args.posonlyargs) + list(node.args.args)
        for index, arg in enumerate(positional):
            if arg.arg != "season_index":
                continue
            default_offset = index - (len(positional) - len(node.args.defaults))
            if default_offset < 0:
                return None
            value = node.args.defaults[default_offset]
            return value.value if isinstance(value, ast.Constant) and isinstance(value.value, int) else None
    return None


def function_source(source: bytes | None, names: tuple[str, ...]) -> str:
    if not source:
        return ""
    try:
        tree = ast.parse(source.decode("utf-8"))
    except SyntaxError:
        return ""
    found = []
    wanted = set(names)
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name in wanted:
            found.append(ast.dump(node, include_attributes=False))
    return "\n".join(found)


def assignment_values(source: bytes | None, names: tuple[str, ...]) -> str:
    if not source:
        return ""
    try:
        tree = ast.parse(source.decode("utf-8"))
    except SyntaxError:
        return ""
    wanted = set(names)
    found = []
    for node in tree.body:
        if isinstance(node, (ast.Assign, ast.AnnAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            assigned = [t.id for t in targets if isinstance(t, ast.Name)]
            if any(name in wanted for name in assigned):
                found.append(ast.dump(node, include_attributes=False))
    return "\n".join(found)


def digest(text: str, length: int = 12) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:length]


def commit_snapshot_id(ref: str, metadata: dict) -> str:
    stored = metadata.get("snapshotId")
    if stored:
        return str(stored)
    paths = (
        "MEGA_games.csv", "MEGA_teams.csv", "MEGA_rankings.csv",
        "mega_elo.csv", "MEGA_elo.csv", "output/ranked_sos_by_conference.csv",
    )
    parts = []
    for path in paths:
        blob = blob_id(ref, path)
        if blob:
            parts.append(f"{path}:{blob}")
    return "gitsha256-" + digest("\n".join(parts), 16)


def saved_model_id(commit: str) -> str:
    report = show(commit, "scripts/team_scenario_report.py")
    calc = show(commit, "scripts/calc_playoff_probabilities.py")
    logic = function_source(report, ("calculate_game_probabilities",))
    tie = assignment_values(calc, ("TIE_PROBABILITY",))
    return "saved-gameprob-" + digest(logic + "\n" + tie)


def mixed_model_id(commit: str) -> tuple[str, bool]:
    calc = show(commit, "scripts/calc_playoff_probabilities.py")
    logic = function_source(
        calc,
        ("load_data", "simulate_remaining_games", "calculate_sov_rating",
         "get_streak_modifier", "is_divisional_game"),
    )
    constants = assignment_values(
        calc,
        ("TIE_PROBABILITY", "HOME_FIELD_ADVANTAGE", "WIN_STREAK_THRESHOLD",
         "WIN_STREAK_BONUS", "DIVISIONAL_REGRESSION", "ELO_WEIGHT",
         "WIN_PCT_WEIGHT", "SOS_WEIGHT", "SOV_WEIGHT", "DEFAULT_ELO"),
    )
    uses_performance_exclusion = bool(calc and b"excluded_game" in calc and b"performance_stats" in calc)
    records = show(commit, "mega/standings/records.py")
    model_id = "mixed-weekly-" + digest(logic + "\n" + constants + "\n" + (records or b"").decode("utf-8", "replace"))
    return model_id, uses_performance_exclusion


def identify_cycle(commit: str, scenario: dict) -> tuple[str, int | None, dict]:
    metadata = parse_json(show(commit, "docs/data/import_metadata.json"))
    if scenario.get("season_index") is not None:
        season = int(scenario["season_index"])
    elif metadata.get("seasonIndex") is not None:
        season = int(metadata["seasonIndex"])
    else:
        season = source_default_season(show(commit, "scripts/calc_playoff_probabilities.py"))
    if metadata.get("game") == "Madden 27":
        edition = "Madden 27"
    else:
        edition = "Madden 26"
    return edition, season, metadata


def elo_source(commit: str, metadata: dict) -> tuple[dict[str, float], int | None, str, str]:
    paths = ("mega_elo.csv", "MEGA_elo.csv")
    selected = next(((path, show(commit, path)) for path in paths if show(commit, path)), ("", None))
    path, raw = selected
    if not raw:
        return {}, None, "", ""
    reader = csv.DictReader(io.StringIO(raw.decode("utf-8-sig")))
    fieldnames = reader.fieldnames or []
    declared = number(metadata.get("eloSourceWeek"))
    candidates = []
    for field in fieldnames:
        match = re.fullmatch(r"\s*Week\s+(\d+)\+\s*", field, re.IGNORECASE)
        if match:
            candidates.append((int(match.group(1)), field))
    if declared is not None:
        target = (int(declared), f"Week {int(declared)}+")
        source_week, column = target
        if column not in fieldnames:
            matching = next((item for item in candidates if item[0] == source_week), None)
            if not matching:
                return {}, source_week, path, ""
            source_week, column = matching
    elif candidates:
        source_week, column = max(candidates)
    else:
        return {}, None, path, ""
    ratings = {}
    for row in csv.DictReader(io.StringIO(raw.decode("utf-8-sig"))):
        team = str(row.get("Team", "")).strip()
        rating = number(row.get(column))
        if team and rating is not None:
            ratings[team] = rating
    blob = blob_id(commit, path)
    return ratings, source_week, path, f"{source_week}+@{blob[:12]}"


def bool_game_rows(commit: str, season: int) -> list[dict]:
    result = []
    for row in rows_from_csv(show(commit, "MEGA_games.csv")):
        if int(row.get("seasonIndex", -1) or -1) != season:
            continue
        if int(row.get("stageIndex", -1) or -1) != 1:
            continue
        status = int(row.get("status", 1) or 1)
        result.append({
            **row,
            "home": str(row.get("homeTeam", "")).strip(),
            "away": str(row.get("awayTeam", "")).strip(),
            "home_score": int(number(row.get("homeScore"), 0.0) or 0.0),
            "away_score": int(number(row.get("awayScore"), 0.0) or 0.0),
            "week_index": int(row.get("weekIndex", 0) or 0),
            "status_int": status,
            "completed": status in COMPLETE_STATUSES,
            "home_score_num": number(row.get("homeScore"), 0.0) or 0.0,
            "away_score_num": number(row.get("awayScore"), 0.0) or 0.0,
            "force_win": truth(row.get("home_fw")) or truth(row.get("away_fw")),
        })
    return result


def matchup_index(rows: list[dict]) -> dict[tuple[str, str, int], list[dict]]:
    result: dict[tuple[str, str, int], list[dict]] = defaultdict(list)
    for row in rows:
        result[(row["home"], row["away"], row["week_index"] + 1)].append(row)
    return result


def probability_entry(scenario: dict, team: str, opponent: str, home: bool, week: int) -> dict | None:
    team_data = scenario.get("teams", {}).get(team, {})
    for item in team_data.get("remaining_games", []):
        if (item.get("opponent") == opponent and bool(item.get("is_home")) == home
                and int(item.get("week", -999)) == week):
            return item
    return None


def outcome_label(row: dict) -> str:
    home_score = row["home_score_num"]
    away_score = row["away_score_num"]
    if home_score > away_score:
        return "home_win"
    if away_score > home_score:
        return "away_win"
    return "tie"


def logistic_elo(home_elo: float, away_elo: float, bonus: float) -> float:
    exponent = (away_elo - home_elo - bonus) / 400.0
    return 1.0 / (1.0 + 10.0 ** exponent)


def model_mixed_home_probability(
    home: str,
    away: str,
    teams_info: dict,
    perf_stats: dict,
    official_stats: dict,
    rankings: dict[str, int],
    home_elo: float,
    away_elo: float,
    uses_performance_exclusion: bool,
) -> float:
    """Reconstruct the committed mixed-model probability without old code."""
    win_pct_source = perf_stats if uses_performance_exclusion else official_stats
    hstat, astat = win_pct_source[home], win_pct_source[away]
    sov_source = perf_stats if uses_performance_exclusion else official_stats
    h_elo = max(0.0, min(1.0, (home_elo - 1000.0) / 400.0))
    a_elo = max(0.0, min(1.0, (away_elo - 1000.0) / 400.0))

    def sov(team: str) -> float:
        opponents = sov_source[team]["defeated_opponents"]
        if not opponents:
            return 0.5
        avg_rank = sum(rankings.get(other, 16) for other in opponents) / len(opponents)
        return 1.0 - (avg_rank - 1) / 31.0

    home_rating = (
        h_elo * 0.50 + hstat["win_pct"] * 0.25
        + teams_info[home]["past_sos"] * 0.15 + sov(home) * 0.10
    )
    away_rating = (
        a_elo * 0.50 + astat["win_pct"] * 0.25
        + teams_info[away]["past_sos"] * 0.15 + sov(away) * 0.10
    )
    home_probability = home_rating / (home_rating + away_rating) if home_rating + away_rating > 0 else 0.5

    def streak_modifier(streak: int) -> float:
        if streak >= 3:
            return 0.03
        if streak <= -3:
            return -0.03
        return 0.0

    home_probability += 0.02
    home_probability += streak_modifier(teams_info[home]["streak"])
    home_probability -= streak_modifier(teams_info[away]["streak"])
    if teams_info[home]["division"] == teams_info[away]["division"] and teams_info[home]["division"]:
        home_probability += (0.5 - home_probability) * 0.15
    return max(0.25, min(0.75, home_probability))


def reconstruct_mixed(
    commit: str,
    season: int,
    game: dict,
    metadata: dict,
    elo_ratings: dict[str, float],
    uses_performance_exclusion: bool,
) -> tuple[float | None, str]:
    if not elo_ratings:
        return None, ""
    teams = {}
    for row in rows_from_csv(show(commit, "MEGA_teams.csv")):
        name = str(row.get("displayName", "")).strip()
        if not name:
            continue
        streak = int(number(row.get("winLossStreak"), 0) or 0)
        if streak > 127:
            streak -= 256
        teams[name] = {
            "conference": str(row.get("conferenceName", "")).strip(),
            "division": str(row.get("divisionName", "")).strip(),
            "streak": streak,
        }
    if game["home"] not in teams or game["away"] not in teams:
        return None, "missing_team_metadata"

    games = bool_game_rows(commit, season)
    if any(row["completed"] and row["week_index"] > game["week_index"] for row in games):
        return None, "snapshot contains completed results after target week"
    official_stats = calculate_team_stats(teams, games)
    performance_games = [row for row in games if not row["force_win"]]
    perf_stats = calculate_team_stats(teams, performance_games)
    rankings: dict[str, int] = {}
    max_week: dict[str, int] = {}
    max_completed_week = max((row["week_index"] for row in games if row["completed"]), default=-1)
    for row in rows_from_csv(show(commit, "MEGA_rankings.csv")):
        if int(row.get("seasonIndex", 0) or 0) != season or not row.get("rank"):
            continue
        team = str(row.get("team", "")).strip()
        week = int(row.get("weekIndex", 0) or 0)
        if week > max_completed_week:
            continue
        rank = int(row.get("rank", 16) or 16)
        if team not in max_week or week > max_week[team]:
            max_week[team] = week
            rankings[team] = rank

    sos = {}
    for row in rows_from_csv(show(commit, "output/ranked_sos_by_conference.csv")):
        team = str(row.get("team", "")).strip()
        value = number(row.get("past_ranked_sos_avg"))
        if team and value is not None:
            sos[team] = value
    for team in teams:
        teams[team]["past_sos"] = sos.get(team, 0.5)

    h_elo = elo_ratings.get(game["home"], 1200.0)
    a_elo = elo_ratings.get(game["away"], 1200.0)
    p = model_mixed_home_probability(
        game["home"], game["away"], teams, perf_stats, official_stats,
        rankings, h_elo, a_elo, uses_performance_exclusion,
    )
    return p, ""


def wilson_interval(wins: int, n: int, z: float = 1.959963984540054) -> tuple[float, float] | None:
    if n <= 0:
        return None
    p = wins / n
    denom = 1.0 + z * z / n
    center = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return max(0.0, center - half), min(1.0, center + half)


def metrics(rows: list[tuple[float, int]]) -> dict:
    n = len(rows)
    if not n:
        return {"n": 0}
    wins = sum(y for _, y in rows)
    return {
        "n": n,
        "mean_p": sum(p for p, _ in rows) / n,
        "actual": wins / n,
        "wilson": wilson_interval(wins, n),
        "brier": sum((p - y) ** 2 for p, y in rows) / n,
        "log_loss": sum(-math.log(max(1e-15, p if y else 1 - p)) for p, y in rows) / n,
    }


def calibration_bins(rows: list[tuple[float, int]]) -> list[tuple[str, dict]]:
    result = []
    labels = ("50–60%", "60–70%", "70–80%", "80–90%", "90–100%")
    for index, label in enumerate(labels):
        lo, hi = BIN_EDGES[index], BIN_EDGES[index + 1]
        group = [(p, y) for p, y in rows if lo <= p < hi]
        if group:
            result.append((label, metrics(group)))
    return result


def bootstrap_delta(
    rows: list[tuple[float, float, int]], seed: int = 0, iterations: int = 10000,
) -> dict:
    """Paired 95% bootstrap CI for loss(+75) minus loss(0)."""
    if not rows:
        return {"n": 0}
    delta_brier = [(p75 - y) ** 2 - (p0 - y) ** 2 for p0, p75, y in rows]
    delta_log = [
        -math.log(max(1e-15, p75 if y else 1 - p75))
        + math.log(max(1e-15, p0 if y else 1 - p0))
        for p0, p75, y in rows
    ]
    rng = random.Random(seed)
    boot_brier, boot_log = [], []
    n = len(rows)
    for _ in range(iterations):
        indices = [rng.randrange(n) for _ in range(n)]
        boot_brier.append(sum(delta_brier[i] for i in indices) / n)
        boot_log.append(sum(delta_log[i] for i in indices) / n)
    boot_brier.sort()
    boot_log.sort()
    q_low = int(0.025 * iterations)
    q_high = min(iterations - 1, int(0.975 * iterations))
    return {
        "n": n,
        "mean_brier_delta": sum(delta_brier) / n,
        "brier_ci": (boot_brier[q_low], boot_brier[q_high]),
        "mean_log_loss_delta": sum(delta_log) / n,
        "log_loss_ci": (boot_log[q_low], boot_log[q_high]),
    }


def percent(value: float | None, digits: int = 1) -> str:
    if value is None:
        return "—"
    return f"{100 * value:.{digits}f}%"


def metric_rows_from_records(records: list[dict], probability_key: str, outcome_key: str = "favorite_won") -> list[tuple[float, int]]:
    result = []
    for row in records:
        p, y = row.get(probability_key), row.get(outcome_key)
        if p is not None and y is not None:
            result.append((float(p), int(y)))
    return result


def build_calibration_table(records: list[dict], key: str) -> str:
    lines = ["| Диапазон прогноза | n | Средний прогноз | Победы | 95% интервал |", "|---|---:|---:|---:|---:|"]
    values = metric_rows_from_records(records, key)
    for label, summary in calibration_bins(values):
        low, high = summary["wilson"]
        lines.append(
            f"| {label} | {summary['n']} | {percent(summary['mean_p'])} "
            f"| {percent(summary['actual'])} | {percent(low)}–{percent(high)} |"
        )
    if len(lines) == 2:
        lines.append("| Нет оценённых матчей | 0 | — | — | — |")
    return "\n".join(lines)


def score_group(records: list[dict], field: str) -> list[tuple[float, int]]:
    return metric_rows_from_records(records, field)


def grouped_records(records: list[dict], predicate) -> dict[tuple, list[dict]]:
    groups: dict[tuple, list[dict]] = defaultdict(list)
    for record in records:
        if predicate(record):
            groups[record["group_key"]].append(record)
    return groups


def create_candidates(
    snapshots: list[str], final_games: dict[str, dict[tuple, dict]],
) -> tuple[dict[tuple, dict], Counter, Counter, dict[str, int]]:
    candidates: dict[tuple, list[dict]] = defaultdict(list)
    exclusions = Counter()
    snapshot_counts = Counter()
    per_cycle_snapshots = Counter()
    for commit in snapshots:
        scenario = parse_json(show(commit, "output/team_scenarios.json"))
        game_source = show(commit, "MEGA_games.csv")
        if not scenario or not game_source:
            exclusions["snapshot_missing_scenario_or_games"] += 1
            continue
        edition, season, metadata = identify_cycle(commit, scenario)
        if season is None:
            exclusions["snapshot_missing_season_index"] += 1
            continue
        scenario_rows = bool_game_rows(commit, season)
        if not scenario_rows:
            exclusions["snapshot_no_regular_schedule_rows"] += 1
            continue
        snapshot_counts[edition] += 1
        per_cycle_snapshots[edition] += 1
        schedule = matchup_index(scenario_rows)
        elo, source_week, elo_path, elo_version = elo_source(commit, metadata)
        saved_version = saved_model_id(commit)
        mixed_version, excludes_fw = mixed_model_id(commit)
        generated_at = str(scenario.get("generated_at") or "")
        commit_timestamp = git_time(commit)
        snapshot_id = commit_snapshot_id(commit, metadata)
        scenario_text = show(commit, "output/team_scenarios.json") or b""
        run_key = (commit, snapshot_id, generated_at, hashlib.sha256(scenario_text).hexdigest())

        for home, team_data in scenario.get("teams", {}).items():
            for prediction in team_data.get("remaining_games", []):
                if not bool(prediction.get("is_home")):
                    continue
                away = str(prediction.get("opponent", "")).strip()
                week = int(prediction.get("week", -1))
                matching = [row for row in schedule.get((home, away, week), []) if not row["completed"]]
                if len(matching) != 1:
                    exclusions["forecast_schedule_unlinked_or_ambiguous"] += 1
                    continue
                source_game = matching[0]
                game_id = str(source_game.get("id", "")).strip()
                key = (edition, season, int(source_game.get("stageIndex", 1)), game_id)
                final = final_games.get(edition, {}).get(key)
                home_forecast = prediction
                away_forecast = probability_entry(scenario, away, home, False, week)
                if not away_forecast:
                    exclusions["forecast_missing_away_mirror"] += 1
                    continue
                values = {
                    "win_prob": number(home_forecast.get("win_prob")),
                    "tie_prob": number(home_forecast.get("tie_prob")),
                    "loss_prob": number(home_forecast.get("loss_prob")),
                    "away_win_prob": number(away_forecast.get("win_prob")),
                    "away_tie_prob": number(away_forecast.get("tie_prob")),
                    "away_loss_prob": number(away_forecast.get("loss_prob")),
                }
                if any(value is None for value in values.values()):
                    exclusions["forecast_missing_probability"] += 1
                    continue
                if (abs(values["win_prob"] - values["away_loss_prob"]) > 0.21
                        or abs(values["tie_prob"] - values["away_tie_prob"]) > 0.21):
                    exclusions["forecast_mirrors_disagree"] += 1
                    continue
                candidate = {
                    "key": key,
                    "edition": edition,
                    "season_index": season,
                    "stage_index": int(source_game.get("stageIndex", 1)),
                    "game_id": game_id,
                    "game_id_external": str(source_game.get("gameId", "")),
                    "home": home,
                    "away": away,
                    "week_index": source_game["week_index"],
                    "display_week": week,
                    "source_status": source_game["status_int"],
                    "generated_at": generated_at,
                    "forecast_commit": commit,
                    "forecast_commit_time": commit_timestamp,
                    "forecast_snapshot_id": snapshot_id,
                    "source_game_blob": blob_id(commit, "MEGA_games.csv"),
                    "saved_model_version": saved_version,
                    "saved_model_label": "team_scenario_report.calculate_game_probabilities",
                    "saved_home_win_raw": values["win_prob"] / 100.0,
                    "saved_tie": values["tie_prob"] / 100.0,
                    "saved_home_loss_raw": values["loss_prob"] / 100.0,
                    "saved_home_win_conditional": values["win_prob"] / (values["win_prob"] + values["loss_prob"]),
                    "saved_away_win_conditional": values["away_win_prob"] / (values["away_win_prob"] + values["away_loss_prob"]),
                    "elo_source_week": source_week,
                    "elo_source_path": elo_path,
                    "elo_source_version": elo_version,
                    "home_elo": elo.get(home),
                    "away_elo": elo.get(away),
                    "mixed_model_version": mixed_version,
                    "mixed_excludes_forcewins": excludes_fw,
                    "source_game": source_game,
                    "terminal_result": final,
                    "run_key": run_key,
                }
                candidates[key].append(candidate)

    selected = {}
    for key, choices in candidates.items():
        # Collapse exact copies of a generated snapshot, but count later
        # regenerations as repeat observations and select the freshest one.
        unique: dict[tuple, dict] = {}
        for item in choices:
            unique[(item["run_key"], item["saved_home_win_raw"])] = item
        ordered = list(unique.values())
        for item in ordered:
            item["forecast_snapshots_seen_for_game"] = len(ordered)
        selected[key] = max(ordered, key=lambda x: (x["generated_at"], x["forecast_commit_time"]))
        selected[key]["forecast_snapshots_seen_for_game"] = len(ordered)
    return selected, exclusions, snapshot_counts, per_cycle_snapshots


def actual_source_rows() -> tuple[dict[str, dict[tuple, dict]], dict[str, dict]]:
    head = git("rev-parse", "HEAD").decode().strip()
    final_commit_by_edition = {"Madden 27": head}
    archive_manifest = parse_json(show(head, "archive/madden-26/manifest.json"))
    m26_source = str(archive_manifest.get("source_commit") or "4a5ee61")
    final_commit_by_edition["Madden 26"] = m26_source
    final = {}
    metadata_by_edition = {}
    for edition, commit in final_commit_by_edition.items():
        raw = show(commit, "MEGA_games.csv")
        if not raw and edition == "Madden 26":
            raw = show(commit, "archive/madden-26/MEGA_games.csv")
        all_rows = rows_from_csv(raw)
        indexed = {}
        for row in all_rows:
            if int(row.get("stageIndex", -1) or -1) != 1:
                continue
            season = int(row.get("seasonIndex", -1) or -1)
            game_id = str(row.get("id", "")).strip()
            indexed[(edition, season, int(row.get("stageIndex", 1)), game_id)] = {
                **row,
                "home": str(row.get("homeTeam", "")).strip(),
                "away": str(row.get("awayTeam", "")).strip(),
                "week_index": int(row.get("weekIndex", 0) or 0),
                "status_int": int(row.get("status", 1) or 1),
                "completed": int(row.get("status", 1) or 1) in COMPLETE_STATUSES,
                "home_score_num": number(row.get("homeScore"), 0.0) or 0.0,
                "away_score_num": number(row.get("awayScore"), 0.0) or 0.0,
                "force_win": truth(row.get("home_fw")) or truth(row.get("away_fw")),
            }
        final[edition] = indexed
        metadata_by_edition[edition] = parse_json(show(commit, "docs/data/import_metadata.json"))
    return final, {
        edition: {
            "commit": commit,
            "snapshot_id": commit_snapshot_id(commit, metadata_by_edition[edition]),
            "metadata": metadata_by_edition[edition],
            "commit_time": git_time(commit),
        }
        for edition, commit in final_commit_by_edition.items()
    }


def materialize_records(
    selected: dict[tuple, dict], final_meta: dict[str, dict],
) -> tuple[list[dict], Counter]:
    result = []
    counts = Counter()
    for key, pred in selected.items():
        edition, season, stage, game_id = key
        actual = pred.get("terminal_result")
        if not actual:
            counts["missing_terminal_game"] += 1
            continue
        if not actual["completed"]:
            counts["pending_no_result"] += 1
            continue
        if actual["home"] != pred["home"] or actual["away"] != pred["away"]:
            counts["terminal_identity_mismatch"] += 1
            continue
        home_score, away_score = actual["home_score_num"], actual["away_score_num"]
        result_label = outcome_label(actual)
        is_tie = result_label == "tie"
        force_win = actual["force_win"]
        phase = "regular" if pred["week_index"] < REGULAR_SEASON_WEEKS else "postseason"
        decisive = not is_tie
        home_cond = pred["saved_home_win_conditional"]
        away_cond = pred["saved_away_win_conditional"]
        home_is_favorite = home_cond >= away_cond
        favorite_probability = home_cond if home_is_favorite else away_cond
        favorite_won = None if is_tie else int((result_label == "home_win") == home_is_favorite)
        source_week = pred["elo_source_week"]
        elo_timely = source_week is not None and pred["display_week"] > source_week
        elo_available = pred["home_elo"] is not None and pred["away_elo"] is not None
        p_elo_0 = p_elo_75 = None
        if elo_timely and elo_available:
            p_elo_0 = logistic_elo(pred["home_elo"], pred["away_elo"], 0.0)
            p_elo_75 = logistic_elo(pred["home_elo"], pred["away_elo"], 75.0)
        mixed_home = None
        mixed_reason = ""
        if edition == "Madden 27":
            if pred["mixed_model_version"] not in SUPPORTED_MIXED_MODEL_VERSIONS:
                mixed_reason = "unsupported model source hash"
                counts["mixed_version_unsupported"] += 1
            else:
                mixed_home, mixed_reason = reconstruct_mixed(
                    pred["forecast_commit"], season, pred["source_game"],
                    parse_json(show(pred["forecast_commit"], "docs/data/import_metadata.json")),
                    ({pred["home"]: pred["home_elo"], pred["away"]: pred["away_elo"]}
                     if elo_available else {}),
                    pred["mixed_excludes_forcewins"],
                )
                if mixed_home is None:
                    counts["mixed_reconstruction_unavailable"] += 1
        if edition == "Madden 27" and mixed_home is not None:
            counts["mixed_reconstructed"] += 1
        mixed_fav = max(mixed_home, 1.0 - mixed_home) if mixed_home is not None else None
        mixed_home_is_fav = mixed_home is not None and mixed_home >= 0.5
        mixed_fav_won = None if is_tie or mixed_home is None else int((result_label == "home_win") == mixed_home_is_fav)
        exclusion = ""
        if force_win:
            exclusion = "Force Win: договорное решение исключено из performance выборки"
        elif is_tie:
            exclusion = "Ничья: исключена из бинарных метрик; учитывается отдельно"
        elif phase != "regular":
            exclusion = "Плей-офф: отдельно от регулярной калибровки"
        elo_exclusion = ""
        if not elo_timely:
            elo_exclusion = "ELO snapshot не предшествует матчу"
        elif not elo_available:
            elo_exclusion = "Нет обоих ELO рейтингов в исходном snapshot"
        group_version = pred["mixed_model_version"] if edition == "Madden 27" else pred["saved_model_version"]
        record = {
            **pred,
            "home_score": home_score,
            "away_score": away_score,
            "actual_result": result_label,
            "force_win": force_win,
            "is_tie": is_tie,
            "phase": phase,
            "decisive": decisive,
            "favorite_team": pred["home"] if home_is_favorite else pred["away"],
            "favorite_probability": favorite_probability,
            "favorite_won": favorite_won,
            "saved_home_win_conditional": home_cond,
            "saved_favorite_probability": favorite_probability,
            "saved_favorite_won": favorite_won,
            "elo_home_p_0": p_elo_0,
            "elo_home_p_75": p_elo_75,
            "mixed_home_probability": mixed_home,
            "mixed_favorite_probability": mixed_fav,
            "mixed_favorite_won": mixed_fav_won,
            "mixed_reconstruction_note": mixed_reason,
            "mixed_version_label": (
                "mixed model; Force Wins excluded from performance inputs"
                if pred["mixed_excludes_forcewins"] else
                "mixed model; official W-L inputs include Force Wins"
            ),
            "elo_timing_eligible": elo_timely,
            "elo_scored_eligible": bool(p_elo_0 is not None and decisive and not force_win and phase == "regular"),
            "performance_eligible": bool(decisive and not force_win and phase == "regular"),
            "exclusion_reason": exclusion,
            "elo_exclusion_reason": elo_exclusion,
            "actual_commit": final_meta[edition]["commit"],
            "actual_snapshot_id": final_meta[edition]["snapshot_id"],
            "actual_commit_time": final_meta[edition]["commit_time"],
            "group_key": (edition, season, pred["saved_model_version"], phase),
            "elo_group_key": (edition, season, source_week, phase),
            "mixed_group_key": (edition, season, pred["mixed_model_version"], phase),
        }
        result.append(record)
        counts["completed_unique"] += 1
        if force_win:
            counts["force_win_excluded"] += 1
        elif is_tie:
            counts["ties_separate"] += 1
        elif phase == "postseason":
            counts["postseason_separate"] += 1
        else:
            counts["regular_decisive"] += 1
        if p_elo_0 is None:
            counts["elo_not_scored"] += 1
        else:
            counts["elo_available"] += 1
    return result, counts


def fmt_metric(summary: dict) -> str:
    if not summary.get("n"):
        return "n=0"
    low, high = summary["wilson"]
    return (
        f"n={summary['n']}, прогноз {percent(summary['mean_p'])}, "
        f"победы {percent(summary['actual'])} (95% ДИ {percent(low)}–{percent(high)}), "
        f"Brier {summary['brier']:.3f}, log loss {summary['log_loss']:.3f}"
    )


def build_report(
    records: list[dict], snapshot_counts: Counter, exclusions: Counter,
    result_counts: Counter, final_meta: dict[str, dict],
) -> str:
    date_stamp = date.today().isoformat()
    m27_meta = final_meta["Madden 27"]["metadata"]
    summary_groups = defaultdict(list)
    mixed_groups = defaultdict(list)
    elo_groups: dict[tuple, dict[int, list[tuple[float, int]]]] = defaultdict(lambda: {0: [], 75: []})
    for row in records:
        if row["performance_eligible"]:
            summary_groups[row["group_key"]].append(row)
            if row["mixed_favorite_probability"] is not None:
                mixed_groups[row["mixed_group_key"]].append(row)
        if row["elo_scored_eligible"]:
            key = row["elo_group_key"]
            y_home = int(row["actual_result"] == "home_win")
            elo_groups[key][0].append((row["elo_home_p_0"], y_home))
            elo_groups[key][75].append((row["elo_home_p_75"], y_home))

    paired_models: dict[tuple, dict[str, list[tuple[float, int]]]] = defaultdict(lambda: defaultdict(list))
    for row in records:
        if not row["elo_scored_eligible"]:
            continue
        outcome_home = int(row["actual_result"] == "home_win")
        base_key = (row["edition"], row["season_index"], row["elo_source_week"], row["mixed_model_version"] if row["edition"] == "Madden 27" else row["saved_model_version"])
        paired_models[base_key]["saved"].append((row["saved_home_win_conditional"], outcome_home))
        paired_models[base_key]["elo_0"].append((row["elo_home_p_0"], outcome_home))
        paired_models[base_key]["elo_75"].append((row["elo_home_p_75"], outcome_home))
        if row["edition"] == "Madden 27" and row["mixed_home_probability"] is not None:
            paired_models[base_key]["mixed"].append((row["mixed_home_probability"], outcome_home))
    duplicate_snapshots = sum(max(0, row["forecast_snapshots_seen_for_game"] - 1) for row in records)

    lines = [
        f"# MEGA прогнозы: ретроспективная проверка ({date_stamp})",
        "",
        "## Короткий вывод",
        "",
        "В Git сохранились реальные вероятности исхода будущих матчей в `output/team_scenarios.json`. "
        "Это не опубликованные вероятности победы в плей-офф или Супербоуле. Восстановлены только те "
        "матчи, где расписание в том же committed snapshot ещё имело незавершённый статус; повторные "
        "прогнозы сведены к одному на игру — самому позднему по `generated_at`.",
        "",
        f"В оценке регулярного сезона: Madden 26 — {sum(1 for r in records if r['edition']=='Madden 26' and r['performance_eligible'])} "
        f"уникальных игр в двух отдельных сезонах; Madden 27 — {sum(1 for r in records if r['edition']=='Madden 27' and r['performance_eligible'])}. "
        "На Madden 27 выборка ещё мала для уверенного вывода о точности диапазонов 60–70% и тем более для оценки чемпионских шансов.",
        "",
        "Домашний ELO +75 не получил устойчивого подтверждения: в Madden 27 на 44 одних и тех же "
        "регулярных матчах ELO без бонуса дал меньший Brier и log loss, а в Madden 26, сезон 2, "
        "на отдельной выборке из 64 матчей +75 оказался немного лучше. Интервалы широкие; менять "
        "параметр по этим данным нельзя.",
        "",
        "## Качество сохранённых прогнозов матчей",
        "",
        "Каждая игра считается один раз. В таблице калибровки вероятность берётся со стороны "
        "фаворита, условно на отсутствие ничьей; результат — победа фаворита. Поэтому процент "
        "побед можно сопоставлять напрямую с диапазоном прогноза. Интервалы — Wilson 95%; Brier "
        "и log loss считаются по решённым матчам; эталон 50/50 имеет Brier 0.250 и log loss 0.693. "
        "Интервалы и paired bootstrap рассчитаны на уровне игр без поправки на повторное участие "
        "тех же команд, поэтому неопределённость может быть занижена.",
        "",
        "Сохранённый `win_prob` в team scenarios — per-game прогноз с 70% веса победного процента "
        "и 30% past SoS, домашней вероятностью, ограниченной 25–75%, и ничьей 0.3%. Это не та же "
        "вероятность, которую выдаёт текущая смешанная симуляция в `calc_playoff_probabilities.py`; "
        "поэтому ниже они проверяются раздельно.",
        "",
    ]

    for group, group_records in sorted(summary_groups.items(), key=lambda item: item[0]):
        edition, season, version, phase = group
        if phase != "regular":
            continue
        values = metric_rows_from_records(group_records, "saved_favorite_probability", "saved_favorite_won")
        summary = metrics(values)
        lines.extend([
            f"### {edition}, seasonIndex={season} — сохранённый прогноз `{version}`",
            "",
            f"Модель версии: `{group_records[0]['saved_model_label']}`; реализация определена по функции "
            "из того же Git snapshot. Число сценариев, отброшенных как повторные, приведено ниже.",
            "",
            f"Итого: {fmt_metric(summary)}. 50/50: Brier 0.250, log loss 0.693.",
            "",
            build_calibration_table(group_records, "saved_favorite_probability"),
            "",
        ])

    if mixed_groups:
        lines.extend([
            "## Реконструкция текущей смешанной модели Madden 27",
            "",
            "Эти вероятности не публиковались в историческом JSON. Они независимо восстановлены из "
            "командных, ELO, рейтинговых и SoS файлов того же snapshot по формуле "
            "`calc_playoff_probabilities.py`; это отдельный hindsight ряд, не подмена сохранённых прогнозов. "
            "Версии разделены по hash логики исходного snapshot. По исходникам эта модель смешивает "
            "нормализованный ELO (50%), W-L (25%), past SoS (15%) и SoV (10%), добавляет домашние 2 "
            "процентных пункта и streak поправку, затем ограничивает вероятность 25–75%. Часть "
            "версий включает Force Win в W-L/SOV, более поздняя версия исключает их из performance входов.",
            "",
        ])
        for group, group_records in sorted(mixed_groups.items(), key=lambda item: item[0]):
            edition, season, version, phase = group
            values = metric_rows_from_records(group_records, "mixed_favorite_probability", "mixed_favorite_won")
            summary = metrics(values)
            lines.extend([
                f"### {edition}, seasonIndex={season} — `{version}`",
                "",
                f"{group_records[0]['mixed_version_label']}. Итого: {fmt_metric(summary)}. "
                "50/50: Brier 0.250, log loss 0.693.",
                "",
                build_calibration_table(group_records, "mixed_favorite_probability"),
                "",
            ])

    lines.extend([
        "## Домашний бонус ELO: одинаковая выборка для 0 и +75",
        "",
        "Обе версии используют рейтинги из того же snapshot, только если рейтинг был доступен до "
        "недели матча: `display_week > source_week`. Вероятность дома — `1/(1+10^((away-home-bonus)/400))`. "
        "Сравниваются только решённые, не Force Win матчи регулярного сезона; различия Brier/log loss "
        "даны как `+75 минус 0` с парным bootstrap 95% интервалом. Ни коэффициент, ни бонус не подбирались.",
        "",
        "| Цикл и сезон | Рейтинг | n | ELO 0: Brier / log loss | ELO +75: Brier / log loss | Δ Brier +75−0 (95% ДИ) | Δ log loss +75−0 (95% ДИ) |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ])
    for key, alternatives in sorted(elo_groups.items(), key=lambda item: item[0]):
        edition, season, source_week, phase = key
        if phase != "regular" or not alternatives[0]:
            continue
        m0, m75 = metrics(alternatives[0]), metrics(alternatives[75])
        paired = []
        for row in records:
            if row["elo_group_key"] != key or not row["elo_scored_eligible"]:
                continue
            y = int(row["actual_result"] == "home_win")
            paired.append((row["elo_home_p_0"], row["elo_home_p_75"], y))
        delta = bootstrap_delta(paired)
        lines.append(
            f"| {edition}, seasonIndex={season} | Week {source_week}+ | {m0['n']} "
            f"| {m0['brier']:.3f} / {m0['log_loss']:.3f} "
            f"| {m75['brier']:.3f} / {m75['log_loss']:.3f} "
            f"| {delta['mean_brier_delta']:+.3f} ({delta['brier_ci'][0]:+.3f}, {delta['brier_ci'][1]:+.3f}) "
            f"| {delta['mean_log_loss_delta']:+.3f} ({delta['log_loss_ci'][0]:+.3f}, {delta['log_loss_ci'][1]:+.3f}) |"
        )
    if not any(key[3] == "regular" and values[0] for key, values in elo_groups.items()):
        lines.append("| Подходящей выборки пока нет | — | 0 | — | — | — | — |")
    lines.extend([
        "",
        "### Сопоставление на точных ELO-eligible матчах",
        "",
        "Все строки внутри одной группы используют те же игры и тот же результат дома; baseline — 50/50.",
        "",
        "| Цикл/сезон | Week ELO | Версия snapshot | Модель | n | Brier | Log loss |",
        "|---|---:|---|---|---:|---:|---:|",
    ])
    for key, alternatives in sorted(paired_models.items(), key=lambda item: item[0]):
        edition, season, source_week, version = key
        for model_name in ("saved", "mixed", "elo_0", "elo_75"):
            values = alternatives.get(model_name, [])
            if not values:
                continue
            summary = metrics(values)
            label = {
                "saved": "сохранённый per-game прогноз",
                "mixed": "смешанная реконструкция",
                "elo_0": "чистый ELO, бонус 0",
                "elo_75": "чистый ELO, бонус +75",
            }[model_name]
            saved_version = next((r["saved_model_version"] for r in records if r["elo_group_key"] == (edition, season, source_week, "regular") and r["mixed_model_version"] == version), version)
            version_label = f"saved `{saved_version}` / snapshot `{version}`" if edition == "Madden 27" else f"saved `{saved_version}`"
            lines.append(
                f"| {edition}, s{season} | {source_week}+ | {version_label} | {label} "
                f"| {summary['n']} | {summary['brier']:.3f} | {summary['log_loss']:.3f} |"
            )
    lines.extend([
        "",
        "Нулевая дельта означает равные результаты; положительная дельта хуже для +75. При широкой "
        "неопределённости эта ретроспектива не доказывает, что бонус не нужен, но не поддерживает "
        "его как уже подтверждённую константу.",
        "",
        "## Плей-офф и Супербоул",
        "",
    ])
    postseason = [r for r in records if r["phase"] == "postseason" and not r["force_win"] and not r["is_tie"]]
    m27_postseason = [r for r in records if r["edition"] == "Madden 27" and r["phase"] == "postseason"]
    terminal_m26 = rows_from_csv(show(final_meta["Madden 26"]["commit"], "MEGA_games.csv"))
    postseason_by_season: dict[int, list[dict]] = defaultdict(list)
    for row in terminal_m26:
        if int(row.get("stageIndex", -1) or -1) == 1 and int(row.get("weekIndex", 0) or 0) >= REGULAR_SEASON_WEEKS:
            postseason_by_season[int(row.get("seasonIndex", -1) or -1)].append(row)
    champions_count = 0
    for season_rows in postseason_by_season.values():
        completed = [r for r in season_rows if int(r.get("status", 1) or 1) in COMPLETE_STATUSES]
        if not completed:
            continue
        final_week = max(int(r.get("weekIndex", 0) or 0) for r in completed)
        final_games = [r for r in completed if int(r.get("weekIndex", 0) or 0) == final_week]
        if len(final_games) == 1:
            champions_count += 1
    post_values = metric_rows_from_records(postseason, "saved_favorite_probability", "saved_favorite_won")
    post_summary = metrics(post_values)
    lines.append(
        f"Сохранённые сценарии дали {len(postseason)} оценённых матчей Madden 26 после 18-й недели "
        "(все — первый сохранённый postseason раунд). "
        f"Описательно: {fmt_metric(post_summary)}; это слишком мало для калибровки турнирной модели "
        "и не включает надёжную выборку Супербоулов. В Madden 27 пока оценённых postseason матчей: "
        f"{len(m27_postseason)}. Регулярные матчи не являются проверкой вероятности чемпионства. "
        f"В доступной истории Madden 26 есть только {champions_count} завершённых сезона с одним "
        "чемпионом на сезон; это не даёт надёжной SB-калибровки."
    )
    lines.extend([
        "",
        "## Объём, исключения и ограничения",
        "",
        f"- Найдено пригодных snapshot сценариев: {snapshot_counts.get('Madden 26', 0)} Madden 26 и "
        f"{snapshot_counts.get('Madden 27', 0)} Madden 27.",
        f"- Завершённых уникальных игр с сохранённым прогнозом: {result_counts.get('completed_unique', 0)}.",
        f"- На этих завершённых играх убрано повторных прогнозных snapshots: {duplicate_snapshots}.",
        f"- Исключено Force Win: {result_counts.get('force_win_excluded', 0)}; ничьи: "
        f"{result_counts.get('ties_separate', 0)} (не входят в бинарные метрики).",
        f"- Основная выборка регулярки: {result_counts.get('regular_decisive', 0)}; postseason отдельно: "
        f"{result_counts.get('postseason_separate', 0)}.",
        f"- Результат ещё не появился в финальном циклическом snapshot: {result_counts.get('pending_no_result', 0)} "
        "уникальных игр; они не оценивались.",
        f"- Для чистого ELO пригодно: {result_counts.get('elo_available', 0)} матчей по всем фазам; "
        f"после Force Win/postseason фильтров сравниваются {sum(1 for r in records if r['elo_scored_eligible'])} "
        f"регулярных матчей; пропущено по сроку/рейтингу: {result_counts.get('elo_not_scored', 0)}.",
        "- Не связаны с единственной строкой расписания либо не прошли проверку зеркальных прогнозов: "
        f"{exclusions.get('forecast_schedule_unlinked_or_ambiguous', 0) + exclusions.get('forecast_missing_away_mirror', 0) + exclusions.get('forecast_missing_probability', 0) + exclusions.get('forecast_mirrors_disagree', 0)} "
        "кандидатных записей.",
        f"- Madden 27 активный result snapshot: `{final_meta['Madden 27']['snapshot_id']}`; метаданные "
        f"обозначают `exportWeekIndex={m27_meta.get('exportWeekIndex')}`, "
        f"`completedThroughWeek={m27_meta.get('completedThroughWeek')}`, "
        f"`eloSourceWeek={m27_meta.get('eloSourceWeek')}`.",
        f"- Madden 26 terminal evidence: commit `{final_meta['Madden 26']['commit'][:12]}`; "
        f"Madden 27 result evidence: commit `{final_meta['Madden 27']['commit'][:12]}`.",
        "- Прогнозный статус взят из того же коммита, что и JSON; матч имел незавершённый status. "
        "У большинства исторических игр нет точного `scheduled_date_time`, поэтому по Git нельзя "
        "доказать wall-clock порядок относительно реального kickoff, только то, что на момент генерации "
        "прогноза committed экспорт ещё считал матч незавершённым.",
        "- Выборки по сезону и версии модели не объединяются. ELO сравнивается только с rating column "
        "из того же snapshot и только после его источниковой недели.",
        f"- Смешанная реконструкция Madden 27: {result_counts.get('mixed_reconstructed', 0)} матчей; "
        f"не восстановлено из-за неподдержанного source hash/недостатка snapshot данных: "
        f"{result_counts.get('mixed_version_unsupported', 0) + result_counts.get('mixed_reconstruction_unavailable', 0)}.",
        "- Для Madden 26 по game-level probability JSON доступны только seasonIndex=2 и 3; "
        "сохранённых match probabilities для сезонов 0 и 1 в пригодных snapshot не найдено.",
        "- Madden 26 regular ELO сравнение есть только там, где сохранились contemporaneous Week 14+ "
        "ratings; для более ранних матчей и части сезона 3 рейтинги появились позднее и исключены.",
        "- `team_scenarios.json` хранит округлённые десятые доли процента. Расчёт модели реконструирован "
        "из исторических файлов, не запуском старых скриптов. Явно сохранённые проценты не заменены.",
        "",
        "## Рекомендации",
        "",
        "1. Не менять +75 только по текущей выборке: Madden 26 и Madden 27 дают разный знак разницы, "
        "а интервалы неопределённости широкие. Сохранить значение как рабочую настройку до накопления "
        "нескольких независимых сезонов.",
        "2. Продолжать сохранять перед каждым туром матчевые вероятности, source ELO week, snapshot ID, "
        "версию формулы и точное время; так будущая выборка станет действительно предматчевой.",
        "3. Для калибровки playoff/SB собирать отдельные preseason/round-by-round прогнозы вместе с "
        "посевом и фактическим bracket; оценивать чемпионские шансы только после многих сезонов.",
        "4. Не подбирать шкалу ELO или бонус на этих же матчах. Если настройка понадобится, выделить "
        "ранние сезоны для обучения, а более поздние сезоны держать как хронологический holdout.",
        "",
        "## Воспроизведение",
        "",
        "```bash",
        "python3 scripts/analyze_forecast_quality.py",
        "```",
        "",
        "Итоговый построчный набор и provenance находятся в `matches.csv` рядом с этим отчётом.",
    ])
    return "\n".join(lines) + "\n"


CSV_FIELDS = (
    "edition", "season_index", "stage_index", "phase", "game_id", "game_id_external",
    "week_index", "display_week", "home", "away", "home_score", "away_score", "actual_result",
    "force_win", "is_tie", "performance_eligible", "exclusion_reason",
    "forecast_commit", "forecast_commit_time", "forecast_generated_at", "forecast_snapshot_id",
    "snapshot_game_status", "forecast_snapshots_seen_for_game", "duplicate_snapshots_discarded",
    "saved_model_version", "saved_home_win_raw", "saved_tie_probability", "saved_home_win_conditional",
    "saved_favorite_team", "saved_favorite_probability", "saved_favorite_won",
    "elo_source_path", "elo_source_version", "elo_source_week", "home_elo", "away_elo",
    "elo_timing_eligible", "elo_home_probability_bonus_0", "elo_home_probability_bonus_75",
    "elo_scored_eligible", "elo_exclusion_reason", "mixed_model_version", "mixed_version_label",
    "mixed_home_probability_reconstructed", "mixed_favorite_probability_reconstructed",
    "mixed_favorite_won_reconstructed", "mixed_reconstruction_note",
    "actual_commit", "actual_commit_time", "actual_snapshot_id",
)


def write_csv(path: Path, records: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_FIELDS, extrasaction="ignore")
        writer.writeheader()
        for row in sorted(records, key=lambda r: (r["edition"], r["season_index"], r["week_index"], r["game_id"])):
            values = {
                "edition": row["edition"],
                "season_index": row["season_index"],
                "stage_index": row["stage_index"],
                "phase": row["phase"],
                "game_id": row["game_id"],
                "game_id_external": row["game_id_external"],
                "week_index": row["week_index"],
                "display_week": row["display_week"],
                "home": row["home"],
                "away": row["away"],
                "home_score": row["home_score"],
                "away_score": row["away_score"],
                "actual_result": row["actual_result"],
                "force_win": str(row["force_win"]).lower(),
                "is_tie": str(row["is_tie"]).lower(),
                "performance_eligible": str(row["performance_eligible"]).lower(),
                "exclusion_reason": row["exclusion_reason"],
                "forecast_commit": row["forecast_commit"],
                "forecast_commit_time": row["forecast_commit_time"],
                "forecast_generated_at": row["generated_at"],
                "forecast_snapshot_id": row["forecast_snapshot_id"],
                "snapshot_game_status": row["source_status"],
                "forecast_snapshots_seen_for_game": row["forecast_snapshots_seen_for_game"],
                "duplicate_snapshots_discarded": max(0, row["forecast_snapshots_seen_for_game"] - 1),
                "saved_model_version": row["saved_model_version"],
                "saved_home_win_raw": f"{row['saved_home_win_raw']:.6f}",
                "saved_tie_probability": f"{row['saved_tie']:.6f}",
                "saved_home_win_conditional": f"{row['saved_home_win_conditional']:.6f}",
                "saved_favorite_team": row["favorite_team"],
                "saved_favorite_probability": f"{row['saved_favorite_probability']:.6f}",
                "saved_favorite_won": "" if row["saved_favorite_won"] is None else row["saved_favorite_won"],
                "elo_source_path": row["elo_source_path"],
                "elo_source_version": row["elo_source_version"],
                "elo_source_week": "" if row["elo_source_week"] is None else row["elo_source_week"],
                "home_elo": "" if row["home_elo"] is None else row["home_elo"],
                "away_elo": "" if row["away_elo"] is None else row["away_elo"],
                "elo_timing_eligible": str(row["elo_timing_eligible"]).lower(),
                "elo_home_probability_bonus_0": "" if row["elo_home_p_0"] is None else f"{row['elo_home_p_0']:.6f}",
                "elo_home_probability_bonus_75": "" if row["elo_home_p_75"] is None else f"{row['elo_home_p_75']:.6f}",
                "elo_scored_eligible": str(row["elo_scored_eligible"]).lower(),
                "elo_exclusion_reason": row["elo_exclusion_reason"],
                "mixed_model_version": row["mixed_model_version"] if row["edition"] == "Madden 27" else "",
                "mixed_version_label": row["mixed_version_label"] if row["edition"] == "Madden 27" else "",
                "mixed_home_probability_reconstructed": "" if row["mixed_home_probability"] is None else f"{row['mixed_home_probability']:.6f}",
                "mixed_favorite_probability_reconstructed": "" if row["mixed_favorite_probability"] is None else f"{row['mixed_favorite_probability']:.6f}",
                "mixed_favorite_won_reconstructed": "" if row["mixed_favorite_won"] is None else row["mixed_favorite_won"],
                "mixed_reconstruction_note": row["mixed_reconstruction_note"],
                "actual_commit": row["actual_commit"],
                "actual_commit_time": row["actual_commit_time"],
                "actual_snapshot_id": row["actual_snapshot_id"],
            }
            writer.writerow(values)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir", default="analysis/forecast_quality",
        help="Output directory relative to repository root (default: analysis/forecast_quality)",
    )
    args = parser.parse_args()
    output_dir = (ROOT / args.output_dir).resolve()

    commits = git("log", "--full-history", "--format=%H", "HEAD", "--", "output/team_scenarios.json").decode().splitlines()
    final_games, final_meta = actual_source_rows()
    selected, exclusions, snapshot_counts, _ = create_candidates(commits, final_games)
    records, result_counts = materialize_records(selected, final_meta)
    result_counts["pending_no_result"] += 0
    report = build_report(records, snapshot_counts, exclusions, result_counts, final_meta)
    output_dir.mkdir(parents=True, exist_ok=True)
    csv_path = output_dir / "matches.csv"
    report_path = output_dir / "report.md"
    write_csv(csv_path, records)
    report_path.write_text(report, encoding="utf-8")

    # Basic artifact integrity checks are part of the reproducible analysis.
    with csv_path.open(encoding="utf-8") as handle:
        exported = list(csv.DictReader(handle))
    if len(exported) != len(records):
        raise RuntimeError("CSV row count does not match the analysis records")
    if len({(r["edition"], r["season_index"], r["stage_index"], r["game_id"]) for r in exported}) != len(exported):
        raise RuntimeError("CSV contains duplicate evaluated game identities")
    if any(row["performance_eligible"] == "true" and row["force_win"] == "true" for row in exported):
        raise RuntimeError("A Force Win entered the performance sample")
    print(f"Snapshots: Madden 26={snapshot_counts.get('Madden 26',0)}, Madden 27={snapshot_counts.get('Madden 27',0)}")
    print(f"Unique final-result match rows: {len(records)}")
    print(f"Regular decisive sample: {result_counts.get('regular_decisive',0)}; Force Wins excluded: {result_counts.get('force_win_excluded',0)}; ties: {result_counts.get('ties_separate',0)}")
    print(f"Madden 27 mixed reconstruction rows: {result_counts.get('mixed_reconstructed',0)}")
    print(f"Wrote {csv_path.relative_to(ROOT)} and {report_path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
