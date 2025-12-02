// Pure cap math helpers implementing simplified Madden rules
// Reference: spec/Salary Cap Works in Madden.md

/** @typedef {import('./models.js').Team} Team */
/** @typedef {import('./models.js').Player} Player */
/** @typedef {import('./models.js').CapSnapshot} CapSnapshot */
/** @typedef {import('./models.js').ScenarioMove} ScenarioMove */

export const MADDEN_BONUS_PRORATION_MAX_YEARS = 5;

function toFinite(n, fallback = 0) {
  const v = typeof n === 'number' ? n : Number(n);
  return Number.isFinite(v) ? v : fallback;
}

function clamp(n, min, max) {
  return Math.max(min, Math.min(max, n));
}

function prorationYears(years) {
  const y = Math.floor(toFinite(years, 1));
  return clamp(y, 1, MADDEN_BONUS_PRORATION_MAX_YEARS);
}

/**
 * Calculate current cap snapshot after applying a list of scenario moves.
 * Assumptions:
 * - team.capAvailable is baseline; deltas from moves adjust it in real-time
 * - For release/trade moves, `savings` reflects net current-year impact (in-game "Savings")
 * - `penalty` on moves is treated as current-year dead money (informational)
 * @param {Team} team
 * @param {Array<ScenarioMove>} moves
 * @returns {CapSnapshot}
 */
export function calcCapSummary(team, moves = []) {
  const capRoom = toFinite(team.capRoom);
  const baseSpent = toFinite(team.capSpent);
  const baseAvail = toFinite(team.capAvailable);

  let deltaSpent = 0; // positive = more spending; negative = savings
  let deadMoney = 0;

  for (const mv of moves || []) {
    if (!mv || typeof mv !== 'object') continue;
    switch (mv.type) {
      case 'release': {
        const savings = toFinite(mv.savings);
        deltaSpent -= savings; // savings reduces spending
        deadMoney += toFinite(mv.penalty);
        break;
      }
      case 'tradeQuick': {
        // Trade quick uses the same savings semantics as release (in-game Savings)
        const savings = toFinite(/** @type {any} */(mv).savings);
        if (Number.isFinite(savings)) deltaSpent -= savings;
        deadMoney += toFinite(mv.penalty);
        break;
      }
      case 'extend':
      case 'convert': {
        deltaSpent += toFinite(mv.capHitDelta);
        break;
      }
      case 'sign': {
        deltaSpent += toFinite(mv.year1CapHit);
        break;
      }
      default:
        break;
    }
  }

  const capSpent = baseSpent + deltaSpent;
  const capAvailable = baseAvail - deltaSpent;
  return {
    capRoom,
    capSpent,
    capAvailable,
    deadMoney,
    baselineAvailable: baseAvail,
    deltaAvailable: capAvailable - baseAvail,
  };
}

/**
 * Simulate a release using provided player fields.
 * - New Cap Space = team.capAvailable + capReleaseNetSavings (per spec)
 * - Dead cap penalty distribution: if years left >=2 → 40/60 split; else 100% current year
 * @param {Team} team
 * @param {Player} player
 */
export function simulateRelease(team, player) {
  const savings = toFinite(player.capReleaseNetSavings);
  const penaltyTotal = Math.max(0, toFinite(player.capReleasePenalty));
  const yearsLeft = Math.max(0, Math.floor(toFinite(player.contractYearsLeft, 0)));

  let penaltyCurrentYear = penaltyTotal;
  let penaltyNextYear = 0;
  if (penaltyTotal > 0 && yearsLeft >= 2) {
    penaltyCurrentYear = Math.round(penaltyTotal * 0.4);
    penaltyNextYear = penaltyTotal - penaltyCurrentYear; // remainder
  }

  const newCapSpace = toFinite(team.capAvailable) + savings; // savings already net of current-year penalty

  const move = {
    type: 'release',
    playerId: player.id,
    penalty: penaltyCurrentYear,
    savings,
    at: Date.now(),
  };

  return {
    savings,
    penaltyTotal,
    penaltyCurrentYear,
    penaltyNextYear,
    newCapSpace,
    move,
  };
}

