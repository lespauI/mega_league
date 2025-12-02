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

// Madden base-salary distribution weights by contract length (percentages that sum ~100%)
// Source: spec/Salary Cap Works in Madden.md
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
    // Fallback to even distribution
    const per = len > 0 ? (tot / len) : 0;
    return Array.from({ length: len }, () => per);
  }
  const sum = w.reduce((a, b) => a + b, 0) || 1;
  // Normalize to exact total avoiding floating drift by fixing last year as remainder
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
      case 'tradeIn': {
        // Incoming trade adds the acquiring team's Year 1 salary-only cap hit
        deltaSpent += toFinite(/** @type {any} */(mv).year1CapHit);
        break;
      }
      default:
        break;
    }
  }

  const capSpent = baseSpent + deltaSpent;
  // Cap Space should be derived from Current Cap − Cap Spent to avoid zero/default errors
  const capAvailable = capRoom - capSpent;
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
 * - Dead cap penalty distribution: if years left >=2 → 60/40 split (current/next); else 100% current year
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
    // In-game behavior observed: larger portion hits immediately.
    // Use 60% in current year, 40% next year for multi-year contracts.
    penaltyNextYear = Math.round(penaltyTotal * 0.4);
    penaltyCurrentYear = penaltyTotal - penaltyNextYear; // remainder (≈60%)
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
 * Simulate trading in a player from another team.
 * Acquiring team only assumes the salary portion in Year 1; the original team's
 * remaining signing bonus stays as their dead money (not counted here).
 * Year 1 Acquiring Cap Hit ≈ player.capHit - (contractBonus / min(length, 5))
 * Remaining Cap After = team.capAvailable - Year1AcquiringCapHit
 * @param {Team} team
 * @param {Player} player
 */
