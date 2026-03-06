# Refactoring Safety Guide

---

## Phase 0: Create Snapshot Tests BEFORE Touching Any Code

> **This is mandatory. Do not skip it. Write the tests first, confirm they pass against master, then refactor.**

We are on a Git worktree branched from `master`. The main worktree at `/Users/lespaul/workspace/MEGA_neonsportz_stats` has all real, production-generated output files on `master`. We use these as **golden snapshots** — the ground truth that our refactored code must reproduce exactly.

### 0.1 — Understand the worktree layout

```
/Users/lespaul/workspace/MEGA_neonsportz_stats   ← master (golden source)
/Users/lespaul/.zenflow/worktrees/refactor-plan-03c3  ← THIS branch (where we work)
```

The master worktree has:
- `output/sos/season2_elo.csv` / `season3_elo.csv` — golden SoS outputs
- `output/sos/season2_elo.json` / `season3_elo.json`
- `output/schedules/season2/all_schedules.json` / `season3/...`
- `output/playoff_probabilities.json`
- `output/ranked_sos_by_conference.csv`
- `output/team_aggregated_stats.csv`
- `output/team_player_usage.csv`
- `output/team_rankings_stats.csv`
- `output/player_team_stints.csv`
- `docs/playoff_race_table.html`
- `docs/playoff_race.html`
- `docs/power_rankings_roster.html`

### 0.2 — Copy golden snapshots into the worktree

Run this once from the worktree root to copy the master outputs as reference snapshots:

```bash
MASTER=/Users/lespaul/workspace/MEGA_neonsportz_stats
mkdir -p tests/snapshots/sos tests/snapshots/output tests/snapshots/docs

# SoS ELO outputs (most critical — these are what the merged script must reproduce)
cp $MASTER/output/sos/season2_elo.csv   tests/snapshots/sos/season2_elo.csv
cp $MASTER/output/sos/season2_elo.json  tests/snapshots/sos/season2_elo.json
cp $MASTER/output/sos/season3_elo.csv   tests/snapshots/sos/season3_elo.csv
cp $MASTER/output/sos/season3_elo.json  tests/snapshots/sos/season3_elo.json

# Schedules
cp $MASTER/output/schedules/season2/all_schedules.json  tests/snapshots/sos/season2_schedules.json
cp $MASTER/output/schedules/season3/all_schedules.json  tests/snapshots/sos/season3_schedules.json

# Stats pipeline outputs
cp $MASTER/output/ranked_sos_by_conference.csv     tests/snapshots/output/ranked_sos_by_conference.csv
cp $MASTER/output/playoff_probabilities.json       tests/snapshots/output/playoff_probabilities.json
cp $MASTER/output/team_aggregated_stats.csv        tests/snapshots/output/team_aggregated_stats.csv
cp $MASTER/output/team_player_usage.csv            tests/snapshots/output/team_player_usage.csv
cp $MASTER/output/team_rankings_stats.csv          tests/snapshots/output/team_rankings_stats.csv
cp $MASTER/output/player_team_stints.csv           tests/snapshots/output/player_team_stints.csv
```

Add `tests/snapshots/` to `.gitignore` so these large files are not committed, but keep them locally for the duration of the refactor.

### 0.3 — Write a snapshot test runner

Create `tests/test_snapshots.py`:

```python
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
```

### 0.4 — Confirm snapshot tests pass BEFORE any refactoring

```bash
PYTHONPATH=. python3 tests/test_snapshots.py
```

All checks must pass. If any fail on the unmodified worktree, investigate before proceeding — it means the worktree diverged from master in a way that affects output.

**The snapshot test is your safety harness. After every refactoring step, run it again. If it stays green, you have not broken anything.**

---

## Phase 1: Run Existing Unit Tests Baseline

```bash
# Python unit tests
PYTHONPATH=. python3 tests/test_power_rankings_roster.py

# Node unit tests
node scripts/tests/test_year_context.mjs
node scripts/tests/test_cap_tool.mjs
```

