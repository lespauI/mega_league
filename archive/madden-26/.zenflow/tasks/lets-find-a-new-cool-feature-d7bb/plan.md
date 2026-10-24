# New feature

## Configuration
- **Artifacts Path**: {@artifacts_path} → `.zenflow/tasks/{task_id}`

---

## Workflow Steps

### [x] Step: Requirements
<!-- chat-id: f6ea20cb-48f9-472e-8555-fbfc8b4c80c8 -->

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
<!-- chat-id: 64438673-37ee-431c-a387-4ba34c672a60 -->

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
<!-- chat-id: df11edb3-cb78-41b7-be83-e1af89dcc643 -->

Create a detailed implementation plan based on `{@artifacts_path}/spec.md`.

1. Break down the work into concrete tasks
2. Each task should reference relevant contracts and include verification steps
3. Replace the Implementation step below with the planned tasks

Rule of thumb for step size: each step should represent a coherent unit of work (e.g., implement a component, add an API endpoint, write tests for a module). Avoid steps that are too granular (single function) or too broad (entire feature).

If the feature is trivial and doesn't warrant full specification, update this workflow to remove unnecessary steps and explain the reasoning to the user.

Save to `{@artifacts_path}/plan.md`.

### [x] Step: Phase 1 – Data & Overview
<!-- chat-id: 62319ba8-e8ff-46f0-8cdc-3acf371ff897 -->

Implement CSV loading, `TeamProfile` normalization, league aggregates, and the basic Matchup Overview UI in `docs/matchup_gameplan.html`.

Tasks:
- Create `docs/matchup_gameplan.html` with base layout (header, explanatory text, containers for controls and panels), following the patterns in existing docs pages.
- Implement `tryCsv` helper and CSV loading pipeline for `output/team_rankings_stats.csv`, `output/team_aggregated_stats.csv`, and `output/team_player_usage.csv`, reusing the multi-path behavior from current stat dashboards.
- Build in-memory `TeamProfile` objects keyed by `team`, left-joining all three CSVs and computing derived fields (e.g., logo URL, win%, offensive/defensive efficiency metrics).
- Precompute league-level aggregates and z-scores/percentiles for core metrics, exposing a `leagueStats` helper with a `strengthLabel(metricValue, metricName)` contract.
- Wire `My Team` and `Opponent Team` `<select>` controls (`#my-team-select`, `#opp-team-select`) populated from rankings data, and implement `renderMatchup()` to drive all overview content.
- Implement the **Matchup Overview** panel (`#matchup-overview`) showing core identity info (record, win%, ELO/rank) and a simple text-based edge summary.

Verification:
- Run `python3 scripts/run_all_stats.py` to regenerate all `output/*.csv` and ensure required files exist.
- Serve the site locally (e.g., `python3 -m http.server`) and open `docs/matchup_gameplan.html`.
- Confirm dropdowns contain all 32 teams and that selecting a valid pair renders the overview without console errors.
- Spot-check a few teams against `output/team_rankings_stats.csv` to verify records, win%, and ELO/rank match.

### [x] Step: Phase 2 – Matchup Panels & Tendencies
<!-- chat-id: b6eaa7c7-a43c-45a8-8652-71d071b45237 -->

Add detailed offense/defense matchup sections and a tendencies/usage panel using season-long stats.

Tasks:
- Implement the **Your Offense vs Their Defense** panel (`#offense-vs-defense`) comparing key offensive metrics (e.g., `pass_yds_per_att`, `rush_yds_per_att`, `yds_per_play`, turnover tendencies) against opponent defensive metrics and league baselines.
- Implement the **Your Defense vs Their Offense** panel (`#defense-vs-offense`) mirroring the above for defensive metrics versus opponent offensive strengths.
- Use `leagueStats` z-scores to add labeled strength/weakness badges (e.g., “Major Strength”, “Weakness”) adjacent to each key metric comparison.
- Implement the **Tendencies & Usage** panel (`#tendencies`) summarizing pass/run distribution, key skill players, and usage concentration from `output/team_player_usage.csv` for both teams.
- Ensure `renderMatchup()` cleanly re-renders all panels on team changes, clearing previous state to avoid duplication.

Verification:
- With the local server running, select multiple known “identity” teams (run-heavy vs pass-heavy, strong defense vs weak defense) and verify that panel summaries and badges align with expectations.
- Cross-check a few metrics (e.g., pass yards per attempt, sacks, INTs) against the underlying CSVs to confirm correct joins and directionality.
- Validate that switching teams repeatedly produces no JS errors and that all DOM sections update consistently.

