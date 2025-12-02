import './models.js';
import { initState, subscribe } from './state.js';
import { loadTeams, loadPlayers } from './csv.js';
import { mountTeamSelector } from './ui/teamSelector.js';
import { mountCapSummary } from './ui/capSummary.js';
import { mountRosterTabs } from './ui/rosterTabs.js';
import { mountProjections } from './ui/projections.js';

// Basic tabs behavior
function initTabs() {
  const tabsRoot = document.getElementById('tabs');
  const panelsRoot = document.getElementById('tab-panels');
  if (!tabsRoot || !panelsRoot) return;
  tabsRoot.addEventListener('click', (e) => {
    const btn = e.target.closest('.tab');
    if (!btn) return;
    const tab = btn.getAttribute('data-tab');
    tabsRoot.querySelectorAll('.tab').forEach((b) => b.classList.toggle('is-active', b === btn));
    panelsRoot.querySelectorAll('.panel').forEach((p) => p.classList.toggle('is-active', p.id === `panel-${tab}`));
  });
}

function mountPlaceholders() {
  // Placeholder table headers for initial scaffold
  const targetIds = ['active-roster-table','injured-reserve-table','dead-money-table','projections-view','draft-picks-table','free-agents-table'];
  for (const id of targetIds) {
    const cont = document.getElementById(id);
    if (!cont) continue;
    cont.innerHTML = `
      <table>
        <thead><tr>
          <th>#</th>
          <th>Player</th>
          <th>2025 Cap</th>
          <th>Dead Cap (Release)</th>
          <th>Dead Cap (Trade)</th>
          <th>Contract</th>
          <th>FA Year</th>
          <th>Action</th>
        </tr></thead>
        <tbody><tr><td colspan="8">Loading…</td></tr></tbody>
      </table>
    `;
  }
}

async function boot() {
  initTabs();
  mountPlaceholders();
  // Load CSV data from Pages data directory
  const [teams, players] = await Promise.all([
    loadTeams('./data/MEGA_teams.csv'),
    loadPlayers('./data/MEGA_players.csv'),
  ]);
  initState({ teams, players });
  // Initial mounts
  mountTeamSelector();
  mountCapSummary();
  mountRosterTabs();
  mountProjections();
  // Subscribe to updates
  subscribe(() => {
    mountTeamSelector();
    mountCapSummary();
    mountRosterTabs();
    mountProjections();
  });
}

boot().catch((err) => {
  console.error('Failed to initialize app', err);
});
