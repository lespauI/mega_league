import { getActiveRoster, getFreeAgents, subscribe } from '../state.js';
import { renderPlayerTable } from './playerTable.js';

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
}

// Optional: live re-render on state changes if imported directly
export function subscribeRosterTabs() {
  return subscribe(() => mountRosterTabs());
}

export default { mountRosterTabs, subscribeRosterTabs };

