# Technical Specification: MEGA League Project Cleanup

## 1. Technical Context

- **Languages / runtimes**
  - Python 3.7+ for all data processing and orchestration (`scripts/`, `stats_scripts/`, `tests/test_power_rankings_roster.py`), invoked as `python3 ...`.
  - Browser‑executed HTML/CSS/JS for dashboards under `docs/` (vanilla JS + D3 from CDN).
  - Node.js + Playwright for roster cap tool E2E tests (`tests/e2e`, `package.json`).
- **Execution model**
  - Scripts are run directly with `python3 path/to/script.py` from the repo root.
  - CSV inputs live at repo root (`MEGA_*.csv`, `mega_elo.csv`).
  - Primary outputs are written to `output/` (CSV/JSON) and `docs/` (HTML/PNG).
  - GitHub Pages (or similar static host) serves `docs/` and `index.html`.
- **Dependencies**
  - Python: standard library only (csv, pathlib, random, statistics, etc.).
  - Node: `playwright`, `@playwright/test` as devDependencies for E2E only.
  - No frameworks (Django/Flask/React/etc.) and no build pipeline are introduced as part of this cleanup.

### 1.1 Dependencies and assumptions

- Current orchestrators (`scripts/run_all.py`, `scripts/run_all_playoff_analysis.py`, `scripts/run_all_stats.py`) remain the canonical way to run workflows.
- CSV schemas and file names are stable and already documented in `spec/data_inputs.md` and `README.md`.
- The cleanup focuses on structure, naming, and documentation clarity, not on changing simulation formulas or domain logic.
- Node.js and Playwright are required only for E2E tests; they are optional for core Python workflows.
- All required CSVs (`MEGA_*.csv`, `mega_elo.csv`) must be present at the repo root for pipelines to succeed.

### 1.2 Out of scope

- No changes to simulation or statistical algorithms (Monte Carlo, SoS formulas, roster metrics, etc.).
- No changes to CSV schemas or column names.
- No changes to public HTML URLs under `docs/` (only documentation and internal references may be updated).
- No introduction of new frameworks or build systems (keep everything script‑driven).

---

## 2. Implementation Approach

### 2.1 Goals Recap (Implementation Lens)

From the PRD, the cleanup aims to:
- Make the architecture and main workflows understandable in a few minutes.
- Make it obvious which scripts are:
  - Core entry points.
  - Domain tools/utilities.
  - Verifiers/smoke tests.
  - Test/dev‑only helpers (JS/MJS/shell).
- Clarify boundaries between domains:
  - Playoff/draft race + SoS Season 2.
  - Stats aggregation and dashboards.
  - Roster cap tool.
- Keep changes simple and backward compatible where possible.

The implementation will therefore:
- Restructure **only where it materially improves clarity** (especially `scripts/`).
- Prefer **docs and naming conventions** over heavy refactors.
- Reuse existing orchestrators and specs as the backbone of the architecture map.

### 2.2 Source Code Structure Changes (To‑Be)

#### 2.2.1 `scripts/` layout

Current: one flat directory mixing Python entry points, helpers, verifiers, JS/MJS helpers, shell scripts, and fixtures.

To‑be layout (conceptual):