export function simulateTradeIn(team, player) {
  // Determine the acquiring team's Year 1 cap hit as base salary only
  // Prefer contract base schedule for the current contract year; fall back to
  // (capHit - bonusPerYear) if salary data is missing.
  const totalBonus = toFinite(player.contractBonus, 0);
  const lenRaw = toFinite(player.contractLength, 0);
  const yearsLeftRaw = toFinite(player.contractYearsLeft, 0);
  const len = Math.max(1, Math.floor(Number.isFinite(lenRaw) && lenRaw > 0 ? lenRaw : toFinite(player.contractYearsLeft, 1)));
  const yearsLeft = Math.max(0, Math.floor(Number.isFinite(yearsLeftRaw) && yearsLeftRaw >= 0 ? yearsLeftRaw : 0));
  const yearsElapsed = clamp(len - yearsLeft, 0, Math.max(0, len - 1));
  const prorateYears = Math.min(len, MADDEN_BONUS_PRORATION_MAX_YEARS);
  const bonusPerYear = totalBonus > 0 ? (totalBonus / prorateYears) : 0;

  // Try to compute current-year base salary from total contract salary using Madden weights
  const contractSalary = toFinite(player.contractSalary, 0);
  let acquiringYear1 = 0;
  if (contractSalary > 0 && len > 0) {
    const schedule = buildBaseSchedule(contractSalary, len);
    const idx = clamp(yearsElapsed, 0, schedule.length - 1);
    acquiringYear1 = Math.max(0, toFinite(schedule[idx], 0));
  } else {
    // Fallback: approximate base as capHit minus bonus proration
    const currentCapHit = toFinite(player.capHit);
    acquiringYear1 = Math.max(0, currentCapHit - bonusPerYear);
  }
  const remainingCapAfter = toFinite(team.capAvailable) - acquiringYear1;

  const move = {
    type: 'tradeIn',
    playerId: player.id,
    year1CapHit: acquiringYear1,
    at: Date.now(),
  };

  return { year1CapHit: acquiringYear1, remainingCapAfter, canTradeIn: remainingCapAfter >= 0, move };
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
  simulateTradeIn,
  simulateExtension,
  simulateConversion,
  simulateSigning,
  projectPlayerCapHits,
  estimateRookieYear1ForSlot,
  estimateRookieReserveForPicks,
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

  // Derive bonus proration per year. Prefer explicit contractBonus; otherwise
  // approximate using capReleasePenalty as the remaining unamortized bonus.
  let bonusTotal = Math.max(0, toFinite(player.contractBonus, 0));
  let remainingProrationNow = Math.max(0, prorateYears - yearsElapsed);
  if (!bonusTotal) {
    const pen = Math.max(0, toFinite(player.capReleasePenalty, 0));
    if (pen > 0 && remainingProrationNow > 0) {
      // Treat penalty as remaining bonus today; approximate total bonus by
      // spreading it evenly across remaining proration windows.
      bonusTotal = pen * (prorateYears / remainingProrationNow);
    }
  }
  const bonusPerYear = bonusTotal > 0 ? (bonusTotal / prorateYears) : 0;

  // Base salary schedule per contract-year using Madden distribution weights when possible.
  const contractSalary = toFinite(player.contractSalary, 0);
  const baseSchedule = (contractSalary > 0)
    ? buildBaseSchedule(contractSalary, len)
    : null;
  // Fallback per-year base when schedule unknown: infer from current capHit minus proration
  const inferredBasePerYear = (() => {
    const cur = toFinite(player.capHit);
    if (Number.isFinite(cur)) return Math.max(0, cur - (remainingProrationNow > 0 ? bonusPerYear : 0));
    return 0;
  })();

  for (let i = 0; i < out.length; i++) {
    if (i === 0) {
      // Use current capHit for Year 0 to reflect live state
      const cur = toFinite(player.capHit);
      out[i] = Number.isFinite(cur) ? cur : ((baseSchedule ? baseSchedule[yearsElapsed] || 0 : inferredBasePerYear) + (remainingProrationNow > 0 ? bonusPerYear : 0));
      continue;
    }
    const withinContract = i < yearsLeft;
    const hasProration = i < remainingProrationNow;
    let base = 0;
    if (withinContract) {
      const schedIdx = yearsElapsed + i;
      base = baseSchedule ? (baseSchedule[schedIdx] || 0) : inferredBasePerYear;
    }
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
export function projectTeamCaps(team, players = [], moves = [], years = 5, opts = {}) {
  const horizon = Math.max(0, Math.floor(toFinite(years, 0)));
  const capRoom = toFinite(team.capRoom);
  const baseSpent = toFinite(team.capSpent);
  const baseAvail = toFinite(team.capAvailable);
  // Exclude players who are not on the active roster or who have been
  // removed via release/trade moves (even if caller hasn't mutated the
  // players array yet). This ensures out-year projections fully recompute
  // after roster moves.
  const removed = new Set(
    (moves || [])
      .filter((mv) => mv && (mv.type === 'release' || mv.type === 'tradeQuick'))
      .map((mv) => mv.playerId)
  );
  const active = (players || []).filter((p) => p && !p.isFreeAgent && p.team === team.abbrName && !removed.has(p.id));
  const dead = deriveDeadMoneySchedule(moves, players, horizon);
  const conv = deriveConversionIncrements(moves, horizon);
  const growthRate = (opts && Number.isFinite(Number(opts.capGrowthRate))) ? Number(opts.capGrowthRate) : 0.09;

  // Compute deltaSpent from moves (same semantics as calcCapSummary)
  let deltaSpent = 0; // positive increases spending, negative = savings
  for (const mv of moves || []) {
    if (!mv || typeof mv !== 'object') continue;
    switch (mv.type) {
      case 'release':
      case 'tradeQuick':
        deltaSpent -= toFinite(/** @type {any} */(mv).savings);
        break;
      case 'extend':
      case 'convert':
        deltaSpent += toFinite(/** @type {any} */(mv).capHitDelta);
        break;
      case 'sign':
        deltaSpent += toFinite(/** @type {any} */(mv).year1CapHit);
        break;
      case 'tradeIn':
        deltaSpent += toFinite(/** @type {any} */(mv).year1CapHit);
        break;
      default:
        break;
    }
  }

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
  let y0CapSpace = 0;
  for (let i = 0; i < horizon; i++) {
    let rosterCap = rosterTotals[i] || 0;
    let deadMoney = dead[i] || 0;
    let totalSpent = rosterCap + deadMoney;
    // Cap room per year: anchor Y0 to team, hardcode next 3 seasons per game behavior,
    // then fall back to growth for farther horizons.
    let capRoomYear;
    if (i === 0) {
      capRoomYear = capRoom;
    } else if (i === 1) {
      capRoomYear = 324_000_000;
    } else if (i === 2) {
      capRoomYear = 334_000_000;
    } else if (i === 3) {
      capRoomYear = 344_000_000;
    } else {
      capRoomYear = capRoom * Math.pow(1 + growthRate, i);
    }
    let capSpace = capRoomYear - totalSpent;

    if (i === 0) {
      // Anchor current-year snapshot to in-game team totals to avoid mismatches
      // and negative cap due to dataset differences (e.g., practice squad/IR counts).
      const anchoredTotal = baseSpent + deltaSpent;
      const anchoredSpace = baseAvail - deltaSpent;
      // Prefer anchored totals for Year 0
      totalSpent = anchoredTotal;
      capSpace = anchoredSpace;
      // Derive a rosterCap that is consistent and non-negative.
      // Note: deadMoney here only includes new scenario moves; baseline dead money is folded into baseSpent.
      rosterCap = Math.max(0, totalSpent - deadMoney);
      // If caller provided baseline dead money for current year (manual input),
      // fold it into Year 0 totals so rollover availability reflects it.
      const dmBaseY0 = (opts && Array.isArray(opts.baselineDeadMoneyByYear)) ? Number(opts.baselineDeadMoneyByYear[0] || 0) : 0;
      if (Number.isFinite(dmBaseY0) && dmBaseY0 > 0) {
        totalSpent += dmBaseY0;
        capSpace = capRoomYear - totalSpent;
        deadMoney += dmBaseY0;
      }
      y0CapSpace = capSpace;
    }

    // Apply Rookie Reserve (future years only). Caller can provide a schedule
    // of rookie reserve dollars per year offset via opts.rookieReserveByYear.
    // We only apply for i > 0 to avoid altering the anchored current year.
    const rr = (opts && Array.isArray(opts.rookieReserveByYear)) ? Number(opts.rookieReserveByYear[i] || 0) : 0;
    if (i > 0 && Number.isFinite(rr) && rr > 0) {
      totalSpent += rr;
      capSpace = capRoomYear - totalSpent;
    }

    // Apply optional baseline dead money for out-years (manual inputs / existing voids)
    // Provided by caller via opts.baselineDeadMoneyByYear[] where index = yearOffset.
    // Note: Year 0 baseline is handled above inside the i===0 anchor block.
    const dmBase = (opts && Array.isArray(opts.baselineDeadMoneyByYear)) ? Number(opts.baselineDeadMoneyByYear[i] || 0) : 0;
    if (i > 0 && Number.isFinite(dmBase) && dmBase > 0) {
      totalSpent += dmBase;
      capSpace = capRoomYear - totalSpent;
      deadMoney += dmBase;
    }

    // Apply any extra planned spending (e.g., re-sign reserve) for out-years.
    const extra = (opts && Array.isArray(opts.extraSpendingByYear)) ? Number(opts.extraSpendingByYear[i] || 0) : 0;
    if (i > 0 && Number.isFinite(extra) && extra > 0) {
      totalSpent += extra;
      capSpace = capRoomYear - totalSpent;
    }

    // Apply rollover from current year into next year (i === 1) up to a cap.
    if (i === 1) {
      const requested = Math.max(0, toFinite(/** @type {any} */(opts).rolloverToNext, 0));
      const cap = Math.max(0, toFinite(/** @type {any} */(opts).rolloverMax, 35_000_000));
      const availableY0 = Math.max(0, toFinite(y0CapSpace, 0));
      const applied = Math.min(requested, cap, availableY0);
      if (applied > 0) {
        capSpace += applied;
      }
    }

    // (Removed) Explicit Year+1 cap override handling

    out.push({ yearOffset: i, capRoom: capRoomYear, rosterCap, deadMoney, totalSpent, capSpace });
  }
  return out;
}

// Marker for tooling/tests
export const __capMath_projections = true;

/**
 * Estimate Year 1 cap hit for a rookie at a given draft slot.
 * Approximates Madden rookie scale using round-based ranges and linear interpolation.
 * - Round 1: $9.0M (1.01) → $2.25M (1.32)
 * - Round 2: $1.9M (2.01) → $1.2M (2.32)
 * - Round 3: $1.2M → $0.95M
 * - Round 4: $0.95M → $0.85M
 * - Round 5: $0.85M → $0.775M
 * - Round 6: $0.775M → $0.70M
 * - Round 7: $0.70M → $0.65M
 * @param {number} round 1-7
 * @param {number} pickInRound 1-32 (approx; comp picks treated as end-of-round)
 */
export function estimateRookieYear1ForSlot(round, pickInRound = 16) {
  const r = Math.max(1, Math.min(7, Math.floor(toFinite(round, 1))));
  const pr = Math.max(1, Math.min(32, Math.floor(toFinite(pickInRound, 16))));
  // Define [start, end] ranges per round (USD)
  /** @type {Record<number, [number, number]>} */
  const ranges = {
    1: [9_000_000, 2_250_000],
    2: [1_900_000, 1_200_000],
    3: [1_200_000, 950_000],
    4: [950_000, 850_000],
    5: [850_000, 775_000],
    6: [775_000, 700_000],
    7: [700_000, 650_000],
  };
  const [start, end] = ranges[r] || [800_000, 700_000];
  const t = (pr - 1) / 31; // 0..1
  return start + (end - start) * t;
}

/**
 * Estimate Rookie Reserve for a set of picks.
 * @param {{ [round: number]: number }} roundCounts Map round→count
 * @returns {number}
 */
export function estimateRookieReserveForPicks(roundCounts = {}) {
  let total = 0;
  for (let r = 1; r <= 7; r++) {
    const count = Math.max(0, Math.floor(toFinite(roundCounts[r] || 0, 0)));
    if (!count) continue;
    // Assume mid-round slot for estimate
    const per = estimateRookieYear1ForSlot(r, 16);
    total += per * count;
  }
  return total;
}
