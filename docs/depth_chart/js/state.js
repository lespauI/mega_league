import { DEPTH_CHART_SLOTS, getPlayersForSlot } from './slots.js';

/**
 * @typedef {'existing' | 'faPlayer' | 'draftR1' | 'draftR2' | 'trade' | 'faPlaceholder'} AcquisitionType
 *
 * @typedef {Object} DepthSlotAssignment
 * @property {string} slotId
 * @property {number} depthIndex
 * @property {AcquisitionType} acquisition
 * @property {string=} playerId
 * @property {string=} placeholder
 *
 * @typedef {Object} DepthPlan
 * @property {string} teamAbbr
 * @property {Record<string, Array<DepthSlotAssignment>>} slots
 */

const STORAGE_PREFIX = 'depthChartPlanner.v1';
const STORAGE_KEYS = {
  rosterEdits: `${STORAGE_PREFIX}.rosterEdits`,
  depthPlans: `${STORAGE_PREFIX}.depthPlans`,
};

const listeners = new Set();

/**
 * Global depth-chart state container.
 */
const state = {
  selectedTeam: null,
  teams: [],
  players: [],
  // Deep snapshot of the initial, normalized roster for all teams.
  baselinePlayers: [],
  // Quick lookup map of current players by id.
  playersById: {},
  // Deltas from baseline per player id: { [id]: { team?: string; isFreeAgent?: boolean } }.
  rosterEdits: {},
  // Per-team depth plans keyed by team abbreviation.
  depthPlansByTeam: {},
};

export function subscribe(fn) {
  listeners.add(fn);
  return () => listeners.delete(fn);
}

function emit() {
  for (const fn of listeners) fn(getState());
}

export function getState() {
  return state;
}

export function setState(partial) {
  if (!partial || typeof partial !== 'object') {
    Object.assign(state, partial);
    emit();
    return;
  }

  let next = partial;
  // If callers pass a fresh players array, normalize team keys and
  // keep playersById in sync. baselinePlayers is intentionally
  // only set in initState (it represents the CSV baseline).
  if (Array.isArray(partial.players)) {
    const teams = partial.teams || state.teams;
    const normalized = normalizePlayersTeams(partial.players, teams);
    next = {
      ...partial,
      players: normalized,
      playersById: buildPlayersById(normalized),
    };
  }

  Object.assign(state, next);

  if (Object.prototype.hasOwnProperty.call(next, 'selectedTeam') && next.selectedTeam) {
    ensureDepthPlanForTeam(next.selectedTeam);
  }

  emit();
}

export function initState({ teams, players }) {
  state.teams = teams || [];

  const normalizedPlayers = normalizePlayersTeams(players || [], state.teams || []);

  // Store a deep baseline copy for future reset/compare and depth planning.
  try {
    state.baselinePlayers = JSON.parse(JSON.stringify(normalizedPlayers));
  } catch {
    state.baselinePlayers = (normalizedPlayers || []).map((p) => ({ ...p }));
  }

  // Load persisted roster edits and depth plans.
  state.rosterEdits = loadPersistedRosterEdits();
  state.depthPlansByTeam = loadPersistedDepthPlans();

  const appliedPlayers = applyRosterEdits(state.baselinePlayers, state.rosterEdits);

  const defaultTeam =
    state.selectedTeam ||
    (state.teams && state.teams.length ? state.teams[0].abbrName : null);

  setState({
    selectedTeam: defaultTeam,
    players: appliedPlayers,
  });

  if (defaultTeam) {
    ensureDepthPlanForTeam(defaultTeam);
  }
}

/**
 * Returns all non-FA players for the given team
 * (or the currently selected team if omitted).
 */
export function getPlayersForTeam(teamAbbr) {
  const team = teamAbbr || state.selectedTeam;
  if (!team) return [];
  return (state.players || []).filter((p) => !p.isFreeAgent && p.team === team);
}

// Backwards-compat alias used by earlier depth-chart code.
export function getTeamPlayers() {
  return getPlayersForTeam();
}

export function getFreeAgents() {
  return (state.players || []).filter((p) => p.isFreeAgent);
}