- `scripts/`
  - **Python entry points (unchanged locations)**
    - `run_all.py` – full end‑to‑end pipeline (Season 2 SoS + playoff + index).
    - `run_all_playoff_analysis.py` – playoff + draft pick race + related visuals.
    - `run_all_stats.py` – stats aggregation pipeline (team/player usage) + joins.
  - **Python domain tools (unchanged locations, documented as such)**
    - Playoff / draft / SoS Season 1:
      - `calc_sos_by_rankings.py`
      - `calc_remaining_sos.py`
      - `calc_playoff_probabilities.py`
      - `playoff_race_table.py`
      - `playoff_race_html.py`
      - `top_pick_race_analysis.py`
      - `generate_index.py`
    - Season 2 SoS (ELO):
      - `calc_sos_season2_elo.py`
      - `verify_sos_season2_elo.py` (verifier, but logically tied to this domain).
    - Draft & rookies:
      - `generate_draft_class.py`
      - `generate_draft_class_analytics.py`
      - `verify_draft_class_analytics.py`
      - `export_2026_rookies.py`
  - Roster / cap:
      - `power_rankings_roster.py`
      - `calc_team_y1_cap.py`
    - Docs / metrics helpers:
      - `add_metric_helps.py` (helper to regenerate docs/metrics snippets; will be documented but not renamed in this cleanup).
  - **Python verifiers (kept flat, documented via naming)**
    - `verify_cap_math.py`
    - `verify_draft_round1_recap.py`
    - `verify_power_rankings_roster_csv.py`
    - `verify_power_rankings_roster_html.py`
    - `verify_team_rosters_export.py`
    - `verify_trade_stats.py`
    - `verify_sos_season2_elo.py` (Season 2 SoS verifier).
    - `verify_draft_class_analytics.py` (draft analytics verifier).
  - **Python fixtures/utilities**
    - `fixtures/` (unchanged; referenced by tests and/or scripts).
- **Non‑Python helpers moved into subfolders for clarity**
    - `scripts/tests/` (dev/test‑only JS/MJS helpers)
      - `check_year_context.js`
      - `check_year_context_port.js`
      - `test_cap_tool.mjs`
      - `test_year_context.mjs`
    - `scripts/smoke/` (shell smoke runners)
      - `smoke_generate_draft_2026.sh`
      - `smoke_roster_cap_tool.sh`
    - `scripts/tools/`
      - `sync_data_to_docs.sh` (data sync for roster cap tool)

Key points:
- **Python script locations stay the same** to avoid churn in imports (e.g., `tests/test_power_rankings_roster.py` continues to import `from scripts import power_rankings_roster`).
- Only **JS/MJS/shell files are moved** into clearly named subfolders; README/docs will be updated where paths change.
- A new `scripts/README.md` will document:
  - Overview of the `scripts/` folder and how it fits into the overall architecture.
  - Script categories: entry points, domain tools, verifiers, smoke scripts, and dev/test helpers.
  - Per‑category tables listing script name, short description, and main inputs/outputs.
  - Conventions for adding new scripts (file naming like `run_all_`, `verify_`, placement by domain).
  - A short “How to add a new analysis script” subsection pointing to the right folder and how to hook into orchestrators.

#### 2.2.2 `stats_scripts/` alignment

Current:
- `stats_scripts/` contains aggregation scripts (`aggregate_team_stats.py`, `aggregate_player_usage.py`, `aggregate_rankings_stats.py`, `build_player_team_stints.py`, `stats_common.py`) and several planning docs.
- Outputs are already written to the top‑level `output/` folder (e.g., `output/team_aggregated_stats.csv`, `output/player_team_stints.csv`), but the `README.md` still references historical paths.

To‑be:
- Keep **code and directory as‑is** (no file moves).
- Update `stats_scripts/README.md` to:
  - Reflect current output paths under `output/` (not `stats_scripts/output/`).
  - Link explicitly to:
    - `docs/team_stats_explorer.html`
    - `docs/team_stats_correlations.html`
  - Clarify that the stats pipeline feeds these dashboards and that the full entry point for “stats only” is `python3 scripts/run_all_stats.py`.
- Keep existing planning docs (`STATS_VISUALIZATION_PLAN.md`, `RANKINGS_VISUALIZATION_PLAN.md`, `CORRELATION_IDEAS.md`) but link to them from a short “Further reading” section; no re‑organization required.

#### 2.2.3 `docs/` and roster cap tool

Current:
- `docs/` mixes generated HTML dashboards, PNGs, and the `roster_cap_tool/` application.
- The roster cap tool already has `USAGE.md` describing user flows and references to cap math spec and verification scripts.

