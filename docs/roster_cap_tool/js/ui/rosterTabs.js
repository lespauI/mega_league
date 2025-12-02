import { getActiveRoster, getFreeAgents, subscribe, getState } from '../state.js';
import { renderPlayerTable } from './playerTable.js';
import { renderDeadMoneyTable } from './deadMoneyTable.js';

let activeSort = { key: 'capHit', dir: 'desc' };
let faSort = { key: 'desiredSalary', dir: 'desc' };

function mountActive() {
  const players = getActiveRoster();
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
  const players = getFreeAgents();
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