export function getDepthPlanForTeam(teamAbbr) {
  const team = teamAbbr || state.selectedTeam;
  if (!team) return null;
  ensureDepthPlanForTeam(team);
  return state.depthPlansByTeam[team] || null;
}

export function getDepthPlanForSelectedTeam() {
  return getDepthPlanForTeam(state.selectedTeam);
}

export function setRosterEdit(playerId, patch) {
  if (!playerId || !patch || typeof patch !== 'object') return;

  const id = String(playerId);
  const current = state.rosterEdits[id] || {};
  const merged = { ...current, ...patch };

  const nextEdits = { ...state.rosterEdits };
  if (Object.keys(merged).length > 0) nextEdits[id] = merged;
  else delete nextEdits[id];

  state.rosterEdits = nextEdits;
  saveRosterEdits(nextEdits);

  const players = applyRosterEdits(state.baselinePlayers, nextEdits);
  setState({ players });
}

export function resetTeamRosterAndPlan(teamAbbr) {
  const team = teamAbbr || state.selectedTeam;
  if (!team) return;

  const baselineById = buildPlayersById(state.baselinePlayers);
  const nextEdits = {};
  for (const id of Object.keys(state.rosterEdits || {})) {
    const edit = state.rosterEdits[id];
    const baseline = baselineById[id];
    if (!baseline) continue;

    const baselineTeam = baseline.team || '';
    const editedTeam =
      Object.prototype.hasOwnProperty.call(edit, 'team') && edit.team !== undefined
        ? edit.team
        : baselineTeam;

    const affectsTeam = baselineTeam === team || editedTeam === team;
    if (!affectsTeam) {
      nextEdits[id] = edit;
    }
  }

  state.rosterEdits = nextEdits;
  saveRosterEdits(nextEdits);

  const players = applyRosterEdits(state.baselinePlayers, nextEdits);
  const teamPlayers = players.filter((p) => !p.isFreeAgent && p.team === team);

  if (!state.depthPlansByTeam) state.depthPlansByTeam = {};
  state.depthPlansByTeam[team] = buildInitialDepthPlanForTeam(team, teamPlayers);
  persistDepthPlans();

  setState({ players });
}

export function buildInitialDepthPlanForTeam(teamAbbr, playersForTeam) {
  const team = teamAbbr;
  const plan = {
    teamAbbr: team,
    slots: {},
  };

  const rosterPlayers = playersForTeam || getPlayersForTeam(team);

  for (const slot of DEPTH_CHART_SLOTS) {
    const eligible = getPlayersForSlot(slot, rosterPlayers);
    if (!eligible.length) continue;

    const maxDepth = Math.min(slot.max || 4, 4);
    const assignments = [];
    for (let i = 0; i < Math.min(maxDepth, eligible.length); i++) {
      const player = eligible[i];
      const id = String(player.id || '').trim();
      if (!id) continue;
      assignments.push({
        slotId: slot.id,
        depthIndex: i + 1,
        acquisition: 'existing',
        playerId: id,
      });
    }

    if (assignments.length) {
      plan.slots[slot.id] = assignments;
    }
  }

  return plan;
}

export function ensureDepthPlanForTeam(teamAbbr) {
  const team = teamAbbr || state.selectedTeam;
  if (!team) return null;

  if (!state.depthPlansByTeam) state.depthPlansByTeam = {};
  let plan = state.depthPlansByTeam[team];

  if (!plan) {
    const teamPlayers = getPlayersForTeam(team);
    plan = buildInitialDepthPlanForTeam(team, teamPlayers);
    state.depthPlansByTeam[team] = plan;
    persistDepthPlans();
  }

  return plan;
}

export function updateDepthSlot({ teamAbbr, slotId, depthIndex, assignment }) {
  const team = teamAbbr || state.selectedTeam;
  if (!team || !slotId || !depthIndex || !assignment) return;

  const plan = ensureDepthPlanForTeam(team);
  if (!plan) return;

  const idx = Math.max(0, depthIndex - 1);
  const currentSlot = Array.isArray(plan.slots[slotId]) ? [...plan.slots[slotId]] : [];

  while (currentSlot.length <= idx) {
    currentSlot.push(null);
  }

  const normalized = {
    slotId,
    depthIndex,
    acquisition: assignment.acquisition,
    playerId: assignment.playerId || undefined,
    placeholder: assignment.placeholder || undefined,
  };

  currentSlot[idx] = normalized;
  plan.slots[slotId] = currentSlot;

  persistDepthPlans();
  emit();
}

