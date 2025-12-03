import './models.js';
import { initState, subscribe } from './state.js';
import { loadTeams, loadPlayers } from './csv.js';
import { mountTeamSelector } from './ui/teamSelector.js';
import { mountCapSummary, mountHeaderProjections } from './ui/capSummary.js';
import { mountRosterTabs } from './ui/rosterTabs.js';
import { mountProjections } from './ui/projections.js';
import { mountScenarioControls } from './ui/scenarioControls.js';
import { mountDraftPicks } from './ui/draftPicks.js';
import { mountYearContext } from './ui/yearContext.js';

// Basic tabs behavior
function initTabs() {
  const tabsRoot = document.getElementById('tabs');
  const panelsRoot = document.getElementById('tab-panels');
  if (!tabsRoot || !panelsRoot) return;
  // ARIA roles
  tabsRoot.setAttribute('role', 'tablist');
  tabsRoot.querySelectorAll('.tab').forEach((btn) => {
    btn.setAttribute('role', 'tab');
    const tab = btn.getAttribute('data-tab');
    const panelId = `panel-${tab}`;
    if (!btn.id) btn.id = `tab-${tab}`;
    btn.setAttribute('aria-controls', panelId);
    btn.setAttribute('aria-selected', btn.classList.contains('is-active') ? 'true' : 'false');
  });
  panelsRoot.querySelectorAll('.panel').forEach((panel) => {
    panel.setAttribute('role', 'tabpanel');
    const id = panel.id.replace(/^panel-/, '');
    panel.setAttribute('aria-labelledby', `tab-${id}`);
  });
  tabsRoot.addEventListener('click', (e) => {
    const btn = e.target.closest('.tab');
    if (!btn) return;
    const tab = btn.getAttribute('data-tab');
    tabsRoot.querySelectorAll('.tab').forEach((b) => {
      const active = b === btn;
      b.classList.toggle('is-active', active);
      b.setAttribute('aria-selected', active ? 'true' : 'false');
    });
    panelsRoot.querySelectorAll('.panel').forEach((p) => p.classList.toggle('is-active', p.id === `panel-${tab}`));
  });
}

function mountPlaceholders() {
  // Placeholder table headers for initial scaffold
  const targetIds = ['active-roster-table','injured-reserve-table','dead-money-table','projections-view','draft-picks-table','free-agents-table'];
  for (const id of targetIds) {
    const cont = document.getElementById(id);
    if (!cont) continue;
    const testId = id.includes('active-roster') ? 'table-active-roster'
      : id.includes('injured-reserve') ? 'table-injured-reserve'
      : id.includes('dead-money') ? 'table-dead-money'
      : id.includes('free-agents') ? 'table-free-agents'
      : id.includes('draft-picks') ? 'table-draft-picks'
      : 'table-generic';
    cont.innerHTML = `
      <table data-testid="${testId}">
        <thead><tr>
          <th>#</th>
          <th>Player</th>
          <th>2025 Cap</th>
          <th>Free cap after release</th>
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
  mountYearContext();
  mountScenarioControls();
  mountCapSummary();
  mountHeaderProjections('projections-top');
  mountRosterTabs();
  mountProjections();
  mountDraftPicks();
  // Subscribe to updates
  subscribe(() => {
    mountTeamSelector();
    mountYearContext();
    mountScenarioControls();
    mountCapSummary();
    mountHeaderProjections('projections-top');
    mountRosterTabs();
    mountProjections();
    mountDraftPicks();
  });
}

boot().catch((err) => {
  console.error('Failed to initialize app', err);
});
