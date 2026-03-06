# Refactoring Evaluation — MEGA League Stats Analysis

> **Goal**: Identify all areas of code duplication, structural messiness, and improvement opportunities without losing any functionality.

---

## 1. Project Overview

The project is a Python + HTML/JS analytics suite for an NFL fantasy league. It has 4 functional domains:

| Domain | Key Scripts | Output |
|--------|-------------|--------|
| Playoff / SoS | `calc_sos_*.py`, `calc_playoff_probabilities.py`, `playoff_race_*.py` | `docs/playoff_race*.html` |
| Stats aggregation | `stats_scripts/aggregate_*.py`, `stats_scripts/build_player_team_stints.py` | `output/*.csv` |
| Roster / Cap | `power_rankings_roster.py`, `calc_team_y1_cap.py` | `docs/roster_cap_tool/`, `docs/power_rankings_roster.html` |
| Draft | `generate_draft_class*.py`, `generate_draft_rounds_recap.py` | `docs/draft_class_*.html` |

---

## 2. Critical Issues (Must Fix)

### 2.1 Near-Identical Duplicated Script Pair: Season 2 vs Season 3 SoS ELO

**Files**: [`scripts/calc_sos_season2_elo.py`](../../scripts/calc_sos_season2_elo.py) and [`scripts/calc_sos_season3_elo.py`](../../scripts/calc_sos_season3_elo.py)

Both files are **476 lines** and are **character-for-character identical** except for:

| Difference | Season 2 file | Season 3 file |
|-----------|---------------|---------------|
| `read_games_*` function name | `read_games_season2` | `read_games_season3` |
| Log message | `"Season 2 slice: ..."` | `"Season 3 slice: ..."` |
| CLI arg | `--season2-start-row` (default: 287) | `--season3-start-row` (default: 571) |
| Schedules dir | `output/schedules/season2/` | `output/schedules/season3/` |
| Output files | `output/sos/season2_elo.csv/json` | `output/sos/season3_elo.csv/json` |

**Suggestion**: Merge into a single `scripts/calc_sos_elo.py` with a `--season-index N` and `--start-row N` argument. The output paths can be derived from the season index automatically:
```bash
python3 scripts/calc_sos_elo.py --season-index 2 --start-row 287
python3 scripts/calc_sos_elo.py --season-index 3 --start-row 571
```

### 2.2 Near-Identical Stub Pair: Verify Season 2 vs Season 3 SoS

**Files**: [`scripts/verify_sos_season2_elo.py`](../../scripts/verify_sos_season2_elo.py) and [`scripts/verify_sos_season3_elo.py`](../../scripts/verify_sos_season3_elo.py)

Both are **stub scripts** (57/56 lines) with the only difference being one string in the `argparse` description. Neither implements any real verification logic (both contain `[stub]` log stubs).

**Suggestion**: Merge into `scripts/verify_sos_elo.py` with `--season-index` arg. Implement real checks when the stubs are fleshed out.

### 2.3 Dead Code in `run_all_playoff_analysis.py`

**File**: [`scripts/run_all_playoff_analysis.py`](../../scripts/run_all_playoff_analysis.py) — Lines 1–203

The top ~200 lines of this orchestrator define:
- `to_int()`, `norm_rank()`, `mean_safe()`
- `compute_strength_score()`
- `read_latest_rankings()`
- `read_games_split()`
- `read_teams_info()`
- `compute_ranked_sos()`
- `write_output()`

These are **never called** — `main()` (line 246) runs everything via `subprocess` by calling `calc_sos_by_rankings.py`. These functions are a copy of code that lives in `calc_sos_by_rankings.py`.

**Suggestion**: Delete lines 1–203 of `run_all_playoff_analysis.py` (the unused SoS utility functions), then ensure the file starts with these three imports:
```python
import os
import sys
import subprocess
```
Note: `import os` was at line 4 in the dead-code block and must be retained — it is still used by `main()` via `os.chdir()` and `os.path.*`.

---

## 3. High-Priority Issues

### 3.1 Triplicated `run_script()` Orchestrator Function

