# Investigation: Roster management bug fixes

## Summary

- Cap Space shows $0 for all teams: The UI displays Cap Space as $0 regardless of team. Expectation is that Cap Space should be derived as Current Cap − Cap Spent.
- Releasing a zero-dead-cap player negatively affects Year+1 cap: Example: releasing DAL RT Jawaan Taylor (capReleasePenalty = 0, FA next year) decreases Year+1 cap space, but it should not affect Year+1 at all because he already has no Y+1 salary.
- Releasing a player with dead cap doesn’t properly adjust Year+1 cap space: Example: releasing Diggs updates current-year cap correctly, but Year+1 cap space doesn’t reflect the removal of his Y+1 salary and addition of next-year dead money as expected; projections should do a full Year+1 recalc after roster moves.

## Root Cause Analysis

1) Cap Space $0 for all teams
- The current cap summary applies an unconditional override to the computed `capAvailable` using the in‑game “Re‑sign” value even when it defaults to 0. This results in `capAvailableEffective` becoming 0 + ΔSpace (typically 0 initially), so the UI shows $0 Cap Space for all teams.
  - Reference: `docs/roster_cap_tool/js/state.js:92-99` — `getCapSummary()` sets `capAvailableEffective` to `inGameReSign + deltaAvailable` whenever `x` is finite, which includes `0`.
  - The fix should either require an explicit user toggle (e.g., `useInGame === true`) or a positive in‑game value to apply the override. Additionally, to honor “Current Cap − Cap Spent = Cap Space”, the code should compute Cap Space as `capRoom − capSpent` when dataset-provided `capAvailable` is missing/inaccurate.

2) Zero-dead-cap release impacts Year+1 negatively
- After a release with zero dead money (e.g., Jawaan Taylor: `capReleasePenalty=0`, `contractYearsLeft=1`), Year+1 cap should be unchanged: he already contributes $0 in Y+1 salary and zero dead money. However, Year+1 decreases due to how re‑sign reserve is applied in projections.
  - The header projections and the projections table add extra planned spending for Y+1 as `reSignReserve = inGameReSign + deltaAvailable`:
    - References: `docs/roster_cap_tool/js/ui/capSummary.js:80-89`, `docs/roster_cap_tool/js/ui/projections.js:53-58`.
  - Releasing a player increases ΔSpace (savings > 0), which increases `reSignReserve` by the same amount. That extra Y+1 spending reduces Y+1 cap space, even though the player had no Y+1 salary and no dead money. This is perceived as a bug.
  - The underlying roster math (excluding re‑sign reserve) is correct: Year+1 roster totals come from `projectTeamCaps()` which sums active roster cap hits and adds dead money for moves:
    - `projectTeamCaps()` uses `active = players.filter(!isFreeAgent && team===abbr)`, so the released player is excluded from Y+1 roster cap after `isFreeAgent: true` is applied (see `docs/roster_cap_tool/js/ui/modals/releaseModal.js:67-91`).
    - Dead money schedule comes from `deriveDeadMoneySchedule()` calling `simulateRelease()` to compute current/next-year splits (see `docs/roster_cap_tool/js/capMath.js:453-469`, `133-165`).
  - Conclusion: Year+1 negative effect stems from the re‑sign reserve logic coupling current-year ΔSpace to Y+1 spending, not from the roster/penalty projections.

3) Dead-cap releases not reflected in Year+1
- The roster/penalty engine does recalc Y+1: `projectTeamCaps()` totals the remaining roster for Y+1 and adds next-year dead money derived from moves (`deriveDeadMoneySchedule()` → `simulateRelease()` with 60/40 split when `contractYearsLeft >= 2`; see `docs/roster_cap_tool/js/capMath.js:140-145` and `465-467`).
- If the user sees Y+1 unchanged after a dead-cap release, it’s likely because the extra Y+1 planned spending (re‑sign reserve = `inGameReSign + deltaAvailable`) offsets the expected improvement (or masks it), rather than a failure to remove the player’s Y+1 salary from the roster projection. This is consistent with the negative/neutral shifts observed.

## Affected Components

- `docs/roster_cap_tool/js/state.js:92-99` — `capAvailableEffective` override logic using in‑game re‑sign value unconditionally when finite (including 0), causing Cap Space to default to $0 for all teams.
- `docs/roster_cap_tool/js/ui/capSummary.js:23, 37-47` — Cap Space display uses `capAvailableEffective` (which is incorrectly overridden); spec calls for Cap Space ≈ Current Cap − Cap Spent.
- `docs/roster_cap_tool/js/ui/projections.js:53-58` and `docs/roster_cap_tool/js/ui/capSummary.js:80-89` — Re‑sign reserve applied to Y+1 as `X + ΔSpace`, which couples current-year savings to Y+1 extra spending and yields unexpected Y+1 decreases for zero‑dead releases.
- `docs/roster_cap_tool/js/capMath.js:71-124` — `calcCapSummary()` uses `baseAvail - deltaSpent`; consider deriving baseline available as `capRoom - capSpent` if dataset `capAvailable` is missing/incorrect.
- `docs/roster_cap_tool/js/capMath.js:480-614` — `projectTeamCaps()` Year 0 anchoring uses `baseAvail - deltaSpent` for current-year cap space; Y+1 uses fully recalculated roster caps, dead money, rookie reserve, re‑sign extra, and rollover.

## Impact Assessment

- Cap Space display incorrect by default: Ends up as $0 for all teams, confusing users and blocking basic planning.
- Y+1 cap space decreases after releasing a zero-dead-cap player: Counterintuitive and contradicts user expectations; stems from re‑sign reserve auto‑adjustment (X + ΔSpace), not from roster math.
- Y+1 not reflecting dead-cap releases as expected: The underlying projection engine removes the player and adds the correct next-year penalty, but the additional Y+1 planned spending (re‑sign reserve) can hide the expected improvement. Users perceive this as “no adjustment”.

## Notes for Solution Design (preview)

- Cap Space computation/display:
  - Only override `capAvailableEffective` when the user explicitly opts in (e.g., `useInGame === true`) and/or when the in‑game value is a positive number.
  - Derive current Cap Space as `capRoom − capSpent` (anchored to current-year after applying delta) if dataset `capAvailable` is missing or when override is not active.
- Projections (Y+1):
  - Decouple Y+1 re‑sign reserve from current-year ΔSpace, or gate it behind a user setting. This prevents zero‑dead releases from reducing Y+1 cap space and aligns with expectations that Year+1 should reflect roster and dead money only unless the user intentionally adjusts the re‑sign budget.