To‑be:
- Add a concise `docs/README.md` that:
  - Lists the main dashboards and what generates them (with script names).
  - Groups pages by domain:
    - Playoff / SoS: `playoff_race.html`, `playoff_race_table.html`, `sos_season2.html`, SoS PNG graphs.
    - Stats dashboards: `team_stats_explorer.html`, `team_stats_correlations.html`, `stats_dashboard.html`.
    - Roster/cap: `roster_cap_tool/index.html`, `roster_cap_tool/test.html`.
    - Misc: `trade_dashboard.html`, `week18_simulator.html`, etc.
  - Links back to `README.md` for entry commands.
- Keep `docs/roster_cap_tool/` structure as a self‑contained SPA:
- Clarify in `USAGE.md` how `scripts/tools/sync_data_to_docs.sh` feeds `docs/roster_cap_tool/data/`.
  - Ensure any references to shell scripts reflect the new `scripts/smoke/` path (e.g., `bash scripts/smoke/smoke_roster_cap_tool.sh`).
  - Briefly mention how to add a new visualization page under `docs/roster_cap_tool/` if ever needed (where JS/CSS live, how data is loaded).

#### 2.2.4 Specs and architecture map

Current:
- `spec/README.md` indexes feature‑specific specs but there is no single “architecture map” tying everything together; the main `README.md` partially fills this role.

To‑be:
- Keep existing specs unchanged.
- Add a short “Architecture at a Glance” section to `README.md` that:
  - Summarizes domains (playoff/draft, stats, SoS Season 2, roster cap tool).
  - Shows **inputs → scripts/orchestrators → outputs → docs pages** in a compact table.
  - Links to:
    - `spec/README.md` for deeper feature specs.
    - `stats_scripts/README.md` and `docs/README.md` for domain‑specific overviews.
  - Optional (lightweight) addition to `spec/README.md`:
  - One paragraph noting that the main architecture map lives in `README.md` and cross‑linking back.

Example architecture table (shape only, actual content will live in `README.md`):

| Domain                | Inputs                          | Orchestrators / Scripts                     | Outputs (data)                             | Key HTML / Docs                 |
|-----------------------|---------------------------------|---------------------------------------------|--------------------------------------------|---------------------------------|
| Playoff + draft race  | `MEGA_teams.csv`, `MEGA_games.csv`, `MEGA_rankings.csv` | `run_all_playoff_analysis.py`, `calc_sos_by_rankings.py`, `calc_playoff_probabilities.py`, `top_pick_race_analysis.py` | `output/ranked_sos_by_conference.csv`, `output/playoff_probabilities.json`, `output/draft_race/draft_race_report.md` | `docs/playoff_race.html`, `docs/playoff_race_table.html` |
| Stats aggregation     | `MEGA_passing.csv`, `MEGA_rushing.csv`, `MEGA_receiving.csv`, `MEGA_defense.csv`, `MEGA_punting.csv`, `MEGA_kicking.csv`, `MEGA_teams.csv` | `run_all_stats.py`, `aggregate_team_stats.py`, `aggregate_player_usage.py`, `aggregate_rankings_stats.py` | `output/team_aggregated_stats.csv`, `output/team_player_usage.csv`, `output/team_rankings_stats.csv` | `docs/team_stats_explorer.html`, `docs/team_stats_correlations.html` |
| SoS Season 2 (ELO)    | `MEGA_games.csv`, `MEGA_teams.csv`, `mega_elo.csv` | `run_all.py`, `calc_sos_season2_elo.py` | `output/sos/season2_elo.csv`, `output/sos/season2_elo.json` | `docs/sos_season2.html`, `docs/sos_graphs.html` |
| Roster / cap          | `MEGA_players.csv`, `MEGA_teams.csv` | `power_rankings_roster.py`, `calc_team_y1_cap.py`, `scripts/tools/sync_data_to_docs.sh` | `output/power_rankings_roster.csv`, `output/cap_tool_verification.json` | `docs/roster_cap_tool/index.html`, `docs/power_rankings_roster.html` |

