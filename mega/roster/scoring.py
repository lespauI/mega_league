"""Roster unit scoring, league metrics, and CSV output."""
from __future__ import annotations

import csv
import math
import os
import statistics as st
import sys

from .inputs import (
    _collect_teams_by_abbrev,
    assign_unit,
    get_attr_keys_for_pos,
    safe_float,
    safe_int,
    select_unit_starters,
)

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
