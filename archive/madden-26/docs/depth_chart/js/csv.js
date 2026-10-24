import { normalizeTeamRow, normalizePlayerRow } from '../../roster_cap_tool/js/validation.js';

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
  for (const row of raw) {
    const result = normalizeTeamRow(row);
    if (result.ok) {
      teams.push({ abbrName: result.team.abbrName, displayName: result.team.displayName });
    }
  }
  return teams;
}

export async function loadPlayers(url) {
  const raw = await loadCsv(url);
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
