# Feature Specification: E2E Playwright Tests for Roster Cap Management Tool

The repository includes a static, browser‑based roster management and salary cap tool under `docs/roster_cap_tool/` with rich UI flows (release, trade, extension, conversion, free‑agent signing), projections, filters, and scenario save/load via `localStorage`. This feature adds end‑to‑end (E2E) tests using Playwright to validate the core user flows and critical cap math outcomes through the UI.


## User Stories*

### User Story 1 - Validate Core Roster Actions

Maintain confidence that critical flows work: releasing a player, signing a free agent, quick trade, extension, and conversion update the roster and cap summary correctly.

**Acceptance Scenarios**:
1. Given the app is served from `http://localhost:8000/docs/roster_cap_tool/`, When a team is selected, Then Active Roster and Cap Summary render with non‑zero counts/values.
2. Given the first roster player is actionable, When the user selects “Release” and confirms, Then the player disappears from the Active Roster, appears in Free Agents, Dead Money shows an entry, and Cap Summary cap space increases by the previewed amount.
3. Given the Free Agents tab lists players, When the user clicks “Make Offer” and confirms with default terms, Then the player appears in Active Roster and Cap Summary cap space decreases by the previewed amount.
4. Given a roster player, When the user applies “Trade (Quick)” and confirms, Then the player is removed from the team and Dead Money shows a trade entry; Cap Summary equals the previewed new cap value.
5. Given a roster player with a valid contract, When an Extension is applied, Then the player’s contract fields and cap hit update and Cap Summary matches the modal’s preview.
6. Given a roster player with convertible base salary, When a Conversion is applied, Then the player’s current‑year cap hit is reduced and Cap Summary matches the preview.

### User Story 2 - Filters, Tabs, and Projections Behave Correctly

Ensure navigation and filtering are discoverable and functional and that projections update when related inputs change.

**Acceptance Scenarios**:
1. Given the Active Roster tab, When the user toggles one or more position chips, Then only matching positions render and the filter state persists across re‑renders and tab switches.
2. Given the Projections header strip, When the user updates Rollover and Re‑sign budget inputs, Then Y+1..Y+3 projected cap values update and the values persist across re‑renders.
3. Given the Dead Money tab, When baseline values are edited and saved, Then totals reflect the change and persist across re‑renders.

### User Story 3 - Scenario Save/Load and Reset

Users can capture scenarios, reload them, and reset to baseline using the header controls.

**Acceptance Scenarios**:
1. Given edits/moves exist, When Save is clicked and a name is confirmed, Then the scenario count increases and appears in the Load list for the selected team.
2. Given a saved scenario exists, When Load is clicked for that scenario, Then roster/moves reflect the scenario and the counts in “edits, moves” chip match the saved scenario.
3. Given any changes exist, When Reset is confirmed, Then roster/moves return to baseline and Dead Money ledger clears.

### User Story 4 - Determinism, Accessibility, and CI

Tests should be deterministic, accessible, and run in CI without flaky dependencies.

**Acceptance Scenarios**:
1. Given the test harness boots a static server and navigates to the tool, When tests run headless in CI, Then all test flows pass on a clean repo using the committed CSV data under `docs/roster_cap_tool/data/` with no external network reliance beyond PapaParse CDN used by the app.
2. Given core UI surfaces, When Playwright’s accessibility snapshot is checked on key pages/modals, Then issues are limited to acceptable known limitations and do not block usage (role attributes on tabs, dialog semantics present).
3. Given selectors are used in tests, When UI changes occur, Then selectors remain stable via roles/text/attributes instead of brittle DOM indices.

---

## Requirements*

- Test runner
  - Use Playwright (TypeScript) with project configuration to run a local static server: `python3 -m http.server 8000` (root of repo) and baseURL `http://localhost:8000`.
  - Default to Chromium for fast/local runs; optional matrix for Firefox/WebKit in CI. [NEEDS CLARIFICATION]
  - Headless by default; expose `HEADFUL=1` to run headed locally.

