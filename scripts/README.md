> **Madden 27 current cycle:** Season 1 (`seasonIndex=0`), results through Week 14, using the supplied Week 8 ELO ratings. Current runners accept `--season-index 0`. See the root README and AGENTS.md for import details; historical examples below may still refer to Madden 26 seasons.

# Scripts Overview

This folder contains compatible command-line entry points and helpers for the MEGA League analysis project. Extracted implementations live under `mega/`: `inputs/`, `standings/`, `stats/`, `roster/`, `draft/`, `reporting/`, and `pipeline/`. Most users only need a few core commands; the rest are domain tools, verifiers, and developer helpers.

## Entry points (recommended)

Run these from the repo root (runner and extracted CLI imports also work from other directories using absolute script paths):

- `python3 scripts/validate_import.py --basic-info-zip BASIC.zip --stats-zip STATS.zip --elo-csv mega_elo.csv --users-csv MEGA_users.csv --season-index 0 --elo-source-week 8` – validate a candidate import. The GM/username map is a separate, provenance-tracked input because it is not included in NeonSportz ZIPs. Add `--activate` only after reviewing the report.
- `python3 scripts/run_all.py --season-index 0` – full staged pipeline: stats, ELO and rankings SoS, scenarios/reports, roster rankings, browser data, and root navigation. Scenario simulations use seed 0, which the build manifest records.
- `python3 scripts/run_all_stats.py` – stats-only selector over the shared task graph.
- `python3 scripts/run_all_playoff_analysis.py --season-index 0` – playoff-only selector, including ELO schedule validation.
- `python3 scripts/calc_sos_elo.py --csv-season-index 0 --elo-source-week 8` – direct ELO SoS run using zero-based CSV season selection and the declared Week 8 rating column.
- `python3 scripts/verify_sos_elo.py --season-index 1` – verify schedules and ELO SoS for one-based display season 1.
- `python3 scripts/generate_index.py` – render root `index.html` from the declared site and artifact manifests; it does not run calculations.

The full pipeline stages files before publication, validates active pages and browser datasets, and rolls back if a publish step fails. `mega/pipeline/artifacts.py` owns producer outputs and browser data URLs. `docs/data/data_manifest.json` supplies logical dataset keys to the frontend. Stats-only and playoff-only runs require a complete build manifest for the same input snapshot. See the root README for the weekly workflow.

## Python domain tools

Domain‑specific scripts that can be run directly or via the entry points:

- **Playoff / draft / SoS (rankings‑based)**  
  `calc_sos_by_rankings.py`, `calc_remaining_sos.py`, `calc_playoff_probabilities.py`,  
  `generate_all_team_scenarios.py`, `playoff_race_table.py`, `playoff_race_html.py`,  
  `generate_team_scenario_html.py`, `top_pick_race_analysis.py`, `generate_index.py`; standings logic is shared in `mega/standings/records.py`, with `standings_domain.py` retained as a compatibility import.
- **ELO SoS**
  `calc_sos_elo.py` and compatibility season wrappers; old start-row flags are accepted but ignored in favor of `seasonIndex`/`stageIndex` filtering. `verify_sos_elo.py` validates actual schedule and SoS contracts.
- **Draft & rookies**  
  `generate_draft_class.py`, `generate_draft_class_analytics.py`,  
  `verify_draft_class_analytics.py`, `verify_draft_round1_recap.py`, `export_rookies.py`.
- **Roster / cap**  
  `power_rankings_roster.py`, `calc_team_y1_cap.py`, `verify_cap_math.py`,  
  `verify_power_rankings_roster_csv.py`, `verify_power_rankings_roster_html.py`,  
  `verify_team_rosters_export.py`, `verify_trade_stats.py`.
- **Misc helpers**  
  `add_metric_helps.py`, `week18_simulator.py`.  
  JSON fixtures for some scripts live under `scripts/fixtures/`.

For most workflows you should prefer the entry‑point scripts; the domain tools are useful for one‑off debugging or experimentation.