**Files**: [`scripts/run_all.py`](../../scripts/run_all.py), [`scripts/run_all_playoff_analysis.py`](../../scripts/run_all_playoff_analysis.py), [`scripts/run_all_stats.py`](../../scripts/run_all_stats.py)

All three define a `run_script()` function that runs a subprocess and prints status. The signatures differ slightly:
- `run_all.py`: supports `optional` and `extra_args` parameters
- `run_all_playoff_analysis.py`: same as above (duplicate)
- `run_all_stats.py`: simpler version without `optional` / `extra_args`

**Suggestion**: Extract to `scripts/run_utils.py` (or `scripts/_runner.py`) with the full-featured version, then import it in all three runners.

### 3.2 Duplicated Low-Level Utility Functions Across Multiple Scripts

The following utility functions are implemented **independently** in multiple files with near-identical logic:

| Function | Files |
|----------|-------|
| `to_int()` | `calc_sos_by_rankings.py`, `run_all_playoff_analysis.py` (dead), `calc_playoff_probabilities.py` (implicit) |
| `norm_rank()` | `calc_sos_by_rankings.py`, `run_all_playoff_analysis.py` (dead) |
| `mean_safe()` | `calc_sos_by_rankings.py`, `run_all_playoff_analysis.py` (dead) |
| `normalize_team_name()` | `calc_sos_season2_elo.py`, `calc_sos_season3_elo.py` (duplicated) |
| `read_elo_map()` | `calc_sos_season2_elo.py`, `calc_sos_season3_elo.py` (duplicated) |
| `read_team_meta()` | `calc_sos_season2_elo.py`, `calc_sos_season3_elo.py` (duplicated) |
| `load_elo_data()` | `playoff_race_table.py`, `calc_playoff_probabilities.py` (both hard-code `mega_elo.csv`) |
| `load_power_rankings()` | `playoff_race_table.py`, `calc_playoff_probabilities.py` |
| `read_csv()` / `load_csv()` | `power_rankings_roster.py` defines `read_csv()`; `stats_scripts/stats_common.py` defines `load_csv()` |
| `safe_int()` / `safe_float()` | `power_rankings_roster.py`, `stats_scripts/stats_common.py`, many more |

**Suggestion**: Consolidate into `scripts/common.py` (mirroring `stats_scripts/stats_common.py`). The `stats_common.py` file already exists as a good pattern but is only used inside `stats_scripts/`.

### 3.3 Hard-Coded File Paths in Scripts

Several scripts open CSV files with hard-coded paths relative to CWD:

```python
# In week18_simulator.py, playoff_race_html.py, playoff_race_table.py, etc.
with open('MEGA_teams.csv', 'r', encoding='utf-8') as f:
with open('mega_elo.csv', 'r', encoding='utf-8') as f:
with open('MEGA_rankings.csv', 'r', encoding='utf-8') as f:
```

Meanwhile, newer scripts (`calc_sos_season2_elo.py`, `power_rankings_roster.py`) use `argparse` with `--players`, `--teams`, `--elo-csv` etc. for configurability.

Scripts with hard-coded paths: `week18_simulator.py`, `playoff_race_html.py`, `playoff_race_table.py`, `calc_playoff_probabilities.py`, `top_pick_race_analysis.py`.

**Suggestion**: Add `argparse` CLI arguments to each of these scripts (with the current hard-coded values as defaults). This enables testing and future path changes without editing source.

---

## 4. Medium-Priority Issues

### 4.1 Stale Plan Files at Project Root

**Files**: [`plan.md`](../../plan.md), [`plan2.md`](../../plan2.md), [`plan3.md`](../../plan3.md)

These are working notes from a past task (writing `wild_card_season_1.md`) left at the project root. They are not part of the main project structure.

**Suggestion**: Delete `plan.md`, `plan2.md`, `plan3.md`. They belong in `.zenflow/tasks/` if they need to be preserved.

### 4.2 Large Monolithic Scripts

The following scripts are very large and mix concerns (data loading, calculation, HTML templating):

