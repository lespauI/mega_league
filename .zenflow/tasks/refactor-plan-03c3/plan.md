# Auto

## Configuration
- **Artifacts Path**: {@artifacts_path} → `.zenflow/tasks/{task_id}`

---

## Agent Instructions

Ask the user questions when anything is unclear or needs their input. This includes:
- Ambiguous or incomplete requirements
- Technical decisions that affect architecture or user experience
- Trade-offs that require business context

Do not make assumptions on important decisions — get clarification first.

---

## Workflow Steps

### [x] Step: Implementation
<!-- chat-id: 81e4a381-d4aa-4782-a12b-a66d72233cf7 -->
- If task is small and clear -> jump directly to implementation, without any additional steps or planning
- If the task is complex enough, plan how you want to address it. Plan can include requirements, tech specification and key implementation steps.
- Break down the work into concrete tasks (incrementable, testable milestones). Rule of thumb for step size: each step should represent a coherent unit of work (e.g., implement a component, add an API endpoint, write tests for a module). Avoid steps that are too granular (single function).
- To reflect actual purpose of the first step, you can update step Implementation, renaming it to something more relevant, like Planning. Do NOT remove meta information, like comments for any step.
- Update `{@artifacts_path}/plan.md`.

### [x] Step: Create snapshot tests (Phase 0)
<!-- chat-id: 651eb250-fb20-4b9f-8518-8db3bd624b4f -->
- Copy golden outputs from master worktree (`/Users/lespaul/workspace/MEGA_neonsportz_stats`) into `tests/snapshots/` (SoS CSVs/JSONs, schedules, stats pipeline outputs)
- Add `tests/snapshots/` to `.gitignore`
- Create `tests/test_snapshots.py` as specified in `refactor_safety_guide.md` Phase 0.3
- Run `PYTHONPATH=. python3 tests/test_snapshots.py` and confirm all checks pass on the unmodified worktree before any code is changed
- This is the safety harness — all subsequent steps must keep this test green

### [x] Step: Delete dead code in run_all_playoff_analysis.py
<!-- chat-id: 203b70cd-0e68-46ef-adf8-08883cfdd274 -->
- Delete lines 1–204 of `scripts/run_all_playoff_analysis.py` (the unused SoS utility functions that are never called)
- Ensure the file starts with `import os`, `import sys`, `import subprocess` (os was in the deleted block but is still required by main())
- Run snapshot tests + unit tests to verify nothing regressed
- Commit: `refactor: remove dead SoS utility code from run_all_playoff_analysis`

### [x] Step: Extract shared run_script() to scripts/run_utils.py
<!-- chat-id: 7729a598-0b2c-4922-8a7b-7d65f8ec739d -->
- Create `scripts/run_utils.py` with the full-featured `run_script()` from `run_all.py` (supports `optional` and `extra_args`)
- Remove the local `run_script` definition from `run_all.py`, `run_all_playoff_analysis.py`, `run_all_stats.py`
- Add `from run_utils import run_script` to each of those three files
- Run snapshot tests + unit tests to verify nothing regressed
- Commit: `refactor: extract run_script() to shared run_utils.py`

### [x] Step: Merge Season 2/3 SoS ELO scripts into one
<!-- chat-id: f6359347-eed0-44c8-ae9a-5816190468e4 -->
- Create `scripts/calc_sos_elo.py` — parameterized version of both season scripts, accepting `--season-index N` and `--start-row N`; output paths derived from season index automatically
- Create `scripts/verify_sos_elo.py` — merged version of both stub verifiers, accepting `--season-index N`
- Update `scripts/run_all.py` to call the new script twice (season-index 2 start-row 287, season-index 3 start-row 571)
- Keep old `calc_sos_season2_elo.py` and `calc_sos_season3_elo.py` as thin wrappers until diff check passes, then delete them
- Run snapshot tests: output for both seasons must be byte-identical to golden snapshots
- Commit: `refactor: merge calc_sos_season2/3_elo.py into single calc_sos_elo.py`

### [x] Step: Delete stale root plan files
<!-- chat-id: 5f0b041e-efbc-45cc-a754-9ce8ba349dbc -->
- Delete `plan.md`, `plan2.md`, `plan3.md` from the project root
- Confirm they are not referenced anywhere: `grep -r "plan\.md\|plan2\.md\|plan3\.md" --include="*.py" --include="*.md" .`
- Commit: `chore: remove stale working-note plan files from project root`

### [x] Step: Add --season-index CLI arg to hard-coded scripts
<!-- chat-id: 79c1473f-54a9-47e6-bc28-d4b9c81c2c2a -->
- Add `argparse` with `--season-index` (default: 2) to `playoff_race_html.py`, `playoff_race_table.py`, `calc_playoff_probabilities.py`
- Replace all hard-coded `seasonIndex == 2` filters with the CLI arg value
- Verify: run each script with default arg and confirm HTML output is identical to the golden snapshot
- Commit: `refactor: add --season-index arg to playoff scripts`

### [x] Step: Create scripts/common.py for shared utilities
<!-- chat-id: 8d95153c-21b1-45e3-822b-3b6acc5be5ed -->
- Create `scripts/common.py` with: `normalize_team_name()`, `to_int()`, `norm_rank()`, `mean_safe()`, `read_elo_map()`, `read_team_meta()`
- Update all callers in `calc_sos_elo.py`, `calc_sos_by_rankings.py` to import from `scripts.common`
- Run snapshot tests to verify all outputs unchanged
- Commit: `refactor: extract shared utilities into scripts/common.py`

### [ ] Step: Low-priority cosmetic cleanup
<!-- chat-id: 8820fdb5-f2f2-4fe1-9467-f37c9370c3be -->
- Move `stats_scripts/STATS_VISUALIZATION_PLAN.md`, `RANKINGS_VISUALIZATION_PLAN.md`, `CORRELATION_IDEAS.md` to `spec/` and update links in `stats_scripts/README.md`
- Rename `mega_elo.csv` → `MEGA_elo.csv`; update all `--elo-csv` defaults and hard-coded opens in `week18_simulator.py`, `calc_playoff_probabilities.py`, `playoff_race_table.py`, `playoff_race_html.py`
- Rename `export_2027_rookies.py` → `export_rookies.py` and add `--year` arg; update README reference
- Remove stale "scaffold" language from docstrings/log messages in the merged `calc_sos_elo.py`
- Run snapshot tests to confirm no regressions
- Commit: `chore: cosmetic cleanup — rename files, move design docs, fix stale comments`
