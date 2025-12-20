const listeners = new Set();

const state = {
  selectedTeam: null,
  teams: [],
  players: [],
  // Deep snapshot of the initial, normalized roster for all teams
  baselinePlayers: [],
  // Quick lookup map of current players by id
  playersById: {},
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
  if (partial && typeof partial === 'object') {
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
  } else {
    Object.assign(state, partial);
  }
  emit();
}

export function getTeamPlayers() {
  if (!state.selectedTeam) return [];
  return state.players.filter((p) => !p.isFreeAgent && p.team === state.selectedTeam);
}

export function initState({ teams, players }) {
  state.teams = teams || [];
  // Normalize player.team to team abbrName so filters work
  try {
    state.players = normalizePlayersTeams(players || [], state.teams || []);
  } catch {
    state.players = players || [];
  }
  // Store a deep baseline copy for future reset/compare and depth planning.
  try {
    state.baselinePlayers = JSON.parse(JSON.stringify(state.players));
  } catch {
    state.baselinePlayers = (state.players || []).map((p) => ({ ...p }));
  }
  // Build quick lookup map for depth planning and CSV export.
  state.playersById = buildPlayersById(state.players);
  if (!state.selectedTeam && teams.length) {
    state.selectedTeam = teams[0].abbrName;
  }
  emit();
}

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
    const abbr = raw ? (teamKeyToAbbr[raw] || p.team) : p.team;
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
