# Implementation: Cut Penalty Year 1/Year 2 Fix

## Changes Made
- Updated penalty split for multi-year releases in `docs/roster_cap_tool/js/capMath.js`:
  - Current year receives ~60% of `capReleasePenalty` and next year receives the remainder (~40%) when `contractYearsLeft >= 2`.
  - This aligns the JS cap tool with in‑game behavior and our Python parity logic.
- Added a “Data Notes” section to `docs/roster_cap_tool/USAGE.md` documenting the CSV label inversion (Penalty Year 1/Year 2 reversed) and rationale for the change.

## Files Modified
- `docs/roster_cap_tool/js/capMath.js: simulateRelease()`
- `docs/roster_cap_tool/USAGE.md`

## Tests and Results
- Node unit tests: `node scripts/test_cap_tool.mjs` — passed (exit code 0).
- Python parity check: `python3 scripts/verify_cap_math.py --teams docs/roster_cap_tool/data/MEGA_teams.csv --players docs/roster_cap_tool/data/MEGA_players.csv --out output/cap_tool_verification.json` — 15/15 assertions passed.
- Browser smoke (`docs/roster_cap_tool/test.html`): contains an assertion for 60/40 split; with the code change, this is expected to pass when opened in a browser.

## Verification Steps
1. Ran `node scripts/test_cap_tool.mjs` to validate projections and penalty allocation logic.
2. Ran `python3 scripts/verify_cap_math.py` to confirm parity and overall cap math consistency.
3. Reviewed `docs/roster_cap_tool/test.html` to ensure its 60/40 expectation matches the new implementation.

## Notes
- The change corrects a mismatch where the JS cap tool previously allocated ~40% current/~60% next. Python and docs already assumed ~60% current/~40% next.
- If/when per‑year penalty fields arrive in CSVs, the tool should normalize by swapping Year 1/Year 2 on ingest to reflect actual in‑game application.
