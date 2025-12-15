# Investigation: Roster management wrong cut logic

## Summary
- Reported behavior: Releasing a player with “FA year 2” wrongly affects Year+1 salary cap. Expected: with FA=2, release should affect current year only; with FA=3, affect current and Year+1; with FA=4, free money for current, Year+1 and Year+2 (3 seasons total). Dead cap penalties should still apply across 2 years (this season + next).
- Current tool: The release simulation removes the released player from all out‑years in projections, and applies a next‑year dead penalty split when there are multiple years left. This causes Year+1 to change even for the “FA year 2” case, contradicting the desired logic.

## Root Cause Analysis
1) Year‑limited effect of releases is not modeled
   - In projections, any release marks the player as “removed”, excluding their cap from all future years, regardless of contract years left.
   - Code reference: `docs/roster_cap_tool/js/capMath.js:511` (active roster filtering uses a `removed` set based on `release` / `tradeQuick` moves).

   File references:
   - docs/roster_cap_tool/js/capMath.js:511
   - docs/roster_cap_tool/js/capMath.js:506-510

   Effect: For a player with 2 years left (interpreting “FA year 2” as `contractYearsLeft = 2`), the tool removes their Year+1 cap from the roster projection. Thus Year+1 cap space changes, which is explicitly not desired.

2) Dead money split always impacts next year when multi‑year
   - `simulateRelease` splits total penalty as ~40% current year / ~60% next year if `contractYearsLeft >= 2`. This is then consumed by `deriveDeadMoneySchedule` and added to Year 0 and Year 1 dead money.
   - Code references:
     - docs/roster_cap_tool/js/capMath.js:134-181 (simulateRelease)
     - docs/roster_cap_tool/js/capMath.js:471-487 (deriveDeadMoneySchedule)

   This matches the “penalties for 2 years” constraint, but combined with (1) it removes the player’s Year+1 cap AND adds next‑year dead money — double‑impact to Year+1 for “FA year 2”, which is not desired.

3) Tests encode the current (undesired) behavior
  - `scripts/tests/test_cap_tool.mjs` Scenario B expects that releasing a 2‑year player increases Year+1 cap space (because the player is removed and only next‑year dead remains). This contradicts the new requested behavior (FA=2 should not affect Year+1).
  - File reference: scripts/tests/test_cap_tool.mjs:46-92

## Affected Components
- Cap math core:
  - docs/roster_cap_tool/js/capMath.js
    - `projectTeamCaps` (active roster filtering for removed players; no per‑year granularity) — docs/roster_cap_tool/js/capMath.js:497-642
    - `simulateRelease` (dead money split) — docs/roster_cap_tool/js/capMath.js:134-181
    - `deriveDeadMoneySchedule` (uses simulate to distribute over current/next year) — docs/roster_cap_tool/js/capMath.js:462-487
- UI flows that create release moves (no change needed for the bug itself but coupled to behavior):
  - docs/roster_cap_tool/js/ui/modals/releaseModal.js
- Projections UI (renders the results):
  - docs/roster_cap_tool/js/ui/projections.js
- Tests that assert current behavior:
  - scripts/tests/test_cap_tool.mjs

## Impact Assessment
- User‑visible:
  - When releasing a player with “FA year 2” (interpreted as `contractYearsLeft = 2`), Year+1 in the Projections view is currently affected (player cap is removed; dead money next year added). The requested behavior is that Year+1 should be unchanged for FA=2.
  - For FA=3 and FA=4, the tool presently removes player cap for ALL future years. The new requirement wants release to free money for only a limited number of seasons:
    - FA=3 → affect current and Year+1 only
    - FA=4 → affect current, Year+1 and Year+2 only
  - Dead money penalties should continue to apply across 2 years as they do now.

- Technical implications for the fix (to be designed/implemented in the next step):
  - `projectTeamCaps` needs per‑year selective removal rather than excluding released players entirely. One approach:
    - Keep players in the “active” list and subtract their projected cap hits only for the specific year offsets that should be affected by a release, based on `contractYearsLeft` at release time.
    - Map from `contractYearsLeft` to “affected out‑year offsets”:
      - FA=2 → affectOutYears = [] (no Year+1 change)
      - FA=3 → affectOutYears = [1]
      - FA=4+ → affectOutYears = [1, 2] (cap removal capped at next two seasons)
  - Alternatively, enrich the `release` move with an `affectsOffsets` field (computed at release time) and have `projectTeamCaps` apply that overlay instead of blanket removal.
  - Update tests in `scripts/tests/test_cap_tool.mjs` to reflect the new logic (e.g., Scenario B will need to expect Year+1 unchanged for FA=2).

## Notes / Assumptions
- “FA year N” is interpreted as `contractYearsLeft = N` at the time of release.
- The current “2‑year penalties” rule (current + next) remains valid and is already implemented.
- Year 0 remains “anchored” to team totals; release savings and current‑year dead money flow through `calcCapSummary` and the projections anchor (no change needed there).

## References
- cap math core: docs/roster_cap_tool/js/capMath.js:360-642, esp. 497-642, 134-181, 462-487
- release flow: docs/roster_cap_tool/js/ui/modals/releaseModal.js:1-160
- projections UI: docs/roster_cap_tool/js/ui/projections.js:1-220
- tests: scripts/tests/test_cap_tool.mjs:1-220
