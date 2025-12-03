// Contract utilities for start year and default distributions
/** @typedef {import('./models.js').Player} Player */

import { getBaseCalendarYear } from './state.js';

function toFinite(n, fallback = 0) {
  const v = typeof n === 'number' ? n : Number(n);
  return Number.isFinite(v) ? v : fallback;
}

function clamp(n, min, max) {
  return Math.max(min, Math.min(max, n));
}

/**
 * Compute the calendar year a player's current contract started.
 * Uses the app's base calendar year and the player's contract length/years left.
 * Returns null when base year is unavailable.
 * @param {Player} player
 * @returns {number|null}
 */
export function computeStartYear(player) {
  const baseYear = getBaseCalendarYear();
  if (baseYear == null) return null;
  const lenRaw = toFinite(player?.contractLength);
  const len = Math.max(1, Math.floor(Number.isFinite(lenRaw) && lenRaw > 0 ? lenRaw : toFinite(player?.contractYearsLeft, 1)));
  const yearsLeftNow = Math.max(0, Math.floor(toFinite(player?.contractYearsLeft, 0)));
  const yearsElapsedNow = clamp(len - yearsLeftNow, 0, len);
  return baseYear - yearsElapsedNow;
}

/**
 * Build a default 50/50 salary/bonus distribution map for remaining years only.
 * Per-year total is computed as (contractSalary + contractBonus) / contractLength.
 * Each year gets salary = bonus = perYear * 0.5 (rounded to dollars).
 * Keys are calendar years starting at the base calendar year for Y+0.
 * @param {Player} player
 * @returns {Record<number, { salary: number, bonus: number }>}
 */
export function computeDefaultDistribution(player) {
  /** @type {Record<number, { salary: number, bonus: number }>} */
  const out = {};
  const baseYear = getBaseCalendarYear();
  if (baseYear == null) return out;

  const lenRaw = toFinite(player?.contractLength);
  const len = Math.max(1, Math.floor(Number.isFinite(lenRaw) && lenRaw > 0 ? lenRaw : toFinite(player?.contractYearsLeft, 1)));
  const yearsLeftNow = Math.max(0, Math.floor(toFinite(player?.contractYearsLeft, 0)));
  if (yearsLeftNow <= 0 || len <= 0) return out;

  const total = Math.max(0, toFinite(player?.contractSalary, 0)) + Math.max(0, toFinite(player?.contractBonus, 0));
  const perYear = len > 0 ? (total / len) : 0;
  const perHalf = perYear * 0.5;

  for (let i = 0; i < yearsLeftNow; i++) {
    const yr = baseYear + i;
    out[yr] = { salary: Math.round(perHalf), bonus: Math.round(perHalf) };
  }
  return out;
}

export default {
  computeStartYear,
  computeDefaultDistribution,
};

