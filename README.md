# MEGA League analytics — Madden 27

Current data: **Madden 27, season 1 (`seasonIndex=0`), results through Week 14**. The team/rankings export has `weekIndex=13`; scheduled games at that index are display Week 14. The supplied **Week 8 ELO** ratings are used for this analysis with the user's approval.

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

Reusable implementations live in the `mega/` Python package. `scripts/` and `stats_scripts/` retain compatible commands and import paths. The package separates input contracts, standings, stats, roster/draft calculations, reporting, and pipeline infrastructure.

`mega/pipeline/execution.py` defines the shared task graph, and `mega/pipeline/artifacts.py` registers generated files and browser datasets. Pipeline commands build in a clean staging workspace and publish only after output and site validation. `output/build_manifest.json` identifies the input snapshot and hashes generated artifacts; its browser copy is `docs/data/build_manifest.json`. `docs/site_manifest.json` declares pages and their artifact/data requirements. `docs/data/data_manifest.json` resolves browser dataset keys to concrete URLs for the active cycle.

| Area | Main code | Purpose |
| --- | --- | --- |
| Playoff and draft race | `scripts/run_all_playoff_analysis.py`, `mega/standings/` | Monte Carlo probabilities, shared completed-game standings, schedule strength, team scenarios, draft order |
| Stats and trades | `scripts/run_all_stats.py`, `mega/stats/` | Team statistics, player usage, rankings, trade-aware team stints |
| ELO SoS | `scripts/calc_sos_elo.py` and season wrappers | Opponent ELO, schedules, strength-of-schedule tables |
| Roster and draft reports | `mega/roster/`, `mega/draft/`, `mega/reporting/` | Roster scores, draft classes, player exports |
| Salary cap | `docs/roster_cap_tool/` | Contracts, releases, trades, cap projections, saved scenarios |
| Depth charts | `docs/depth_chart/` | Roster edits, positional slots, draft picks and export |
| OVR research | `scripts/players_ovr/` | Position formulas, model training, position-change analysis |

`docs/` contains both reusable application code and generated reports. The rendered Madden 26 reports moved to the archive; the applications stayed. Current playoff calculations read the ELO week from cycle metadata, and browser charts use the generated one-week `docs/data/current_elo.csv` view while retaining the raw multiweek ELO file. The cap and depth-chart apps share CSV loading and cycle-scoped browser storage; users can deliberately copy legacy data or import/export a backup. Formula references remain in `Formula.md` and `spec/`. Saved coefficients, the guard model, and the attribute reference remain under `output/` as explicit exceptions to clearing generated data.

See [AGENTS.md](AGENTS.md) for module responsibilities, data contracts, rollover constraints, and testing instructions. The [dashboard catalog](docs/README.md) and [script guide](scripts/README.md) describe the retained implementations. The [previous README](archive/madden-26/reference/README.md) retains the detailed Madden 26 workflows.

## Export and update workflow

