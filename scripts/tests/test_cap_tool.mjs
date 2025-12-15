// Lightweight Node tests for roster cap tool projections
// Run with: node scripts/tests/test_cap_tool.mjs
import { readFile } from 'node:fs/promises';
const capMathCode = await readFile(new URL('../../docs/roster_cap_tool/js/capMath.js', import.meta.url), 'utf8');
const capMathMod = await import('data:text/javascript;base64,' + Buffer.from(capMathCode).toString('base64'));
const { projectTeamCaps, simulateRelease, projectPlayerCapHits } = capMathMod;

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

// Scenario B: Release 2-year player with bonus → Y+1 increases only by next-year dead penalty (salary remains)
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

  // For FA=2, Year+1 should be unaffected except for next-year dead penalty
  assert(money(afterY1Spent) === money(baseY1Spent + sim.penaltyNextYear), `Scenario B: expected Y+1 spent base + next-year penalty (${afterY1Spent} vs ${baseY1Spent} + ${sim.penaltyNextYear})`);
  assert(money(afterY1Space) === money(baseY1Space - sim.penaltyNextYear), `Scenario B: expected Y+1 space base - next-year penalty (${afterY1Space} vs ${baseY1Space} - ${sim.penaltyNextYear})`);
})();

console.log('Cap tool tests completed. Check exit code for failures.');

// Scenario C: Multi-year contract (3y left). After release, Y+1 changes (salary removed + penalty), Y+2 unchanged.
(() => {
  const teamC = { abbrName: 'DAL', capRoom: 300_000_000, capSpent: 200_000_000, capAvailable: 100_000_000 };
  const p = {
    id: 'P3', firstName: 'Test', lastName: 'Three', position: 'OT',
    isFreeAgent: false, team: 'DAL',
    capHit: 16_000_000, // approximated current
    contractSalary: 36_000_000, // ~12M/yr base schedule
    contractBonus: 9_000_000,   // proration 3y → 3M/yr
    contractLength: 3,
    contractYearsLeft: 3,
    capReleasePenalty: 9_000_000,
    capReleaseNetSavings: 1_000_000,
  };
  const players = [p];
  const baseline = projectTeamCaps(teamC, players, [], 4);
  const caps = projectPlayerCapHits(p, 4);
  const baseY2Spent = baseline[2].totalSpent;
  const baseY2Space = baseline[2].capSpace;
  const baseY1Spent = baseline[1].totalSpent;
  const baseY1Space = baseline[1].capSpace;

  const sim = simulateRelease(teamC, p);
  const moves = [sim.move];
  const playersAfter = [{ ...p, isFreeAgent: true, team: '' }];
  const after = projectTeamCaps(teamC, playersAfter, moves, 4);
  const afterY2Spent = after[2].totalSpent;
  const afterY2Space = after[2].capSpace;
  const afterY1Spent = after[1].totalSpent;
  const afterY1Space = after[1].capSpace;

  // Y+1: removed salary plus next-year dead penalty
  assert(money(afterY1Spent) === money(baseY1Spent - caps[1] + sim.penaltyNextYear), `Scenario C: expected Y+1 spent = base - cap[1] + penaltyNext (${afterY1Spent} vs ${baseY1Spent} - ${caps[1]} + ${sim.penaltyNextYear})`);
  assert(money(afterY1Space) === money(baseY1Space + caps[1] - sim.penaltyNextYear), `Scenario C: expected Y+1 space = base + cap[1] - penaltyNext (${afterY1Space} vs ${baseY1Space} + ${caps[1]} - ${sim.penaltyNextYear})`);

  // Y+2 unchanged for FA=3
  assert(money(afterY2Spent) === money(baseY2Spent), `Scenario C: expected Y+2 spent unchanged (${afterY2Spent} vs ${baseY2Spent})`);
  assert(money(afterY2Space) === money(baseY2Space), `Scenario C: expected Y+2 space unchanged (${afterY2Space} vs ${baseY2Space})`);
})();

// Scenario D: 4y left. After release, Y+1 and Y+2 free salary (Y+1 also adds penalty), Y+3 unchanged.
(() => {
  const teamD = { abbrName: 'DAL', capRoom: 300_000_000, capSpent: 200_000_000, capAvailable: 100_000_000 };
  const p = {
    id: 'P4', firstName: 'Test', lastName: 'Four', position: 'CB',
    isFreeAgent: false, team: 'DAL',
    capHit: 12_000_000,
    contractSalary: 40_000_000,
    contractBonus: 10_000_000,
    contractLength: 4,
    contractYearsLeft: 4,
    capReleasePenalty: 10_000_000,
    capReleaseNetSavings: 3_000_000,
  };
  const players = [p];
  const baseline = projectTeamCaps(teamD, players, [], 5);
  const caps = projectPlayerCapHits(p, 5);
  const baseY1Spent = baseline[1].totalSpent;
  const baseY1Space = baseline[1].capSpace;
  const baseY2Spent = baseline[2].totalSpent;
  const baseY2Space = baseline[2].capSpace;
  const baseY3Spent = baseline[3].totalSpent;
  const baseY3Space = baseline[3].capSpace;

  const sim = simulateRelease(teamD, p);
  const after = projectTeamCaps(teamD, [{ ...p, isFreeAgent: true, team: '' }], [sim.move], 5);
  const afterY1Spent = after[1].totalSpent;
  const afterY1Space = after[1].capSpace;
  const afterY2Spent = after[2].totalSpent;
  const afterY2Space = after[2].capSpace;
  const afterY3Spent = after[3].totalSpent;
  const afterY3Space = after[3].capSpace;

  // Y+1: remove cap + add next-year dead
  assert(money(afterY1Spent) === money(baseY1Spent - caps[1] + sim.penaltyNextYear), `Scenario D: Y+1 spent mismatch`);
  assert(money(afterY1Space) === money(baseY1Space + caps[1] - sim.penaltyNextYear), `Scenario D: Y+1 space mismatch`);
  // Y+2: remove cap only
  assert(money(afterY2Spent) === money(baseY2Spent - caps[2]), `Scenario D: Y+2 spent = base - cap[2]`);
  assert(money(afterY2Space) === money(baseY2Space + caps[2]), `Scenario D: Y+2 space = base + cap[2]`);
  // Y+3: unchanged
  assert(money(afterY3Spent) === money(baseY3Spent), `Scenario D: Y+3 spent unchanged`);
  assert(money(afterY3Space) === money(baseY3Space), `Scenario D: Y+3 space unchanged`);
})();
