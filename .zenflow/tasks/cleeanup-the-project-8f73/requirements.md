# PRD: Project Cleanup & Reorganization for MEGA League Stats

## 1. Context and Goals

The MEGA League project has grown into a rich ecosystem around a single Madden / Neon Sports league:
- Python scripts for playoff probabilities, strength of schedule (rankings and ELO), draft pick race, and season-wide simulations (e.g. `scripts/run_all.py`, `scripts/run_all_playoff_analysis.py`, `scripts/run_all_stats.py`).
- Team and player stats aggregation and visualization under `stats_scripts/` with HTML dashboards in `docs/` (team stats explorer, correlations, SOS views, etc.).
- A Spotrac‑style roster cap tool under `docs/roster_cap_tool/` (JS app plus data sync/verification scripts).
- A growing set of specs under `spec/` and task artifacts under `.zenflow/tasks/`.

Over time, new features and one‑off scripts have been added quickly. The result is:
- Multiple overlapping “entry points” and scripts whose responsibilities are not obvious from names alone.
- Mixed concerns in the `scripts/` folder (core pipeline, verification scripts, experiments, smoke tests).
- Several specs and docs that partially overlap with the actual code structure.
- High cognitive load for remembering “where things live” and how they relate.

This cleanup/reorganization feature focuses on making the project easier to understand and safer to extend **without changing the core analytical behavior**.

Primary goals:
- Make it obvious:
  - What the core domains are (playoff analysis, stats aggregation/visualizations, roster cap tool, draft/draft analytics, SoS Season 2).
  - Which scripts are canonical entry points vs helpers vs verification tools.
  - Where to plug in new code for each domain.
- Reduce friction for weekly usage by league commissioners and for future development by you/other contributors.
- Improve internal consistency (naming, folder structure, documentation) while keeping the implementation simple and dependency‑light.

Non‑goals (for this feature):
- No major rewrite of simulation logic or stat formulas.
- No large framework adoption (no Django/Flask backend, no heavy bundler for the JS apps).
- No breaking changes to public HTML URLs under `docs/` unless explicitly decided later.

Assumptions:
- Python 3 remains the main runtime, using standard library or the minimal existing dependencies.
- GitHub Pages (or equivalent static hosting) remains the deployment approach.
- CSV schema and filenames (`MEGA_*.csv`, `mega_elo.csv`, `output/*.csv/json`) remain compatible; cleanup may improve how they are documented, not fundamentally change them.

## 2. Target Users

- **League Commissioner / Power User**
  - Runs scripts weekly or after big events (trades, playoffs, rookie drafts).
  - Comfortable with basic CLI, but doesn’t want to read through all the code to remember which script to run.
  - Needs simple, trustworthy run commands and clear troubleshooting steps.

- **League Analyst / Maintainer (you)**
  - Adds new metrics, visualizations, and small tools as the league evolves.
  - Wants a project layout that makes it obvious where to add/modify code and how it flows end‑to‑end.
  - Cares about not breaking existing flows and keeping the repo approachable.

- **Future Contributors / Co‑owners**
  - Know Python/JS but are new to this repo.
  - Need a “mental map” of the system and conventions for adding features (e.g., a clear place for new stats dashboards or verification scripts).

## 3. User Stories with Acceptance Scenarios

### Story 1: Understand the Architecture in 5 Minutes

As a new contributor,  
I want a concise, accurate overview of the project structure and domains,  
so that I can understand how everything fits together without reading every file.

**Acceptance Criteria (Given/When/Then):**
- Given I open the main README or a dedicated “Architecture/Project Map” doc,  
  When I skim it for a few minutes,  
  Then I see:
  - The main domains (playoff pipeline, stats aggregation/visualizations, roster cap tool, draft analytics, SoS Season 2).
  - The primary entry‑point scripts for each domain.
  - A high‑level dataflow (inputs → scripts → outputs → docs).

- Given I follow links from that overview,  
  When I click into domain‑specific READMEs (e.g., in `scripts/`, `stats_scripts/`, `docs/roster_cap_tool/`),  
  Then each explains what lives there and how to run or extend it.

### Story 2: One Obvious Command per Workflow

As a league commissioner,  
I want a single obvious command for each major workflow,  
so that I don’t have to remember long sequences of scripts.

**Acceptance Criteria:**
- Given I read the Quick Start section of the main README,  
  When I look for “Playoff analysis”, “Stats aggregation”, and “Full run”,  
  Then I see:
  - One canonical command for full analysis (e.g., `python3 scripts/run_all.py`).
  - One command for playoff‑only (e.g., `python3 scripts/run_all_playoff_analysis.py`).
  - One command for stats‑only (e.g., `python3 scripts/run_all_stats.py`).

