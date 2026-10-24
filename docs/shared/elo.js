const metadataUrl = new URL('../data/import_metadata.json', import.meta.url);
const currentEloUrl = new URL('../data/current_elo.csv', import.meta.url);

async function readText(url, fetchImpl) {
  const response = await fetchImpl(url, { cache: 'no-store' });
  if (!response.ok) throw new Error(`Request failed (${response.status}): ${url}`);
  return response.text();
}

/** Load the browser's one-column ELO view and verify it matches cycle metadata. */
export async function loadCurrentElo(parseCsv, fetchImpl = globalThis.fetch) {
  if (typeof parseCsv !== 'function') throw new Error('An ELO CSV parser is required.');
  if (typeof fetchImpl !== 'function') throw new Error('Fetch is unavailable for current ELO data.');

  const metadata = JSON.parse(await readText(metadataUrl, fetchImpl));
  const sourceWeek = Number(metadata.eloSourceWeek);
  if (!Number.isInteger(sourceWeek) || sourceWeek < 0) {
    throw new Error('Cycle metadata has no valid eloSourceWeek.');
  }

  const rows = parseCsv(await readText(currentEloUrl, fetchImpl));
  if (!Array.isArray(rows) || rows.length === 0) throw new Error('Current ELO data has no team ratings.');
  const byTeam = new Map();
  for (const row of rows) {
    const team = String(row.Team || '').trim();
    const elo = Number(row.ELO);
    const rowWeek = Number(row.sourceWeek);
    if (!team || !Number.isFinite(elo)) throw new Error('Current ELO data contains an invalid team rating.');
    if (rowWeek !== sourceWeek) {
      throw new Error(`Current ELO source week ${rowWeek} does not match metadata Week ${sourceWeek}.`);
    }
    if (byTeam.has(team)) throw new Error(`Current ELO data contains duplicate team ${team}.`);
    byTeam.set(team, elo);
  }
  return { sourceWeek, rows, byTeam };
}
