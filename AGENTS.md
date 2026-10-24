# MEGA League agent guide

## Current cycle and boundaries

- Active game: **Madden 27**. No Madden 27 league exports have been imported yet.
- Madden 26 is archived under `archive/madden-26/` (2026-10-24). See its `README.md` and `manifest.json` for provenance, inventory, and recovery.
- Treat the archive as immutable historical evidence. Exclude `archive/` from normal searches and data discovery. Read it only for explicit historical work or a deliberate comparison.
- Never restore Madden 26 CSVs into the active root as a fallback for missing Madden 27 data. Do not create fabricated league data or empty results to make a pipeline appear successful.
- The rollover preserved calculation source and formula artifacts. Legacy season defaults and model calibration are **not yet validated for Madden 27**; inspect fresh exports before adapting configuration.
- Preserve formulas, weights, cap math, tiebreakers, OVR coefficients, and trained models unless the user specifically requests changes to those calculations.
- Preserve unrelated user changes. Untracked `.zenflow/tasks/` work predating the rollover remains user-owned.
- After fixes, remove temporary review/fix reports and generated test artifacts that are no longer needed. Report outcomes in chat; preserve history in Git. Keep current documentation and explicitly requested archives.

## Architecture

This is a file-based analytics pipeline and static website, with no application server or database.

```text
NeonSportz exports: MEGA_*.csv + mega_elo.csv (repository root)
    ├── scripts/ + stats_scripts/ → output/ CSV, JSON, reports
    │                                  └── docs/ dashboard readers
    ├── scripts/ HTML generators → docs/ rendered reports with embedded data
    └── docs/roster_cap_tool/ + docs/depth_chart/ → direct CSV reads

scripts/generate_index.py → index.html (repository root)
archive/madden-26/ → isolated historical data/site, never active inputs
```

### Domain ownership

| Domain | Implementation | Outputs / consumers |
| --- | --- | --- |
| Playoff probabilities, standings, tiebreakers, draft race | `calc_playoff_probabilities.py`, `team_scenario_report.py`, `generate_all_team_scenarios.py`, `calc_remaining_sos.py`, `calc_sos_by_rankings.py`, `top_pick_race_analysis.py` in `scripts/` | `output/playoff_probabilities.json`, `output/team_scenarios.json`, SoS tables, draft-race reports; HTML renderers in `scripts/` |
| Team/player statistics and trades | `stats_scripts/aggregate_team_stats.py`, `aggregate_player_usage.py`, `aggregate_rankings_stats.py`, `build_player_team_stints.py`; shared helpers in `stats_common.py` | Team aggregation, usage, rankings, player/team stint and traded-player CSVs; stats/trade dashboards |
| ELO strength of schedule | `scripts/calc_sos_elo.py`, season 2/3/4 wrappers, `scripts/common.py` | `output/sos/`, `output/schedules/`, browser copies under `docs/data/` |
| Roster rankings and draft analysis | `scripts/power_rankings_roster.py`, `generate_draft_class*.py`, `generate_draft_rounds_recap.py`, `export_rookies.py` | Roster scores/exports, rookie CSVs, generated draft and roster HTML reports |
| Cap management | `docs/roster_cap_tool/js/` | Vanilla ES modules: `csv.js`/`models.js` parse inputs; `capMath.js`/`contractUtils.js` calculate; `context.js` handles year offsets; `state.js` owns scenarios; `ui/` renders controls |
| Depth charts | `docs/depth_chart/js/` | Vanilla JS roster/slot editing, draft picks, CSV export; `state.js` and browser storage hold edits |
| OVR research | `scripts/players_ovr/` | Optional ML workflow, per-position training exports, coefficients and serialized models |

`docs/` mixes source applications with generated output. Do not archive or delete all HTML indiscriminately. Stats, SoS, playoff-bracket and roster-chart readers are source; draft reports, playoff-race tables, team scenarios, week-18 simulator output, and roster-ranking reports embed a particular dataset and must be regenerated.

Reusable references: `Formula.md`, `spec/`, `scripts/README.md`, `docs/README.md`, and `docs/roster_cap_tool/USAGE.md`. Preserved formula artifacts also include `output/attributes.md`, `output/individual_position_formulas.txt`, and `output/trained_models/`. These are exceptions to treating `output/` as disposable. Their Madden 26 provenance must not be mistaken for Madden 27 calibration.

### Orchestration and rollover traps