- Given I run the documented commands from the repo root with valid CSV inputs,  
  When execution completes successfully,  
  Then all expected artifacts for that workflow are generated in their documented locations (e.g., `docs/playoff_race.html`, `output/team_aggregated_stats.csv`, SoS Season 2 CSV/JSON files).

### Story 3: Find the Right Place to Add New Code

As a maintainer,  
I want clear boundaries and conventions for where different kinds of scripts and assets live,  
so that I can add a new feature without scattering code randomly.

**Acceptance Criteria:**
- Given I want to add a new analysis script that consumes `MEGA_*` CSVs and writes an output CSV,  
  When I check the project structure and developer docs,  
  Then I see:
  - A documented home for new analysis scripts (e.g., a clarified layout under `scripts/` vs `stats_scripts/`).
  - A pattern for adding that script to an orchestrator (if it’s part of a pipeline).

- Given I want to add a new HTML/JS visualization,  
  When I look at the docs/structure and any frontend notes,  
  Then I see:
  - Where to place new HTML files and any helper JS.
  - How to hook it into `index.html` or relevant dashboards.

### Story 4: Distinguish Core Scripts from Helpers and Verifiers

As any user of the repo,  
I want it to be obvious which scripts are user‑facing commands and which are internal helpers/verification tools,  
so that I don’t accidentally run the wrong thing or miss important checks.

**Acceptance Criteria:**
- Given I list the top‑level `scripts/` directory,  
  When I read its README or structure notes,  
  Then I can clearly see:
  - Which scripts are core entry points (e.g., `run_all.py`, `run_all_stats.py`, `run_all_playoff_analysis.py`).
  - Which scripts are domain tools (e.g., draft class analytics, Week 18 simulator).
  - Which scripts are verifiers/smoke tests or one‑off utilities (e.g., `verify_*`, `smoke_*`).

- Given I follow documentation for verification scripts,  
  When I run a recommended verifier (`verify_cap_math.py`, `verify_trade_stats.py`, etc.),  
  Then it is clear what it checks and how it relates to the main workflows.

### Story 5: Keep the Roster Cap Tool Clearly Scoped

As a roster/cap tool user or contributor,  
I want the cap management app to feel like a coherent sub‑project,  
so that I can work on it without accidentally breaking league‑wide stats pipelines.

**Acceptance Criteria:**
- Given I open `docs/roster_cap_tool/`,  
  When I read its usage and dev documentation,  
  Then it:
  - Explains its relationship to the main Python scripts (data sync via `scripts/sync_data_to_docs.sh`, verification via `verify_cap_math.py`).
  - Clarifies that it’s a front‑end JS app with its own data and UI code.

- Given I make local changes only within `docs/roster_cap_tool/` and its related test scripts,  
  When I run league‑wide orchestrators (`run_all.py`, `run_all_stats.py`, `run_all_playoff_analysis.py`),  
  Then those still function as expected (no hidden coupling).

### Story 6: Lower the “WTF” Factor for Future You

As future‑me coming back after a few months,  
I want to quickly reconstruct what each part of the project does and how to run it,  
so that I don’t have to re‑reverse‑engineer everything or dig through old tasks.

**Acceptance Criteria:**
- Given I return to the repo after time away,  
  When I open the main README and any architecture/dev docs,  
  Then I can:
  - Identify the main workflows and commands.
  - See where to find scripts, outputs, and HTML dashboards for each domain.
  - Locate references to more detailed specs under `spec/` (e.g., playoff rules, cap math) when needed.

- Given I scan `.zenflow/tasks/` briefly,  
  When I look at their plans/requirements,  
  Then they align with the structure and naming used in the actual code (minimal divergence between plans and reality).

## 4. Functional Requirements

### 4.1 Documentation & Project Map

- The project SHALL include an up‑to‑date high‑level map of domains and pipelines:
  - Either within `README.md` or a linked `docs/`/`spec/` document.
  - Showing inputs, main scripts/orchestrators, and key outputs for:
    - Playoff analysis and draft pick race.
    - Stats aggregation and visualization dashboards.
    - Roster cap tool.
    - Season 2 SoS (ELO) tooling.
- Each major directory (`scripts/`, `stats_scripts/`, `docs/roster_cap_tool/`, `spec/`) SHOULD have a short README or section describing:
  - Its purpose.
  - Key entry files.
  - How it connects to the rest of the system.

