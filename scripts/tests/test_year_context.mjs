// Node unit tests for Year Context helpers
// Run: node scripts/tests/test_year_context.mjs

import assert from 'node:assert/strict';
import {
  projectPlayerCapHits,
  projectTeamCaps,
  calcCapSummaryForContext,
  simulateRelease,
} from '../../docs/roster_cap_tool/js/capMath.js';
import { contextualizePlayer } from '../../docs/roster_cap_tool/js/context.js';

function approxEqual(a, b, eps = 1) {
  assert.ok(Number.isFinite(a) && Number.isFinite(b), `non-finite compare: ${a} vs ${b}`);
  const d = Math.abs(a - b);
  assert.ok(d <= eps, `Expected ~${b}, got ${a} (diff ${d})`);
}

function testContextualizePlayer_basic() {
  const team = { abbrName: 'ABC', displayName: 'ABC', capRoom: 300_000_000, capSpent: 200_000_000, capAvailable: 100_000_000, seasonIndex: 0, weekIndex: 1 };
  const p = {
    id: 'p1', firstName: 'Test', lastName: 'Player', position: 'QB',
    team: 'ABC', isFreeAgent: false,
    contractLength: 4, contractYearsLeft: 3,
    contractSalary: 100_000_000, contractBonus: 20_000_000,
    // Year 0: base (index 1 = 24.3% of 100M) + bonus/year (5M) = 29.3M
    capHit: 29_300_000,
  };

  const off = 1;
  const c = contextualizePlayer(p, team, off);
  assert.equal(c.contractYearsLeft_ctx, 2, 'years left context');
  assert.equal(c.isFreeAgent_ctx, false, 'FA flag');

  // capHit_ctx equals projected cap at offset
  const caps = projectPlayerCapHits(p, off + 1);
  assert.equal(caps.length, 2);
  approxEqual(c.capHit_ctx, caps[off], 1e-3);

  // Penalty current: remaining unamortized bonus at context, 40% in current year when >=2 years left
  // Bonus per year = 20M/4 = 5M; remaining proration at context (len=4, yearsElapsed_ctx=2) = 2
  // penaltyTotal_ctx = 5M * 2 = 10M; current-year penalty ~ 4M
  approxEqual(c.capReleasePenalty_ctx, 4_000_000, 1);

  // Net savings ≈ base(year at context) - penaltyCurrent
  // Base at context index (elapsed 2) = 25.5% of 100M = 25.5M; savings ≈ 21.5M
  approxEqual(c.capReleaseNetSavings_ctx, 21_500_000, 2);
}

function testContextualizePlayer_penaltyFromCapReleasePenalty() {
  const team = { abbrName: 'ABC', displayName: 'ABC', capRoom: 300_000_000, capSpent: 200_000_000, capAvailable: 100_000_000, seasonIndex: 0, weekIndex: 1 };
  const p = {
    id: 'p2', firstName: 'Alt', lastName: 'Bonus', position: 'WR',
    team: 'ABC', isFreeAgent: false,
    contractLength: 4, contractYearsLeft: 3,
    contractSalary: 100_000_000,
    // No explicit contractBonus → derive from capReleasePenalty
    contractBonus: 0,
    // Today remaining proration is 3 (len 4, elapsed 1), so total bonus ≈ 15M * (4/3) = 20M
    capReleasePenalty: 15_000_000,
    // Year 0 capHit consistent with above (24.3M base + 5M proration)
    capHit: 29_300_000,
  };
  const off = 1;
  const c = contextualizePlayer(p, team, off);
  // Expect same penalty current as in basic case
  approxEqual(c.capReleasePenalty_ctx, 4_000_000, 1);
  // Cap hit at context should match projection
  const caps = projectPlayerCapHits(p, off + 1);
  approxEqual(c.capHit_ctx, caps[off], 1e-3);
}

function testContextualizePlayer_offsetBeyondContract() {
  const team = { abbrName: 'ABC', displayName: 'ABC', capRoom: 300_000_000, capSpent: 200_000_000, capAvailable: 100_000_000, seasonIndex: 0, weekIndex: 1 };
  const p = {
    id: 'p3', firstName: 'Edge', lastName: 'Case', position: 'CB',
    team: 'ABC', isFreeAgent: false,
    contractLength: 3, contractYearsLeft: 2,
    contractSalary: 30_000_000, contractBonus: 6_000_000,
    // Year 0 capHit approximate (index 1: 33.3% of 30M = 9.99M) + 2M proration = 11.99M
    capHit: 11_990_000,
  };
  const off = 3; // beyond yearsLeft (2)
  const c = contextualizePlayer(p, team, off);
  assert.equal(c.contractYearsLeft_ctx, 0, 'years left at/beyond horizon');
  assert.equal(c.isFreeAgent_ctx, true, 'becomes FA');
  assert.equal(c.capReleasePenalty_ctx, 0, 'no penalty for FA');
  assert.equal(c.capReleaseNetSavings_ctx, 0, 'no savings for FA');
  assert.equal(c.capHit_ctx, 0, 'no cap hit beyond contract');
}

