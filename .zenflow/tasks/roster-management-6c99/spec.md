# Technical Specification: Future-Year Roster Context & Simulation

## Technical Context
- Frontend: Static web app under `docs/roster_cap_tool/` using vanilla ES modules (no bundler)
  - Core modules: `js/state.js`, `js/capMath.js`, `js/models.js`, `js/ui/*`
  - Data: CSVs parsed with PapaParse CDN (`data/MEGA_teams.csv`, `data/MEGA_players.csv`)
  - Persistence: `localStorage` (scenarios, filters, rollover, re-sign, dead money baselines)
- Tests: Playwright E2E (`tests/e2e/*`), local Node scripts (`scripts/test_cap_tool.mjs`)
- Dev server: Playwright spins `python3 -m http.server 8000` (see `playwright.config.ts`)

## Technical Implementation Brief
Add a “Year Context” system that lets users operate the tool as if the current year is Y+0 (default), Y+1, Y+2, Y+3, etc. This affects:
- Roster views (active/free agents) and per-player contract fields “as of” the selected year
- Cap summary and move simulations (release/trade/extend/convert/sign) computed for the selected context year
- Projections header strip and Projections tab remain projections; the context selector does not repurpose them, only the main “current year” calculations and labels
- Scenario save/load/reset preserves the selected context

Key design choices:
- Non-destructive contextualization: Do not mutate `state.players`. Instead, compute a derived, “contextual” view of players for roster tables and math. This avoids corrupting baselines, diffs, and scenario persistence.
- Cap computations for a non-zero context use `projectTeamCaps(...)` and read the snapshot at `yearOffset = context`. This automatically rolls forward dead money, roster spend, extra reserves, and growth-based cap room.
- For move previews (release/trade) in future contexts, use contextualized player fields to ensure correct years-left, base salary index, and unamortized bonus/penalty.
- Default context is 0 to preserve current behavior and tests. All changes must be gated behind `yearContextOffset`.

## Source Code Structure
- New modules/files
  - `docs/roster_cap_tool/js/context.js` (new): Pure helpers to compute a context-adjusted player view.
  - `docs/roster_cap_tool/js/ui/yearContext.js` (new): UI component to render/select the Year Context and persist selection.
- Updated modules
  - `docs/roster_cap_tool/js/state.js`:
    - Add `yearContextOffset: number` (default 0) to app state.
    - Persist per team: `localStorage['rosterCap.yearContextByTeam']` as `{ [abbr]: number }`.
    - Expose getters/setters: `getYearContextOffset()`, `setYearContextOffset(n)`, `getContextLabel()`, and `getContextualPlayers()`.
    - Update derived getters (`getActiveRoster`, `getFreeAgents`, `getCapSummary`) to use contextualized players and context-aware cap math (details below).
    - Scenario persistence: include `yearContextOffset` in saved objects and apply on load.
  - `docs/roster_cap_tool/js/capMath.js`:
    - Export helpers to support contextualization where needed (e.g., `buildBaseSchedule` reuse) or add a small helper to compute remaining signing bonus.
    - Add `calcCapSummaryForContext(team, players, moves, contextOffset, opts)` which wraps `projectTeamCaps` and returns a `CapSnapshot` for the selected offset including `baselineAvailable` and `deltaAvailable` computed via a baseline-vs-current diff (moves vs no-moves) at that offset.
  - `docs/roster_cap_tool/js/ui/capSummary.js`:
    - Read the Cap Snapshot from `State.getCapSummary()` which becomes context-aware.
    - Show dynamic labels for the “Cap” column year (e.g., `Cap (Y+2)` if context=2) and ensure the metric values reflect the context year.
  - `docs/roster_cap_tool/js/ui/playerTable.js`:
    - Use contextualized players from `getActiveRoster()`/`getFreeAgents()`.
    - Replace hardcoded header “2025 Cap” with `Cap (Y+N)` label or actual year if needed, computed from team’s `seasonIndex + context`.
    - Update FA Year calculation to use contextual `contractYearsLeft` (years-left reduced by offset) so FA year = `team.seasonIndex + contextualYearsLeft`.
  - `docs/roster_cap_tool/js/ui/modals/releaseModal.js` and trade quick flows in `playerTable.js`:
    - Continue reading effective team cap from `State.getCapSummary()` (now context-aware).
    - Ensure passed player is contextual (via `getActiveRoster()` data source).
  - `docs/roster_cap_tool/js/ui/projections.js` and `ui/capSummary.js` header strip:
    - No behavior change for projections; they remain forward-looking from real Y+0. Inputs like re-sign budget and rollover still drive projections. The context affects only “as-of current” roster and cap math.
  - `docs/roster_cap_tool/js/ui/scenarioControls.js`:
    - Scenario save/load: persist and restore `yearContextOffset`.
  - `docs/roster_cap_tool/index.html`:
    - Mount the Year Context UI near team selector/header controls.

## Contracts
- State model additions
  - `state.yearContextByTeam: { [abbr: string]: number }` persisted to `localStorage['rosterCap.yearContextByTeam']`.
  - Derived `state.yearContextOffset: number` (read from map for selected team; defaults to 0).
  - New public API:
    - `getYearContextOffset(): number`
    - `setYearContextOffset(n: number): void` (clamp to [0..max], emits + persists)
    - `getContextLabel(): string` (e.g., `Y+0`, `Y+1`, ...)
    - `getContextualPlayers(): Player[]` (context-view, non-destructive)
  - Scenario object: add `yearContextOffset: number` field, default 0 when absent in older scenarios.

