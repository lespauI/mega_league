import { normalizeTeamRow, normalizePlayerRow } from '../../roster_cap_tool/js/validation.js';
import { parseCsvRows } from '../../shared/csv.js';

function loadRows(key) {
  const loader = globalThis.MegaData;
  if (!loader) throw new Error('The shared browser data loader did not load.');
  return loader.loadCsv(key, (text) => parseCsvRows(text));
}

export async function loadTeams(key = 'teams') {
  const raw = await loadRows(key);
  const teams = [];
  for (const row of raw) {
    const result = normalizeTeamRow(row);
    if (result.ok) {
      teams.push({ abbrName: result.team.abbrName, displayName: result.team.displayName });
    }
  }
  return teams;
}

export async function loadPlayers(key = 'players') {
  const raw = await loadRows(key);
  const players = [];
  for (const row of raw) {
    const result = normalizePlayerRow(row);
    if (result.ok) {
      const p = result.player;
      // Keep the full normalized player model used by the cap tool
      // and add a convenience `ovr` field for depth ordering.
      const ovr = (p.playerBestOvr || p.playerSchemeOvr || 0) || 0;
      players.push({
        ...p,
        ovr,
      });
    }
  }
  return players;
}
