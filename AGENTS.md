# MEGA League agent guide

## Current cycle and boundaries

- Active game: **Madden 27, season 1 (`seasonIndex=0`)**, with results through Week 12 plus completed Week 13 games. Team/rankings exports have `weekIndex=12`; scheduled games at that index are display Week 13.
- Madden 26 is archived under `archive/madden-26/` (2026-10-24). See its `README.md` and `manifest.json` for provenance, inventory, and recovery.
- Treat the archive as immutable historical evidence. Exclude `archive/` from normal searches and data discovery. Read it only for explicit historical work or a deliberate comparison.
- Never restore Madden 26 CSVs into the active root as a fallback for missing Madden 27 data. Do not create fabricated league data or empty results to make a pipeline appear successful.
- The rollover preserved calculation source and formula artifacts. Current runners are configured for CSV season 0 and locate the season in the export. OVR model calibration is **not yet validated for Madden 27**; inspect fresh exports before adapting configuration.
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
| Team/player statistics and trades | `stats_scripts/aggregate_team_stats.py`, `aggregate_player_usage.py`, `aggregate_rankings_stats.py`, `build_player_team_stints.py`; implementations in `mega/stats/`, CSV/cycle/identity contracts in `mega/inputs/`, compatibility exports in `stats_scripts/` | Team aggregation, usage, rankings, player/team stint and traded-player CSVs; stats/trade dashboards |
| ELO strength of schedule | `scripts/calc_sos_elo.py`, season 2/3/4 wrappers, `scripts/common.py` | Reads the declared cycle ELO week; produces `output/sos/`, `output/schedules/`, and a one-week `docs/data/current_elo.csv` browser view while retaining the raw multiweek source copy |
| Roster rankings and draft analysis | `scripts/power_rankings_roster.py`, `generate_draft_class*.py`, `generate_draft_rounds_recap.py`, `export_rookies.py` | Roster scores/exports, rookie CSVs, generated draft and roster HTML reports |
| Cap management | `docs/roster_cap_tool/js/` | Vanilla ES modules: `csv.js`/`models.js` parse inputs; `capMath.js`/`contractUtils.js` calculate; `context.js` handles year offsets; `state.js` owns scenarios; `ui/` renders controls |
| Depth charts | `docs/depth_chart/js/` | Vanilla JS roster/slot editing, draft picks, CSV export; `state.js` and browser storage hold edits |
| Shared standings rules | `mega/standings/records.py` (`scripts/standings_domain.py` compatibility import) | Pure completed-game records, conference/division results, and strength metrics shared by playoff probabilities and the Week 18 simulator |
| OVR research | `scripts/players_ovr/` | Optional ML workflow, per-position training exports, coefficients and serialized models |

`docs/` mixes source applications with generated output. Do not archive or delete all HTML indiscriminately. Stats, SoS, playoff-bracket and roster-chart readers are source; draft reports, playoff-race tables, team scenarios, week-18 simulator output, and roster-ranking reports embed a particular dataset and must be regenerated.

Reusable references: `Formula.md`, `spec/`, `scripts/README.md`, `docs/README.md`, and `docs/roster_cap_tool/USAGE.md`. Preserved formula artifacts also include `output/attributes.md`, `output/individual_position_formulas.txt`, and `output/trained_models/`. These are exceptions to treating `output/` as disposable. Their Madden 26 provenance must not be mistaken for Madden 27 calibration.

### Orchestration and rollover traps

