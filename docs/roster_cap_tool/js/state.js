// Minimal pub/sub app state for the tool
/** @typedef {import('./models.js').CapSnapshot} CapSnapshot */
import { calcCapSummary, estimateRookieReserveForPicks } from './capMath.js';

const listeners = new Set();

const state = {
  /** @type {string|null} */
  selectedTeam: null,
  /** @type {Array<any>} */
  teams: [],
  /** @type {Array<any>} */
  players: [],
  /** Baseline players snapshot for scenario reset/compare */
  /** @type {Array<any>} */
  baselinePlayers: [],
  /** @type {Array<any>} */
  deadMoneyLedger: [],
  /** @type {Array<any>} */
  moves: [],
  /** @type {CapSnapshot|null} */
  snapshot: null,
  /** Persisted draft picks config per team: { [abbr]: {1:number,...,7:number} } */
  draftPicksByTeam: {},
};

export function subscribe(fn) {
  listeners.add(fn);
  return () => listeners.delete(fn);
}

function emit() {
  // Light debug hook for devtools
  try { console.debug && console.debug('[state] update', state); } catch {}
  for (const fn of listeners) fn(getState());
}

export function getState() {
  return state;
}

export function setState(partial) {
  Object.assign(state, partial);
  emit();
}

// Derived getters (simple for now; cap summary computed later)
export function getActiveRoster() {
  if (!state.selectedTeam) return [];
  return state.players.filter((p) => !p.isFreeAgent && p.team === state.selectedTeam);
}

export function getFreeAgents() {
  return state.players.filter((p) => p.isFreeAgent);
}

/** Compute the current cap snapshot for the selected team */
export function getCapSummary() {
  const team = state.teams.find((t) => t.abbrName === state.selectedTeam);
  if (!team) {
    return {
      capRoom: 0,
      capSpent: 0,
      capAvailable: 0,
      deadMoney: 0,
      baselineAvailable: 0,
      deltaAvailable: 0,
      rookieReserveEstimate: 0,
      capAfterRookies: 0,
    };
  }
  const snap = calcCapSummary(team, state.moves);
  const picks = getDraftPicksForSelectedTeam();
  const rookieReserveEstimate = estimateRookieReserveForPicks(picks);
  return {
    ...snap,
    rookieReserveEstimate,
    capAfterRookies: (snap.capAvailable || 0) - rookieReserveEstimate,
  };
}

export function initState({ teams, players }) {
  state.teams = teams;
  // Normalize player.team to team abbrName so filters work
  try {
    /** @type {Record<string,string>} */
    const teamKeyToAbbr = Object.create(null);
    for (const t of teams || []) {
      const keys = [t.abbrName, t.displayName, t.teamName].filter(Boolean);
      for (const k of keys) {
        teamKeyToAbbr[String(k).trim().toLowerCase()] = t.abbrName;
      }
    }
    state.players = (players || []).map((p) => {
      if (p && p.isFreeAgent) return p;
      const raw = (p && p.team) ? String(p.team).trim().toLowerCase() : '';
      const abbr = raw ? (teamKeyToAbbr[raw] || p.team) : p.team;
      return { ...p, team: abbr };
    });
  } catch {
    state.players = players;
  }
  // Store a deep baseline copy for scenario reset/compare
  // Important: use the NORMALIZED players (state.players) so Reset restores a valid roster
  try {
    state.baselinePlayers = JSON.parse(JSON.stringify(state.players));
  } catch {
    state.baselinePlayers = (state.players || []).map(p => ({ ...p }));
  }
  if (!state.selectedTeam && teams.length) {
    state.selectedTeam = teams[0].abbrName;
  }
  // Load draft picks from localStorage once
  try {
    const raw = localStorage.getItem('rosterCap.draftPicks');
    const parsed = raw ? JSON.parse(raw) : {};
    if (parsed && typeof parsed === 'object') state.draftPicksByTeam = parsed;
  } catch {}
  emit();
}

// ----- Scenario (What-if) persistence -----

const SCENARIOS_KEY = 'rosterCap.scenarios';

function loadAllScenarios() {
  try {
    const raw = localStorage.getItem(SCENARIOS_KEY);
    if (!raw) return [];
    const arr = JSON.parse(raw);
    return Array.isArray(arr) ? arr : [];
  } catch { return []; }
}

function saveAllScenarios(list) {
  try { localStorage.setItem(SCENARIOS_KEY, JSON.stringify(list)); } catch {}
}

