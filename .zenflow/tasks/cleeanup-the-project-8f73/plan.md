# New feature

## Configuration
- **Artifacts Path**: {@artifacts_path} → `.zenflow/tasks/{task_id}`

---

## Workflow Steps

### [x] Step: Requirements
<!-- chat-id: 42829de6-fad2-4d39-b4b7-e6c7a4ba8124 -->

Create a Product Requirements Document (PRD) based on the feature description.

1. Review existing codebase to understand current architecture and patterns
2. Analyze the feature definition and identify unclear aspects
3. Ask the user for clarifications on aspects that significantly impact scope or user experience
4. Make reasonable decisions for minor details based on context and conventions
5. If user can't clarify, make a decision, state the assumption, and continue

Save the PRD to `{@artifacts_path}/requirements.md` with:
- User stories with acceptance scenarios (Given/When/Then)
- Functional requirements
- Success criteria

### [x] Step: Technical Specification
<!-- chat-id: f95f51bd-2d75-4b78-86bc-c24ecbe4cf28 -->

Create a technical specification based on the PRD in `{@artifacts_path}/requirements.md`.

1. Review existing codebase architecture and identify reusable components
2. Define the implementation approach

Save to `{@artifacts_path}/spec.md` with:
- Technical context (language, dependencies)
- Implementation approach referencing existing code patterns
- Source code structure changes
- Data model / API / interface changes
- Delivery phases (incremental, testable milestones)
- Verification approach using project lint/test commands

### [x] Step: Planning
<!-- chat-id: 89966388-bc3e-4175-8bc0-004a0a45155f -->

Create a detailed implementation plan based on `{@artifacts_path}/spec.md`.

1. Break down the work into concrete tasks
2. Each task should reference relevant contracts and include verification steps
3. Replace the Implementation step below with the planned tasks

Rule of thumb for step size: each step should represent a coherent unit of work (e.g., implement a component, add an API endpoint, write tests for a module). Avoid steps that are too granular (single function) or too broad (entire feature).

If the feature is trivial and doesn't warrant full specification, update this workflow to remove unnecessary steps and explain the reasoning to the user.

Save to `{@artifacts_path}/plan.md`.

### [ ] Step: Phase 1 – Architecture map & docs

Align high-level architecture documentation with the PRD and spec.