| File | Lines | Concerns mixed |
|------|-------|---------------|
| [`scripts/power_rankings_roster.py`](../../scripts/power_rankings_roster.py) | 2636 | Data loading, scoring, CSV export, HTML generation |
| [`scripts/generate_draft_class_analytics.py`](../../scripts/generate_draft_class_analytics.py) | 1685 | Data loading, analytics, full HTML generation |
| [`scripts/week18_simulator.py`](../../scripts/week18_simulator.py) | 1485 | Data loading, simulation, HTML generation |
| [`scripts/playoff_race_table.py`](../../scripts/playoff_race_table.py) | 1011 | Data loading, Monte Carlo simulation, HTML generation |
| [`scripts/calc_playoff_probabilities.py`](../../scripts/calc_playoff_probabilities.py) | 837 | Monte Carlo simulation, tiebreaker logic, file I/O |
| [`scripts/playoff_race_html.py`](../../scripts/playoff_race_html.py) | 708 | Data loading, narrative generation, HTML templating |

**Suggestion**: These don't all need to be split immediately, but each should at minimum separate:
1. Data loading functions (testable in isolation)
2. Computation/logic functions (pure, testable)
3. HTML output rendering (separate function or module)

This separation would make unit testing much more feasible.

### 4.3 Season Index Hard-Coded in Many Scripts

Multiple scripts hard-code `seasonIndex == 2` to filter data:

```python
# In playoff_race_html.py
if status == '1' and season_index == 2 and stage_index == 1:

# In calc_playoff_probabilities.py
if int(row.get('seasonIndex', 0)) != 2:

# In playoff_race_table.py
if int(row.get('seasonIndex', 0)) != 2:
```

`calc_sos_by_rankings.py` already has `--season-index` as a CLI argument, but others don't.

**Suggestion**: Add a `--season-index` (or `--season`) CLI arg to all scripts that filter by season. Default to the current season. This is a significant quality-of-life improvement for next season.

### 4.4 `export_2027_rookies.py` vs README Reference

**File**: [`scripts/export_2027_rookies.py`](../../scripts/export_2027_rookies.py)

The [`scripts/README.md`](../../scripts/README.md) references `export_2026_rookies.py`, but the actual file is `export_2027_rookies.py`. This is either a renamed file or a stale README reference.

**Suggestion**: Reconcile the name — either rename the file to be generic (`export_rookies.py --year 2027`) or update the README.

### 4.5 Duplicated Data in `docs/data/` vs Project Root

The project root has:
- `MEGA_teams.csv`, `mega_elo.csv`, etc. (source data)
- `docs/data/MEGA_teams.csv`, `docs/data/mega_elo.csv`, `docs/data/season3_elo.csv` etc. (copies in docs)

**Suggestion**: Clarify which is the canonical location. The `docs/data/` copies appear to be for the cap tool's local-server use, but this can be confusing. A symlink or a `--data-dir` argument would be cleaner.

### 4.6 `mega_elo.csv` Naming Inconsistency

The root has both `mega_elo.csv` (lowercase) and `MEGA_*.csv` (uppercase) files. The ELO CSV breaks the naming convention.

**Suggestion**: Rename `mega_elo.csv` to `MEGA_elo.csv` for consistency, and update all scripts that reference it (`--elo-csv` default, hard-coded opens).

---

## 5. Low-Priority Issues

### 5.1 Plan/Design Doc Files in `stats_scripts/`

**Files**: [`stats_scripts/STATS_VISUALIZATION_PLAN.md`](../../stats_scripts/STATS_VISUALIZATION_PLAN.md), [`stats_scripts/RANKINGS_VISUALIZATION_PLAN.md`](../../stats_scripts/RANKINGS_VISUALIZATION_PLAN.md), [`stats_scripts/CORRELATION_IDEAS.md`](../../stats_scripts/CORRELATION_IDEAS.md)

These are large design documents inside the `stats_scripts/` folder. They're useful but are embedded in the code directory rather than `spec/` or `docs/`.

