const listeners = new Set();

const state = {
  selectedTeam: null,
  teams: [],
  players: [],
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
  Object.assign(state, partial);
  emit();
}

export function getTeamPlayers() {
  if (!state.selectedTeam) return [];
  return state.players.filter((p) => !p.isFreeAgent && p.team === state.selectedTeam);
}

export function initState({ teams, players }) {
  state.teams = teams;
  state.players = normalizePlayersTeams(players, teams);
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
