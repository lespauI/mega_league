# Feature Specification: Future-Year Roster Context & Simulation

## User Stories*

### User Story 1 - Switch Future-Year Context

As a GM user, I can switch the roster tool’s “current year” context to Y+1, Y+2, Y+3, etc., so that all roster tables, cap summary, and actions behave as if I am operating in that future season.

**Acceptance Scenarios**:

1. Given the default current season view (Y+0), When I change the context to Y+1 using a year selector in the header, Then the cap room baseline updates to the next-season cap, roster cap columns relabel to the correct years, and player contract/FA statuses advance one year.
2. Given the Y+1 context, When I switch to Y+2, Then contracts advance an additional year, remaining bonus proration and years-left reflect the new context, and any players with no years remaining become free agents off my roster.

---

### User Story 2 - Perform Moves “As Of” Future Year

As a GM user, I can perform releases, trades, extensions, conversions, and signings while viewing a future-year context, and the tool applies cap math as of that selected season.

**Acceptance Scenarios**:

1. Given Y+1 context, When I simulate a release, Then the net savings and dead cap reflect the player’s remaining bonus and years-left as of Y+1 (e.g., a 1-year-left contract yields 100% current-year penalty, no next-year portion).
2. Given Y+1 context, When I sign a free agent for N years with salary/bonus, Then Year 1 cap hit is applied to Y+1 (not the current real-world year), and out-year projections shift accordingly.

---

### User Story 3 - Rollover, Rookie Reserve, and Dead Money in Future Years

As a GM user, I can see projected cap space in the selected future-year context that includes rollover, rookie reserve, and baseline dead money for that year.

**Acceptance Scenarios**:

1. Given Y+1 context with a rollover set to X and in-game re-sign reserve set to R, When I view Cap Summary and Header Projections, Then Y+1 cap space reflects: cap room for Y+1 minus roster cap, minus baseline dead money for Y+1, minus rookie reserve for Y+1, plus capped rollover from Y+0 (up to the configured maximum).
2. Given releases/trades made in Y+0 that create a 40/60 split dead money, When I switch to Y+1, Then the prior-year (Y+0) portion is no longer counted and only the “next year” portion applies as current-year dead money in Y+1.

---

### User Story 4 - Persistence and Reset with Year Context

As a GM user, I can save, load, and reset scenarios and the selected year context is preserved with the scenario state to avoid confusion when revisiting a scenario.

**Acceptance Scenarios**:

1. Given a scenario saved in Y+2 context, When I load it later, Then the tool restores the Y+2 context, the roster state for that year, and all moves applied relative to Y+2.
2. Given I reset a scenario while viewing Y+1 or Y+2, When I confirm reset, Then roster and moves revert to the baseline for the selected team and the year context remains whatever I selected (so I can continue planning in that future year).

---

## Requirements*

### Scope
- Add a “Year Context” selector in the tool header to choose the operating season: Y+0 (default), Y+1, Y+2, Y+3, … up to a reasonable limit (at least 3 future years, matching current projections, with potential to extend later).
- When a future year is selected, treat it as the “current year” for all calculations, UI labels, and actions:
  - Cap room baseline uses in-game future cap amounts (e.g., 324M for Y+1, 334M for Y+2, 344M for Y+3), then growth thereafter per existing projection logic.
  - Player contract progression advances by the selected year offset:
    - `contractYearsLeft` reduced by offset (not below 0).
    - Remaining bonus proration windows reduced by offset.
    - Base salary schedule indexed by years elapsed + offset.
    - Players with 0 years left at the selected context are treated as free agents (off the active roster) unless already re-signed within the scenario.
  - Release/trade savings and penalty use the player’s state “as of” the selected context (e.g., fewer years remaining may eliminate next-year penalty split).
  - Sign/extend/convert apply to the selected context’s “current year”.
  - Rollover from Y+0 into Y+1 is applied when Y+1 is selected (capped by configured maximum and by available Y+0 space). If viewing Y+2+, rollover is only the original Y+0→Y+1 transfer (i.e., we do not auto-chain rollovers unless explicitly configured later).
  - Rookie Reserve and Re-sign Reserve apply to the selected future year consistent with current projections.