/**
 * Quick trade simulation: remove player and apply dead money.
 * Mirrors release in terms of net savings and penalty handling.
 * @param {Team} team
 * @param {Player} player
 */
export function simulateTradeQuick(team, player) {
  const res = simulateRelease(team, player);
  // Tag move as tradeQuick
  res.move.type = 'tradeQuick';
  return res;
}

/**
 * Simulate a contract extension (simplified current-year math).
 * New Cap Hit = (New Total Salary + New Bonus) / New Contract Length
 * Cap Impact (delta) = New Cap Hit - Old Cap Hit
 * @param {Player} player
 * @param {{ years: number, totalSalary: number, signingBonus: number }} opts
 */
export function simulateExtension(player, opts) {
  const years = Math.max(1, Math.floor(toFinite(opts.years, 1)));
  const totalSalary = Math.max(0, toFinite(opts.totalSalary));
  const signingBonus = Math.max(0, toFinite(opts.signingBonus));

  const newCapHit = (totalSalary + signingBonus) / years;
  const capHitDelta = newCapHit - toFinite(player.capHit);

  const move = {
    type: 'extend',
    playerId: player.id,
    years,
    salary: totalSalary,
    bonus: signingBonus,
    capHitDelta,
    at: Date.now(),
  };

  return { newCapHit, capHitDelta, move };
}

/**
 * Simulate converting base salary to signing bonus.
 * Current-year reduction: convertAmount - (convertAmount / prorationYears)
 * Future-year increases: + (convertAmount / prorationYears) for remaining years
 * @param {Player} player
 * @param {{ convertAmount: number, yearsRemaining: number }} opts
 */
export function simulateConversion(player, opts) {
  const yearsRemaining = Math.max(1, Math.floor(toFinite(opts.yearsRemaining, 1)));
  const pYears = prorationYears(yearsRemaining);

  // Approximate current-year base salary as capHit minus bonus-per-year if available
  const bonusPerYear = (() => {
    const totalBonus = toFinite(player.contractBonus, 0);
    const len = Math.max(1, Math.floor(toFinite(player.contractLength, 1)));
    const prorateYears = Math.min(len, MADDEN_BONUS_PRORATION_MAX_YEARS);
    if (!totalBonus) return 0;
    return totalBonus / prorateYears;
  })();

  const currentCapHit = toFinite(player.capHit);
  const approxBaseSalary = Math.max(0, currentCapHit - bonusPerYear);

  let convertAmount = Math.max(0, toFinite(opts.convertAmount));
  // cannot convert more than base salary portion (approx)
  convertAmount = Math.min(convertAmount, approxBaseSalary);

  const perYearProration = convertAmount / pYears;
  const newCurrentYearCapHit = currentCapHit - convertAmount + perYearProration;
  const capHitDelta = newCurrentYearCapHit - currentCapHit; // typically negative

  /** Future impact view only (next years increase by perYearProration) */
  const futureYears = Array.from({ length: Math.max(0, pYears - 1) }, () => perYearProration);

  const move = {
    type: 'convert',
    playerId: player.id,
    convertAmount,
    yearsRemaining,
    capHitDelta,
    at: Date.now(),
  };

  return { newCurrentYearCapHit, perYearProration, capHitDelta, futureYears, move };
}

/**
 * Simulate signing a free agent.
 * Year 1 Cap Hit = salary + (bonus / min(years, 5))
 * Remaining Cap After = team.capAvailable - Year 1 Cap Hit
 * Also flags a lowball warning if offer < 90% of desired terms in any dimension.
 * @param {Team} team
 * @param {Player} player
 * @param {{ years: number, salary: number, bonus: number }} offer
 */
