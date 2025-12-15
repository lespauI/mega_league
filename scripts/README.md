# Scripts Overview

This folder contains the main command‑line entry points and helpers for the MEGA League analysis project. Most users only need a few core commands; the rest are domain tools, verifiers, and developer helpers.

## Entry points (recommended)

Run these from the repo root:

- `python3 scripts/run_all.py` – full pipeline (stats + Season 2 SoS + playoff + index).
- `python3 scripts/run_all_playoff_analysis.py` – playoff + draft pick race only.
- `python3 scripts/run_all_stats.py` – stats‑only pipeline (team aggregation, player usage, rankings joins).
- `python3 scripts/calc_sos_season2_elo.py --season2-start-row ...` – Season 2 SoS (ELO) only.

See the “Architecture at a Glance”, “Quick Start”, and “Typical Workflow” sections in `README.md` for details on when to use each.

## Python domain tools

Domain‑specific scripts that can be run directly or via the entry points:

- **Playoff / draft / SoS (rankings‑based)**  
  `calc_sos_by_rankings.py`, `calc_remaining_sos.py`, `calc_playoff_probabilities.py`,  
  `playoff_race_table.py`, `playoff_race_html.py`, `top_pick_race_analysis.py`, `generate_index.py`.
- **Season 2 SoS (ELO)**  
  `calc_sos_season2_elo.py` (+ verifier `verify_sos_season2_elo.py`).
- **Draft & rookies**  
  `generate_draft_class.py`, `generate_draft_class_analytics.py`,  
  `verify_draft_class_analytics.py`, `verify_draft_round1_recap.py`, `export_2026_rookies.py`.
- **Roster / cap**  
  `power_rankings_roster.py`, `calc_team_y1_cap.py`, `verify_cap_math.py`,  
  `verify_power_rankings_roster_csv.py`, `verify_power_rankings_roster_html.py`,  
  `verify_team_rosters_export.py`, `verify_trade_stats.py`.
- **Misc helpers**  
  `add_metric_helps.py`, `week18_simulator.py`.  
  JSON fixtures for some scripts live under `scripts/fixtures/`.

For most workflows you should prefer the entry‑point scripts; the domain tools are useful for one‑off debugging or experimentation.

## Verifiers

Verification scripts are named `verify_*.py` and are safe to run repeatedly:

- Playoff / SoS: `verify_sos_season2_elo.py`, `verify_table_scroll_wrap.py`.
- Draft class: `verify_draft_class_analytics.py`, `verify_draft_round1_recap.py`.
- Roster / cap: `verify_cap_math.py`, `verify_power_rankings_roster_csv.py`, `verify_power_rankings_roster_html.py`, `verify_team_rosters_export.py`, `verify_trade_stats.py`.

Each verifier prints a short summary and usually writes additional CSV/JSON files under `output/` for inspection. Recommended verifiers for each workflow are listed in `README.md`.

## Non‑Python helpers

Non‑Python helpers are isolated in subfolders so the top‑level `scripts/` view stays focused on Python entry points and tools.

- `scripts/tests/` – Node/Playwright‑style developer tests (not part of the main pipelines).
  - `check_year_context.js` – Playwright helper to inspect year‑context UI in a running dev server.
  - `check_year_context_port.js` – Variant that spins up a local `http.server` before testing.
  - `test_cap_tool.mjs` – Node ESM unit tests for `docs/roster_cap_tool/js/capMath.js`.
  - `test_year_context.mjs` – Node ESM unit tests for Year Context helpers in the cap tool.
- `scripts/smoke/` – Shell smoke tests that exercise end‑to‑end flows.
  - `smoke_generate_draft_2026.sh` – Generates `docs/draft_class_2026.html` and runs draft verifiers.
  - `smoke_roster_cap_tool.sh` – Serves the repo and checks that `docs/roster_cap_tool` + CSVs are available.
- `scripts/tools/` – Small maintenance utilities.
  - `sync_data_to_docs.sh` – Copies `MEGA_*.csv` from the repo root into `docs/roster_cap_tool/data/` for the cap tool.

Run these helpers from the repo root, for example:

```bash
node scripts/tests/test_cap_tool.mjs
node scripts/tests/test_year_context.mjs
bash scripts/smoke/smoke_generate_draft_2026.sh
bash scripts/smoke/smoke_roster_cap_tool.sh
bash scripts/tools/sync_data_to_docs.sh --all
```

## Conventions for new scripts

When adding new code:

- **Analysis scripts** that read `MEGA_*.csv` and produce CSV/JSON should live under `scripts/` (or `stats_scripts/` if they extend the stats pipeline). Prefer descriptive names: `calc_*`, `generate_*`, `*_analysis.py`.
- **Entry points** that orchestrate several steps should start with `run_all_` and live at the top level of `scripts/`.
- **Verifiers** should be named `verify_*.py` and placed at the top level of `scripts/`, near the workflow they validate.
- **Smoke tests** belong in `scripts/smoke/` and are typically small shell scripts that call existing Python tools.
- **Dev/test helpers** (Node/Playwright scripts) belong in `scripts/tests/`.
- **Utility tools** such as file sync scripts belong in `scripts/tools/`.

If your new script generates or updates an HTML page under `docs/`, document it in:

- The relevant section of `README.md` (Architecture / Quick Start / Workflow), and
- `docs/README.md` under the appropriate domain table (Playoff & SoS, Stats Dashboards, Roster / Cap, Misc & Utilities).