export function clearDepthSlot({ teamAbbr, slotId, depthIndex }) {
  const team = teamAbbr || state.selectedTeam;
  if (!team || !slotId || !depthIndex) return;

  const plan = ensureDepthPlanForTeam(team);
  if (!plan || !plan.slots[slotId]) return;

  const idx = Math.max(0, depthIndex - 1);
  const currentSlot = [...plan.slots[slotId]];
  if (idx >= currentSlot.length) return;

  currentSlot[idx] = null;

  // Trim trailing nulls to keep arrays compact.
  while (currentSlot.length && currentSlot[currentSlot.length - 1] == null) {
    currentSlot.pop();
  }

  if (currentSlot.length) plan.slots[slotId] = currentSlot;
  else delete plan.slots[slotId];

  persistDepthPlans();
  emit();
}

/* Internal helpers */

function normalizePlayersTeams(players, teams) {
  const teamKeyToAbbr = Object.create(null);
  for (const t of teams || []) {
    const keys = [t.abbrName, t.displayName].filter(Boolean);
    for (const k of keys) {
      teamKeyToAbbr[String(k).trim().toLowerCase()] = t.abbrName;
    }
  }
  return (players || []).map((p) => {
    if (!p || p.isFreeAgent) return p;
    const raw = (p.team ? String(p.team) : '').trim().toLowerCase();
    const abbr = raw ? teamKeyToAbbr[raw] || p.team : p.team;
    return { ...p, team: abbr };
  });
}

function buildPlayersById(players) {
  const byId = Object.create(null);
  for (const p of players || []) {
    if (!p) continue;
    const id = String(p.id || '').trim();
    if (!id) continue;
    byId[id] = p;
  }
  return byId;
}

function applyRosterEdits(baselinePlayers, rosterEdits) {
  const edits = rosterEdits || {};
  const result = [];
  for (const base of baselinePlayers || []) {
    if (!base) continue;
    const id = String(base.id || '').trim();
    const patch = id && edits[id] ? edits[id] : null;
    if (!patch) {
      result.push({ ...base });
      continue;
    }
    const next = { ...base };
    if (Object.prototype.hasOwnProperty.call(patch, 'team')) {
      next.team = patch.team;
    }
    if (Object.prototype.hasOwnProperty.call(patch, 'isFreeAgent')) {
      next.isFreeAgent = !!patch.isFreeAgent;
    }
    result.push(next);
  }
  return result;
}

function getStorage() {
  try {
    if (typeof window !== 'undefined' && window.localStorage) {
      return window.localStorage;
    }
  } catch {
    // Ignore access errors (e.g., in non-browser environments).
  }
  return null;
}

function safeParseJSON(text, fallback) {
  if (!text) return fallback;
  try {
    const value = JSON.parse(text);
    if (value && typeof value === 'object') {
      return value;
    }
  } catch {
    // ignore
  }
  return fallback;
}

function loadPersistedRosterEdits() {
  const storage = getStorage();
  if (!storage) return {};
  const raw = storage.getItem(STORAGE_KEYS.rosterEdits);
  return safeParseJSON(raw, {});
}

function saveRosterEdits(edits) {
  const storage = getStorage();
  if (!storage) return;
  try {
    storage.setItem(STORAGE_KEYS.rosterEdits, JSON.stringify(edits || {}));
  } catch {
    // ignore
  }
}

function loadPersistedDepthPlans() {
  const storage = getStorage();
  if (!storage) return {};
  const raw = storage.getItem(STORAGE_KEYS.depthPlans);
  return safeParseJSON(raw, {});
}

function saveDepthPlans(plans) {
  const storage = getStorage();
  if (!storage) return;
  try {
    storage.setItem(STORAGE_KEYS.depthPlans, JSON.stringify(plans || {}));
  } catch {
    // ignore
  }
}

function persistDepthPlans() {
  saveDepthPlans(state.depthPlansByTeam || {});
}

