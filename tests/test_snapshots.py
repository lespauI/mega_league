#!/usr/bin/env python3
"""
Snapshot tests: run each pipeline script and verify output matches
the golden snapshots captured from master.

Run from project root:
    PYTHONPATH=. python3 tests/test_snapshots.py
"""
import csv
import json
import subprocess
import sys
import os
from pathlib import Path

SNAPSHOTS = Path("tests/snapshots")
MASTER = Path("/Users/lespaul/workspace/MEGA_neonsportz_stats")

PASS = []
FAIL = []


def run(cmd, desc):
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if result.returncode != 0:
        FAIL.append(f"SCRIPT FAILED [{desc}]: {result.stderr.strip()}")
        return False
    return True


def diff_csv(actual_path, snapshot_path, label):
    """Compare two CSV files row-by-row (order matters)."""
    try:
        with open(actual_path, newline="", encoding="utf-8") as f:
            actual = list(csv.DictReader(f))
        with open(snapshot_path, newline="", encoding="utf-8") as f:
            expected = list(csv.DictReader(f))
    except FileNotFoundError as e:
        FAIL.append(f"MISSING FILE [{label}]: {e}")
        return
    if actual == expected:
        PASS.append(label)
    else:
        FAIL.append(f"CSV MISMATCH [{label}]: {len(actual)} rows actual vs {len(expected)} expected")


def diff_json(actual_path, snapshot_path, label):
    """Compare two JSON files by value (not byte-for-byte to tolerate whitespace)."""
    try:
        with open(actual_path, encoding="utf-8") as f:
            actual = json.load(f)
        with open(snapshot_path, encoding="utf-8") as f:
            expected = json.load(f)
    except FileNotFoundError as e:
        FAIL.append(f"MISSING FILE [{label}]: {e}")
        return
    if actual == expected:
        PASS.append(label)
    else:
        FAIL.append(f"JSON MISMATCH [{label}]")


# ── SoS ELO (Season 2) ────────────────────────────────────────────────────────
if run("python3 scripts/calc_sos_season2_elo.py --season2-start-row 287", "calc_sos_season2_elo"):
    diff_csv("output/sos/season2_elo.csv",  SNAPSHOTS / "sos/season2_elo.csv",  "sos/season2_elo.csv")
    diff_json("output/sos/season2_elo.json", SNAPSHOTS / "sos/season2_elo.json", "sos/season2_elo.json")

# ── SoS ELO (Season 3) ────────────────────────────────────────────────────────
if run("python3 scripts/calc_sos_season3_elo.py --season3-start-row 571", "calc_sos_season3_elo"):
    diff_csv("output/sos/season3_elo.csv",  SNAPSHOTS / "sos/season3_elo.csv",  "sos/season3_elo.csv")
    diff_json("output/sos/season3_elo.json", SNAPSHOTS / "sos/season3_elo.json", "sos/season3_elo.json")

# ── Stats pipeline ────────────────────────────────────────────────────────────
if run("python3 stats_scripts/aggregate_team_stats.py", "aggregate_team_stats"):
    diff_csv("output/team_aggregated_stats.csv", SNAPSHOTS / "output/team_aggregated_stats.csv", "team_aggregated_stats.csv")

if run("python3 stats_scripts/aggregate_player_usage.py", "aggregate_player_usage"):
    diff_csv("output/team_player_usage.csv", SNAPSHOTS / "output/team_player_usage.csv", "team_player_usage.csv")

if run("python3 stats_scripts/aggregate_rankings_stats.py", "aggregate_rankings_stats"):
    diff_csv("output/team_rankings_stats.csv", SNAPSHOTS / "output/team_rankings_stats.csv", "team_rankings_stats.csv")

if run("python3 stats_scripts/build_player_team_stints.py", "build_player_team_stints"):
    diff_csv("output/player_team_stints.csv", SNAPSHOTS / "output/player_team_stints.csv", "player_team_stints.csv")

# ── SoS by Rankings ───────────────────────────────────────────────────────────
if run("python3 scripts/calc_sos_by_rankings.py --season-index 2 --out-csv output/ranked_sos_by_conference.csv", "calc_sos_by_rankings"):
    diff_csv("output/ranked_sos_by_conference.csv", SNAPSHOTS / "output/ranked_sos_by_conference.csv", "ranked_sos_by_conference.csv")


# ── Report ────────────────────────────────────────────────────────────────────
print(f"\n{'='*60}")
print(f"SNAPSHOT TESTS: {len(PASS)} passed, {len(FAIL)} failed")
print(f"{'='*60}")
for p in PASS:
    print(f"  ✅ {p}")
for f in FAIL:
    print(f"  ❌ {f}")

sys.exit(1 if FAIL else 0)
