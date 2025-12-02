import { getState } from '../state.js';

function fmtMoney(n) {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    maximumFractionDigits: 0,
  }).format(n || 0);
}

/**
 * Render the Dead Money ledger into container `dead-money-table`.
 * Sources entries from state.deadMoneyLedger if available, otherwise derives from moves.
 */
export function renderDeadMoneyTable(containerId = 'dead-money-table') {
  const el = document.getElementById(containerId);
  if (!el) return;

  const st = getState();

  // Build entries list: prefer explicit ledger, fallback to deriving from moves
  /** @type {Array<{ playerId: string, name: string, type: string, penalty: number, at: number }>} */
  let entries = [];
  if (Array.isArray(st.deadMoneyLedger) && st.deadMoneyLedger.length) {
    entries = st.deadMoneyLedger.slice();
  } else {
    // Derive minimal view from moves
    const idToPlayer = new Map(st.players.map(p => [p.id, p]));
    for (const mv of st.moves || []) {
      if (!mv) continue;
      if (mv.type === 'release' || mv.type === 'tradeQuick') {
        const p = idToPlayer.get(mv.playerId);
        const name = p ? `${p.firstName || ''} ${p.lastName || ''}`.trim() : mv.playerId;
        const penalty = Number(mv.penalty || 0);
        entries.push({ playerId: mv.playerId, name, type: mv.type, penalty, at: Number(mv.at || Date.now()) });
      }
    }
  }

  // Sort by most recent first
  entries.sort((a, b) => b.at - a.at);

  const table = document.createElement('table');
  const thead = document.createElement('thead');
  const headRow = document.createElement('tr');
  ['When', 'Player', 'Move', 'Dead Money (This Year)'].forEach((h) => {
    const th = document.createElement('th');
    th.textContent = h;
    headRow.appendChild(th);
  });
  thead.appendChild(headRow);

  const tbody = document.createElement('tbody');

  if (!entries.length) {
    const tr = document.createElement('tr');
    const td = document.createElement('td');
    td.colSpan = 4;
    td.textContent = 'No dead money yet.';
    tr.appendChild(td);
    tbody.appendChild(tr);
  } else {
    for (const e of entries) {
      const tr = document.createElement('tr');
      const when = new Date(e.at);
      const tdWhen = document.createElement('td');
      tdWhen.textContent = isFinite(when.getTime()) ? when.toLocaleString() : '-';
      const tdName = document.createElement('td');
      tdName.textContent = e.name || e.playerId;
      const tdMove = document.createElement('td');
      tdMove.textContent = e.type === 'release' ? 'Release' : e.type === 'tradeQuick' ? 'Trade (Quick)' : e.type;
      const tdPenalty = document.createElement('td');
      tdPenalty.className = 'money-neg';
      tdPenalty.textContent = fmtMoney(e.penalty || 0);
      tr.append(tdWhen, tdName, tdMove, tdPenalty);
      tbody.appendChild(tr);
    }
  }

  table.appendChild(thead);
  table.appendChild(tbody);

  el.innerHTML = '';
  el.appendChild(table);
}

export default { renderDeadMoneyTable };

