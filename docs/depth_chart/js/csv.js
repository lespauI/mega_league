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

function toBool(v) {
  if (typeof v === 'boolean') return v;
  if (typeof v === 'number') return v !== 0;
  if (typeof v === 'string') {
    const s = v.trim().toLowerCase();
    return s === '1' || s === 'true' || s === 'yes' || s === 'y';
  }
  return false;
}

function toNum(v) {
  if (typeof v === 'number') return v;
  if (typeof v === 'string') {
    const cleaned = v.replace(/[$, ]/g, '');
    const n = Number(cleaned);
    return Number.isFinite(n) ? n : NaN;
  }
  return NaN;
}

function toStr(v) {
  return v == null ? '' : String(v);
}

export async function loadTeams(url) {
  const raw = await loadCsv(url);
  const teams = [];
  for (const row of raw) {
    const abbrName = toStr(row.abbrName || row.team || row.abbr || '');
    const displayName = toStr(row.displayName || row.name || '');
    if (abbrName && displayName) {
      teams.push({ abbrName, displayName });
    }
  }
  return teams;
}

export async function loadPlayers(url) {
  const raw = await loadCsv(url);
  const players = [];
  for (const row of raw) {
    const firstName = toStr(row.firstName || row.fname || '');
    const lastName = toStr(row.lastName || row.lname || '');
    const position = toStr(row.position || row.pos || '');
    const team = toStr(row.team || '');
    const isFreeAgent = toBool(row.isFreeAgent);
    const playerBestOvr = Number.isFinite(toNum(row.playerBestOvr)) ? toNum(row.playerBestOvr) : 0;
    const playerSchemeOvr = Number.isFinite(toNum(row.playerSchemeOvr)) ? toNum(row.playerSchemeOvr) : 0;
    if (firstName && lastName && position) {
      players.push({ firstName, lastName, position, team, isFreeAgent, playerBestOvr, playerSchemeOvr });
    }
  }
  return players;
}
