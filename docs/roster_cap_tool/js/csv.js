import { normalizeTeamRow, normalizePlayerRow } from './validation.js';

/**
 * Load a CSV via fetch and PapaParse.
 * @param {string} url
 * @returns {Promise<Array<Object>>}
 */
function loadCsv(url) {
  return new Promise((resolve, reject) => {
    Papa.parse(url, {
      download: true,
      header: true,
      skipEmptyLines: true,
      complete: (res) => resolve(res.data || []),
      error: (err) => reject(err),
    });
  });
}

export async function loadTeams(url) {
  const raw = await loadCsv(url);
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
  const raw = await loadCsv(url);
  const players = [];
  let invalid = 0;
  for (const row of raw) {
    const { ok, player } = normalizePlayerRow(row);
    if (ok) players.push(player); else invalid++;
  }
  if (invalid) console.warn(`[players] skipped invalid rows: ${invalid}`);
  return players;
}

