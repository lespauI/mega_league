# Investigation — Roster Cap Tool

## Summary
- Report: Reset and Trade actions stop working after the user selects “Do not show this window again” on a popup alert.
- Observed pattern in code: These actions rely on native `window.confirm` dialogs for confirmation.
- When the browser suppresses dialogs (e.g., after the user clicks “Prevent this page from creating additional dialogs”), subsequent `confirm` calls do not display and effectively return a falsy result, so the app aborts the action.

## Root Cause Analysis
- The app uses native blocking dialogs (`window.confirm`) for critical flows:
  - Reset scenario: `docs/roster_cap_tool/js/ui/scenarioControls.js:48`
  - Quick trade from roster table: `docs/roster_cap_tool/js/ui/playerTable.js:251`
  - Trade-in flow (acquire player): `docs/roster_cap_tool/js/ui/modals/tradeInModal.js:70`
  - Delete saved scenario: `docs/roster_cap_tool/js/ui/modals/scenarioModals.js:94`
- Browsers can suppress native dialogs for the remainder of the page session after repeated dialogs or if the user checks a “do not show/prevent additional dialogs” option. In this state, `window.confirm` does not show a modal and the code path treats this as “user canceled,” causing no-op behavior.
- The app already uses custom `<dialog>`-based modals for most UX (release, extension, conversion, offers, scenario save/load/compare) but not for these confirmations, creating an inconsistent dependency on native dialogs.

## Affected Components (files)
- `docs/roster_cap_tool/js/ui/scenarioControls.js:41–50` — Reset action confirmation (Reset button becomes a no-op when dialogs are suppressed).
- `docs/roster_cap_tool/js/ui/playerTable.js:242–254` — Quick Trade confirmation in the action dropdown.
- `docs/roster_cap_tool/js/ui/modals/tradeInModal.js:65–71` — Trade In confirmation within the modal.
- `docs/roster_cap_tool/js/ui/modals/scenarioModals.js:93–96` — Delete scenario confirmation inside the load dialog.

## Impact Assessment
- Severity: High for workflow — Users who have suppressed dialogs cannot:
  - Reset scenarios to baseline
  - Execute quick trades from the roster table
  - Confirm trade-ins of players
  - Delete saved scenarios from the load dialog
- UX impact: Buttons appear to do nothing (silent failure) because the confirmation modal never shows and the code treats it as “canceled.” Users may not know to reload the page to restore dialogs.
- Scope: Limited to flows using `window.confirm`. Other modals (release, extension, conversion, signing) use custom `<dialog>` components and are unaffected.
- Persistence: Suppression typically lasts for the current page session; a full reload restores dialogs, but this is non-obvious.

## Reproduction Steps
1. Open `docs/roster_cap_tool/index.html` in a browser.
2. Trigger a confirmation several times (e.g., attempt a quick trade or reset) until the browser offers “Prevent this page from creating additional dialogs,” then select it (or otherwise suppress dialogs).
3. Attempt the Reset or Trade action again — no confirmation appears; action does not proceed.

## Notes
- The codebase already includes a11y helpers and consistent styling for custom modals (`<dialog>` + `enhanceDialog`). Migrating these confirmations to app-controlled modals will eliminate dependency on native dialogs and resolve the issue.
