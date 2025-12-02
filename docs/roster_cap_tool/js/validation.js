/** Coerce various truthy/falsey values to boolean */
export function toBool(v) {
  if (typeof v === 'boolean') return v;
  if (typeof v === 'number') return v !== 0;
  if (typeof v === 'string') {
    const s = v.trim().toLowerCase();
    return s === '1' || s === 'true' || s === 'yes' || s === 'y';
  }
  return false;
}

/** Coerce to number, return NaN if not parseable */
export function toNum(v) {
  if (typeof v === 'number') return v;
  if (typeof v === 'string') {
    const cleaned = v.replace(/[$, ]/g, '');
    const n = Number(cleaned);
    return Number.isFinite(n) ? n : NaN;
  }
  return NaN;
}

/** Ensure a primitive string */
export function toStr(v) {
  return v == null ? '' : String(v);
}

/** Validate and normalize a Team CSV row */
export function normalizeTeamRow(row) {
  const abbrName = toStr(row.abbrName || row.team || row.abbr || '');
  const displayName = toStr(row.displayName || row.name || '');
  const capRoom = toNum(row.capRoom);
  const capSpent = toNum(row.capSpent);
  const capAvailable = toNum(row.capAvailable);
  const seasonIndex = toNum(row.seasonIndex);
  const weekIndex = toNum(row.weekIndex);

  const errors = [];
  if (!abbrName) errors.push('abbrName missing');
  if (!displayName) errors.push('displayName missing');
  if (!Number.isFinite(capRoom)) errors.push('capRoom invalid');
  if (!Number.isFinite(capSpent)) errors.push('capSpent invalid');
  if (!Number.isFinite(capAvailable)) errors.push('capAvailable invalid');
  if (!Number.isFinite(seasonIndex)) errors.push('seasonIndex invalid');
  if (!Number.isFinite(weekIndex)) errors.push('weekIndex invalid');

  return {
    ok: errors.length === 0,
    team: { abbrName, displayName, capRoom, capSpent, capAvailable, seasonIndex, weekIndex },
    errors,
  };
}

/** Validate and normalize a Player CSV row */
export function normalizePlayerRow(row) {
  const id = toStr(row.id || row.gsisId || row.playerId || `${toStr(row.firstName)}-${toStr(row.lastName)}-${toStr(row.team)}`);
  const firstName = toStr(row.firstName || row.fname || '');
  const lastName = toStr(row.lastName || row.lname || '');
  const position = toStr(row.position || row.pos || '');
  const age = Number.isFinite(toNum(row.age)) ? toNum(row.age) : undefined;
  const height = toStr(row.height || '');
  const weight = Number.isFinite(toNum(row.weight)) ? toNum(row.weight) : undefined;
  const team = toStr(row.team || '');
  const isFreeAgent = toBool(row.isFreeAgent);
  const yearsPro = Number.isFinite(toNum(row.yearsPro)) ? toNum(row.yearsPro) : undefined;

  const capHit = toNum(row.capHit);
  const capReleaseNetSavings = Number.isFinite(toNum(row.capReleaseNetSavings)) ? toNum(row.capReleaseNetSavings) : undefined;
  const capReleasePenalty = Number.isFinite(toNum(row.capReleasePenalty)) ? toNum(row.capReleasePenalty) : undefined;

  const contractSalary = Number.isFinite(toNum(row.contractSalary)) ? toNum(row.contractSalary) : undefined;
  const contractBonus = Number.isFinite(toNum(row.contractBonus)) ? toNum(row.contractBonus) : undefined;
  const contractLength = Number.isFinite(toNum(row.contractLength)) ? toNum(row.contractLength) : undefined;
  const contractYearsLeft = Number.isFinite(toNum(row.contractYearsLeft)) ? toNum(row.contractYearsLeft) : undefined;

  const desiredSalary = Number.isFinite(toNum(row.desiredSalary)) ? toNum(row.desiredSalary) : undefined;
  const desiredBonus = Number.isFinite(toNum(row.desiredBonus)) ? toNum(row.desiredBonus) : undefined;
  const desiredLength = Number.isFinite(toNum(row.desiredLength)) ? toNum(row.desiredLength) : undefined;
  const reSignStatus = Number.isFinite(toNum(row.reSignStatus)) ? toNum(row.reSignStatus) : undefined;

  const errors = [];
  if (!firstName) errors.push('firstName missing');
  if (!lastName) errors.push('lastName missing');
  if (!position) errors.push('position missing');
  if (!Number.isFinite(capHit)) errors.push('capHit invalid');
  if (!isFreeAgent && !team) errors.push('team missing for non-FA');

  return {
    ok: errors.length === 0,
    player: {
      id, firstName, lastName, position, age, height, weight, team,
      isFreeAgent, yearsPro, capHit, capReleaseNetSavings, capReleasePenalty,
      contractSalary, contractBonus, contractLength, contractYearsLeft,
      desiredSalary, desiredBonus, desiredLength, reSignStatus,
    },
    errors,
  };
}

