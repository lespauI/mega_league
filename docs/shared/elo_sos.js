import { loadCurrentElo } from './elo.js';

/** Load and enrich the common ELO SOS inputs for a season-specific page. */
export async function loadEloSosData(displaySeason, parseCsv) {
  const loader = globalThis.MegaData;
  if (!loader) throw new Error('The shared browser data loader did not load.');
  const cycle = await loader.assertCycle({ displaySeason });
  const [rows, teams, schedules, { byTeam: eloByTeam, sourceWeek }] = await Promise.all([
    loader.loadCsv('elo_sos', parseCsv),
    loader.loadCsv('teams', parseCsv),
    loader.loadJson('schedules'),
    loadCurrentElo(parseCsv),
  ]);

  const teamMeta = new Map();
  for (const team of teams) {
    if (!team.displayName) continue;
    teamMeta.set(String(team.displayName).trim(), {
      logoId: team.logoId,
      conference: team.conferenceName || team.conference,
      division: team.divName || team.divisionName || team.division,
    });
  }

  for (const row of rows) {
    const name = String(row.team || '').trim();
    const meta = teamMeta.get(name);
    if (meta) {
      row.conference = row.conference || meta.conference || null;
      row.division = row.division || meta.division || null;
      if (meta.logoId !== undefined && meta.logoId !== null && meta.logoId !== '') {
        row.logoUrl = `https://cdn.neonsportz.com/teamlogos/256/${meta.logoId}.png`;
      }
    }
    if (eloByTeam.has(name)) row.own_elo = eloByTeam.get(name);
  }

  const conferences = Array.from(new Set(rows.map((row) => String(row.conference || '').toUpperCase()).filter(Boolean))).sort();
  const divisionsByConf = new Map();
  for (const conference of conferences) {
    const divisions = Array.from(new Set(
      rows.filter((row) => String(row.conference || '').toUpperCase() === conference)
        .map((row) => row.division).filter(Boolean),
    )).sort();
    divisionsByConf.set(conference, divisions);
  }
  const allDivisions = Array.from(new Set(rows.map((row) => row.division).filter(Boolean))).sort();

  const scheduleMap = new Map();
  if (schedules && typeof schedules === 'object' && !Array.isArray(schedules)) {
    for (const [teamName, record] of Object.entries(schedules)) {
      const games = Array.isArray(record?.schedule) ? record.schedule : [];
      const enriched = games.map((game, week) => {
        const opponent = String(game.opponent || '').trim();
        const opponentElo = game.oppElo == null ? eloByTeam.get(opponent) : game.oppElo;
        const meta = teamMeta.get(opponent) || {};
        const logoUrl = meta.logoId !== undefined && meta.logoId !== null && meta.logoId !== ''
          ? `https://cdn.neonsportz.com/teamlogos/256/${meta.logoId}.png`
          : null;
        return {
          week,
          opponent,
          elo: opponentElo,
          homeAway: game.homeAway || '',
          gameId: game.gameId || '',
          logoUrl,
        };
      });
      scheduleMap.set(String(teamName).trim(), enriched);
    }
  }

  return { rows, conferences, divisionsByConf, allDivisions, scheduleMap, sourceWeek, cycle };
}
