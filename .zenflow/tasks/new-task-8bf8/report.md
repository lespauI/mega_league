## Summary

- Updated depth chart initialization in `docs/depth_chart/js/state.js` so that, by default, WR1 gets the top overall WR and WR2 gets the second overall WR for each team.
- Applied the same alternating assignment logic for DT1 and DT2, ensuring DT1 starts with the top overall DT and DT2 with the second overall DT.
- The split logic keeps WR1/WR2 and DT1/DT2 using distinct players while preserving existing behavior for other positions.