---

## 3. Data Model, APIs, and Interfaces

### 3.1 Data model (CSV / JSON / HTML)

No schema changes are required for the cleanup. Instead, the spec will:
- Reuse existing definitions from `spec/data_inputs.md` and `README.md` (sections “Required Data Files”, “Season 2 Strength of Schedule (ELO)”, “Draft Class Analytics”).
- Ensure the architecture map clearly associates:
  - **Inputs**:
    - `MEGA_teams.csv`, `MEGA_games.csv`, `MEGA_rankings.csv`.
    - Player stats: `MEGA_passing.csv`, `MEGA_rushing.csv`, `MEGA_receiving.csv`, `MEGA_defense.csv`, `MEGA_punting.csv`, `MEGA_kicking.csv`.
    - `MEGA_players.csv` for draft analytics and roster power rankings.
    - `mega_elo.csv` for Season 2 SoS.
  - **Intermediate outputs**:
    - `output/ranked_sos_by_conference.csv`
    - `output/remaining_sos_by_conference.csv`
    - `output/playoff_probabilities.json`
    - `output/draft_race/draft_race_report.md`
    - `output/team_aggregated_stats.csv`
    - `output/team_player_usage.csv`
    - `output/team_rankings_stats.csv`
    - `output/player_team_stints.csv`
    - `output/sos/season2_elo.csv`, `output/sos/season2_elo.json`
    - `output/cap_tool_verification.json`, `output/traded_players_report.csv`
  - **User‑facing artifacts**:
    - `docs/playoff_race.html`, `docs/playoff_race_table.html`, `docs/playoff_race_report.md`
    - `docs/sos_season2.html`, `docs/sos_graphs.html`
    - `docs/team_stats_explorer.html`, `docs/team_stats_correlations.html`, `docs/stats_dashboard.html`
    - `docs/draft_class_*.html`
    - `docs/trade_dashboard.html`, `docs/week18_simulator.html`
    - `docs/roster_cap_tool/index.html`

### 3.2 Script interfaces (CLI APIs)

No new CLI framework is introduced; scripts remain simple `argparse` or constant‑config CLIs.

The cleanup will:
- Re‑affirm canonical commands in `README.md`:
  - Full pipeline: `python3 scripts/run_all.py`
  - Playoff + draft: `python3 scripts/run_all_playoff_analysis.py`
  - Stats only: `python3 scripts/run_all_stats.py`
  - Season 2 SoS only: `python3 scripts/calc_sos_season2_elo.py ...`
  - Draft analytics: `python3 scripts/generate_draft_class_analytics.py --year 2026 ...`
- Explicitly list **verifier commands** next to each pipeline:
  - `python3 scripts/verify_trade_stats.py`
  - `python3 scripts/verify_cap_math.py`
  - `python3 scripts/verify_sos_season2_elo.py --check sos`
  - `python3 scripts/verify_power_rankings_roster_csv.py` / `..._html.py`
  - `python3 scripts/verify_draft_class_analytics.py ...`

Interfaces between Python and HTML/JS remain file‑based (CSV/JSON/MD/HTML), with no runtime coupling.

---

## 4. Delivery Phases

The cleanup will be implemented in small, testable steps that can be committed independently.

### Phase 1 – Architecture map & documentation alignment

- Update `README.md`:
  - Add “Architecture at a Glance” section with a simple table mapping domains → inputs → orchestrators → outputs → key HTML pages.
  - Ensure Quick Start and Weekly Workflow sections reference the canonical commands and link to the new `scripts/README.md`.
- Lightly update `spec/README.md` to cross‑link with the new architecture section.
- Add `docs/README.md` summarizing dashboards and their generator scripts.