### Known Baseline State

| Test | Command | Expected |
|------|---------|----------|
| Roster rankings | `PYTHONPATH=. python3 tests/test_power_rankings_roster.py` | ✅ 7/7 pass |
| Year context helpers | `node scripts/tests/test_year_context.mjs` | ✅ All pass |
| Cap tool math | `node scripts/tests/test_cap_tool.mjs` | ⚠️ Some failures — **pre-existing before any refactoring** |

> The cap tool failures are not caused by anything we plan to change. Do not attempt to fix them as part of this refactor.

---

## The Golden Rules

### Rule 1: One change, one commit, one test
After each step in the roadmap:
1. Run all the baseline tests above
2. Verify the affected script(s) still produce the same output (see Rule 2)
3. Commit with a clear message like `refactor: merge season SoS ELO scripts`

Never batch multiple roadmap steps into a single commit.

### Rule 2: Diff outputs to prove nothing changed
For any change that touches calculation logic, capture output before and after and diff it:

```bash
# Step A — capture BEFORE output (do this before making any code change)
python3 scripts/calc_sos_season2_elo.py --season2-start-row 287
cp output/sos/season2_elo.csv /tmp/season2_before.csv
cp output/sos/season2_elo.json /tmp/season2_before.json

# Step B — make the code change, then run the new version
python3 scripts/calc_sos_elo.py --season-index 2 --start-row 287

# Step C — diff (should print nothing if output is identical)
diff /tmp/season2_before.csv output/sos/season2_elo.csv
diff /tmp/season2_before.json output/sos/season2_elo.json
```

Repeat the same pattern for any other script whose output files you care about.

### Rule 3: Git is your undo button
Every commit is a safe restore point. If something breaks:

```bash
# Undo the last commit (keeps changes in working directory so you can inspect)
git revert HEAD

# Or discard everything since the last commit entirely
git checkout .
```

### Rule 4: Do not touch the large monolithic scripts until last
The big scripts are the highest risk. Leave these for a dedicated effort with tests:

| Script | Lines | Risk |
|--------|-------|------|
| `scripts/power_rankings_roster.py` | 2636 | High |
| `scripts/generate_draft_class_analytics.py` | 1685 | High |
| `scripts/week18_simulator.py` | 1485 | High |

---

## Execution Order (Safest → Riskiest)

Work through these steps in order. Do not skip ahead.

### Step 1 — Delete dead code in `run_all_playoff_analysis.py`
**Risk**: None. The functions are provably never called.

**What to do**: Delete lines 1–204 of `scripts/run_all_playoff_analysis.py`, then make sure the file starts with exactly these three imports (all were in the deleted block but `os` is still needed):
```python
import os
import sys
import subprocess
```

**How to verify**:
```bash
python3 scripts/run_all_playoff_analysis.py --help   # must not crash
# Then run the full pipeline and check it completes
```

---

### Step 2 — Extract shared `run_script()` to `scripts/run_utils.py`
**Risk**: Low. Moving a function to a new file and importing it.

**What to do**:
1. Create `scripts/run_utils.py` with the full-featured version of `run_script()` (the one that supports `optional` and `extra_args` — from `run_all.py`).
2. In `run_all.py`, `run_all_playoff_analysis.py`, `run_all_stats.py` — delete the local `run_script` definition and add: `from run_utils import run_script`

**How to verify**:
```bash
python3 scripts/run_all_stats.py          # must complete without error
python3 scripts/run_all_playoff_analysis.py  # must complete without error
```

---

### Step 3 — Merge Season 2/3 SoS ELO scripts
**Risk**: Low. API change to CLI only; callers in `run_all.py` need updating.