### 4.2 Canonical Entry Points

- The cleanup SHALL identify and document:
  - One canonical “full pipeline” command (currently `python3 scripts/run_all.py`).
  - One canonical “playoff analysis only” command (currently `python3 scripts/run_all_playoff_analysis.py`).
  - One canonical “stats aggregation only” command (currently `python3 scripts/run_all_stats.py`).
- Each canonical command SHALL:
  - Be described in the README with purpose, prerequisites, and expected outputs.
  - Log progress in a clear, consistent way (start/end per step, summary).
- If additional orchestrators are introduced (e.g., for draft analytics), they SHALL follow the same pattern and be explicitly documented.

### 4.3 Folder and Naming Conventions

- The project SHALL define and follow simple conventions for:
  - Where new analysis scripts live (Python, CSV in/out).
  - Where new visualizations live (HTML/JS/CSS under `docs/`).
  - How verification scripts are named (e.g., `verify_*`, `smoke_*`) and where they reside.
- Any necessary script relocations/renames during cleanup SHALL:
  - Preserve backward compatibility where practical (e.g., via updated docs and/or small wrappers).
  - Update references in docs, specs, and orchestrators to the new paths.

### 4.4 Verification & Safety Nets

- For key workflows, the cleanup SHALL ensure:
  - There is at least one documented verification step (e.g., `verify_trade_stats.py`, `verify_cap_math.py`, `verify_sos_season2_elo.py`).
  - The relationship between each verifier and its pipeline is clear in documentation.
- Running verifiers SHALL NOT require extra hidden setup beyond what the main workflows need (same CSV inputs and environment).

### 4.5 Roster Cap Tool Boundaries

- The roster cap tool SHALL:
  - Continue to load its data from `docs/roster_cap_tool/data/` (synced via `scripts/sync_data_to_docs.sh`).
  - Be documented as a standalone JS app backed by CSV exports, with cross‑links to the cap math spec (`spec/Salary Cap Works in Madden.md`) and verification script.
- Any changes to repo structure SHALL ensure:
  - Existing URLs like `/docs/roster_cap_tool/` remain valid or are updated intentionally with clear migration notes.

### 4.6 Developer Experience

- The cleanup SHALL provide a short “Developer Guide” section (either in README or a dedicated file) that explains:
  - How to set up the environment (Python version, optional node/npm for tests).
  - How to run tests (Python tests under `tests/`, Playwright tests under `tests/e2e/`).
  - How to add a new script or visualization following the conventions above.

## 5. Non‑Functional Requirements

- **Maintainability**
  - The reorganized structure SHOULD reduce cross‑directory coupling and make it easier to reason about each domain in isolation.
  - Comments and docs SHOULD favor clarity over cleverness; no heavy abstraction layers added just for neatness.

- **Backward Compatibility**
  - Existing documented commands SHOULD continue to work or be replaced with clearly documented alternatives.
  - Existing HTML pages under `docs/` SHOULD remain accessible without breaking links used in league communications.

- **Simplicity**
  - No new heavy runtime dependencies (frameworks, complex CLIs, or build systems) SHOULD be introduced as part of this cleanup.
  - Any helper utilities or modules added SHOULD be thin and focused on reducing duplication or clarifying behavior.

- **Discoverability**
  - A new or returning user SHOULD be able to find how to:
    - Run main workflows.
    - Regenerate stats and visualizations.
    - Work on the roster cap tool.
    - Understand the purpose of each top‑level directory.

## 6. Success Criteria

This cleanup/reorganization is considered successful if:

1. **Onboarding Speed**
   - A new contributor can read the main docs and identify:
     - The main domains and dataflows.
     - The primary entry‑point commands.
     - Where to add or modify scripts for a given domain.

2. **Reduced Friction for Weekly Runs**
   - League commissioners (or you) can run weekly updates using a small, clearly documented set of commands, without needing to remember obscure script names or orderings.

3. **Consistency Between Code and Docs**
   - Directory structure, file names, and orchestrator behavior match what is described in README/spec docs, with minimal surprises.

4. **Safe Extensibility**
   - Adding a new metric, visualization, or tool feels straightforward because:
     - There is a natural “home” for the new code.
     - Integration points (orchestrators, docs, verifiers) are easy to update.

5. **No Regressions in Core Behavior**
   - All existing key workflows (playoff analysis, stats aggregation, SoS Season 2, roster cap tool) continue to produce correct outputs given the same inputs as before cleanup.

