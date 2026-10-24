const STORAGE_KEY = 'rosterCap.draftPicks';

function loadDraftPicksMap() {
  try {
    if (typeof window === 'undefined' || !window.localStorage) return {};
    const raw = window.localStorage.getItem(STORAGE_KEY);
    const parsed = raw ? JSON.parse(raw) : null;
    if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) return {};
    return parsed;
  } catch {
    return {};
  }
}

function saveDraftPicksMap(map) {
  try {
    if (typeof window === 'undefined' || !window.localStorage) return;
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(map || {}));
  } catch {
    // ignore
  }
}

function buildDefaultPicks() {
  return { 1: 1, 2: 1, 3: 1, 4: 1, 5: 1, 6: 1, 7: 1 };
}

/**
 * Get per-round draft pick counts for a team.
 * Defaults to 1 pick in rounds 1–7 when not configured.
 * @param {string} teamAbbr
 * @returns {{1:number,2:number,3:number,4:number,5:number,6:number,7:number}}
 */
export function getDraftPicksForTeam(teamAbbr) {
  const abbr = (teamAbbr || '').trim();
  if (!abbr) return buildDefaultPicks();

  const map = loadDraftPicksMap();
  const cur = map[abbr];
  const out = buildDefaultPicks();
  if (cur && typeof cur === 'object') {
    for (let r = 1; r <= 7; r++) {
      const v = Number(cur[r] || 0);
      out[r] = Number.isFinite(v) && v >= 0 ? Math.floor(v) : 0;
    }
  }
  return out;
}

/**
 * Set per-round draft pick counts for a team and persist alongside the Roster Cap Tool.
 * @param {string} teamAbbr
 * @param {{[round:number]:number}} picksPerRound
 */
export function setDraftPicksForTeam(teamAbbr, picksPerRound) {
  const abbr = (teamAbbr || '').trim();
  if (!abbr) return;

  const map = loadDraftPicksMap();
  const clean = { 1: 0, 2: 0, 3: 0, 4: 0, 5: 0, 6: 0, 7: 0 };
  for (let r = 1; r <= 7; r++) {
    const raw = picksPerRound && Object.prototype.hasOwnProperty.call(picksPerRound, r)
      ? picksPerRound[r]
      : undefined;
    const v = Number(raw || 0);
    clean[r] = Number.isFinite(v) && v >= 0 ? Math.floor(v) : 0;
  }
  map[abbr] = clean;
  saveDraftPicksMap(map);
}

export default { getDraftPicksForTeam, setDraftPicksForTeam };