## Verifiers

Run `python3 scripts/check.py` for the Python/Node suite; `--build`, `--site`, and `--browser` add staged-build, assembled-publication, and current-cycle browser checks. The default command reports the existing cap B/C/D failures; `--allow-known-cap-failures` accepts only their exact six-assertion baseline.

`python3 scripts/verify_site.py [--root PATH]` is a read-only assembled-site gate. It checks active snapshot hashes, enabled pages and their data requirements, local assets, and nested JS module imports.

Verification scripts are named `verify_*.py`. The SoS verifier is read-only; some domain verifiers intentionally write reports under `output/`:

- Playoff / SoS: `verify_sos_elo.py`, `verify_trade_stats.py`, `verify_table_scroll_wrap.py`.
- Draft class: `verify_draft_class_analytics.py`, `verify_draft_round1_recap.py`.
- Roster / cap: `verify_cap_math.py`, `verify_power_rankings_roster_csv.py`, `verify_power_rankings_roster_html.py`, `verify_team_rosters_export.py`, `verify_trade_stats.py`.

Each verifier prints a short summary and usually writes additional CSV/JSON files under `output/` for inspection. Recommended verifiers for each workflow are listed in `README.md`.

## Non‑Python helpers

Non‑Python helpers are isolated in subfolders so the top‑level `scripts/` view stays focused on Python entry points and tools.

- `scripts/tests/` – Node/Playwright‑style developer tests (not part of the main pipelines).
  - `check_year_context.js` – Playwright helper to inspect year‑context UI in a running dev server.
  - `check_year_context_port.js` – Variant that spins up a local `http.server` before testing.
  - `test_cap_tool.mjs` – Node ESM unit tests for `docs/roster_cap_tool/js/capMath.js`.
  - `test_cycle_storage.mjs` – cycle-scoped storage, migration, and backup behavior.
  - `test_current_elo.mjs` – declared-week browser ELO data and metadata checks.
  - `test_shared_csv.mjs` – shared browser CSV loader success/error handling.
  - `test_year_context.mjs` – Node ESM unit tests for Year Context helpers in the cap tool.
- `scripts/smoke/` – Shell smoke tests that exercise end‑to‑end flows.
  - `smoke_generate_draft_2026.sh` – Generates `docs/draft_class_2026.html` and runs draft verifiers.
  - `smoke_roster_cap_tool.sh` – Serves the repo and checks that `docs/roster_cap_tool` + CSVs are available.
- `scripts/tools/` – Small maintenance utilities.

Run these helpers from the repo root, for example:

```bash
node scripts/tests/test_cap_tool.mjs
node scripts/tests/test_cycle_storage.mjs
node scripts/tests/test_current_elo.mjs
node scripts/tests/test_shared_csv.mjs
node scripts/tests/test_year_context.mjs
bash scripts/smoke/smoke_generate_draft_2026.sh
bash scripts/smoke/smoke_roster_cap_tool.sh
```

## Conventions for new scripts

When adding new code:

- **Calculation implementations** belong in the relevant `mega/` domain package. Keep `scripts/` and `stats_scripts/` as compatible CLI adapters; do not introduce working-directory changes or `sys.path` changes inside package implementations.
- **Entry points** that orchestrate several steps should start with `run_all_` and live at the top level of `scripts/`.
- **Verifiers** should be named `verify_*.py` and placed at the top level of `scripts/`, near the workflow they validate.
- **Smoke tests** belong in `scripts/smoke/` and are typically small shell scripts that call existing Python tools.
- **Dev/test helpers** (Node/Playwright scripts) belong in `scripts/tests/`.
- **Utility tools** such as file sync scripts belong in `scripts/tools/`.

If your new script generates or updates an HTML page under `docs/`, document it in:

- The relevant section of `README.md` (Architecture / Quick Start / Workflow), and
- `docs/README.md` under the appropriate domain table (Playoff & SoS, Stats Dashboards, Roster / Cap, Misc & Utilities).
