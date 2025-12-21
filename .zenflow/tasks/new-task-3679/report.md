## Summary

- Updated the depth chart position card rendering (`docs/depth_chart/js/ui/depthChart.js:120`) to use a dynamic row count per slot, showing at least three rows and always enough rows to display all existing depth assignments for that position.
- Adjusted split-position logic in `getPlayersForSlot` (`docs/depth_chart/js/slots.js:71`) so split slots (e.g., WR1/WR2, DT1/DT2, CB1/CB2) assign the top overall player as the primary in the “1” slot, the second-best overall as the primary in the “2” slot, then divide the remaining players in half between the two slots without overlap.
- Attempted to run the depth chart tests, but `npm test` failed because there is no `test` script defined in `package.json`; no automated tests were executed.

