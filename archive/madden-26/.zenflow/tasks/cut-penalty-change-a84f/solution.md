# Solution Design: Cut Penalty Year Swap and 60/40 Fix

## Proposed Fix

1) Correct penalty split in the cap tool
- Location: `docs/roster_cap_tool/js/capMath.js`
- Problem: `simulateRelease()` currently allocates ~40% of `capReleasePenalty` to the current year and ~60% to next year when `contractYearsLeft >= 2`. This contradicts both our written docs and tests, and does not match in‑game behavior.
- Fix: Allocate ~60% to the current year and the remainder (~40%) to next year.
  - `penaltyCurrentYear = Math.round(penaltyTotal * 0.6)`
  - `penaltyNextYear = penaltyTotal - penaltyCurrentYear`
- Keep existing behavior for single‑year scenarios (100% current year).

2) Data ingestion safeguard (CSV Year 1/Year 2 labels are inverted)
- Context: The CSV source’s “Penalty Year 1” and “Penalty Year 2” labels are reversed versus how the game actually applies them.
- Current repo state: We do not currently ingest explicit per‑year penalty fields (we typically use `capReleasePenalty` only). If/when per‑year penalty fields are added to our ingest pipeline, normalize them by swapping on read:
  - Source `penalty_year_1` → App’s “next year”
  - Source `penalty_year_2` → App’s “current year”
- Where to apply: Centralize in the roster cap tool normalization (e.g., `docs/roster_cap_tool/js/validation.js` or `csv.js`) so all UI and math receive corrected values.

3) Documentation updates
- Add a short “Data correction note” explaining the Year 1/Year 2 inversion in the CSV and why we apply a swap/derive a 60/40 split to reflect actual in‑game application.
- Suggested placements:
  - `docs/roster_cap_tool/USAGE.md` (under Financial Rules Reference or a new Data Notes section)
  - Optional cross‑link in `spec/Salary Cap Works in Madden.md`

## Files to Modify
- `docs/roster_cap_tool/js/capMath.js` — implement 60/40 current/next split when `yearsLeft >= 2`.
- `docs/roster_cap_tool/USAGE.md` — add a “Data correction note” describing the CSV Year 1/Year 2 inversion and the rationale for the change.
- (Future) `docs/roster_cap_tool/js/validation.js` or `docs/roster_cap_tool/js/csv.js` — if explicit per‑year penalty fields are ingested, swap them on load.

## Testing Strategy
- Browser smoke tests: `docs/roster_cap_tool/test.html`
  - Already asserts 60/40 current/next split for release; should pass after the change.
- Script parity check: `scripts/verify_cap_math.py` and `scripts/tests/test_cap_tool.mjs`
  - Ensure computed current‑year and next‑year penalties match expectations and that Y+1 projections reflect the corrected next‑year dead money.
- Manual UI validation:
  - Release modal dead cap shows larger current‑year portion (~60%).
  - Dead money table and cap summary totals update accordingly.
  - Y+1/Y+2 projections respond as expected when releasing multi‑year contracts.

## Edge Cases and Considerations
- Single‑year remaining (`yearsLeft < 2`): 100% current‑year penalty (unchanged).
- Non‑finite/negative inputs: We already clamp `penaltyTotal` to `>= 0` and coerce numerics; keep this behavior.
- Rounding: We round the current‑year portion; next‑year receives the remainder. This mirrors our docs/tests and avoids off‑by‑one drift across years.
- Future ingestion of per‑year fields: Perform the Year 1/Year 2 swap at normalization time to keep the math functions simple and correct.

## Risk Assessment
- Low risk to code structure — the change is localized to `simulateRelease()` and documentation.
- Behavioral shift in UI and projections (current‑year dead money increases; next‑year decreases) — this corrects a known mismatch and aligns with our docs and tests.
- If any downstream logic assumed 40/60, it will now align with the documented 60/40 rule; tests that encoded 60/40 expectations should start passing.
