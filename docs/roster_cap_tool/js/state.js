// Minimal pub/sub app state for the tool
/** @typedef {import('./models.js').CapSnapshot} CapSnapshot */
import { calcCapSummary } from './capMath.js';

const listeners = new Set();

const state = {
  /** @type {string|null} */
  selectedTeam: null,
  /** @type {Array<any>} */
  teams: [],
  /** @type {Array<any>} */
  players: [],
  /** @type {Array<any>} */
  deadMoneyLedger: [],
  /** @type {Array<any>} */
  moves: [],
  /** @type {CapSnapshot|null} */
  snapshot: null,
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
    };
  }
  return calcCapSummary(team, state.moves);
}

export function initState({ teams, players }) {
  state.teams = teams;
  state.players = players;
  if (!state.selectedTeam && teams.length) {
    state.selectedTeam = teams[0].abbrName;
  }
  emit();
}
