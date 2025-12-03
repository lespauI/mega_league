// Contextual roster helpers (pure, non-mutating)
// Computes per-player derived fields for a future "Year Context" (Y+offset)
// using the same proration and base-schedule logic as capMath.

/** @typedef {import('./models.js').Team} Team */
/** @typedef {import('./models.js').Player} Player */

import { projectPlayerCapHits, MADDEN_BONUS_PRORATION_MAX_YEARS } from './capMath.js';
import { getState, getYearContextForSelectedTeam, getCustomContract } from './state.js';

function toFinite(n, fallback = 0) {
  const v = typeof n === 'number' ? n : Number(n);
  return Number.isFinite(v) ? v : fallback;
}

function clamp(n, min, max) {
  return Math.max(min, Math.min(max, n));
}

function prorationYears(years) {
  const y = Math.max(1, Math.floor(toFinite(years, 1)));
  return clamp(y, 1, MADDEN_BONUS_PRORATION_MAX_YEARS);
}

// Keep base-salary weights aligned with capMath's buildBaseSchedule to avoid drift
const BASE_SALARY_WEIGHTS = {
  2: [48.7, 51.3],
  3: [31.7, 33.3, 35.0],
  4: [23.2, 24.3, 25.5, 27.0],
  5: [18.0, 19.0, 20.0, 21.0, 22.0],
  6: [14.7, 15.4, 16.2, 17.0, 17.9, 18.8],
  7: [12.3, 12.9, 13.5, 14.2, 14.9, 15.7, 16.5],
};

function buildBaseSchedule(totalSalary, length) {
  const len = Math.max(1, Math.floor(toFinite(length, 1)));
  const tot = Math.max(0, toFinite(totalSalary, 0));
  const w = BASE_SALARY_WEIGHTS[len];
  if (!w || !Array.isArray(w) || w.length !== len) {
    const per = len > 0 ? (tot / len) : 0;
    return Array.from({ length: len }, () => per);
  }
  const sum = w.reduce((a, b) => a + b, 0) || 1;
  const out = new Array(len).fill(0);
  let acc = 0;
  for (let i = 0; i < len; i++) {
    if (i === len - 1) {
      out[i] = Math.max(0, tot - acc);
    } else {
      const v = (tot * (w[i] / sum));
      out[i] = v;
      acc += v;
    }
  }
  return out;
}

/**
 * Derive (approximate) total signing bonus from player fields.
 * Prefers contractBonus; otherwise uses capReleasePenalty and remaining proration.
 */
function deriveBonusTotal(player) {
  const lenRaw = toFinite(player.contractLength);
  const len = Math.max(1, Math.floor(Number.isFinite(lenRaw) && lenRaw > 0 ? lenRaw : toFinite(player.contractYearsLeft, 1)));
  const yearsLeftNow = Math.max(0, Math.floor(toFinite(player.contractYearsLeft, 0)));
  const yearsElapsedNow = clamp(len - yearsLeftNow, 0, len);
  const prorateYears = Math.min(len, MADDEN_BONUS_PRORATION_MAX_YEARS);

  let bonusTotal = Math.max(0, toFinite(player.contractBonus, 0));
  if (!bonusTotal) {
    const remainingProrationNow = Math.max(0, prorateYears - yearsElapsedNow);
    const pen = Math.max(0, toFinite(player.capReleasePenalty, 0));
    if (pen > 0 && remainingProrationNow > 0) {
      bonusTotal = pen * (prorateYears / remainingProrationNow);
    }
  }
  return bonusTotal;
}

/**
 * Compute context-adjusted fields for a single player (pure; no mutation).
 * Adds the following derived fields on the returned object (suffix _ctx):
 * - contractYearsLeft_ctx
 * - isFreeAgent_ctx
 * - capHit_ctx
 * - capReleasePenalty_ctx (current-year penalty if released/traded in this context)
 * - capReleaseNetSavings_ctx (approx Savings in this context)
 * @param {Player} player
 * @param {Team} team
 * @param {number} offset
 */
