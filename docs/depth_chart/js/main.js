import { initState, subscribe } from './state.js';
import { loadTeams, loadPlayers } from './csv.js';
import { mountTeamSelector } from './ui/teamSelector.js';
import { mountDepthChart } from './ui/depthChart.js';
import { mountRosterPanel } from './ui/rosterPanel.js';
import { loadCycleIdentity } from '../../shared/cycleStorage.js';
import { mountCycleStorageControls } from '../../shared/cycleStorageControls.js';
import { DEPTH_CHART_STORAGE_CONTROLS, SHARED_DRAFT_PICKS_STORAGE_CONTROLS } from './storageConfig.js';

async function boot() {
  const [teams, players, cycle] = await Promise.all([
    loadTeams('teams'),
    loadPlayers('players'),
    loadCycleIdentity(),
  ]);

  initState({ teams, players, cycle });
  mountCycleStorageControls('cycle-storage-controls', {
    namespace: DEPTH_CHART_STORAGE_CONTROLS.namespace,
    legacyKeys: DEPTH_CHART_STORAGE_CONTROLS.keys,
    title: DEPTH_CHART_STORAGE_CONTROLS.title,
  });
  mountCycleStorageControls('shared-draft-storage-controls', {
    namespace: SHARED_DRAFT_PICKS_STORAGE_CONTROLS.namespace,
    legacyKeys: SHARED_DRAFT_PICKS_STORAGE_CONTROLS.keys,
    title: SHARED_DRAFT_PICKS_STORAGE_CONTROLS.title,
  });

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
  const notice = document.getElementById('cycle-storage-controls');
  if (notice) notice.textContent = `The depth chart could not load cycle metadata or its CSV inputs: ${err.message || err}`;
});
