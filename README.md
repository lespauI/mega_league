# MEGA League analytics — Madden 27

Current data: **Madden 27, season 1 (`seasonIndex=0`), results through Week 12**. The team/rankings export has `weekIndex=12`; scheduled games at that index are display Week 13. The supplied **Week 8 ELO** ratings are used for this analysis with the user's approval.

All 12 NeonSportz CSV exports are imported. [ELO and GM labels](mega_elo.csv), [GM-to-NeonSportz user mapping](MEGA_users.csv), and [source metadata](docs/data/import_metadata.json) preserve their provenance. The original screenshot is [available here](docs/data/elo_week8.png). Raw export usernames are unchanged.

Madden 26 exports and results remain isolated in [the archive](archive/madden-26/README.md). Calculation formulas, cap math and OVR models are preserved; OVR calibration has not been revalidated for the new game.

## Architecture

This is a Python analytics pipeline with a static HTML/JavaScript frontend. There is no backend service or database.

```text
Root NeonSportz CSV exports
  ├─ scripts/ + stats_scripts/ → output/ CSV/JSON → docs/ dashboards
  ├─ scripts/ report generators → docs/ HTML with embedded results
  └─ docs/roster_cap_tool/ + docs/depth_chart/ → browser tools

scripts/generate_index.py → root index.html
archive/madden-26/ → historical snapshot, isolated from current inputs
```

| Area | Main code | Purpose |
| --- | --- | --- |
| Playoff and draft race | `scripts/run_all_playoff_analysis.py` | Monte Carlo probabilities, tiebreakers, schedule strength, team scenarios, draft order |
| Stats and trades | `scripts/run_all_stats.py`, `stats_scripts/` | Team statistics, player usage, rankings, trade-aware team stints |
| ELO SoS | `scripts/calc_sos_elo.py` and season wrappers | Opponent ELO, schedules, strength-of-schedule tables |
| Roster and draft reports | `scripts/power_rankings_roster.py`, `scripts/generate_draft_class_analytics.py` | Roster scores, draft classes, player exports |
| Salary cap | `docs/roster_cap_tool/` | Contracts, releases, trades, cap projections, saved scenarios |
| Depth charts | `docs/depth_chart/` | Roster edits, positional slots, draft picks and export |
| OVR research | `scripts/players_ovr/` | Position formulas, model training, position-change analysis |

`docs/` contains both reusable application code and generated reports. The rendered Madden 26 reports moved to the archive; the applications stayed. Formula references remain in `Formula.md` and `spec/`. Saved coefficients, the guard model, and the attribute reference remain under `output/` as explicit exceptions to clearing generated data.

See [AGENTS.md](AGENTS.md) for module responsibilities, data contracts, rollover constraints, and testing instructions. The [dashboard catalog](docs/README.md) and [script guide](scripts/README.md) describe the retained implementations. The [previous README](archive/madden-26/reference/README.md) retains the detailed Madden 26 workflows.

## Export and update workflow

1. Go to the [MEGA export page](https://neonsportz.com/leagues/MEGA/export).
2. Set the delivery email to **lespaul1488@gmail.com**.
3. Export both **Basic Info** and **Stats**.
4. Open that mailbox and download the ZIP attachments from the **two export emails**.
5. Extract both ZIP files and place the exported `MEGA_*.csv` files in the repository root, replacing the active cycle's previous exports. Keep the original filenames and use both exports from the same update. Leave `archive/madden-26/` unchanged.
6. Run the analysis scripts from the repository root. Check the season settings below for each import, then run `python3 scripts/run_all.py --season-index 0`, run the relevant verification scripts, and inspect the refreshed dashboards.
7. Commit the updated inputs and intended generated results on a feature branch, then push the branch to Git. Review the staged files before committing; required files under the ignored `output/` directory may need to be added explicitly.
8. Open a pull request, review the changes and checks, then **merge the pull request**.

## Start Madden 27

1. Follow the [export workflow above](#export-and-update-workflow) to place fresh NeonSportz data in the repository root. Core inputs are `MEGA_teams.csv`, `MEGA_games.csv`, `MEGA_players.csv`, and `MEGA_rankings.csv`. Add the six positional-stat CSVs, draft/trade exports, and a fresh `mega_elo.csv` for the tools that use them. See [input columns](spec/data_inputs.md). Do not copy archived league rows into current inputs.
2. Inspect the new schema and actual season/week indices. Madden **27** is the game edition; it does not determine the franchise draft year or CSV `seasonIndex`.
3. Review season configuration before running calculations. Current runners default to CSV `seasonIndex=0` and accept `--season-index`. The full runner locates the selected season automatically and translates CSV index 0 to ELO season 1. Legacy season wrappers, bracket generation, and draft examples still require their own configuration. Update `docs/data/import_metadata.json` when importing a new snapshot; keep the ELO source week distinct from the export week.
4. Validate the workflows separately, then run the appropriate pipeline and verification scripts. Generate fresh results in `output/` and fresh reports/browser data in `docs/`; never write to `archive/`.
5. Run `python3 scripts/generate_index.py` to refresh the root landing page. With missing core exports it shows an awaiting-data message and skips aggregation.
6. Serve the repository root with `python3 -m http.server 8000` and open [the local site](http://localhost:8000/index.html). Root CSV and output paths are part of the frontend contract.

Pipeline commands after the import and season review:

```bash
python3 scripts/run_all_stats.py
python3 scripts/run_all_playoff_analysis.py --season-index 0
python3 scripts/run_all.py --season-index 0
```

The full runner processes the selected season only, builds player/team stints before the dependent aggregations, and publishes current browser data after verification. It also refreshes roster rankings. ELO tools and other tools use different season-index conventions; check each command's arguments.

Cap/depth-chart scenarios live in browser storage, outside this repository. Export old scenarios if desired, then reset those apps' storage or use a fresh profile for Madden 27. The playoff dashboard's community-prediction integration also needs a separate Madden 27 store before use; remote Madden 26 votes were not migrated by this archive.

## Verification without league data

```bash
python3 -m unittest discover -s tests -p 'test_current_cycle.py'
python3 -m unittest discover -s tests -p 'test_index_generation.py'
python3 -m unittest discover -s tests -p 'test_power_rankings_roster.py'
python3 scripts/tests/test_week_numbers.py
node scripts/tests/test_year_context.mjs
node scripts/tests/test_cap_tool.mjs
```

The last command has pre-existing projection expectation failures in scenarios B/C/D; the rollover leaves those calculations untouched. The roster-ranking test generates a temporary HTML report in `output/`; remove it after testing.

Do not run broad unittest discovery over `tests/test_snapshots.py`: that legacy harness runs data pipelines at import time and its golden snapshot directory is absent. Data-dependent verification scripts, snapshot tests and Playwright E2E tests need fresh inputs/generated pages and deliberate fixture updates.

For browser tests once those prerequisites are ready:

```bash
npm install
npm run pw:install
npm run test:e2e
```

Core Python calculations use the standard library; optional OVR/plotting workflows have additional dependencies. Frontend applications use vanilla JavaScript and browser storage.
