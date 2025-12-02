# Implementation: Roster management wrong cut logic

## Changes Made

- docs/roster_cap_tool/js/models.js: expanded move typings to support FA-context fields
  - Added optional `faYearsAtRelease?: number` and `freeOutYears?: number` to `ReleaseMove` and `TradeQuickMove` (docs/roster_cap_tool/js/models.js:33).

- docs/roster_cap_tool/js/capMath.js:
  - simulateRelease: captured FA context on move
    - Added `faYearsAtRelease` and `freeOutYears = clamp(yearsLeft - 2, 0, 2)` to the generated move (docs/roster_cap_tool/js/capMath.js:169).
  - Added `deriveReleaseAddBackOverlay(...)` helper to compute add-back schedule for unaffected out-years (docs/roster_cap_tool/js/capMath.js:388).
  - projectTeamCaps: applied add-back overlay to roster totals so that releases only free cap for the correct number of seasons per FA year (docs/roster_cap_tool/js/capMath.js:449).

- scripts/test_cap_tool.mjs: updated and extended tests to the new rules
  - Scenario B (FA=2): Year+1 now increases only by next-year dead penalty; salary remains (scripts/test_cap_tool.mjs:47).
  - Scenario C (FA=3): Year+1 reflects removal + next-year penalty; Year+2 unchanged (scripts/test_cap_tool.mjs:84).
  - Added Scenario D (FA=4): Y+1 and Y+2 free salary (Y+1 also adds penalty); Y+3 unchanged (scripts/test_cap_tool.mjs:106).

## Test Results

- Ran `node scripts/test_cap_tool.mjs` locally.
- All assertions pass; process exits with code 0.
- Console: "Cap tool tests completed. Check exit code for failures." confirms run completion with no failures.

## Verification Steps

1. Build mental baselines via `projectTeamCaps` without moves for various FA-year players.
2. Simulate releases (`simulateRelease`) and re-run projections with players marked FA.
3. Observed expected out-year effects:
   - FA 2: Year+1 unchanged except for added next-year dead penalty.
   - FA 3: Year+1 frees salary + adds next-year dead; Year+2 unchanged.
   - FA 4: Years 1–2 free salary (Y+1 adds next-year dead); Year+3 unchanged.
4. Verified current-year anchoring remains intact and `calcCapSummary` semantics unchanged.

## Notes

- Dead money schedule logic unchanged; penalties continue to apply across current and next year.
- Backward compatibility: if older moves lack the new fields, `projectTeamCaps` infers `freeOutYears` from the player’s `contractYearsLeft` at projection time.

