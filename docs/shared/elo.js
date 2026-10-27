/** Load the one-week browser ELO view and validate it against the data manifest. */
export async function loadCurrentElo(parseCsv) {
  if (typeof parseCsv !== 'function') throw new Error('An ELO CSV parser is required.');
  const data = globalThis.MegaData;
  if (!data) throw new Error('The shared browser data loader did not load.');

  const manifest = await data.getManifest();
  const sourceWeek = manifest.cycle.eloSourceWeek;
  const rows = await data.loadCsv('elo', parseCsv);
  if (!Array.isArray(rows) || rows.length === 0) throw new Error('Current ELO data has no team ratings.');
  const byTeam = new Map();
  for (const row of rows) {
    const team = String(row.Team || '').trim();
    const elo = Number(row.ELO);
    const rowWeek = Number(row.sourceWeek);
    if (!team || !Number.isFinite(elo)) throw new Error('Current ELO data contains an invalid team rating.');
    if (rowWeek !== sourceWeek) {
      throw new Error(`Current ELO source week ${rowWeek} does not match manifest Week ${sourceWeek}.`);
    }
    if (byTeam.has(team)) throw new Error(`Current ELO data contains duplicate team ${team}.`);
    byTeam.set(team, elo);
  }
  return { sourceWeek, rows, byTeam };
}
