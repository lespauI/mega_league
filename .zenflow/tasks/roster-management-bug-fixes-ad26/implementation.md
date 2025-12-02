# Implementation: Roster management bug fixes

## Changes Made

- Cap Space display (Current Cap − Cap Spent)
  - Updated `docs/roster_cap_tool/js/capMath.js::calcCapSummary()` to compute `capAvailable = capRoom - capSpent` so Cap Space is derived from arithmetic totals and not a stale dataset field.
  - Updated `docs/roster_cap_tool/js/ui/capSummary.js` to render Cap Space using `Current Cap − Cap Spent` to avoid any fallback to 0.

- Gate in‑game re‑sign override
  - In `docs/roster_cap_tool/js/state.js::getCapSummary()`, only apply the in‑game re‑sign override when the entered value is > 0; otherwise, use the computed `capAvailable`.

- Decouple Y+1 re‑sign reserve from ΔSpace
  - In `docs/roster_cap_tool/js/ui/projections.js` and `docs/roster_cap_tool/js/ui/capSummary.js` header projections, changed `reSignReserve` to use only the in‑game value (removed `+ ΔSpace`). Tooltips and help text updated accordingly.

- Full Year+1 recalculation after releases
  - In `docs/roster_cap_tool/js/capMath.js::projectTeamCaps()`, exclude players removed by `release/tradeQuick` moves even if the caller hasn’t mutated the players array yet. This guarantees Y+1 excludes their salary while `deriveDeadMoneySchedule()` adds next‑year penalty.
  - Unified quick trade preview to use the same effective cap as the Release modal in `docs/roster_cap_tool/js/ui/playerTable.js`.

## Tests Added

- Added `scripts/test_cap_tool.mjs` (Node ESM script) to validate projection behavior:
  - Scenario A: Release a 1‑year player with 0 dead cap → Y+1 cap space unchanged.
  - Scenario B: Release a 2‑year player with bonus → Y+1 cap space increases vs baseline (salary removed, only dead penalty remains).

Run: `node scripts/test_cap_tool.mjs`

## Test Results

- Local run: “Cap tool tests completed. Check exit code for failures.” (Exit code 0)

## Verification Steps

1) Launch the tool (`docs/roster_cap_tool/index.html`):
   - Cap Space now equals `Current Cap − Cap Spent` (no more default $0).
2) Release a zero‑dead‑cap player in final contract year (e.g., Jawaan Taylor‑like case):
   - Current year Cap Space increases by Savings.
   - Y+1 Cap Space unchanged (no re‑sign coupling to ΔSpace; no dead money added).
3) Release a player with dead cap (e.g., Diggs‑like case):
   - Current year Cap Space matches preview.
   - Y+1 Cap Space updates: salary removed, next‑year penalty applied.
4) Adjust “Resign budget” input:
   - Y+1 Cap Space decreases by exactly this value; current ΔSpace no longer affects it.

These changes align with the plan and address both reported issues.