Verification:
- Manual doc review in a browser/editor.
- Confirm all script names and paths used in docs exist via `rg`/`ls`, for example:
  - `rg "python3 scripts/\\w+\\.py" README.md docs -o --no-filename | sort -u`
  - For each referenced script, confirm `ls scripts/<name>.py` succeeds.

### Phase 2 – `scripts/` structure and conventions

- Create `scripts/README.md`:
  - Categorize scripts as entry points, domain tools, verifiers, smoke scripts, and dev/test helpers.
  - Document conventions for new scripts (file naming, where to place them, how to hook into `run_all*.py`).
  - Include a short “How to add a new visualization” note pointing from scripts to `docs/` (which HTML page to regenerate).
- Create subfolders and move non‑Python helpers:
  - `scripts/tests/`: move `check_year_context.js`, `check_year_context_port.js`, `test_cap_tool.mjs`, `test_year_context.mjs`.
  - `scripts/smoke/`: move `smoke_generate_draft_2026.sh`, `smoke_roster_cap_tool.sh`.
  - `scripts/tools/`: move `sync_data_to_docs.sh`.
- Update references:
  - In `README.md`, `docs/roster_cap_tool/USAGE.md`, comments inside moved scripts, relevant `.zenflow/tasks/*`, and any other mentions, replace old paths with new ones.

Verification:
- `python -m compileall scripts` to ensure Python scripts remain valid after moves (no path changes for them).
- `rg "scripts/(smoke_|sync_data)" -n .` to ensure references are updated to the new subfolders (`scripts/smoke/`, `scripts/tools/`), including `.zenflow/` plans.
- Optionally run key smoke scripts (if environment and data are present) and check for exit code 0:
  - `bash scripts/smoke/smoke_generate_draft_2026.sh`
  - `bash scripts/smoke/smoke_roster_cap_tool.sh`

### Phase 3 – Stats and docs cohesion

- Update `stats_scripts/README.md` to:
  - Reference `output/team_aggregated_stats.csv` and other real output paths (fixing any remaining `stats_scripts/output/...` references).
  - Mention `scripts/run_all_stats.py` as the primary entry point for regenerating stats.
  - Link to `docs/team_stats_explorer.html` and `docs/team_stats_correlations.html`.
- Add or update `docs/README.md` (from Phase 1) to ensure:
  - Each major HTML dashboard lists its generator script.
  - There is a pointer back to `README.md` for running the associated pipeline.

Verification:
- Sanity run of stats aggregation (if data present):
  - `python3 stats_scripts/aggregate_team_stats.py` or `python3 scripts/run_all_stats.py`.
- Confirm that the described output files actually appear under `output/` with expected filenames.

### Phase 4 – Safety nets and tests

- Ensure Python unit tests still pass:
  - `python -m unittest tests/test_power_rankings_roster.py`
- For roster cap tool (optional / when environment available):
  - Install Playwright deps: `npm install` then `npm run pw:install`.
  - Run a small subset of E2E tests: `npm run test:e2e -- --grep cap`.
- Add or update a “Developer Guide” section in `README.md` that covers:
  - Environment setup (Python version, optional Node/Playwright for E2E).
  - How to run Python unit tests and Playwright E2E tests.
  - How to add a new analysis script (where to place it in `scripts/` or `stats_scripts/`, how to wire it into an orchestrator).
  - How to add a new HTML/JS visualization (where to place files in `docs/`, which data outputs it should consume, and which generator script to run).

Verification:
- All targeted tests pass.
- Basic manual spot‑check: open key HTML outputs in a browser and verify navigation links (e.g., from `index.html` to playoff pages and stats dashboards).

If any of the structural changes (especially file moves) cause problems, rollback is simply reverting the corresponding Git commit or, in a local branch, restoring the previous folder layout for the moved helper scripts.

---

## 5.1 User story mapping

