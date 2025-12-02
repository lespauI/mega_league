# Implementation — Roster Cap Tool

## Changes Made

- Added reusable confirmation dialog to avoid native `window.confirm` suppression:
  - `docs/roster_cap_tool/js/ui/modals/confirmDialog.js` — `confirmWithDialog(opts)` Promise-based, accessible `<dialog>` with optional "Don't ask again" support via `localStorage`.

- Replaced all native confirms in the cap tool with `confirmWithDialog`:
  - `docs/roster_cap_tool/js/ui/scenarioControls.js` — Reset scenario confirmation with per-team remember key `rosterCap.skipConfirm.resetScenario.<TEAM>`.
  - `docs/roster_cap_tool/js/ui/playerTable.js` — Quick Trade confirmation now uses dialog; per-team remember key `rosterCap.skipConfirm.tradeQuick.<TEAM>`.
  - `docs/roster_cap_tool/js/ui/modals/tradeInModal.js` — Trade In confirmation via dialog; per-team remember key `rosterCap.skipConfirm.tradeIn.<TEAM>`.
  - `docs/roster_cap_tool/js/ui/modals/scenarioModals.js` — Delete saved scenario confirmation via dialog (destructive styling).

- Updated smoke tests:
  - `docs/roster_cap_tool/test.html` — Added a small check that pre-sets a remember key and asserts `confirmWithDialog` resolves `true` without showing UI.

## Test Results

- Search shows no remaining usages of `window.confirm` in `docs/roster_cap_tool`.
- Opened `docs/roster_cap_tool/test.html` manually:
  - All existing smoke assertions pass for cap math and state flows.
  - New confirm memory test passes (logs PASS), and does not display a blocking dialog when `localStorage` is available.

- Manual UI verification in `docs/roster_cap_tool/index.html`:
  - Reset: opens custom dialog; confirming resets scenario; checking "Don't ask again" skips future prompts for the active team.
  - Trade (Quick): opens custom dialog with Dead Cap/Savings/New Cap Space; confirming applies move; remember works per team.
  - Trade In: opens custom dialog with Year 1 Cap Hit and remaining cap; confirming applies move; remember works per team.
  - Delete Scenario: uses custom destructive dialog; works as expected.

## Verification Steps Performed

1. Added and imported the new dialog module across affected files.
2. Ensured event handlers using `await` are marked `async`.
3. Verified modal accessibility via existing `enhanceDialog` helper.
4. Scoped remember keys by action and team to avoid unintended global skipping.
5. Confirmed no regressions to existing release/extension/conversion modals (unchanged).

## Notes

- If users want to re-enable confirmations after choosing "Don't ask again", they can clear corresponding keys in `localStorage` (prefix `rosterCap.skipConfirm.*`). A dedicated "Clear confirmations" control can be added later if desired.

