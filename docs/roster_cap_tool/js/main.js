import './models.js';
import { initState, subscribe, getState, setState } from './state.js';
import { loadTeams, loadPlayers } from './csv.js';

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

function mountTeamSelector() {
  const el = document.getElementById('team-selector');
  if (!el) return;
  el.innerHTML = '';
  const sel = document.createElement('select');
  const st = getState();
  st.teams.forEach((t) => {
    const opt = document.createElement('option');
    opt.value = t.abbrName; opt.textContent = `${t.abbrName} — ${t.displayName}`;
    if (t.abbrName === st.selectedTeam) opt.selected = true;
    sel.appendChild(opt);
  });
  sel.addEventListener('change', () => setState({ selectedTeam: sel.value }));
  el.appendChild(sel);
}

function fmtMoney(n) {
  return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 }).format(n || 0);
}

function mountCapSummary() {
  const el = document.getElementById('cap-summary');
  if (!el) return;
  const st = getState();
  const team = st.teams.find((t) => t.abbrName === st.selectedTeam);
  if (!team) { el.textContent = ''; return; }
  const spent = team.capSpent; const room = team.capRoom; const avail = team.capAvailable; // baseline; will be dynamic later
  const pct = Math.max(0, Math.min(100, Math.round((spent / room) * 100)));
  el.innerHTML = `
    <div class="metric"><span class="label">Original Cap</span><span class="value">${fmtMoney(room)}</span></div>
    <div class="metric"><span class="label">Cap Spent</span><span class="value">${fmtMoney(spent)}</span></div>
    <div class="metric"><span class="label">Cap Space</span><span class="value">${fmtMoney(avail)}</span></div>
    <div class="metric"><span class="label">Spent / Cap</span>
      <div class="progress"><div class="bar" style="width:${pct}%"></div></div>
    </div>
  `;
}

function mountPlaceholders() {
  // Placeholder table headers for initial scaffold
  const targetIds = ['active-roster-table','injured-reserve-table','dead-money-table','draft-picks-table','free-agents-table'];
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
  // Subscribe to updates
  subscribe(() => {
    mountTeamSelector();
    mountCapSummary();
  });
}

boot().catch((err) => {
  console.error('Failed to initialize app', err);
});