- Contextual player view (computed fields)
  - `contractYearsLeft_ctx = max(0, contractYearsLeft - offset)`
  - `yearsElapsed_ctx = clamp(contractLength - contractYearsLeft_ctx, 0, contractLength - 1)`
  - `bonusProrationYears = min(contractLength, MADDEN_BONUS_PRORATION_MAX_YEARS)`
  - `bonusPerYear = contractBonus / bonusProrationYears`
  - `baseSchedule = buildBaseSchedule(contractSalary, contractLength)`
  - `capHit_ctx = baseSchedule[yearsElapsed_ctx] + bonusPerYear` (guarded for undefined values)
  - `capReleasePenalty_ctx = remaining signing bonus = max(0, contractBonus - bonusPerYear * yearsElapsed_ctx)`
  - `capReleaseNetSavings_ctx = approxBase(ctx) - currentYearPenaltySplit(ctx)` when `capReleaseNetSavings` not reliable for future; otherwise use provided if present and clearly intended. For safety, prefer recompute fallback in context view.
  - `isFreeAgent_ctx = isFreeAgent || contractYearsLeft_ctx === 0` (remove from active roster in context)
  - These `_ctx` fields exist only on the derived view; original objects are not mutated.

- Cap snapshot for context
  - `calcCapSummaryForContext(team, players, moves, contextOffset, opts)`:
    - Compute `projCurrent = projectTeamCaps(team, players, moves, contextOffset + 1, opts)` and `projBaseline = projectTeamCaps(team, players, [], contextOffset + 1, opts)`.
    - Read snapshot `snap = projCurrent[contextOffset]` and baseline `base = projBaseline[contextOffset]`.
    - Return `{ capRoom: snap.capRoom, capSpent: snap.totalSpent, capAvailable: snap.capSpace, deadMoney: snap.deadMoney, baselineAvailable: base.capSpace, deltaAvailable: snap.capSpace - base.capSpace }`.

- UI contracts
  - Year Context selector element IDs/testids:
    - Container mount: `#year-context`
    - Buttons/selector values: data-testid `year-context-0`, `year-context-1`, `year-context-2`, ...
    - Label helper: `data-testid="year-context-label"`
  - Roster table column header changes:
    - Cap column header: `Cap (Y+N)` with `data-testid="col-cap-label"`

## Delivery Phases
1) Add state + helpers (no UI yet)
   - Implement `state.yearContextByTeam`, getters/setters, and `context.js` with transformation functions.
   - Update `getActiveRoster`/`getFreeAgents` to return contextualized players.
   - Implement `calcCapSummaryForContext` and wire `getCapSummary()` to use it when context > 0.

2) Add Year Context UI + wiring
   - Implement `ui/yearContext.js` and mount it in header (next to team selector).
   - Persist per team; update labels in `playerTable.js` and `capSummary.js`.

3) Actions in context (release/trade/extend/convert/sign)
   - Ensure modals and simulations use contextual players and context-aware cap snapshot.
   - Verify penalty split logic via Node tests and E2E.

4) Scenario persistence
   - Include `yearContextOffset` in save/load and keep Reset behavior (Reset keeps current context per PRD).

5) Projections polish
   - Keep projections semantics; add small note in header UI indicating current context to avoid confusion.

## Verification Strategy

Commands
- E2E tests: `npm run test:e2e` (starts server and runs Playwright)
- Node tests: `node scripts/test_cap_tool.mjs` (existing) and `node scripts/test_year_context.mjs` (to be added)

MCP servers (recommended)
- Filesystem server: to read/write repo files during automated verification
- Process/shell server: to run Node/Playwright commands
- Git server (optional): to diff/inspect changes during iterative development

Helper scripts to add
- `scripts/test_year_context.mjs`:
  - Unit-test `contextualizePlayer` transformation across edge cases:
    - Contract with 0, 1, 2+ years left at various offsets
    - Verify `capHit_ctx` follows base schedule index advancement
    - Verify `capReleasePenalty_ctx` equals unamortized bonus
  - Unit-test `calcCapSummaryForContext(...)` against `projectTeamCaps(...)[offset]` parity

E2E tests to add
- `tests/e2e/year-context.spec.ts`:
  - Renders Year Context control; default `Y+0` active
  - Switch to `Y+1`:
    - Cap Summary values change to reflect `projectTeamCaps(...)[1]`
    - Active roster count decreases for players expiring in Y+0 (they move to FA)
    - Cap column header shows `Cap (Y+1)`
  - Trigger Release on a player with 2 years left while in Y+1 and assert modal preview uses contextual penalty/savings
  - Switch to `Y+2` and confirm FA roll-off and labels again
  - Save scenario; reload; assert context persists

Sample input artifacts
- Use existing CSVs under `docs/roster_cap_tool/data/` (a: provided in repo)
- No additional sample inputs required; tests consume the hosted static tool

Acceptance/Regression checks
- Existing E2E tests (`smoke.spec.ts`, `projections.spec.ts`) must continue to pass under `Y+0` default
- New tests ensure correctness under `Y+1+` without changing default behavior

