# Refactoring Safety Guide

## Test Baseline (Run Before Touching Anything)

Establish a green baseline first. These are the commands to run:

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

Run this after every step to confirm nothing regressed:

```bash
PYTHONPATH=. python3 tests/test_power_rankings_roster.py  && \
node scripts/tests/test_year_context.mjs && \
echo "ALL BASELINE TESTS PASSED"
```
