# Solution Design — Roster Cap Tool

## Proposed Fix
- Eliminate all uses of native `window.confirm` in the app and replace them with an app‑controlled confirmation dialog built on the existing `<dialog>` pattern used by other modals (release, extension, conversion, etc.).
- Implement a reusable `confirmWithDialog(opts)` in a new module to render an accessible, styled confirmation modal that returns a Promise<boolean>.
- Optional UX: include a “Don’t ask again” checkbox scoped by an action‑specific storage key so users can skip confirmations by choice without breaking the app. Store this in `localStorage` and provide a safe default if storage is unavailable.

Why this fixes the bug: Browsers can suppress native dialogs after the user selects “Prevent additional dialogs / Do not show again.” When suppressed, `window.confirm` never shows and effectively returns false, so actions silently no‑op. Using an in‑app `<dialog>` avoids browser suppression entirely and restores consistent behavior.

## Scope of Changes (files)
- Add new module:
  - `docs/roster_cap_tool/js/ui/modals/confirmDialog.js` — exports `confirmWithDialog(opts)`.
- Replace native confirms with `confirmWithDialog` in:
  - `docs/roster_cap_tool/js/ui/scenarioControls.js:46–52` — Reset scenario.
  - `docs/roster_cap_tool/js/ui/playerTable.js:242–260` — Quick Trade confirmation.
  - `docs/roster_cap_tool/js/ui/modals/tradeInModal.js:61–76` — Trade In confirmation.
  - `docs/roster_cap_tool/js/ui/modals/scenarioModals.js:90–98` — Delete saved scenario (consistency).
- No CSS changes strictly required (reuses existing modal styling: `.modal-actions`, typography). If desired, add minor tweaks for the optional “Don’t ask again” row.

## New API: confirmWithDialog
Signature:
```
confirmWithDialog({
  title: string,
  message: string,           // plain text; can include line breaks
  confirmText?: string,      // default: 'Confirm'
  cancelText?: string,       // default: 'Cancel'
  danger?: boolean,          // style confirm as destructive
  rememberKey?: string,      // localStorage key to skip next time if user opts in
  rememberLabel?: string,    // label for the checkbox
}): Promise<boolean>
```

Behavior:
- If `rememberKey` is provided and localStorage has `true`, resolves to `true` immediately without rendering UI.
- Otherwise renders a `<dialog>` with title, message, Cancel and Confirm buttons; resolves `true` on confirm, `false` on cancel/close/Escape.
- When the “Don’t ask again” checkbox is checked and user confirms, it persists `true` to `rememberKey` (ignore on cancel).
- Uses `enhanceDialog` for focus‑trap and a11y; mounts under `#modals-root` if present, else `document.body`.

## Call‑site Replacements
- Reset (scenarioControls):
  - Replace `window.confirm('Reset scenario…')` with:
    - `confirmWithDialog({ title: 'Reset Scenario?', message: 'This clears all moves and edits.', confirmText: 'Reset', danger: true, rememberKey: 'rosterCap.skipConfirm.resetScenario.<TEAM>' })`
    - On `true`, call `resetScenario()`.
- Quick Trade (playerTable):
  - Replace `window.confirm(… Dead Cap / Savings / New Cap Space …)` with `confirmWithDialog` using the same computed numbers in `message` and `confirmText: 'Confirm Trade'`.
  - Optional `rememberKey: 'rosterCap.skipConfirm.tradeQuick.<TEAM>'` if we want to allow skipping future confirmations per team.
- Trade In (tradeInModal):
  - Replace `window.confirm(… Year 1 Cap Hit …)` with `confirmWithDialog` and confirm text `Trade In`.
- Delete Scenario (scenarioModals):
  - Replace `window.confirm('Delete this saved scenario?')` with `confirmWithDialog` and `danger: true`.

Note: Use per‑team keys (include `selectedTeam`) when the action materially affects current team roster, so the skip applies only to the active team.

## Edge Cases and Considerations
- LocalStorage unavailable: wrap gets/sets in try/catch and proceed without “remember” if storage is blocked.
- Dialog stacking: guard against multiple open confirms by disabling triggers while one is open; or rely on call‑site UX (buttons/menus already close on click). The dialog Promise resolves before a subsequent one can open in normal use.
- Keyboard/A11y: support Escape to cancel; Tab trap via `enhanceDialog`; restore focus to opener.
- Internationalization: messages are plain strings today; centralized API makes future i18n easier.
- Content safety: set `textContent` for message and title to avoid HTML injection; we display numeric values formatted via existing money formatter.
- Defaults: if anything fails in rendering, conservatively resolve `false` (no action) to avoid destructive changes without explicit confirmation.

## Testing Strategy
- Manual
  - Reproduce original problem: trigger native dialog suppression in a current build; observe Reset/Trade break. Then test the fixed build: confirmations appear via custom dialog and actions proceed.
  - Verify all four flows: Reset, Quick Trade, Trade In, Delete Scenario.
  - Verify keyboard (Tab/Escape) and focus return to the triggering control.
  - Verify optional “Don’t ask again”:
    - Check the box → subsequent actions skip confirmation and proceed.
    - Clear the stored flag manually (DevTools localStorage) to re‑enable prompts.
- Regression
  - Confirm existing `<dialog>` modals (release, extension, conversion, signing, scenario save/load/compare) still work.
  - Load in Chrome/Edge/Firefox/Safari; `<dialog>` already used elsewhere in the app.
- Optional: add a tiny harness in `test.html` to exercise `confirmWithDialog` (not required for fix).

## Risks and Mitigations
- Behavior change: users no longer see native browser confirms; mitigated by matching the same text and improving clarity.
- Silent auto‑confirm if “remember” is enabled: scope keys per team and action; provide a straightforward way to clear (see below) and default to off.
- Styling consistency: reuse existing `.modal-actions`; minimal/no CSS changes.

## Follow‑ups (nice‑to‑have)
- Add a small “Clear confirmations” link in scenario controls that removes `rosterCap.skipConfirm.*` keys for the active team.
- Telemetry/log lines for confirms (debug only) to aid support if needed.

## Implementation Notes
- The repository already contains `docs/roster_cap_tool/js/ui/a11y.js` used by other modals; reuse it here.
- Place the new file alongside existing modals: `docs/roster_cap_tool/js/ui/modals/confirmDialog.js`.
- Keep the function self‑contained and dependency‑free beyond `enhanceDialog`.