### UI/UX
- Add a compact selector (dropdown or segmented buttons) labeled “Year Context” near the existing header projections.
  - Default selection: Y+0 (Current Season). Persist the selection across tabs and page reloads (per team).
  - Range: Y+0..Y+3 minimum. If projections horizon is extended by the user, selector should expand accordingly (up to a max cap, e.g., Y+5).
- Update table column headers and labels to match the selected context (e.g., in Y+1, the “2025 Cap” column should reflect the user’s Y+1 year and downstream years shift accordingly).
- Cap Summary reflects the selected context’s cap space and dead money; include an informational note that figures are “as of Y+N”.
- In Projections view, the top-strip header values should reflect deltas caused by actions in the selected context.
- Preserve accessibility and keyboard navigation for the selector; provide an aria-label describing the currently selected year.

### Data & Calculations
- Do not mutate the original CSV data; maintain a derived view based on the selected year offset, scenario moves, and projection math.
- When computing “current year” numbers in a future context:
  - Use `projectPlayerCapHits()` at offset N for roster players that remain under contract in Y+N.
  - Recompute release/trade penalties using `simulateRelease()` semantics but with `contractYearsLeft` and proration reduced by the selected offset.
  - Respect conversion increments applied in earlier contexts so that proration increases carry into out-years.
  - Only the relevant dead money for the current context is counted (e.g., the Y+1 portion of a prior 40/60 split).
  - Cap room baseline for Y+N uses the same source as in `projectTeamCaps` (hard-coded next 3 seasons, then growth).
- Rollover:
  - Allow user to specify a rollover value for Y+0 that is applied when viewing Y+1 context (min of requested, cap, and actual positive Y+0 cap space). Do not automatically roll beyond Y+1 unless a future enhancement defines that behavior.

### Scenario Persistence
- Save/Load should include the selected Year Context so restoring a scenario reproduces the same planning vantage point.
- Reset clears moves and roster edits but should not change the selected Year Context.

### Compatibility & Non-Functional
- Default behavior (Y+0) must remain unchanged to avoid regressions in current tests.
- Year Context changes should not degrade performance noticeably; all calculations remain client-side and leverage existing projection utilities.
- Maintain unit/e2e test coverage:
  - Add tests to verify: year selector presence; switching Y+0→Y+1 updates cap room and contract/FA status; release in Y+1 yields different penalty than in Y+0 with the same player; and header/table labels update accordingly.
  - Ensure existing tests pass unchanged when selector remains at default Y+0.

## Success Criteria*

- A “Year Context” selector exists, is accessible, and persists per team between sessions.
- With Y+1 selected:
  - Team cap room, roster cap, and dead money reflect Y+1 baselines, rookie reserve, re-sign reserve, and applied rollover.
  - Players whose contracts expire by Y+1 appear as free agents (unless re-signed in scenario) and are removed from the active roster totals.
  - Release/trade math uses Y+1 state (years left, remaining proration), changing 40/60 splits as appropriate.
  - Sign/extend/convert affect Y+1 “current-year” cap and update out-years accordingly.
- Switching Y+1→Y+2 advances the above effects by an additional year and updates labels/figures.
- All existing tests pass with selector at Y+0 and new tests pass for Y+1 semantics.

---

Assumptions applied where unspecified:
- Cap room anchors for Y+1..Y+3 remain 324M/334M/344M as in current projections; later years use growth rate.
- Free agents at Y+N are those with `contractYearsLeft - N <= 0` unless a scenario re-sign exists; we will not auto-generate re-signs.
- Rollover applies only from Y+0 to Y+1 with an upper bound (default $35M) and cannot exceed actual available Y+0 cap space.
- Rookie Reserve for Y+1 uses user-configured draft picks; Y+2+ assume 1 pick/round by default (consistent with current tool behavior).

