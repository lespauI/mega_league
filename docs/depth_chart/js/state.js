import { DEPTH_CHART_SLOTS, getPlayersForSlot } from './slots.js';

/**
 * @typedef {'existing' | 'faPlayer' | 'draftR1' | 'draftR2' | 'draftR3' | 'draftR4' | 'draftR5' | 'draftR6' | 'draftR7' | 'trade' | 'faPlaceholder'} AcquisitionType
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
  selectedTeam: `${STORAGE_PREFIX}.selectedTeam`,
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
  if (!partial || typeof partial !== 'object') return;

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
    saveSelectedTeam(next.selectedTeam);
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
  state.depthPlansByTeam = loadPersistedDepthPlans(state.teams);

  const appliedPlayers = applyRosterEdits(state.baselinePlayers, state.rosterEdits);

  const persistedTeam = loadPersistedSelectedTeam(state.teams);
  const defaultTeam =
    persistedTeam ||
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

   // Special handling for split positions where the top two players
   // should be the WR1/WR2 and DT1/DT2 starters by default.
  function assignAlternatingSplitPair(primaryId, secondaryId) {
    const primarySlot = DEPTH_CHART_SLOTS.find((s) => s.id === primaryId);
    const secondarySlot = DEPTH_CHART_SLOTS.find((s) => s.id === secondaryId);
    if (!primarySlot || !secondarySlot) return;

    const baseSlot = {
      id: primarySlot.id,
      label: primarySlot.label,
      positions: primarySlot.positions,
      max: Math.max(primarySlot.max || 4, secondarySlot.max || 4),
    };

    const allEligible = getPlayersForSlot(baseSlot, rosterPlayers);
    if (!allEligible.length) return;

    const primaryMaxDepth = Math.min(primarySlot.max || 4, 4);
    const secondaryMaxDepth = Math.min(secondarySlot.max || 4, 4);

    const primaryAssignments = [];
    const secondaryAssignments = [];

    for (let i = 0; i < allEligible.length; i++) {
      const player = allEligible[i];
      const id = String(player.id || '').trim();
      if (!id) continue;

      if (i % 2 === 0) {
        const depthIndex = primaryAssignments.length + 1;
        if (depthIndex <= primaryMaxDepth) {
          primaryAssignments.push({
            slotId: primarySlot.id,
            depthIndex,
            acquisition: 'existing',
            playerId: id,
          });
        }
      } else {
        const depthIndex = secondaryAssignments.length + 1;
        if (depthIndex <= secondaryMaxDepth) {
          secondaryAssignments.push({
            slotId: secondarySlot.id,
            depthIndex,
            acquisition: 'existing',
            playerId: id,
          });
        }
      }
    }

    if (primaryAssignments.length) {
      plan.slots[primarySlot.id] = primaryAssignments;
    }
    if (secondaryAssignments.length) {
      plan.slots[secondarySlot.id] = secondaryAssignments;
    }
  }

  assignAlternatingSplitPair('WR1', 'WR2');
  assignAlternatingSplitPair('DT1', 'DT2');
  assignAlternatingSplitPair('CB1', 'CB2');

  for (const slot of DEPTH_CHART_SLOTS) {
    if (
      slot.id === 'WR1' ||
      slot.id === 'WR2' ||
      slot.id === 'DT1' ||
      slot.id === 'DT2' ||
      slot.id === 'CB1' ||
      slot.id === 'CB2'
    ) {
      continue;
    }

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

  const needsRebuild =
    !plan ||
    typeof plan !== 'object' ||
    !plan.teamAbbr ||
    plan.teamAbbr !== team ||
    !plan.slots ||
    typeof plan.slots !== 'object' ||
    Array.isArray(plan.slots);

  if (needsRebuild) {
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

  const playerId =
    assignment.playerId !== undefined && assignment.playerId !== null
      ? String(assignment.playerId).trim()
      : '';

  if (playerId) {
    removePlayerFromAllDepthPlans(playerId);
  }

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

export function clearPlayerFromAllDepthSlots(playerId) {
  const id = playerId !== undefined && playerId !== null ? String(playerId).trim() : '';
  if (!id || !state.depthPlansByTeam) return;

  let changed = false;

  for (const team of Object.keys(state.depthPlansByTeam)) {
    const plan = state.depthPlansByTeam[team];
    if (!plan || !plan.slots) continue;

    const slots = plan.slots;
    for (const slotId of Object.keys(slots)) {
      const arr = slots[slotId];
      if (!Array.isArray(arr) || !arr.length) continue;

      let touched = false;
      for (let i = 0; i < arr.length; i++) {
        const entry = arr[i];
        if (entry && String(entry.playerId || '').trim() === id) {
          arr[i] = null;
          touched = true;
          changed = true;
        }
      }

      if (touched) {
        while (arr.length && arr[arr.length - 1] == null) {
          arr.pop();
        }
        if (!arr.length) {
          delete slots[slotId];
        }
      }
    }
  }

  if (changed) {
    persistDepthPlans();
    emit();
  }
}

export function reorderDepthSlot({ teamAbbr, slotId, depthIndex, direction }) {
  const team = teamAbbr || state.selectedTeam;
  if (!team || !slotId || !depthIndex || !direction) return;

  const plan = ensureDepthPlanForTeam(team);
  if (!plan || !plan.slots || !Array.isArray(plan.slots[slotId])) return;

  const current = plan.slots[slotId].filter(Boolean);
  if (current.length <= 1) return;

  const fromIdx = Math.max(0, Math.min(current.length - 1, depthIndex - 1));
  const delta = direction === 'up' ? -1 : direction === 'down' ? 1 : 0;
  if (!delta) return;

  const toIdx = fromIdx + delta;
  if (toIdx < 0 || toIdx >= current.length) return;

  const updated = current.slice();
  const [moved] = updated.splice(fromIdx, 1);
  updated.splice(toIdx, 0, moved);

  for (let i = 0; i < updated.length; i++) {
    const entry = updated[i];
    if (entry) {
      entry.depthIndex = i + 1;
    }
  }

  plan.slots[slotId] = updated;
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
    if (value && typeof value === 'object' && !Array.isArray(value)) {
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
  const parsed = safeParseJSON(raw, {});
  if (!parsed || typeof parsed !== 'object') return {};

  const safe = {};
  for (const key of Object.keys(parsed)) {
    const value = parsed[key];
    if (!value || typeof value !== 'object' || Array.isArray(value)) continue;
    safe[key] = { ...value };
  }
  return safe;
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

function loadPersistedDepthPlans(teams) {
  const storage = getStorage();
  if (!storage) return {};
  const raw = storage.getItem(STORAGE_KEYS.depthPlans);
  const parsed = safeParseJSON(raw, {});
  if (!parsed || typeof parsed !== 'object') return {};

  const validTeams = new Set(
    (teams || state.teams || []).map((t) => (t && t.abbrName ? String(t.abbrName) : '')).filter(
      Boolean
    )
  );

  const safePlans = {};

  for (const teamKey of Object.keys(parsed)) {
    if (validTeams.size && !validTeams.has(teamKey)) continue;
    const rawPlan = parsed[teamKey];
    if (!rawPlan || typeof rawPlan !== 'object') continue;

    const slots =
      rawPlan.slots && typeof rawPlan.slots === 'object' && !Array.isArray(rawPlan.slots)
        ? rawPlan.slots
        : {};

    safePlans[teamKey] = {
      teamAbbr: typeof rawPlan.teamAbbr === 'string' && rawPlan.teamAbbr
        ? rawPlan.teamAbbr
        : teamKey,
      slots,
    };
  }

  return safePlans;
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

function loadPersistedSelectedTeam(teams) {
  const storage = getStorage();
  if (!storage) return null;
  const raw = storage.getItem(STORAGE_KEYS.selectedTeam);
  if (!raw || typeof raw !== 'string') return null;
  
  const teamAbbr = raw.trim();
  if (!teamAbbr) return null;
  
  const validTeams = (teams || state.teams || []).map((t) => t && t.abbrName).filter(Boolean);
  if (validTeams.length && !validTeams.includes(teamAbbr)) {
    return null;
  }
  
  return teamAbbr;
}

function saveSelectedTeam(teamAbbr) {
  const storage = getStorage();
  if (!storage) return;
  try {
    if (teamAbbr && typeof teamAbbr === 'string') {
      storage.setItem(STORAGE_KEYS.selectedTeam, teamAbbr);
    }
  } catch {
    // ignore
  }
}

function removePlayerFromAllDepthPlans(playerId) {
  const id = playerId !== undefined && playerId !== null ? String(playerId).trim() : '';
  if (!id || !state.depthPlansByTeam) return;

  for (const team of Object.keys(state.depthPlansByTeam)) {
    const plan = state.depthPlansByTeam[team];
    if (!plan || !plan.slots) continue;

    const slots = plan.slots;
    for (const slotId of Object.keys(slots)) {
      const arr = slots[slotId];
      if (!Array.isArray(arr) || !arr.length) continue;

      let touched = false;
      for (let i = 0; i < arr.length; i++) {
        const entry = arr[i];
        if (entry && String(entry.playerId || '').trim() === id) {
          arr[i] = null;
          touched = true;
        }
      }

      if (touched) {
        while (arr.length && arr[arr.length - 1] == null) {
          arr.pop();
        }
        if (!arr.length) {
          delete slots[slotId];
        }
      }
    }
  }
}
