# Investigation: Cut Penalty Year 1/Year 2 Flip

## Summary of the bug
- The data source/CSV provides two dead money (cap penalty) numbers labeled for Year 1 and Year 2 when a player is cut/traded with 2+ years remaining. In practice (in‑game), these values apply in the opposite years.
- Our code also contains an inconsistency: the JS cap tool splits the penalty as 40% in the current year and 60% in the next year, while the documentation, tests, and Python verification logic all reflect that the current year should get the larger share (~60%) and next year the remainder (~40%).

## Root cause analysis
- The roster cap tool’s JS implementation `simulateRelease()` currently assigns:
  - `penaltyCurrentYear = round(total * 0.4)`
  - `penaltyNextYear = total - penaltyCurrentYear` (≈ 60%)
  when `yearsLeft >= 2`.
- This contradicts both our docs and tests, and mismatches the in‑game behavior that current year receives the larger portion of the dead money (~60%).
- Python parity code already uses 60/40 for current/next, and an inline comment states the same. The smoke test expects 60/40 as well. Thus, the JS code is the outlier.
- The CSV note from the report (“Year 1/Year 2 reversed”) reinforces that the labeling from the source is inverted relative to in‑game application. Even though we don’t currently ingest per‑year penalty fields for players, our derived split in JS should align with the game (60/40 current/next). If we later ingest per‑year fields, we must swap them on read.

## Affected components
- JS cap tool release logic:
  - docs/roster_cap_tool/js/capMath.js: simulateRelease() — lines around 139–148
    - Comment says “60/40 (current/next)”, but implementation does 40/60.
- UI surfaces that depend on simulateRelease() output:
  - docs/roster_cap_tool/js/ui/modals/releaseModal.js (dead cap shown in modal)
  - docs/roster_cap_tool/js/ui/playerTable.js (quick trade/release preview)
  - docs/roster_cap_tool/js/ui/deadMoneyTable.js (ledger totals by year)
  - docs/roster_cap_tool/js/ui/projections.js and js/ui/capSummary.js (Y+1 projections incorporate next‑year dead $)
- Verification/tests and docs (already consistent with 60/40):
  - scripts/verify_cap_math.py — uses 60% current / 40% next
  - docs/roster_cap_tool/test.html — asserts 60/40 current/next
  - docs/roster_cap_tool/USAGE.md and spec/Salary Cap Works in Madden.md — describe current year ≈ 60%, next year ≈ 40%

## Impact assessment
- Current UI shows incorrect current‑year dead money for releases/trades with 2+ years remaining (understated by using ~40% rather than ~60%).
- Y+1/Y+2 cap projections are skewed because dead money is allocated to the wrong year, potentially misleading roster decisions (e.g., overestimating current‑year cap space and underestimating next‑year impact).
- Smoke test expectations (60/40) do not match the current JS logic.
- Python verification and written documentation reflect the correct behavior; only the JS cap tool logic needs correction. If/when we ingest explicit per‑year penalty fields from CSV, we must swap Year 1/Year 2 from source to match the in‑game application.

## Evidence and references
- JS (incorrect split): docs/roster_cap_tool/js/capMath.js:139–148
  - Implements 40% current / 60% next.
- Python (correct split): scripts/verify_cap_math.py:240–260
  - Implements 60% current / 40% next.
- Test (expects 60/40): docs/roster_cap_tool/test.html:62–66
- Docs (state 60/40 current/next):
  - docs/roster_cap_tool/USAGE.md (dead money distribution note)
  - "spec/Salary Cap Works in Madden.md" (Year 1 ≈ 60%, Year 2 ≈ 40%)

## Notes for Solution Design (next step)
- Update simulateRelease() to use 60/40 when `yearsLeft >= 2`:
  - `penaltyCurrentYear = Math.round(total * 0.6)`
  - `penaltyNextYear = total - penaltyCurrentYear`
- Add a clarifying note in documentation explaining:
  - The CSV source labels Year 1/Year 2 reversed vs in‑game behavior, and we intentionally correct (swap) them on ingest or via derived 60/40 split to match actual game outcomes.
- Verify that smoke test numbers align after the change and spot‑check projections.
