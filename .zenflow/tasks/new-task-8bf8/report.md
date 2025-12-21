## Summary

- Updated depth chart initialization in `docs/depth_chart/js/state.js` so that, by default, WR1 gets the top overall WR and WR2 gets the second overall WR for each team.
- Applied the same alternating assignment logic for DT1 and DT2, ensuring DT1 starts with the top overall DT and DT2 with the second overall DT.
- Extended the alternating split behavior to CB1 and CB2 so CB1 gets the top overall CB and CB2 gets the second overall CB.
- The split logic keeps WR1/WR2, DT1/DT2, and CB1/CB2 using distinct players while preserving existing behavior for other positions.
