import { initState, subscribe } from './state.js';
import { loadTeams, loadPlayers } from './csv.js';
import { mountTeamSelector } from './ui/teamSelector.js';
import { mountDepthChart } from './ui/depthChart.js';
import { mountRosterPanel } from './ui/rosterPanel.js';

async function boot() {
  const [teams, players] = await Promise.all([
    loadTeams('../../MEGA_teams.csv'),
    loadPlayers('../../MEGA_players.csv'),
  ]);

  initState({ teams, players });

  mountTeamSelector();
  mountDepthChart();
  mountRosterPanel();

  subscribe(() => {
    mountTeamSelector();
    mountDepthChart();
    mountRosterPanel();
  });
}

boot().catch((err) => {
  console.error('Failed to initialize depth chart', err);
});