- `scripts/run_all.py --season-index 0`: player/team stints first, then team/usage/rankings aggregation, ELO and rankings SoS for the selected season, playoff scenarios/reports, the Week 18 simulator, draft race, roster power rankings, trade verification, browser-data publication and root index. The default is CSV season 0.
- `mega/pipeline/execution.py` owns the dependency graph; `scripts/pipeline_tasks.py` preserves its compatible API, selected by `run_all.py`, `run_all_stats.py`, and `run_all_playoff_analysis.py`. Playoff Monte Carlo tasks use seed 0 and record it in the build manifest. Tasks stop after the first failure. The full runner builds in a clean temporary workspace, validates required outputs and SoS artifacts, records `output/build_manifest.json`, then publishes changed files with rollback on a publication error. Subset builds require a complete manifest for the same input snapshot.
- `scripts/run_all_stats.py`: player/team stints before dependent aggregations, trade verification, and navigation rendering.
- `scripts/run_all_playoff_analysis.py --season-index 0`: ELO and rankings SoS, playoff scenarios/reports, draft race, browser-data publication and navigation rendering.
- `scripts/run_utils.py` launches subprocesses. Optional-step failures are failures; only a task explicitly disabled by configuration is skipped.
- `mega/pipeline/artifacts.py` centrally registers generated outputs, ownership, and logical browser datasets. `docs/data/data_manifest.json` maps those dataset keys to URLs relative to the manifest. `scripts/verify_site.py` validates enabled pages, data, local assets and snapshot hashes; staged builds run it before publication. Maintain `requires` and `requiresData` in `docs/site_manifest.json` when adding consumers.
- `scripts/generate_index.py` writes **root `index.html`**, despite older docs mentioning `docs/index.html`. It renders navigation only, using the declared `docs/site_manifest.json` inventory and the active snapshot's build manifest. Missing or mismatched artifacts are not linked.
- `scripts/calc_sos_elo.py` now selects rows by the CSV `seasonIndex` and regular-season `stageIndex`. The legacy one-based `--season-index` argument and row flags remain adapters; current runners pass `--csv-season-index`.
- `scripts/validate_import.py` validates Basic Info and Stats ZIPs, the ELO CSV, and the separately maintained `MEGA_users.csv` map before activation. Validation-only is the default; `--activate` installs the fully validated CSV set and metadata with rollback on a failed file replacement. The NeonSportz ZIPs do not contain the user map, so pass it with `--users-csv`.
- `scripts/verify_sos_elo.py --season-index N` checks reciprocal schedules, complete opponent ELOs, team counts, ranks, and CSV/JSON agreement for display season N.
- Season-specific SoS HTML and the draft tools/tests contain historical filenames and year assumptions. These are reusable implementations, not current results.
- `docs/playoff_dashboard.html` contains a legacy community-prediction service configuration. Do not use its Madden 26 remote store for Madden 27; set up a separate store before enabling predictions. Local archival does not archive remote votes.
- Browser cap/depth-chart scenarios are outside Git. New storage is scoped by edition, CSV season, and calendar year. Legacy unscoped entries stay in their original keys; the in-page controls require a deliberate copy or backup import and never overwrite an existing cycle value. Do not automatically clear browser state. Both tools require active `docs/data/import_metadata.json` before reading or writing cycle-scoped state.

## Data contracts

