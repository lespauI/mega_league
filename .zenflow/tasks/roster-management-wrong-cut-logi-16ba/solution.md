# Solution Design: Roster management wrong cut logic

## Proposed Fix

Goal: Apply release (“cut”) effects to out-year projections based on FA year (contract years left) at the time of the move, instead of removing the player from all future years. Continue applying dead-cap penalties across two seasons (current + next) as today.

Rules to implement (interpreting “FA year N” as `contractYearsLeft = N` at release time):
- FA = 2 → affect current year only (no removal in Year+1). Dead penalty still applies to Year+1.
- FA = 3 → affect current year and Year+1 (no removal in Year+2).
- FA ≥ 4 → affect current, Year+1 and Year+2 (cap the effect to 3 seasons total). Dead penalty still 2 seasons (current + Year+1).

Key idea: Keep the current UI behavior that marks a released player as FA (so they disappear from the active roster), but “add back” their projected cap hits for the out-year offsets that should remain unaffected by the cut according to FA rules. This avoids double-impact to Year+1 in the FA=2 case.

Algorithm changes:
1) Extend release/tradeQuick move payload with FA context at move creation time:
   - `faYearsAtRelease: number` (copy of `player.contractYearsLeft` at time of move)
   - `freeOutYears: number` (number of out-year offsets to free/remove; mapping: `freeOutYears = clamp(faYearsAtRelease - 2, 0, 2)` → FA 2→0, 3→1, 4+→2)
   - These are persisted on the move to avoid recomputing from a mutated player object later.

2) In `projectTeamCaps`, after computing `rosterTotals[]` for the active roster (which excludes released players), add an overlay that re-adds released players’ cap hits for unaffected out-years:
   - Build `overlayAdd[]` initialized to zeros for the projection horizon.
   - For each move of type `release` or `tradeQuick`:
     - Find the player by id in the provided `players` array.
     - Determine `freeOutYears` from the move; if missing (back-compat), derive as `clamp(player.contractYearsLeft - 2, 0, 2)`.
     - Compute the player’s projected cap schedule via `projectPlayerCapHits(player, horizon)`.
     - For year offsets `o` where `o >= 1 + freeOutYears`, add back `caps[o]` into `overlayAdd[o]`.
     - If there are conversion moves for this player (from `deriveConversionIncrements`), also add back those increments for the same `o`.
   - After the roster totals loop, add `overlayAdd[o]` into `rosterTotals[o]` before building final per-year snapshots.
   - Never add back Year 0 (offset 0) — current year remains anchored to team totals and already reflects the move’s savings and current-year dead money.

3) Leave dead money schedule as-is:
   - `deriveDeadMoneySchedule` continues to place current-year penalty in `out[0]` and next-year penalty in `out[1]` based on `simulateRelease()` split. This preserves the “penalties for 2 years” rule while preventing unintended removal of out-year salary beyond the allowed windows.

Behavior outcomes:
- FA=2: Year+1 no longer benefits from salary removal; it only reflects next-year dead penalty (if any). This eliminates the current “double-impact” to Year+1.
- FA=3: Year+1 reflects removal + dead penalty; Year+2 remains unaffected (salary added back).
- FA≥4: Years 1 and 2 reflect removal (plus Year+1 dead penalty); Year+3+ remain unaffected.

Notes:
- This design assumes FA year mapping caps the out-year removal at two offsets (Y+1 and Y+2). If the user later wants a different cap, it’s a single constant change.
- Backward compatibility: Moves saved before the change won’t have `faYearsAtRelease/freeOutYears`. The fallback computation in `projectTeamCaps` handles these by inferring from the current player object (which retains `contractYearsLeft`).

## Files to Modify
- `docs/roster_cap_tool/js/capMath.js`
  - `simulateRelease(team, player)`: include `faYearsAtRelease` and `freeOutYears` on the returned `move`.
  - `projectTeamCaps(...)`: remove blanket “removed set” effect for out-years by adding an overlay step that re-adds unaffected out-year cap hits for released players based on `freeOutYears`. Keep Year 0 anchoring logic intact.
  - (Optional) Add a small helper e.g. `deriveReleaseAddBackOverlay(moves, players, horizon, convInc)` to keep `projectTeamCaps` readable.

- `docs/roster_cap_tool/js/models.js`
  - Update JSDoc typedefs for moves:
    - `ReleaseMove`: add optional `faYearsAtRelease?: number`, `freeOutYears?: number`.
    - `TradeQuickMove`: same optional fields for consistency.

- `docs/roster_cap_tool/js/ui/modals/releaseModal.js`
  - No UI changes required. It already takes `res.move` from `simulateRelease`; the new fields will be present automatically. Keep the explanatory text; behavior changes are reflected in projections.

- `scripts/tests/test_cap_tool.mjs`
  - Update expectations:
    - FA=2 case: Year+1 totalSpent should increase by next-year dead penalty only (no salary removal benefit), i.e., `ΔY+1 ≈ +penaltyNextYear`.
    - FA=3 case: Year+1 reflects removal + penalty; Year+2 unchanged vs baseline.
    - FA=4 case: Years 1 and 2 reflect removal (Year+1 also gets penalty); Year+3 unchanged vs baseline.

## Testing Strategy
- Unit tests (Node): extend `scripts/tests/test_cap_tool.mjs` with targeted scenarios:
  1) FA=2 (2y left): verify Year+1 roster salary is still included; only dead penalty affects Y+1; Year+2 baseline unaffected by contract termination.
  2) FA=3 (3y left): verify Y+1 decreases by (removed salary − next-year penalty); Y+2 unchanged vs baseline.
  3) FA=4 (4y left): verify Y+1 and Y+2 decrease by removed salary (Y+1 also adds penalty); Y+3 unchanged.
  4) Conversion before release: ensure add-back includes conversion increments for unaffected out-years.
  5) Back-compat: simulate a move without `freeOutYears` and confirm fallback logic produces the same results.

- UI sanity (manual):
  - In the Projections view, release a player with FA=2 and check that Year+1 Cap Space no longer gets a “double boost”; only next-year dead money is added.
  - Repeat for FA=3 and FA=4; confirm out-year effects stop at the correct offset.

## Risk Assessment
- Backward compatibility: Old scenarios missing the new fields are handled via fallback; risk is low.
- Double counting Year 0: Avoided by never adding back offset 0 and preserving anchor math.
- Conversion overlays: Ensure add-back includes conversion increments for removed players to prevent undercounting in unaffected years.
- Performance: Additional per-move loop with simple arrays; negligible overhead relative to existing projection work.
- Data correctness: Edge cases where multiple moves exist for the same player should be either prevented by UI or deduped in overlay (we’ll guard by only processing the first release/tradeQuick per player).