- **Story 1 – Understand the architecture in 5 minutes**
  - Addressed primarily by Phase 1 (Architecture map in `README.md`, `docs/README.md`, cross‑links from `spec/README.md`).
- **Story 2 – One obvious command per workflow**
  - Addressed by Phase 1 and 3 via explicit canonical commands in `README.md` and per‑domain docs.
- **Story 3 – Find the right place to add new code**
  - Addressed by Phase 2 (script categorization and conventions in `scripts/README.md`) and Phase 4 (Developer Guide “how to add new script/visualization”).
- **Story 4 – Distinguish core scripts from helpers and verifiers**
  - Addressed by Phase 2 via `scripts/README.md` categories and naming conventions (`run_all_`, `verify_`, `smoke_`).
- **Story 5 – Keep the roster cap tool clearly scoped**
  - Addressed by Phase 1 and 2.2.3 (docs for `docs/roster_cap_tool/`, clear data sync and verifier relationships, and stable URLs).
- **Story 6 – Lower the “WTF” factor for future you**
  - Addressed across all phases by clearer docs, architecture map, script categorization, and a concrete Developer Guide.

---

## 5. Verification Approach (Summary)

The following checks will be used to confirm the cleanup is safe and aligned with the PRD:

- **Static checks**
  - `python -m compileall scripts stats_scripts` to catch syntax/import errors.
  - `rg`‑based searches to ensure updated paths in docs and comments are consistent with the new `scripts/` layout.
- **Python unit tests**
  - `python -m unittest tests/test_power_rankings_roster.py`.
- **Pipeline spot‑checks** (when CSV inputs are available)
  - Playoff pipeline: `python3 scripts/run_all_playoff_analysis.py` → confirm `docs/playoff_race.html` and `docs/playoff_race_table.html` exist and are non‑empty.
  - Stats pipeline: `python3 scripts/run_all_stats.py` → confirm `output/team_aggregated_stats.csv`, `output/team_player_usage.csv`, `output/team_rankings_stats.csv`, `output/player_team_stints.csv`.
  - Season 2 SoS: `python3 scripts/calc_sos_season2_elo.py --season2-start-row 287` → confirm `output/sos/season2_elo.csv` and `output/sos/season2_elo.json`.
- **Verifiers**
  - `python3 scripts/verify_trade_stats.py`
  - `python3 scripts/verify_cap_math.py`
  - `python3 scripts/verify_sos_season2_elo.py --check sos`
  - `python3 scripts/verify_draft_class_analytics.py 2026 --players MEGA_players.csv --teams MEGA_teams.csv --html docs/draft_class_2026.html`
- **Optional E2E**
  - `npm run test:e2e` or targeted subsets, to ensure roster cap tool and docs views still behave as expected.

This technical specification keeps the implementation incremental and low‑risk: most changes are documentation and small file moves for non‑Python helpers, without introducing new abstractions or altering domain logic. The result should be a project that is easier to navigate, with clear entry points and boundaries, while remaining familiar to current workflows.

---

## 6. Success metrics

To align with the PRD success criteria, the cleanup will be considered successful if:

- **Onboarding speed**
  - A new contributor can, in under 10 minutes, read `README.md` and the new docs and identify main domains, entry‑point commands, and where scripts live.
- **Weekly run simplicity**
  - Weekly league updates can be run with ≤ 3 documented commands (e.g., `run_all.py`, `run_all_stats.py`, selected verifiers).
- **Scripts folder clarity**
  - The flat `scripts/` directory primarily contains Python scripts (≈ 25–30 files), with JS/MJS/shell helpers moved into clearly named subfolders.
- **Consistency between docs and code**
  - References to script paths and outputs in `README.md`, `docs/README.md`, `stats_scripts/README.md`, and `.zenflow/` tasks match the actual file layout.
- **No regressions**
  - All existing key workflows and verifiers continue to pass using the same inputs as before the cleanup.
