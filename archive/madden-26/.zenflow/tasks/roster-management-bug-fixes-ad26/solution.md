# Solution Design: Roster management bug fixes

## Proposed Fixes

1) Cap Space shows $0 for all teams
- Compute current-year Cap Space as `Current Cap − Cap Spent` consistently.
  - In `calcCapSummary(team, moves)`, keep deriving `capSpent = team.capSpent + deltaSpent` (where `deltaSpent` aggregates moves), and set `capAvailable = team.capRoom − capSpent`.
  - Set `deltaAvailable = -deltaSpent` so Gain/Loss reflects only scenario deltas, independent of dataset inconsistencies between `capRoom`, `capSpent`, and `capAvailable`.
  - Preserve `baselineAvailable = team.capAvailable` for reference and for any UI that still wants to show the in-game baseline snapshot.
- Gate the “in‑game re‑sign override” used for `capAvailableEffective` so it does not default Cap Space to 0.
  - Only apply `capAvailableEffective = inGameReSign + deltaAvailable` when either:
    - the team setting `useInGame` is true; or
    - the provided in‑game value is a positive number.
  - Otherwise, use the computed `capAvailable` (i.e., `capRoom − capSpent`).

Outcome:
- Cap Space displayed in the summary becomes `Current Cap − Cap Spent` and no longer shows $0 by default for all teams.
- “Cap Gain/Loss” remains a pure delta from scenario moves (`-deltaSpent`).

2) Releasing a zero-dead-cap player reduces Year+1 cap (should not)
- Decouple Y+1 projections from current-year ΔSpace in the re‑sign reserve logic.
  - In both the header projections strip and the projections table, change `reSignReserve` from `inGameReSign + deltaAvailable` to just `inGameReSign` (the user‑entered value). Optionally, expose a toggle to “Include current ΔSpace in re‑sign” for power users; default OFF.
  - This prevents zero-dead-cap releases from decreasing Y+1 cap space via the re‑sign reserve coupling.

3) Releasing a player with dead cap doesn’t adjust Year+1 (should do)
- Ensure projections continue to fully recalc Y+1 using the roster after moves and the derived dead‑money schedule:
  - Keep removing released players from the active roster (`isFreeAgent: true, team: ''`) so their Y+1 base salary/cap is excluded.
  - Derive next‑year dead money through `deriveDeadMoneySchedule()` which recomputes current vs next‑year splits (60/40 when `contractYearsLeft >= 2`, otherwise 100% current year). The projections then add that next‑year penalty to Y+1 totals.
- With the re‑sign reserve decoupled from ΔSpace, the expected improvement (remove salary, add penalty) will be visible in Y+1 cap space after each roster move.

4) Consistency improvements (minor, to avoid preview mismatches)
- In quick trade preview, use the same effective cap (`capAvailableEffective`) that the release modal uses when computing “New Cap Space” so confirmations and post‑apply snapshots match.

## Files to Modify

- `docs/roster_cap_tool/js/capMath.js`
  - `calcCapSummary()`: set `capAvailable = capRoom − (capSpent)`; set `deltaAvailable = -deltaSpent`.
- `docs/roster_cap_tool/js/state.js`
  - `getCapSummary()`: gate `capAvailableEffective` override by `useInGame === true` or `inGameValue > 0`; default to computed `capAvailable` otherwise.
  - `getRolloverForSelectedTeam()`: leave default fallback based on computed `capAvailable` (not the override) so rollover reflects true leftover space.
- `docs/roster_cap_tool/js/ui/capSummary.js`
  - Continue rendering “Cap Space” from `capAvailableEffective` (now correctly computed); no extra math in the view.
  - In header projections (`mountHeaderProjections()`), change `reSignReserve` to use only the in‑game value (remove `+ deltaAvailable`). Update the “Applied” label text accordingly.
- `docs/roster_cap_tool/js/ui/projections.js`
  - Same `reSignReserve` change and “Applied” label text as above for the full projections table.
- `docs/roster_cap_tool/js/ui/playerTable.js`
  - For `tradeQuick` preview, use `capAvailableEffective` like the Release modal for parity.

## Testing Strategy

Manual smoke (docs/roster_cap_tool/index.html or test.html):
- Baseline summary
  - Load any team; verify Cap Space equals `Current Cap − Cap Spent` and is no longer $0 by default.
  - Verify Cap Gain/Loss (Δ) starts at 0 and changes sign correctly: release → positive Δ; sign/extend/convert increasing cap hit → negative Δ.
- Release with zero dead cap (e.g., a player with `capReleasePenalty = 0` and FA next year)
  - Confirm current-year Cap Space increases by the “Savings” amount.
  - Confirm Y+1 cap space is unchanged (no dead money added; no re‑sign reserve coupling to ΔSpace).
- Release with dead cap (e.g., Diggs‑like case)
  - Confirm current-year Cap Space matches preview.
  - Confirm Y+1 cap space recalculates: the player’s Y+1 cap is removed and the next‑year penalty is added; net effect should reflect “only dead money remains”.
- Re‑sign reserve input
  - Set a non‑zero in‑game re‑sign value; verify Y+1 cap space decreases by exactly that value (no ΔSpace coupling).
  - With value set to 0, verify Y+1 cap space is unaffected by zero‑dead releases.

Regression checks
- Test “Trade (Quick)”, “Extension”, “Conversion”, and “Sign” flows to ensure preview values match post‑apply `getCapSummary()` and projections update immediately.
- Multi‑team sanity: spot‑check several teams to ensure Cap Space is no longer hard‑coded to $0.

## Risk Assessment

- Initial Cap Space may now differ slightly from the dataset’s `capAvailable` when `capRoom ≠ capSpent + capAvailable` due to data quirks. This is intentional to satisfy “Current Cap − Cap Spent = Cap Space”. We keep the dataset value as `baselineAvailable` for reference.
- Some users may prefer “re‑sign reserve = X + ΔSpace” behavior. Making ΔSpace opt‑in (toggle) preserves the option without surprising defaults. For now, default to “X only”.
- Projections rely on `contractYearsLeft` to split dead money 60/40 across current/next year on release/trade; inaccuracies in that field can affect the next‑year penalty schedule. This matches the existing simplification and is unchanged by this fix.

---

This design addresses both reported issues: Cap Space display no longer defaults to $0 and Year+1 projections reflect releases correctly without unintended coupling to current-year ΔSpace.