**Suggestion**: Move to `spec/` to align with the rest of the design documentation.

### 5.2 `scripts/tests/` vs `tests/e2e/` vs `tests/` — Three Test Locations

Tests are spread across:
- `scripts/tests/` — Node/JS unit tests for cap tool math
- `scripts/smoke/` — Shell smoke tests
- `tests/e2e/` — Playwright E2E tests
- `tests/` — Python unit tests (`test_power_rankings_roster.py`)
- `scripts/players_ovr/test_ol_position_changes.py` — another Python test

**Suggestion**: No change needed in locations if they remain separated by type, but the `scripts/tests/` vs root `tests/` split should be documented clearly in the README (it already is, mostly). Consider moving `scripts/players_ovr/test_ol_position_changes.py` to `tests/` for consistency.

### 5.3 `scripts/players_ovr/` Sub-Folder

**Files**: `scripts/players_ovr/{analyze_team.py,calculate_advanced_formulas.py,export_individual_positions.py,optimize_positions.py}`

This sub-folder appears to be an experimental/analysis tool with its own `README.md` and `requirements.txt` (`scikit-learn>=1.8.0`, `numpy>=2.4.0`), making it the only part of the project with external Python dependencies.

**Suggestion**: Ensure these scripts are clearly documented as optional/experimental, or isolate them more explicitly (e.g., `tools/players_ovr/`). Their `requirements.txt` (`scikit-learn`, `numpy`) contradicts the "no external dependencies required" claim in the root README.

### 5.4 Stale Comment "scaffold" in SoS ELO Scripts

Both `calc_sos_season2_elo.py` and `calc_sos_season3_elo.py` contain:
```python
logging.info("Finished (scaffold). Downstream steps will implement calculations and outputs.")
```
And the docstring says "This file currently implements argument parsing and logging scaffolding, along with stubbed functions...". However, the scripts appear to be fully functional now (they do write real outputs).

**Suggestion**: Remove "scaffold" language from docstrings and log messages once confirmed that the implementations are complete.

### 5.5 Leftover `export_2027_rookies.py` Incomplete Name

The script `export_2027_rookies.py` has a year hard-coded in its filename. The `generate_draft_class_analytics.py` takes a `--year` argument. For consistency:

**Suggestion**: Rename to `export_rookies.py` with a `--year` arg.

---

## 6. Structural Refactoring Roadmap

Listed in priority order. Each step is self-contained and safe (existing functionality preserved).

### Step 1: Eliminate Dead Code in `run_all_playoff_analysis.py` ⭐⭐⭐
**Risk**: None — the functions are not called.
**Action**: Delete lines 1–204 of [`scripts/run_all_playoff_analysis.py`](../../scripts/run_all_playoff_analysis.py) (the unused SoS utility functions), then ensure the file starts with:
```python
import os
import sys
import subprocess
```
`import os` was part of the deleted block (line 4) but is still used by `main()` via `os.chdir()` and `os.path.*` — it must be retained.

### Step 2: Extract Shared `run_script()` to `scripts/run_utils.py` ⭐⭐⭐
**Risk**: Low — just moving a function.
**Action**: Create `scripts/run_utils.py` with the full-featured `run_script()` (with `optional` and `extra_args` support). Update `run_all.py`, `run_all_playoff_analysis.py`, `run_all_stats.py` to `from run_utils import run_script`.

### Step 3: Merge Season 2/3 SoS ELO Scripts ⭐⭐⭐
**Risk**: Low — API change only to CLI args (callers in `run_all.py` must update).
**Action**:
- Create `scripts/calc_sos_elo.py` combining both scripts parameterized by `--season-index N` and `--start-row N`.
- Create `scripts/verify_sos_elo.py` combining the two stub verifiers.
- Update `run_all.py` to call `calc_sos_elo.py --season-index 2 --start-row 287` and `--season-index 3 --start-row 571`.
- Keep old files as thin wrappers for backward compat (or remove if nothing else calls them).

### Step 4: Delete Stale Root Plan Files ⭐⭐
**Risk**: None — these are not code.
**Action**: Delete `plan.md`, `plan2.md`, `plan3.md` from project root.