export function contextualizePlayer(player, team, offset = 0) {
  const off = Math.max(0, Math.floor(toFinite(offset, 0)));
  const lenRaw = toFinite(player.contractLength);
  const len = Math.max(1, Math.floor(Number.isFinite(lenRaw) && lenRaw > 0 ? lenRaw : toFinite(player.contractYearsLeft, 1)));
  const yearsLeftNow = Math.max(0, Math.floor(toFinite(player.contractYearsLeft, 0)));
  const yearsLeft_ctx = Math.max(0, yearsLeftNow - off);
  const isFA_ctx = !!(player.isFreeAgent || yearsLeft_ctx <= 0);

  // Cap hit at the context year
  const baseCalendarYear = Number(team?.calendarYear || 0);
  const custom = getCustomContract(player.id);
  const caps = projectPlayerCapHits(player, off + 1, {
    customByAbsoluteYear: custom || undefined,
    baseCalendarYear: (Number.isFinite(baseCalendarYear) && baseCalendarYear > 0) ? baseCalendarYear : undefined,
  });
  const capHit_ctx = caps[off] || 0;

  // Derive bonus and proration windows at the context year
  const yearsElapsed_ctx = clamp(len - yearsLeft_ctx, 0, len);
  const prorateYears = Math.min(len, MADDEN_BONUS_PRORATION_MAX_YEARS);
  const remainingProration_ctx = Math.max(0, prorateYears - yearsElapsed_ctx);
  let bonusPerYear = 0;
  let remainingProration_ctx = Math.max(0, prorateYears - yearsElapsed_ctx);
  if (custom && baseCalendarYear > 0) {
    // When custom distribution is present, approximate remaining bonus as sum of per-year bonus from this context forward
    let totalRemain = 0;
    const startYear = baseCalendarYear + off;
    for (let i = 0; i < yearsLeft_ctx; i++) {
      const v = custom[startYear + i];
      if (v && Number.isFinite(Number(v.bonus))) totalRemain += Number(v.bonus);
    }
    // Distribute evenly across remaining proration windows for savings calc compatibility
    bonusPerYear = (remainingProration_ctx > 0) ? (totalRemain / remainingProration_ctx) : 0;
  } else {
    const bonusTotal = deriveBonusTotal(player);
    bonusPerYear = bonusTotal > 0 ? (bonusTotal / prorateYears) : 0;
    remainingProration_ctx = Math.max(0, prorateYears - yearsElapsed_ctx);
  }

  // Total penalty if released in this context equals remaining unamortized bonus
  const penaltyTotal_ctx = bonusPerYear * remainingProration_ctx;
  const penaltyCurrent_ctx = (penaltyTotal_ctx > 0 && yearsLeft_ctx >= 2)
    ? Math.round(penaltyTotal_ctx * 0.4)
    : penaltyTotal_ctx;

  // Approximate base salary for the context year
  let approxBase_ctx = 0;
  if (custom && baseCalendarYear > 0) {
    const v = custom[baseCalendarYear + off];
    approxBase_ctx = v ? Math.max(0, Number(v.salary || 0)) : 0;
  } else {
    const contractSalary = toFinite(player.contractSalary, 0);
    if (contractSalary > 0 && len > 0) {
      const sched = buildBaseSchedule(contractSalary, len);
      const idx = clamp(yearsElapsed_ctx, 0, sched.length - 1);
      approxBase_ctx = yearsLeft_ctx > 0 ? Math.max(0, toFinite(sched[idx], 0)) : 0;
    } else {
      // Fallback: base ≈ capHit - (bonusPerYear if proration remains)
      approxBase_ctx = Math.max(0, toFinite(capHit_ctx, 0) - (remainingProration_ctx > 0 ? bonusPerYear : 0));
    }
  }

  const capReleaseNetSavings_ctx = isFA_ctx ? 0 : (approxBase_ctx - penaltyCurrent_ctx);

  return {
    ...player,
    contractYearsLeft_ctx: yearsLeft_ctx,
    isFreeAgent_ctx: isFA_ctx,
    capHit_ctx: capHit_ctx,
    capReleasePenalty_ctx: isFA_ctx ? 0 : penaltyCurrent_ctx,
    capReleaseNetSavings_ctx: isFA_ctx ? 0 : capReleaseNetSavings_ctx,
  };
}

/**
 * Contextualize a list of players for a given team and offset.
 * @param {Array<Player>} players
 * @param {Team} team
 * @param {number} offset
 */
export function contextualizeRoster(players = [], team, offset = 0) {
  const list = Array.isArray(players) ? players : [];
  return list.map((p) => contextualizePlayer(p, team, offset));
}

/**
 * Convenience wrapper using global state selection.
 * Returns contextualized players for the currently selected team and its Year Context.
 */
export function getContextualPlayers() {
  const st = getState();
  const team = (st.teams || []).find((t) => t.abbrName === st.selectedTeam) || null;
  const off = getYearContextForSelectedTeam();
  return contextualizeRoster(st.players || [], team, off);
}

export default {
  contextualizePlayer,
  contextualizeRoster,
  getContextualPlayers,
};