export function simulateSigning(team, player, offer) {
  const years = Math.max(1, Math.floor(toFinite(offer.years, 1)));
  const salary = Math.max(0, toFinite(offer.salary)); // annual salary
  const bonus = Math.max(0, toFinite(offer.bonus));

  const pYears = prorationYears(years);
  const year1CapHit = salary + (bonus / pYears);
  const remainingCapAfter = toFinite(team.capAvailable) - year1CapHit;

  const warnLowball = (() => {
    const ds = toFinite(player.desiredSalary);
    const db = toFinite(player.desiredBonus);
    const dl = Math.max(1, Math.floor(toFinite(player.desiredLength, 1)));
    const salaryOk = !Number.isFinite(ds) || ds === 0 ? true : salary >= 0.9 * ds;
    const bonusOk = !Number.isFinite(db) || db === 0 ? true : bonus >= 0.9 * db;
    const yearsOk = !Number.isFinite(dl) || dl === 0 ? true : years >= Math.floor(0.9 * dl);
    return !(salaryOk && bonusOk && yearsOk);
  })();

  const move = {
    type: 'sign',
    playerId: player.id,
    years,
    salary,
    bonus,
    year1CapHit,
    at: Date.now(),
  };

  return { year1CapHit, remainingCapAfter, warnLowball, canSign: remainingCapAfter >= 0, move };
}

export default {
  MADDEN_BONUS_PRORATION_MAX_YEARS,
  calcCapSummary,
  simulateRelease,
  simulateTradeQuick,
  simulateExtension,
  simulateConversion,
  simulateSigning,
  projectPlayerCapHits,
  deriveConversionIncrements,
  deriveDeadMoneySchedule,
  projectTeamCaps,
};

/**
 * Project per-year cap hits for a player over N future seasons.
 * Year 0 = current season and uses player.capHit (reflects conversions/extensions already applied).
 * Future years use simplified model: base = totalSalary/length for remaining contract years,
 * bonus proration = totalBonus / min(length, 5) for remaining proration years.
 * @param {Player} player
 * @param {number} years
 * @returns {number[]} length `years` array
 */
export function projectPlayerCapHits(player, years = 5) {
  const out = Array.from({ length: Math.max(0, Math.floor(toFinite(years, 0))) }, () => 0);
  if (out.length === 0) return out;

  const lenRaw = toFinite(player.contractLength);
  const len = Math.max(1, Math.floor(Number.isFinite(lenRaw) && lenRaw > 0 ? lenRaw : toFinite(player.contractYearsLeft, 1)));
  const yearsLeft = Math.max(0, Math.floor(toFinite(player.contractYearsLeft, 0)));
  const yearsElapsed = clamp(len - yearsLeft, 0, len);
  const prorateYears = Math.min(len, MADDEN_BONUS_PRORATION_MAX_YEARS);
  const bonusTotal = Math.max(0, toFinite(player.contractBonus, 0));
  const bonusPerYear = bonusTotal > 0 ? (bonusTotal / prorateYears) : 0;
  const remainingProrationNow = Math.max(0, prorateYears - yearsElapsed);
  const basePerYear = Math.max(0, toFinite(player.contractSalary, 0)) / len;

  for (let i = 0; i < out.length; i++) {
    if (i === 0) {
      // Use current capHit for Year 0 to reflect any live changes
      const cur = toFinite(player.capHit);
      out[i] = Number.isFinite(cur) ? cur : (basePerYear + (remainingProrationNow > 0 ? bonusPerYear : 0));
      continue;
    }
    const withinContract = i < yearsLeft;
    const hasProration = i < remainingProrationNow;
    const base = withinContract ? basePerYear : 0;
    const pr = hasProration ? bonusPerYear : 0;
    out[i] = base + pr;
  }
  return out;
}