- Data and determinism
  - Use committed datasets at `docs/roster_cap_tool/data/MEGA_players.csv` and `MEGA_teams.csv` to avoid mutation of root CSVs.
  - Where specific numbers are needed, assert against UI previews (modal “New Cap Space”, “Remaining Cap After”) and then verify Cap Summary equals the previewed values (exact equality with integer rounding where applicable) to tolerate data changes.
  - If necessary for determinism, inject one synthetic player and one synthetic FA via `page.evaluate()` (mirroring `docs/roster_cap_tool/test.html`) to run a controlled release/sign flow without depending on real player fields. Prefer using real roster data first. [Assumption]

- Core coverage (happy paths + basic error/guard states)
  - Load app; ensure Team selector present and selects first team.
  - Active Roster action menu supports: Release (modal confirm), Trade (Quick) (confirm), Extension (modal), Conversion (modal).
  - Free Agents: “Make Offer” modal with default terms; disabled Confirm when insufficient cap; lowball warning visibility when below 90% of desired terms.
  - Tabs: Active Roster, Injured Reserve (may be empty), Dead Money (ledger and baseline form), Projections (header strip present), Draft Picks, Free Agents.
  - Filters: position chips toggling and persisting for both Active and FA lists.
  - Scenario controls: Save, Load (list, load, delete), Reset, Compare modal opens.

- Assertions and tolerances
  - Prefer equality against previewed figures rendered inside modals; then assert Cap Summary reflects the same value (within ±$2 to accommodate rounding where we display currency). [Assumption]
  - Dead Money ledger row added after Release/Trade shows non‑zero current‑year penalty and correct move label.

- Reliability and performance
  - Tests isolate state via a new browser context per test and clear `localStorage` between tests to avoid cross‑test leakage.
  - Avoid brittle selectors; prefer role‑based, label text, button text, `data-` attributes if added.
  - Keep test runtime under ~90 seconds locally on Chromium and under ~5 minutes in CI (3 browsers).

- CI integration
  - Add a GitHub Actions workflow to run Playwright tests on push/PR targeting main branches. [NEEDS CLARIFICATION]
  - Cache Playwright browsers; run Chromium only by default or full matrix if required. [NEEDS CLARIFICATION]

- Out of scope
  - Visual regression testing/snapshots.
  - Non‑UI unit tests (already present via Python verification scripts and `test.html`).
  - External network mocking (the app is static; PapaParse CDN is acceptable for CI, or can be vendored later if needed). [Assumption]


## Success Criteria*

- Functional coverage
  - E2E tests exercise and assert all core flows: Release, Trade (Quick), Extension, Conversion, Free‑Agent Signing, Filters, Tabs navigation, Projections controls, Dead Money baseline edit, Scenario Save/Load/Reset.

- Deterministic behavior
  - Tests pass repeatedly on clean clones using only committed CSVs and a local static server.
  - Local run: `npx playwright test` passes; CI run passes on a standard Ubuntu runner.

- Quality and maintainability
  - Tests use resilient selectors and include inline helper utilities only where necessary.
  - Flakiness is minimized (no timing races; wait for visible/attached and specific text before asserting).

- CI visibility
  - A CI workflow executes tests on PRs and surfaces traces/screenshots for failures.

- Documentation
  - `README.md` or a `tests/e2e/README.md` documents how to install Playwright, run tests locally, and common troubleshooting steps.


—

Top Clarifications Requested (prioritized):
1) Browser targets in CI: Chromium only, or Chromium + Firefox + WebKit? If all, must we run matrix on every PR? [scope/time]
2) CI provider preference: Should we add a GitHub Actions workflow in this repo, and what branches should trigger it? [scope/process]
3) Determinism approach: Is it acceptable to inject one synthetic player/FA via `page.evaluate()` to guarantee a stable flow, or must tests use only real data? [UX/testing policy]
4) Numeric assertion tolerance: Is ±$2 acceptable for currency display rounding where exact integer equality isn’t guaranteed? [UX/validation]
5) Any flows explicitly out of scope (e.g., Injured Reserve tab when empty, trade‑in modal search specifics), or must we cover them at a smoke level? [scope]

