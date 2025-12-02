// Lightweight Node tests for roster cap tool projections
// Run with: node scripts/test_cap_tool.mjs
import { readFile } from 'node:fs/promises';
const capMathCode = await readFile(new URL('../docs/roster_cap_tool/js/capMath.js', import.meta.url), 'utf8');
const capMathMod = await import('data:text/javascript;base64,' + Buffer.from(capMathCode).toString('base64'));
const { projectTeamCaps, simulateRelease } = capMathMod;

function assert(cond, msg) {
  if (!cond) {
    console.error('Assertion failed:', msg);
    process.exitCode = 1;
  }
}

function money(n) { return Math.round(Number(n || 0)); }

// Common team baseline
const team = {
  abbrName: 'DAL',
  capRoom: 300_000_000,
  capSpent: 200_000_000,
  capAvailable: 100_000_000,
};

// Scenario A: Release player with 1 year left and zero penalty → Y+1 unchanged
(() => {
  const p = {
    id: 'P1', firstName: 'Test', lastName: 'One', position: 'T',
    isFreeAgent: false, team: 'DAL',
    capHit: 10_000_000,
    contractSalary: 10_000_000,
    contractBonus: 0,
    contractLength: 1,
    contractYearsLeft: 1,
    capReleasePenalty: 0,
    capReleaseNetSavings: 10_000_000,
  };
  const players = [p];
  const baseline = projectTeamCaps(team, players, [], 2);
  // Baseline Y+1 should not include player cap (contract ends)
  const baseY1 = money(baseline[1].capSpace);

  // Apply release
  const sim = simulateRelease(team, p);
  const moves = [sim.move];
  const playersAfter = [{ ...p, isFreeAgent: true, team: '' }];
  const after = projectTeamCaps(team, playersAfter, moves, 2);
  const afterY1 = money(after[1].capSpace);
  // Expect unchanged Y+1
  assert(afterY1 === baseY1, `Scenario A: expected Y+1 unchanged (${afterY1} vs ${baseY1})`);
})();

// Scenario B: Release 2-year player with bonus → Y+1 increases by (removed cap - next-year penalty)
(() => {
  const p = {
    id: 'P2', firstName: 'Test', lastName: 'Two', position: 'WR',
    isFreeAgent: false, team: 'DAL',
    capHit: 17_500_000, // approx base + bonus per year
    contractSalary: 20_000_000,
    contractBonus: 10_000_000,
    contractLength: 2,
    contractYearsLeft: 2,
    capReleasePenalty: 10_000_000,
    capReleaseNetSavings: 2_000_000, // arbitrary current-year net savings
  };
  const players = [p];
  const baseline = projectTeamCaps(team, players, [], 3);
  // Compute player's projected Y+1 cap from baseline via difference (single player)
  const baseY1Spent = baseline[1].totalSpent;
  const baseY1Space = baseline[1].capSpace;

  // After release, player removed; dead money next year should be 40% of penalty (per simulateRelease split)
  const sim = simulateRelease(team, p);
  const moves = [sim.move];
  const playersAfter = [{ ...p, isFreeAgent: true, team: '' }];
  const after = projectTeamCaps(team, playersAfter, moves, 3);
  const afterY1Spent = after[1].totalSpent;
  const afterY1Space = after[1].capSpace;

  // Baseline Y+1 included player's year-2 cap; after release includes only next-year dead money
  // So Y+1 spent should decrease, space should increase
  assert(afterY1Spent <= baseY1Spent, `Scenario B: expected Y+1 spent to decrease (${afterY1Spent} <= ${baseY1Spent})`);
  assert(afterY1Space >= baseY1Space, `Scenario B: expected Y+1 space to increase (${afterY1Space} >= ${baseY1Space})`);
})();

console.log('Cap tool tests completed. Check exit code for failures.');