/** Compute minimal roster diff from baselinePlayers to current players */
function computeRosterEdits() {
  /** @type {Record<string, any>} */
  const baseById = Object.create(null);
  for (const p of state.baselinePlayers || []) baseById[p.id] = p;
  const fields = ['isFreeAgent','team','capHit','contractSalary','contractBonus','contractLength','contractYearsLeft'];
  /** @type {Array<{id:string, patch:any}>} */
  const edits = [];
  for (const cur of state.players || []) {
    const base = baseById[cur.id];
    if (!base) continue;
    /** @type {any} */
    const patch = {};
    for (const k of fields) {
      const bv = base[k];
      const cv = cur[k];
      // Compare loosely, normalize number-ish
      const same = (Number.isFinite(bv) || Number.isFinite(cv)) ? (Number(bv) === Number(cv)) : (bv === cv);
      if (!same) patch[k] = cv;
    }
    if (Object.keys(patch).length) edits.push({ id: cur.id, patch });
  }
  return edits;
}

/** Apply roster edits to a deep-cloned baseline */
function applyRosterEdits(edits) {
  let out;
  try { out = JSON.parse(JSON.stringify(state.baselinePlayers || [])); } catch { out = (state.baselinePlayers || []).map(p => ({ ...p })); }
  /** @type {Record<string, any>} */
  const byId = Object.create(null);
  for (const p of out) byId[p.id] = p;
  for (const e of edits || []) {
    const p = byId[e.id];
    if (!p) continue;
    Object.assign(p, e.patch || {});
  }
  return out;
}

/** Create and persist a scenario; returns saved scenario id */
export function saveScenario(name = '') {
  const id = `scn_${Date.now()}_${Math.random().toString(36).slice(2,7)}`;
  const rosterEdits = computeRosterEdits();
  const scenario = {
    id,
    name: name?.trim() || 'Untitled Scenario',
    teamAbbr: state.selectedTeam || '',
    savedAt: Date.now(),
    moves: (state.moves || []).slice(),
    rosterEdits,
  };
  const all = loadAllScenarios();
  all.unshift(scenario);
  saveAllScenarios(all);
  return id;
}

/** List scenarios, optionally filtered by team abbr */
export function listScenarios(teamAbbr) {
  const all = loadAllScenarios();
  if (!teamAbbr) return all;
  return all.filter(s => s.teamAbbr === teamAbbr);
}

/** Delete a scenario by id */
export function deleteScenario(id) {
  const cur = loadAllScenarios();
  const next = cur.filter(s => s.id !== id);
  saveAllScenarios(next);
}

/** Load a scenario by id and apply to state */
export function loadScenario(id) {
  const cur = loadAllScenarios();
  const scn = cur.find(s => s.id === id);
  if (!scn) return false;
  const players = applyRosterEdits(scn.rosterEdits || []);
  const moves = (scn.moves || []).slice();
  const selectedTeam = scn.teamAbbr || state.selectedTeam;
  setState({ players, moves, selectedTeam, deadMoneyLedger: [] });
  return true;
}

/** Reset to baseline players and clear moves */
export function resetScenario() {
  let players;
  try { players = JSON.parse(JSON.stringify(state.baselinePlayers || [])); } catch { players = (state.baselinePlayers || []).map(p => ({ ...p })); }
  setState({ players, moves: [], deadMoneyLedger: [] });
}

/** Return computed roster edits vs baseline (for UI stats) */
export function getScenarioEdits() {
  return computeRosterEdits();
}

// ----- Draft Picks (Rookie Reserve) -----

/** Return per-round pick counts for selected team. */
export function getDraftPicksForSelectedTeam() {
  const abbr = state.selectedTeam || '';
  const cur = state.draftPicksByTeam?.[abbr];
  // Default 0 picks in all rounds
  const out = { 1:0, 2:0, 3:0, 4:0, 5:0, 6:0, 7:0 };
  if (cur && typeof cur === 'object') {
    for (let r = 1; r <= 7; r++) out[r] = Number(cur[r] || 0) || 0;
  }
  return out;
}

/** Update per-round pick counts for selected team and persist. */
export function setDraftPicksForSelectedTeam(picksPerRound) {
  const abbr = state.selectedTeam || '';
  const next = { ...(state.draftPicksByTeam || {}) };
  const clean = { 1:0,2:0,3:0,4:0,5:0,6:0,7:0 };
  for (let r = 1; r <= 7; r++) {
    const v = picksPerRound?.[r] ?? 0;
    clean[r] = Math.max(0, Math.floor(Number(v) || 0));
  }
  next[abbr] = clean;
  state.draftPicksByTeam = next;
  try { localStorage.setItem('rosterCap.draftPicks', JSON.stringify(next)); } catch {}
  emit();
}

/** Compute rookie reserve estimate for selected team. */
export function getRookieReserveEstimate() {
  const picks = getDraftPicksForSelectedTeam();
  return estimateRookieReserveForPicks(picks);
}
