import { normalizeTeamRow, normalizePlayerRow } from './validation.js';
import { parseCsvRows } from '../../shared/csv.js';

function loadRows(key) {
  const loader = globalThis.MegaData;
  if (!loader) throw new Error('The shared browser data loader did not load.');
  return loader.loadCsv(key, (text) => parseCsvRows(text));
}

/**
 * Load normalized team rows using a manifest data key.
 * @param {string} key
 * @returns {Promise<Array<Object>>}
 */
export async function loadTeams(key = 'teams') {
  const raw = await loadRows(key);
  const teams = [];
  let invalid = 0;
  for (const row of raw) {
    const { ok, team } = normalizeTeamRow(row);
    if (ok) teams.push(team); else invalid++;
  }
  if (invalid) console.warn(`[teams] skipped invalid rows: ${invalid}`);
  return teams;
}

export async function loadPlayers(key = 'players') {
  const raw = await loadRows(key);
  const players = [];
  let invalid = 0;
  for (const row of raw) {
    const { ok, player } = normalizePlayerRow(row);
    if (ok) players.push(player); else invalid++;
  }
  if (invalid) console.warn(`[players] skipped invalid rows: ${invalid}`);
  return players;
}

