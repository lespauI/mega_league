import { normalizeTeamRow, normalizePlayerRow } from './validation.js';
import { loadCsvRows } from '../../shared/csv.js';

/**
 * Load a CSV via fetch and PapaParse.
 * @param {string} url
 * @returns {Promise<Array<Object>>}
 */
export async function loadTeams(url) {
  const raw = await loadCsvRows(url);
  const teams = [];
  let invalid = 0;
  for (const row of raw) {
    const { ok, team } = normalizeTeamRow(row);
    if (ok) teams.push(team); else invalid++;
  }
  if (invalid) console.warn(`[teams] skipped invalid rows: ${invalid}`);
  return teams;
}

export async function loadPlayers(url) {
  const raw = await loadCsvRows(url);
  const players = [];
  let invalid = 0;
  for (const row of raw) {
    const { ok, player } = normalizePlayerRow(row);
    if (ok) players.push(player); else invalid++;
  }
  if (invalid) console.warn(`[players] skipped invalid rows: ${invalid}`);
  return players;
}