### [x] Step: Phase 3 – Suggestions Engine
<!-- chat-id: 43085410-3096-4ae3-8692-37246074d35d -->

Implement the rule-based gameplan suggestions engine and surface results in the UI.

Tasks:
- Design and implement a `computeSuggestions(matchupViewModel)` helper that returns a list of `Suggestion` objects `{ category: 'Attack' | 'Protect' | 'Defend', severity: 'major' | 'moderate', text }`, based on z-score thresholds and cross-metric comparisons.
- Plug the engine into the main flow so that each time a valid matchup is selected, suggestions are recomputed and rendered into the `#suggestions` section.
- Group suggestion bullets by category with clear headings and concise, action-oriented text (e.g., “Attack: Lean into deep passing vs their weak pass defense”).
- Implement basic deduplication and conflict resolution so the final suggestion list is focused and readable (no contradictory or repetitive bullets).
- Ensure the suggestions logic is defensive against missing metrics and falls back gracefully where data is incomplete.

Verification:
- Manually test a variety of matchups, focusing on extreme contrasts (elite offense vs weak defense, turnover-prone QB vs ball-hawking defense) to confirm suggestions match intuitive expectations.
- Inspect JS console for errors and log a few sample `matchupViewModel` and `Suggestion` outputs to validate that rules trigger as designed.
- Optionally document a few representative rule cases in comments or a short developer note for future tuning.

### [x] Step: Phase 4 – Recent Form & Trending (v1.1)
<!-- chat-id: 43182b55-b700-405d-8ad4-40600cbaebeb -->

Optionally add a recent-form toggle using `MEGA_games.csv` to compute last-N-game stats and trend indicators.

Tasks:
- Extend `docs/matchup_gameplan.html` controls with a simple time-window selector (e.g., radio buttons for `Full season` vs `Last 4 games`), wiring it into the same `renderMatchup()` flow.
- Load `MEGA_games.csv` using `tryCsv` and compute per-team rolling aggregates for the chosen recent window (e.g., last 4 games), reusing existing MEGA-game joining logic where possible.
- Integrate recent-form metrics into the overview panel and, where appropriate, into offense/defense panels to highlight differences between season-long and recent performance.
- Implement optional “Trending up/down” indicators when recent metrics diverge significantly from season baselines, using z-score deltas.
- Ensure that when MEGA data is unavailable or incomplete, the UI cleanly falls back to season-long stats without breaking.

Verification:
- Regenerate MEGA CSVs if needed and validate that `MEGA_games.csv` loads without errors.
- Toggle between `Full season` and `Last 4 games` for several teams, confirming that displayed recent metrics and trend indicators change sensibly.
- Sanity-check a small sample of game histories in `MEGA_games.csv` against computed last-4-game stats to ensure aggregation correctness.

### [x] Step: Phase 5 – QA & E2E Smoke
<!-- chat-id: 4ccbc1cd-4ddf-4c14-8e0b-aa596440200c -->

Perform end-to-end validation and integrate the new page into navigation.

Tasks:
- Update `docs/stats_dashboard.html` to add a new card linking to `docs/matchup_gameplan.html`, following existing copy and styling conventions.
- Update `index.html` (if applicable) to reference the Matchup Gameplan Advisor alongside other tools.
- Run `python3 scripts/run_all_stats.py` to ensure all CSV dependencies are freshly generated and consistent.
- Install Node dependencies if needed (`npm install`) and run `npm run test:e2e` to verify existing Playwright tests still pass.
- Optionally add a minimal Playwright smoke test that opens `docs/matchup_gameplan.html`, selects a known matchup, and asserts that key sections (`#matchup-overview`, `#offense-vs-defense`, `#defense-vs-offense`, `#tendencies`, `#suggestions`) render without errors.

Verification:
- Manually click through from `index.html` / `docs/stats_dashboard.html` to the new page and confirm navigation works.
- Confirm all planned manual checks (from the spec’s Verification Approach) pass: dropdown population, metric sanity checks, tendencies alignment, and sensible suggestions.
- Ensure automated tests (`npm run test:e2e`) complete successfully, or document any unrelated failures observed during execution.

### [x] Step: Create an HTML page with links
<!-- chat-id: 305cbea4-c49a-48dd-945c-c5e3519b8170 -->

Create an HTML page with links to new tools with explanation on what is that and how to use