1. Go to the [MEGA export page](https://neonsportz.com/leagues/MEGA/export).
2. Set the delivery email to **lespaul1488@gmail.com**.
3. Export both **Basic Info** and **Stats**.
4. Open that mailbox and download the ZIP attachments from the **two export emails**.
5. Validate both ZIPs and the matching ELO CSV before changing active files:

   ```bash
   python3 scripts/validate_import.py \
     --basic-info-zip /path/to/basic-info.zip \
     --stats-zip /path/to/stats.zip \
     --elo-csv /path/to/mega_elo.csv \
     --users-csv /path/to/MEGA_users.csv \
     --season-index 0 --elo-source-week 8
   ```

   Validation does not change active files. `MEGA_users.csv` is maintained separately from the NeonSportz ZIPs; it preserves approved GM labels and raw exported usernames and is checked against `MEGA_teams.csv.userName`. After reviewing the reported season/week, run the same command with `--activate`. It installs the canonical CSVs and matching metadata together. Leave `archive/madden-26/` unchanged.
6. Run `python3 scripts/run_all.py --season-index 0` from the repository root. The runner stages calculations, validates SoS and required outputs, then publishes the complete generated set. Inspect the refreshed dashboards.
7. Commit the updated inputs and intended generated results on a feature branch, then push the branch to Git. Review the staged files before committing. The full build manifests, browser data manifest, existing published results, and generated pages belong to the publication. The registered publication output families are explicitly versionable; the artifact registry defines which generated files belong in the site. See the publication policy below.
8. Open a pull request, review the changes and checks, then **merge the pull request into `master`**. GitHub Pages publishes this repository from `master`, path `/`; pushing a feature branch alone does not update the live site. Verify the Pages configuration if hosting changes.
9. Wait for the GitHub Pages build **and deployment** for the merged commit to succeed. A successful build with a queued or waiting deployment is not a live update. Inspect failures and report any external blocker instead of claiming completion.
10. Open the [public playoff table](https://lespaui.github.io/mega_league/docs/playoff_race_table.html) and landing page after deployment. Verify the displayed week against `docs/data/import_metadata.json`, the update date, and representative refreshed standings. Verify the live metadata snapshot ID matches the local import. If caching is suspected, use a commit-specific query parameter and check again. Report the live link and verification result; if deployment is still pending, say so explicitly.

For an ordinary request to refresh NeonSportz data and push/publish the update, complete steps 1–10, including the PR merge and live verification. Stop at a feature branch only when the user explicitly requests branch-only or PR-only delivery. Documentation alone does not authorize running the workflow.

## Start Madden 27

1. Follow the [export workflow above](#export-and-update-workflow) to validate and activate fresh NeonSportz data. Core inputs are `MEGA_teams.csv`, `MEGA_games.csv`, `MEGA_players.csv`, and `MEGA_rankings.csv`; the importer also checks all six positional-stat exports, draft/trade exports, users, and the selected ELO column. See [input columns](spec/data_inputs.md). Do not copy archived league rows into current inputs.
2. Inspect the new schema and actual season/week indices. Madden **27** is the game edition; it does not determine the franchise draft year or CSV `seasonIndex`.
3. Review the validated cycle metadata before running calculations. Runners accept the zero-based CSV `--season-index`; ELO artifact names use a one-based display season internally. `--start-row` is deprecated and ignored. Keep the ELO source week distinct from the export week.
4. Run the appropriate pipeline. The first run after import should be `python3 scripts/run_all.py --season-index 0`; it stages stats, ELO and rankings SoS, playoff reports, roster rankings, browser data, and navigation together. Stats-only and playoff-only runs require a completed full-build manifest for the same input snapshot.
5. `python3 scripts/generate_index.py` renders the root landing page only. It reads `docs/site_manifest.json` and links an artifact-backed page only when its files match `output/build_manifest.json` for the active snapshot. With missing core exports it shows an awaiting-data message.
6. Serve the repository root with `python3 -m http.server 8000` and open [the local site](http://localhost:8000/index.html). Root CSV and output paths are part of the frontend contract.

Pipeline commands after the import and season review:

```bash
python3 scripts/run_all_stats.py
python3 scripts/run_all_playoff_analysis.py --season-index 0
python3 scripts/run_all.py --season-index 0
```

The shared task graph runs each prerequisite once, stops after a failure, and validates complete schedules and ELO coverage before browser publication. Playoff Monte Carlo tasks use seed 0, recorded in the build manifest, so full and subset runs reproduce the same simulation inputs. Full builds write a snapshot/schema manifest and publish from staging with rollback. See [the script guide](scripts/README.md) for task selectors.

Cap and depth-chart saved data live in browser storage, outside this repository. Both tools now scope new data by edition, CSV season, and calendar year. They do not automatically apply old unscoped data. The in-page storage controls can export a backup, copy legacy entries into the selected cycle after confirmation, or import a backup without overwriting existing cycle values; legacy keys remain intact. The playoff dashboard's community-prediction integration still needs a separate Madden 27 store before use; remote Madden 26 votes were not migrated by this archive.

## Verification

Run the fixture suite and Node checks from any working directory by passing the absolute script path, or from the repository root:

```bash
python3 scripts/check.py
```

The legacy cap projection test currently fails six assertions in scenarios B/C/D. The default check command reports failure. During structural refactoring, this explicit option accepts only that exact known failure set; any new failure still fails the run:

```bash
python3 scripts/check.py --allow-known-cap-failures
```

For a full staged build, including active-page and browser-data validation without changing published files:

```bash
python3 scripts/check.py --build --allow-known-cap-failures
```

After a full build has published locally, validate the assembled tree and run the current-cycle browser smoke suite:

```bash
python3 scripts/verify_site.py
npm ci
npx playwright install chromium
npm run test:e2e:smoke
```

An installed Chrome can be used explicitly with `PLAYWRIGHT_CHROMIUM_CHANNEL=chrome npm run test:e2e:smoke`.

`python3 scripts/check.py --site --browser --allow-known-cap-failures` combines fixture, Node, current-site and browser checks. The broader `npm run test:e2e` suite retains historical fixtures and is not the current-cycle smoke gate. The legacy draft KPI verifier also has expectations that need separate review; structural extraction preserves its original output.

## Publication policy

The repository root remains the hosting surface: `index.html`, maintained `docs/` applications, generated reports, root CSV inputs, and browser-consumed `output/` files. Do not serve only `docs/`. Publishing a site externally or changing hosting configuration is a separate operation.

Registered generated text files are normalized to LF before hashing, matching `.gitattributes`; committing and checking out the publication therefore preserves manifest hashes. Raw inputs and protected assets are not changed by this assembly step.

Each full build emits `output/build_manifest.json`, `docs/data/build_manifest.json`, and `docs/data/data_manifest.json`. Keep both build manifests and the data manifest with the generated files they describe when committing a refresh. Existing tracked publication files remain tracked. The registered publication output families are allowed by `.gitignore`; optional research output and temporary files remain ignored. When adding a new artifact family, update its registry entry and the publication allowlist together. Stage only intended files listed in the build manifest’s `artifacts` map. Protected formulas/models are versioned separately and never treated as disposable build output.

Subset builds require a complete same-snapshot full build. All manifest-listed files must still match their hashes. Navigation rendering runs no calculations. A failed build leaves the previous publication intact; successful builds clean only registry-owned obsolete files for the same snapshot.

Core Python calculations use the standard library; optional OVR/plotting workflows have additional dependencies. Frontend applications use vanilla JavaScript and browser storage.