function testCalcCapSummaryForContext_parity_noMoves() {
  const team = { abbrName: 'ABC', displayName: 'ABC', capRoom: 300_000_000, capSpent: 200_000_000, capAvailable: 100_000_000, seasonIndex: 0, weekIndex: 1 };
  const players = [
    {
      id: 'p1', firstName: 'Test', lastName: 'Player', position: 'QB',
      team: 'ABC', isFreeAgent: false,
      contractLength: 4, contractYearsLeft: 3,
      contractSalary: 100_000_000, contractBonus: 20_000_000,
      capHit: 29_300_000,
    },
    {
      id: 'p2', firstName: 'Other', lastName: 'Guy', position: 'LT',
      team: 'ABC', isFreeAgent: false,
      contractLength: 5, contractYearsLeft: 4,
      contractSalary: 50_000_000, contractBonus: 10_000_000,
      // Year 0: index 1 of 5-year schedule = 19% of 50M = 9.5M + 2M = 11.5M
      capHit: 11_500_000,
    },
  ];
  const off = 1;
  const snap = calcCapSummaryForContext(team, players, [], off);
  const proj = projectTeamCaps(team, players, [], off + 1);
  const base = projectTeamCaps(team, players, [], off + 1);
  const s = proj[off];
  const b = base[off];
  approxEqual(snap.capRoom, s.capRoom, 1e-3);
  approxEqual(snap.capSpent, s.totalSpent, 1e-3);
  approxEqual(snap.capAvailable, s.capSpace, 1e-3);
  approxEqual(snap.deadMoney, s.deadMoney, 1e-3);
  approxEqual(snap.baselineAvailable, b.capSpace, 1e-3);
  approxEqual(snap.deltaAvailable, 0, 1e-3);
}

function testCalcCapSummaryForContext_parity_withReleaseMove() {
  const team = { abbrName: 'ABC', displayName: 'ABC', capRoom: 300_000_000, capSpent: 200_000_000, capAvailable: 100_000_000, seasonIndex: 0, weekIndex: 1 };
  const p1 = {
    id: 'p1', firstName: 'Test', lastName: 'Player', position: 'QB',
    team: 'ABC', isFreeAgent: false,
    contractLength: 4, contractYearsLeft: 3,
    contractSalary: 100_000_000, contractBonus: 20_000_000,
    capHit: 29_300_000,
  };
  const p2 = {
    id: 'p2', firstName: 'Other', lastName: 'Guy', position: 'LT',
    team: 'ABC', isFreeAgent: false,
    contractLength: 5, contractYearsLeft: 4,
    contractSalary: 50_000_000, contractBonus: 10_000_000,
    capHit: 11_500_000,
  };
  const players = [p1, p2];
  const { move } = simulateRelease(team, p1);
  const moves = [move];
  const off = 1;
  const snap = calcCapSummaryForContext(team, players, moves, off);
  const proj = projectTeamCaps(team, players, moves, off + 1);
  const base = projectTeamCaps(team, players, [], off + 1);
  const s = proj[off];
  const b = base[off];
  approxEqual(snap.capRoom, s.capRoom, 1e-3);
  approxEqual(snap.capSpent, s.totalSpent, 1e-3);
  approxEqual(snap.capAvailable, s.capSpace, 1e-3);
  approxEqual(snap.deadMoney, s.deadMoney, 1e-3);
  approxEqual(snap.baselineAvailable, b.capSpace, 1e-3);
  approxEqual(snap.deltaAvailable, snap.capAvailable - b.capSpace, 1e-3);
}

async function main() {
  const tests = [
    ['contextualizePlayer basic', testContextualizePlayer_basic],
    ['contextualizePlayer derive bonus from capReleasePenalty', testContextualizePlayer_penaltyFromCapReleasePenalty],
    ['contextualizePlayer offset beyond contract', testContextualizePlayer_offsetBeyondContract],
    ['calcCapSummaryForContext parity (no moves)', testCalcCapSummaryForContext_parity_noMoves],
    ['calcCapSummaryForContext parity (release move)', testCalcCapSummaryForContext_parity_withReleaseMove],
  ];
  for (const [name, fn] of tests) {
    try {
      await fn();
      console.log(`ok - ${name}`);
    } catch (err) {
      console.error(`FAIL - ${name}:`, err && err.message ? err.message : err);
      process.exitCode = 1;
      return;
    }
  }
  console.log('All year context helper tests passed');
}

main();