**What to do**:
1. Create `scripts/calc_sos_elo.py` — parameterized version of both season scripts, accepting `--season-index N` and `--start-row N`.
2. Create `scripts/verify_sos_elo.py` — merged version of both stub verifiers, accepting `--season-index N`.
3. Update `scripts/run_all.py` to call the new script twice:
   ```python
   ('scripts/calc_sos_elo.py', 'Season 2 SoS (ELO)', False, ['--season-index', '2', '--start-row', '287']),
   ('scripts/calc_sos_elo.py', 'Season 3 SoS (ELO)', False, ['--season-index', '3', '--start-row', '571']),
   ```
4. Keep the old `calc_sos_season2_elo.py` and `calc_sos_season3_elo.py` files temporarily as thin wrappers that call the new script — remove them only after the diff check passes.

**How to verify** (using the diff pattern from Rule 2):
```bash
# Capture old output FIRST (before creating new script)
python3 scripts/calc_sos_season2_elo.py --season2-start-row 287
cp output/sos/season2_elo.csv /tmp/s2_before.csv

python3 scripts/calc_sos_season3_elo.py --season3-start-row 571
cp output/sos/season3_elo.csv /tmp/s3_before.csv

# After creating new script:
python3 scripts/calc_sos_elo.py --season-index 2 --start-row 287
diff /tmp/s2_before.csv output/sos/season2_elo.csv    # must be empty

python3 scripts/calc_sos_elo.py --season-index 3 --start-row 571
diff /tmp/s3_before.csv output/sos/season3_elo.csv    # must be empty
```

---

### Step 4 — Delete stale root plan files
**Risk**: None. These are notes, not code.

**What to do**: Delete `plan.md`, `plan2.md`, `plan3.md` from the project root.

**How to verify**: No tests needed. Just confirm they are not referenced anywhere:
```bash
grep -r "plan\.md\|plan2\.md\|plan3\.md" --include="*.py" --include="*.md" --include="*.html" .
```

---

### Step 5 — Add `--season-index` to hard-coded scripts
**Risk**: Low. Additive change — defaults preserve current behavior exactly.

**Scripts to update**: `playoff_race_html.py`, `playoff_race_table.py`, `calc_playoff_probabilities.py`

**How to verify**: Capture HTML outputs before and after with the default arg:
```bash
python3 scripts/playoff_race_table.py
cp docs/playoff_race_table.html /tmp/table_before.html
# make the change, then:
python3 scripts/playoff_race_table.py --season-index 2
diff /tmp/table_before.html docs/playoff_race_table.html   # must be empty
```

---

### Step 6 — Create `scripts/common.py` for shared utilities
**Risk**: Low. Moving pure functions that have no side effects.

**What to do**: Extract into `scripts/common.py`:
- `normalize_team_name()`
- `to_int()`
- `norm_rank()`
- `mean_safe()`
- `read_elo_map()`
- `read_team_meta()`

Update all callers to import from `scripts.common` (or use relative import when running from project root).

**How to verify**: Run all baseline tests. Run each affected script and diff its outputs against a pre-captured version.

---

### Steps 7–9 — Low-priority cosmetic changes
These are safe at any time and need no output verification:
- **Step 7**: Move `stats_scripts/*.md` design docs to `spec/`
- **Step 8**: Rename `mega_elo.csv` → `MEGA_elo.csv` (update all references)
- **Step 9**: Rename `export_2027_rookies.py` → `export_rookies.py` with `--year` arg

---

### Step 10 — Decompose large monolithic scripts (last, highest risk)
Only tackle after all previous steps are committed and verified. Each script decomposition should come with new unit tests before the code is moved.

---

## Quick Reference: Verify Everything Still Works

Run this after **every single step** to confirm nothing regressed:

```bash
# Snapshot tests (output must match master exactly)
PYTHONPATH=. python3 tests/test_snapshots.py && \

# Unit tests
PYTHONPATH=. python3 tests/test_power_rankings_roster.py && \
node scripts/tests/test_year_context.mjs && \

echo "ALL TESTS PASSED — safe to commit"
```

If any of these fail after a change: **do not commit**. Investigate immediately, or `git checkout .` to revert and try again.