The user-maintained [export and update workflow](README.md#export-and-update-workflow) is the standard refresh procedure: request **Basic Info** and **Stats** at `https://neonsportz.com/leagues/MEGA/export`, delivered to **lespaul1488@gmail.com**; download the ZIP attachments from both emails, extract the CSVs into the repository root, run and verify the configured pipelines, commit and push a feature branch, then open and merge its pull request. Documenting this procedure does not itself request an export, email access, or Git publication; perform those actions when the user asks to execute the workflow.

The approved ELO snapshot is **Week 8**, used with the exports refreshed on 2026-10-27 (including completed Week 13 games); preserve that source label. `mega_elo.csv` holds the source ratings and GM labels, `MEGA_users.csv` maps exported NeonSportz usernames separately, and `docs/data/import_metadata.json` records source-byte and normalized working-file hashes plus week conventions. Current playoff calculations and browser charts must use the declared metadata week; `docs/data/current_elo.csv` is the one-week browser view. Do not overwrite `MEGA_teams.csv` usernames with screenshot GM labels.

See `spec/data_inputs.md` for columns. Import fresh, mutually consistent `MEGA_teams.csv`, `MEGA_games.csv`, `MEGA_players.csv`, `MEGA_rankings.csv`, positional stat exports, draft/trade exports as required, and fresh `mega_elo.csv` for ELO analysis. Preserve the lower-case on-disk ELO filename; some older prose uses a different spelling.

Joins use team names/abbreviations and player IDs; respect normalization and trade-aware stint logic. Confirm `seasonIndex`, `stageIndex`, `weekIndex`, and displayed draft years from the new exports. Madden edition, franchise year, and season index are different concepts.

Player statistics CSVs contain season totals, not individual game box scores. For a specific game's player stats use the NeonSportz game page with the CSV's `id` field, not `gameId`, and its Player tab. Never infer a box score from season totals.

## Development and validation

Reusable Python code lives in `mega/inputs/`, `mega/standings/`, `mega/stats/`, `mega/roster/`, `mega/draft/`, `mega/reporting/`, and `mega/pipeline/`. Existing script and stats-script paths are compatibility entry points. Keep new calculation code in the package and retain explicit input/output paths; package imports must not change the working directory.

Python core uses the standard library. Optional OVR research needs the dependencies in `scripts/players_ovr/requirements.txt`; plotting may also need optional libraries. Follow existing coding style. Frontend is vanilla JS; cap-tool modules declare ESM in their local `package.json`.

Use `python3 scripts/check.py` for all fixture and Node checks. Its default exit code includes the recorded cap B/C/D failures. `--allow-known-cap-failures` permits only that exact six-assertion baseline; other failures remain fatal. Add `--build` for a full staged build without publication, `--site` for read-only validation of the current publication, and `--browser` for current-cycle browser smoke tests after installing Playwright.

Individual fixture-based and data-independent checks, from repository root:

```bash
python3 -m unittest discover -s tests -p 'test_current_cycle.py'
python3 -m unittest discover -s tests -p 'test_elo_column.py'
python3 -m unittest discover -s tests -p 'test_index_generation.py'
python3 -m unittest discover -s tests -p 'test_power_rankings_roster.py'
python3 -m unittest discover -s tests -p 'test_import_validation.py'
python3 -m unittest discover -s tests -p 'test_pipeline_tasks.py'
python3 -m unittest discover -s tests -p 'test_sos_verifier.py'
python3 -m unittest discover -s tests -p 'test_site_manifest.py'
python3 -m unittest discover -s tests -p 'test_standings_domain.py'
python3 -m unittest discover -s tests -p 'test_snapshots.py'
python3 -m unittest discover -s tests -p 'test_week18_input.py'
python3 scripts/tests/test_week_numbers.py
node scripts/tests/test_cycle_storage.mjs
node scripts/tests/test_current_elo.mjs
node scripts/tests/test_shared_csv.mjs
node scripts/tests/test_data_manifest.mjs
node scripts/tests/test_year_context.mjs
node scripts/tests/test_cap_tool.mjs
```

All new fixture tests write only to temporary directories. The cap-tool test had recorded projection expectation failures in scenarios B/C/D at rollover; classify those separately and do not change formulas merely to make them green.

`tests/test_snapshots.py` is now a safe fixture-based contract suite; importing it does not run pipelines. It covers malformed inputs, valid empty trades, trade-aware stints, ties, multiple seasons, postseason filtering, and seeded simulation output.

After data import/configuration, use the appropriate pipeline and `scripts/verify_*.py`. Playwright E2E tests in `tests/e2e/` require data and generated pages; some assert historical players/seasons. Update those fixtures deliberately before treating E2E as Madden 27 validation.

```bash
python3 -m http.server 8000  # serve repository root, open /index.html
npm install
npm run pw:install
npm run test:e2e:smoke  # current-cycle manifest and browser-tool checks
npm run test:e2e        # broader historical fixtures require deliberate review
```

Playwright config serves port 8000 with Chromium projects for cleared/persisted storage. Avoid serving just `docs/` for tools that read root CSVs and `output/`.

## Git and maintenance

### Refresh completion and live publication

- A user request to refresh NeonSportz data and push/publish the update authorizes the complete README export workflow: import, full build, validation, feature-branch push, PR review/merge, and live-site verification. Honor an explicit branch-only or PR-only restriction. Do not stop after pushing a feature branch for an ordinary refresh.
- GitHub Pages currently serves `master`, path `/`, at `https://lespaui.github.io/mega_league/`. Verify the hosting configuration before publication; merge the validated update into the configured publishing branch through a PR. A feature-branch push is not deployment.
- Before merging, check regenerated page titles, visible week labels, and update timestamps against the active snapshot. Derive week labels from cycle metadata; never hard-code a week in a reusable generator. A timestamp labeled ET must use `America/New_York`, including daylight saving time.
- Wait for both the Pages build and deployment for the merged commit to succeed. Build success alone is insufficient. If deployment is queued, waiting, or failed, continue investigating and report its actual state; do not say the update is live.
- After deployment, read the public landing page and `docs/playoff_race_table.html`. Confirm the active week, update date, and representative standings; compare the public `docs/data/import_metadata.json` snapshot ID with the local snapshot. Use a commit-specific cache-busting query if needed. Local tests and repository files do not prove the public site updated.
- Report completion with the verified public URL and merged commit/PR. If external deployment or authentication prevents completion, state what remains pending. Preserve the existing six known cap-test failures separately from new failures.

Keep commits short and descriptive. Follow the repository's `mega-<feature>-<short-id>` branch naming convention when a branch is needed. Never commit fresh exports or generated results into the historical archive. For the current repository-root hosting model, keep `output/build_manifest.json`, `docs/data/build_manifest.json`, and `docs/data/data_manifest.json` with the generated publication they describe. Existing tracked outputs remain versioned; add new generated outputs only when their registered artifact paths are required by the site. Temporary builds, logs, test reports, and optional research output remain ignored. Do not commit/push unless the user requests it. Update current documentation when changing entry points or data contracts; older instructions under `archive/` are historical only.