### Step 5: Add `--season-index` to Hard-Coded Scripts ⭐⭐
**Risk**: Low — additive change, defaults preserve current behavior.
**Action**: Add `argparse` with `--season-index` (default: `2` or the current active season) to:
- `playoff_race_html.py`
- `playoff_race_table.py`
- `calc_playoff_probabilities.py`

### Step 6: Create `scripts/common.py` for Shared Utilities ⭐⭐
**Risk**: Low — refactoring only.
**Action**: Extract `normalize_team_name()`, `to_int()`, `norm_rank()`, `mean_safe()`, `read_elo_map()`, `read_team_meta()` into `scripts/common.py`. Update callers to import from there. The pattern already exists in `stats_scripts/stats_common.py`.

### Step 7: Move Design Docs to `spec/` ⭐
**Risk**: None.
**Action**: Move `stats_scripts/STATS_VISUALIZATION_PLAN.md`, `RANKINGS_VISUALIZATION_PLAN.md`, `CORRELATION_IDEAS.md` to `spec/`. Update `stats_scripts/README.md` links.

### Step 8: Rename `mega_elo.csv` ⭐
**Risk**: Low — requires updating all references.
**Action**: Rename to `MEGA_elo.csv`. Update `--elo-csv` defaults and hard-coded opens in `week18_simulator.py`, `calc_playoff_probabilities.py`, `playoff_race_table.py`, and `playoff_race_html.py`.

### Step 9: Refactor Monolithic Scripts (Long-Term) ⭐
**Risk**: Higher — requires careful decomposition.
**Action**: For `power_rankings_roster.py`, `generate_draft_class_analytics.py`, `week18_simulator.py` — separate into:
1. `_data.py` (loading functions)
2. `_calc.py` (pure computation)
3. Main script (orchestration + HTML output)

This is the biggest change and should only be done when there's time to add tests alongside.

---

## 7. What NOT to Touch

The following are intentional design decisions and should be left as-is:

- **No external Python dependencies** in the main pipeline — using stdlib only is intentional. Do not introduce pandas, numpy, etc. in `scripts/` or `stats_scripts/`.
- **Single-file scripts** — the scripts in `scripts/` are intentionally standalone entry points. Some size is expected.
- **HTML generation in Python** — generating HTML via f-strings in Python is the established pattern. Don't introduce Jinja or other templating frameworks.
- **`docs/` as static site root** — `docs/` is served by GitHub Pages and has specific structure expectations. Don't reorganize it.
- **`stats_scripts/` as separate namespace** — these scripts import from `stats_common.py` using a relative import, which requires running from project root. This is consistent and intentional.
- **Playwright E2E tests** — the `tests/e2e/` structure and `playwright.config.ts` are working and should not be moved.

---

## 8. Summary of File Changes

| Action | Files | Priority |
|--------|-------|----------|
| Delete dead code (lines 1–204) | `scripts/run_all_playoff_analysis.py` | Critical |
| Merge into one file | `calc_sos_season2_elo.py` + `calc_sos_season3_elo.py` → `calc_sos_elo.py` | Critical |
| Merge into one file | `verify_sos_season2_elo.py` + `verify_sos_season3_elo.py` → `verify_sos_elo.py` | Critical |
| Extract shared utility | New: `scripts/run_utils.py`, update 3 runners | High |
| Extract shared utility | New: `scripts/common.py`, update callers | High |
| Delete | `plan.md`, `plan2.md`, `plan3.md` (root) | Medium |
| Add CLI args | `playoff_race_html.py`, `playoff_race_table.py`, `calc_playoff_probabilities.py` | Medium |
| Move files | `stats_scripts/*.md` → `spec/` | Low |
| Rename | `mega_elo.csv` → `MEGA_elo.csv` | Low |
| Rename | `export_2027_rookies.py` → `export_rookies.py --year` | Low |
| Update stale comments | `calc_sos_season2_elo.py`, `calc_sos_season3_elo.py` | Low |