- `scripts/run_all.py`: stats, ELO SoS for seasons 2/3/4, rankings SoS, playoff scenarios/reports, draft race, index, and trade verification.
- `scripts/run_all_stats.py`: four stats producers, index generation, and trade verification.
- `scripts/run_all_playoff_analysis.py`: rankings SoS, playoff scenarios/reports, and draft race.
- `scripts/run_utils.py` launches subprocesses. Main entry points normally change to the repository root.
- `scripts/generate_index.py` writes **root `index.html`**, despite older docs mentioning `docs/index.html`. With missing core exports it writes an awaiting-data page and does not run aggregation. With inputs present, its existing behavior also runs two stats aggregators.
- Do not run the full pipeline blindly after the first Madden 27 import: `run_all.py` retains Madden 26 start rows **287/571/872** and season selections; the playoff pipeline and `generate_playoff_dashboard.py` retain `seasonIndex=3` assumptions. ELO's `--season-index` is a human season number, while other tools commonly use zero-based CSV indices. Read each tool's arguments.
- Season-specific SoS HTML and the draft tools/tests contain historical filenames and year assumptions. These are reusable implementations, not current results.
- `docs/playoff_dashboard.html` contains a legacy community-prediction service configuration. Do not use its Madden 26 remote store for Madden 27; set up a separate store before enabling predictions. Local archival does not archive remote votes.
- Browser cap/depth-chart scenarios are outside Git. Export them if needed, then reset the relevant app storage or use a fresh browser profile before using new-cycle rosters. Do not automatically delete user browser state.

## Data contracts

The user-maintained [export and update workflow](README.md#export-and-update-workflow) is the standard refresh procedure: request **Basic Info** and **Stats** at `https://neonsportz.com/leagues/MEGA/export`, delivered to **lespaul1488@gmail.com**; download the ZIP attachments from both emails, extract the CSVs into the repository root, run and verify the configured pipelines, commit and push a feature branch, then open and merge its pull request. Documenting this procedure does not itself request an export, email access, or Git publication; perform those actions when the user asks to execute the workflow.

See `spec/data_inputs.md` for columns. Import fresh, mutually consistent `MEGA_teams.csv`, `MEGA_games.csv`, `MEGA_players.csv`, `MEGA_rankings.csv`, positional stat exports, draft/trade exports as required, and fresh `mega_elo.csv` for ELO analysis. Preserve the lower-case on-disk ELO filename; some older prose uses a different spelling.

Joins use team names/abbreviations and player IDs; respect normalization and trade-aware stint logic. Confirm `seasonIndex`, `stageIndex`, `weekIndex`, and displayed draft years from the new exports. Madden edition, franchise year, and season index are different concepts.

Player statistics CSVs contain season totals, not individual game box scores. For a specific game's player stats use the NeonSportz game page with the CSV's `id` field, not `gameId`, and its Player tab. Never infer a box score from season totals.

## Development and validation

Python core uses the standard library. Optional OVR research needs the dependencies in `scripts/players_ovr/requirements.txt`; plotting may also need optional libraries. Follow existing coding style. Frontend is vanilla JS; cap-tool modules declare ESM in their local `package.json`.

Data-independent checks, from repository root:

```bash
python3 -m unittest discover -s tests -p 'test_index_generation.py'
python3 -m unittest discover -s tests -p 'test_power_rankings_roster.py'
python3 scripts/tests/test_week_numbers.py
node scripts/tests/test_year_context.mjs
node scripts/tests/test_cap_tool.mjs
```

The roster-ranking test writes `output/test_power_rankings_roster_report.html`; remove that temporary result after testing. At rollover the cap-tool test already failed projection expectations in scenarios B/C/D. Do not change formulas merely to make those assertions green.

`tests/test_snapshots.py` is an old data-dependent script that executes pipelines at import time and expects absent `tests/snapshots/` data. Do not use broad discovery that imports it on an empty cycle. Target the independent test modules above. Retain the snapshot harness for an intentional refresh using Madden 27 fixtures.

After data import/configuration, use the appropriate pipeline and `scripts/verify_*.py`. Playwright E2E tests in `tests/e2e/` require data and generated pages; some assert historical players/seasons. Update those fixtures deliberately before treating E2E as Madden 27 validation.

```bash
python3 -m http.server 8000  # serve repository root, open /index.html
npm install
npm run pw:install
npm run test:e2e
```

Playwright config serves port 8000 with Chromium projects for cleared/persisted storage. Avoid serving just `docs/` for tools that read root CSVs and `output/`.

## Git and maintenance

Keep commits short and descriptive. Follow the repository's `mega-<feature>-<short-id>` branch naming convention when a branch is needed. Never commit fresh exports or generated results into the historical archive. Do not commit/push unless the user requests it. Update current documentation when changing entry points or data contracts; older instructions under `archive/` are historical only.
