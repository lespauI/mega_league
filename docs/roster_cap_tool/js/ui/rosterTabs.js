import { getActiveRoster, getFreeAgents, subscribe, getState, getPositionFilter, setPositionFilter } from '../state.js';
import { renderPlayerTable } from './playerTable.js';
import { renderDeadMoneyTable } from './deadMoneyTable.js';

let activeSort = { key: 'capHit', dir: 'desc' };
let faSort = { key: 'desiredSalary', dir: 'desc' };

const POSITION_ORDER = [
  // Offense
  'QB','RB','HB','FB','WR','TE','LT','LG','C','RG','RT','OL',
  // Defense
  'LE','RE','DE','DT','DL','EDGE','LOLB','MLB','ROLB','OLB','LB','CB','FS','SS','S','DB',
  // Specialists
  'K','P','LS'
];

function sortPositions(keys) {
  const order = new Map(POSITION_ORDER.map((p, i) => [p, i]));
  return keys.slice().sort((a, b) => {
    const ia = order.has(a) ? order.get(a) : 999 + a.charCodeAt(0);
    const ib = order.has(b) ? order.get(b) : 999 + b.charCodeAt(0);
    if (ia !== ib) return ia - ib;
    return a.localeCompare(b);
  });
}

function uniquePositions(players) {
  const set = new Set();
  for (const p of players || []) {
    const pos = (p?.position ? String(p.position) : '').toUpperCase().trim();
    if (pos) set.add(pos);
  }
  return sortPositions(Array.from(set));
}

function renderPositionFilters(containerId, type, players) {
  const el = document.getElementById(containerId);
  if (!el) return;
  const available = uniquePositions(players);
  const selected = getPositionFilter(type);
  const isSelected = (pos) => selected.includes(pos);

  // Build content
  const frag = document.createDocumentFragment();
  const label = document.createElement('span');
  label.className = 'filters-label';
  label.textContent = 'Positions:';
  frag.appendChild(label);

  const makeChip = (text, opts = {}) => {
    const chip = document.createElement('button');
    chip.type = 'button';
    chip.className = 'chip';
    chip.textContent = text;
    if (opts.active) chip.classList.add('is-active');
    if (opts.onClick) chip.addEventListener('click', opts.onClick);
    return chip;
  };

  const allBtn = makeChip('All', {
    onClick: () => setPositionFilter(type, [])
  });
  frag.appendChild(allBtn);

  const clearBtn = makeChip('Clear', {
    onClick: () => setPositionFilter(type, [])
  });
  clearBtn.title = 'Show all positions';
  frag.appendChild(clearBtn);

  for (const pos of available) {
    const chip = document.createElement('button');
    chip.type = 'button';
    chip.className = 'chip';
    chip.innerHTML = `<span class="swatch" style="background: currentColor"></span><span class="badge pos-${pos}">${pos}</span>`;
    if (isSelected(pos)) chip.classList.add('is-active');
    chip.addEventListener('click', () => {
      const cur = getPositionFilter(type);
      const next = cur.includes(pos) ? cur.filter((p) => p !== pos) : [...cur, pos];
      setPositionFilter(type, next);
    });
    frag.appendChild(chip);
  }

  el.innerHTML = '';
  el.appendChild(frag);
}

function mountActive() {
  const basePlayers = getActiveRoster();
  const sel = getPositionFilter('active');
  const players = (Array.isArray(sel) && sel.length)
    ? basePlayers.filter(p => sel.includes((p?.position || '').toString().toUpperCase()))
    : basePlayers;
  renderPositionFilters('active-roster-filters', 'active', basePlayers);
  renderPlayerTable('active-roster-table', players, {
    type: 'active',
    sortKey: activeSort.key,
    sortDir: activeSort.dir,
    onSortChange: (key, dir) => {
      activeSort = { key, dir };
      mountActive();
    },
  });
}

function mountFreeAgents() {
  const basePlayers = getFreeAgents();
  const sel = getPositionFilter('fa');
  const players = (Array.isArray(sel) && sel.length)
    ? basePlayers.filter(p => sel.includes((p?.position || '').toString().toUpperCase()))
    : basePlayers;
  renderPositionFilters('free-agents-filters', 'fa', basePlayers);
  renderPlayerTable('free-agents-table', players, {
    type: 'fa',
    sortKey: faSort.key,
    sortDir: faSort.dir,
    onSortChange: (key, dir) => {
      faSort = { key, dir };
      mountFreeAgents();
    },
  });
}

export function mountRosterTabs() {
  mountActive();
  mountFreeAgents();
  // Injured Reserve: filter active roster by isOnIR flag if present
  try {
    const st = getState();
    const irPlayers = getActiveRoster().filter((p) => p && p.isOnIR);
    renderPlayerTable('injured-reserve-table', irPlayers, {
      type: 'active',
      sortKey: 'capHit',
      sortDir: 'desc',
      onSortChange: () => {
        // Re-render on sort change using the same filtering
        const updated = getActiveRoster().filter((p) => p && p.isOnIR);
        renderPlayerTable('injured-reserve-table', updated, { type: 'active', sortKey: 'capHit', sortDir: 'desc' });
      },
    });
  } catch {}

  // Dead Money tab
  try {
    renderDeadMoneyTable('dead-money-table');
  } catch {}
}

// Optional: live re-render on state changes if imported directly
export function subscribeRosterTabs() {
  return subscribe(() => mountRosterTabs());
}

export default { mountRosterTabs, subscribeRosterTabs };