- Tasks:
  - Update `README.md` to add an “Architecture at a Glance” section that maps domains → inputs → orchestrators → outputs → key HTML pages, following `spec.md` §2.2.4 and §4 “Phase 1 – Architecture map & documentation alignment`.
  - Ensure Quick Start / Weekly Workflow sections in `README.md` clearly document one canonical command per workflow (full run, playoff-only, stats-only, SoS Season 2), per PRD Stories 1–2 and `spec.md` §3.2.
  - Lightly update `spec/README.md` to reference the new architecture section as the canonical entry point for system overview, as described in `spec.md` §2.2.4.
  - Create or update `docs/README.md` to summarize the main dashboards, group them by domain (playoff/SoS, stats, roster/cap, misc), and list which scripts generate each page, per `spec.md` §2.2.3 and §4 Phase 1.
- Contracts:
  - PRD §5.1 Documentation & Project Map; PRD Stories 1–2 and 6.
  - Technical spec `spec.md` §2.2.3, §2.2.4, §3.2, and §4 Phase 1.
- Verification:
  - Manually review `README.md`, `spec/README.md`, and `docs/README.md` to ensure:
    - Every major domain has documented inputs, orchestrators, outputs, and key HTML pages.
    - Commands and script paths in docs correspond to real files under `scripts/` and `stats_scripts/`.
  - Use `rg "python3 scripts/.*\\.py" README.md docs -n` to confirm all referenced script paths exist and are consistent.

### [ ] Step: Phase 2 – Scripts layout & helpers

Clarify the role and structure of `scripts/` and isolate non-Python helpers.

- Tasks:
  - Author `scripts/README.md` that categorizes scripts into entry points, domain tools, verifiers, smoke scripts, and dev/test helpers, and documents conventions for new scripts, per `spec.md` §2.2.1 and §4 Phase 2.
  - Create subfolders and move non-Python helpers:
    - `scripts/tests/`: move `check_year_context.js`, `check_year_context_port.js`, `test_cap_tool.mjs`, `test_year_context.mjs`.
    - `scripts/smoke/`: move `smoke_generate_draft_2026.sh`, `smoke_roster_cap_tool.sh`.
    - `scripts/tools/`: move `sync_data_to_docs.sh`.
  - Update all references to moved helpers in:
    - `README.md`, `docs/roster_cap_tool/USAGE.md`, comments inside the moved scripts, and any relevant `.zenflow/tasks/*` plans, so they point to `scripts/tests/`, `scripts/smoke/`, and `scripts/tools/`.
  - Ensure `scripts/` top-level is primarily Python entry points, domain tools, and verifiers, matching the categorization in `spec.md` §2.2.1.
- Contracts:
  - PRD §5.2 Scripts Structure & Conventions; PRD Stories 3–4.
  - Technical spec `spec.md` §2.2.1 and §4 Phase 2.
- Verification:
  - Run `python -m compileall scripts` to ensure all Python files in `scripts/` still compile after the layout changes.
  - Run `rg "scripts/(smoke_|tools/|tests/)" -n .` to confirm documentation and comments use the new paths.
  - Optionally run smoke helpers (when environment and data are available) and confirm they succeed:
    - `bash scripts/smoke/smoke_generate_draft_2026.sh`
    - `bash scripts/smoke/smoke_roster_cap_tool.sh`

### [ ] Step: Phase 3 – Stats & docs cohesion

Tighten the connection between stats aggregation scripts, outputs, and dashboards.

- Tasks:
  - Update `stats_scripts/README.md` so it:
    - References the real output locations under `output/` (e.g., `output/team_aggregated_stats.csv`, `output/team_player_usage.csv`, `output/team_rankings_stats.csv`, `output/player_team_stints.csv`), instead of any outdated `stats_scripts/output/...` paths.
    - Documents `python3 scripts/run_all_stats.py` as the primary entry point for regenerating stats, in line with `spec.md` §2.2.2 and §3.2.
    - Links to the corresponding dashboards: `docs/team_stats_explorer.html`, `docs/team_stats_correlations.html`, `docs/stats_dashboard.html`.
  - Ensure `docs/README.md` (from Phase 1) clearly lists for each stats-related HTML dashboard which outputs it consumes and which script(s) generate those outputs.
  - Confirm that any planning docs in `stats_scripts/` (e.g., `STATS_VISUALIZATION_PLAN.md`, `RANKINGS_VISUALIZATION_PLAN.md`, `CORRELATION_IDEAS.md`) are linked from `stats_scripts/README.md` as “further reading”.
- Contracts:
  - PRD §5.3 Stats & Dashboards Cohesion; PRD Stories 2–3.
  - Technical spec `spec.md` §2.2.2 and §4 Phase 3.
- Verification:
  - Run a stats aggregation command (when CSV inputs are available), e.g.:
    - `python3 scripts/run_all_stats.py` (preferred) or `python3 stats_scripts/aggregate_team_stats.py`.
  - Check that expected outputs exist under `output/` with the filenames documented in `stats_scripts/README.md`.
  - Manually verify that `docs/team_stats_explorer.html` and `docs/team_stats_correlations.html` are mentioned in both `stats_scripts/README.md` and `docs/README.md` with consistent descriptions.

### [ ] Step: Phase 4 – Tests & developer guide

Reinforce safety nets and document how to extend the project safely.

- Tasks:
  - Confirm Python unit tests are documented and still pass, focusing on `tests/test_power_rankings_roster.py`.
  - For the roster cap tool, document and (when environment permits) run core Playwright E2E tests:
    - Ensure `README.md` (Developer Guide section) explains how to install Node/Playwright (`npm install`, `npm run pw:install`) and how to run E2E tests (e.g., `npm run test:e2e -- --grep cap`), per `spec.md` §4 Phase 4.
  - Add or expand a “Developer Guide” section in `README.md` that covers:
    - Environment setup (Python version, optional Node/Playwright).
    - How to run Python unit tests and Playwright E2E tests.
    - Where to add new analysis scripts (`scripts/` vs `stats_scripts/`), and how to wire them into orchestrators (`run_all.py`, `run_all_stats.py`, `run_all_playoff_analysis.py`).
    - How to add new HTML/JS visualizations under `docs/` and connect them to CSV/JSON outputs.
  - Ensure guidance aligns with and references the architecture map and `scripts/README.md`, so there is a single, coherent extension story.
- Contracts:
  - PRD §5.4 Testing & Safety Nets; PRD Stories 3–6.
  - Technical spec `spec.md` §4 Phase 4 and §5 Verification Approach.
- Verification:
  - Run `python -m unittest tests/test_power_rankings_roster.py` and confirm it passes.
  - When feasible, run a focused subset of Playwright tests (e.g., `npm run test:e2e -- --grep cap`) and ensure they pass.
  - Manually review the new Developer Guide section in `README.md` to confirm it references:
    - Architecture map.
    - `scripts/README.md`.
    - `docs/README.md`.
    - Key test commands (Python + E2E).