/**
 * Build a map of conversion increments per player over future years (offsets 1..pYears-1).
 * @param {Array<ScenarioMove>} moves
 * @param {number} years
 */
export function deriveConversionIncrements(moves = [], years = 5) {
  /** @type {Record<string, number[]>} */
  const inc = {};
  const horizon = Math.max(0, Math.floor(toFinite(years, 0)));
  for (const mv of moves || []) {
    if (!mv || mv.type !== 'convert') continue;
    const pYears = prorationYears(/** @type {any} */(mv).yearsRemaining);
    const perYear = Math.max(0, toFinite(/** @type {any} */(mv).convertAmount)) / pYears;
    if (!inc[mv.playerId]) inc[mv.playerId] = Array.from({ length: horizon }, () => 0);
    // Apply to offsets 1..pYears-1 within horizon
    for (let o = 1; o < pYears && o < horizon; o++) {
      inc[mv.playerId][o] += perYear;
    }
  }
  return inc;
}

/**
 * Compute dead money schedule over N years from release/trade moves.
 * Year 0 includes current-year penalties; year 1 includes next-year penalties if split applies.
 * @param {Array<ScenarioMove>} moves
 * @param {Array<Player>} players
 * @param {number} years
 * @returns {number[]} length `years` array
 */
export function deriveDeadMoneySchedule(moves = [], players = [], years = 5) {
  const out = Array.from({ length: Math.max(0, Math.floor(toFinite(years, 0))) }, () => 0);
  if (out.length === 0) return out;
  /** @type {Record<string, Player>} */
  const byId = {};
  for (const p of players || []) byId[p.id] = p;
  for (const mv of moves || []) {
    if (!mv) continue;
    if (mv.type !== 'release' && mv.type !== 'tradeQuick') continue;
    const pl = byId[mv.playerId];
    if (!pl) continue;
    // Recompute penalties from player fields
    const sim = simulateRelease({ capAvailable: 0, capRoom: 0, capSpent: 0 }, pl);
    out[0] += Math.max(0, toFinite(sim.penaltyCurrentYear));
    if (out.length > 1) out[1] += Math.max(0, toFinite(sim.penaltyNextYear));
  }
  return out;
}

/**
 * Project team cap over N years using roster players and moves.
 * Returns an array of yearly snapshots: { yearOffset, capRoom, rosterCap, deadMoney, totalSpent, capSpace }.
 * @param {Team} team
 * @param {Array<Player>} players
 * @param {Array<ScenarioMove>} moves
 * @param {number} years
 */
export function projectTeamCaps(team, players = [], moves = [], years = 5) {
  const horizon = Math.max(0, Math.floor(toFinite(years, 0)));
  const capRoom = toFinite(team.capRoom);
  const active = (players || []).filter((p) => p && !p.isFreeAgent && p.team === team.abbrName);
  const dead = deriveDeadMoneySchedule(moves, players, horizon);
  const conv = deriveConversionIncrements(moves, horizon);

  // Sum roster caps per year
  const rosterTotals = Array.from({ length: horizon }, () => 0);
  for (const p of active) {
    const caps = projectPlayerCapHits(p, horizon);
    // Overlay conversion increments for this player if any
    const inc = conv[p.id];
    if (inc) {
      for (let i = 0; i < horizon; i++) {
        caps[i] += inc[i] || 0;
      }
    }
    for (let i = 0; i < horizon; i++) rosterTotals[i] += caps[i] || 0;
  }

  // Build result
  const out = [];
  for (let i = 0; i < horizon; i++) {
    const rosterCap = rosterTotals[i] || 0;
    const deadMoney = dead[i] || 0;
    const totalSpent = rosterCap + deadMoney;
    const capSpace = capRoom - totalSpent;
    out.push({ yearOffset: i, capRoom, rosterCap, deadMoney, totalSpent, capSpace });
  }
  return out;
}

// Marker for tooling/tests
export const __capMath_projections = true;
