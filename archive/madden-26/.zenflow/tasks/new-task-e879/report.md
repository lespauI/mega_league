Implementation summary:

- Added shared draft pick storage for the depth chart (`docs/depth_chart/js/draftPicks.js`) reusing the same `localStorage` key as the Roster Cap Tool, with a default of 1 pick per round (1–7) when unset.
- Wired draft pick configuration into the depth-chart roster panel (`docs/depth_chart/js/ui/rosterPanel.js`) via a simple “Draft picks” section that lets users set per-round counts for the selected team.
- Updated the slot editor (`docs/depth_chart/js/ui/slotEditor.js`) to:
  - Read team draft picks and current depth plan usage.
  - Offer placeholder pills for Draft R1–R7, Trade, and FA.
  - Enforce per-round limits by disabling draft-round pills once their pick allocations are exhausted (while still allowing editing of the current assignment).
  - Add a “Cut to FA” button when a real player is assigned, which moves the player to FA, clears them from all depth slots, and closes the editor.
- Extended acquisition handling:
  - Added `draftR3`–`draftR7` to the acquisition type (`docs/depth_chart/js/state.js`).
  - Updated acquisition labels in the depth chart UI (`docs/depth_chart/js/ui/depthChart.js`) and CSV export (`docs/depth_chart/js/csvExport.js`) so all draft rounds export and render correctly.
- Adjusted styles in `docs/depth_chart/css/styles.css`:
  - Extended draft badge styling to `draftR3`–`draftR7`.
  - Styled disabled draft placeholder pills and the new slot-editor “Cut to FA” button.
  - Added compact layout styles for the new “Draft picks” section in the roster panel.

Notes:

- Depth-chart draft pick settings are persisted in `localStorage` under `rosterCap.draftPicks`, so they stay in sync with the Roster Cap Tool’s Draft Picks tab.
- Playwright is not installed in this environment, so I could not run `npm run test:e2e`; changes were aligned with existing patterns and existing depth-chart tests (e.g., those that look for “Draft R1”/“Draft R2” pills) were preserved semantically.

