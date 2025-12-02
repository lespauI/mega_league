import { getState, getBaselineDeadMoney, setBaselineDeadMoney } from '../state.js';
import { simulateRelease } from '../capMath.js';

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
  const baseline = getBaselineDeadMoney();

  // Build entries list: prefer explicit ledger, fallback to deriving from moves
  /** @type {Array<{ playerId: string, name: string, type: string, penaltyCurrentYear: number, penaltyNextYear: number, penaltyTotal: number, at: number }>} */
  let entries = [];
  if (Array.isArray(st.deadMoneyLedger) && st.deadMoneyLedger.length) {
    // Normalize ledger entries to include both current and next year components
    entries = st.deadMoneyLedger.map((e) => {
      const cur = Number(e.penaltyCurrentYear ?? e.penalty ?? 0) || 0;
      const next = Number(e.penaltyNextYear ?? 0) || 0;
      return {
        playerId: e.playerId,
        name: e.name,
        type: e.type,
        penaltyCurrentYear: cur,
        penaltyNextYear: next,
        penaltyTotal: cur + next,
        at: Number(e.at || Date.now()),
      };
    });
  } else {
    // Derive minimal view from moves
    const idToPlayer = new Map(st.players.map(p => [p.id, p]));
    for (const mv of st.moves || []) {
      if (!mv) continue;
      if (mv.type === 'release' || mv.type === 'tradeQuick') {
        const p = idToPlayer.get(mv.playerId);
        const name = p ? `${p.firstName || ''} ${p.lastName || ''}`.trim() : mv.playerId;
        // Re-simulate to compute year split
        const sim = p ? simulateRelease({ capAvailable: 0, capRoom: 0, capSpent: 0 }, p) : { penaltyCurrentYear: Number(mv.penalty || 0) || 0, penaltyNextYear: 0 };
        const cur = Number(sim.penaltyCurrentYear || 0);
        const next = Number(sim.penaltyNextYear || 0);
        entries.push({ playerId: mv.playerId, name, type: mv.type, penaltyCurrentYear: cur, penaltyNextYear: next, penaltyTotal: cur + next, at: Number(mv.at || Date.now()) });
      }
    }
  }

  // Sort by most recent first
  entries.sort((a, b) => b.at - a.at);

  // Compute totals
  const totalCur = entries.reduce((s, e) => s + (Number(e.penaltyCurrentYear) || 0), 0);
  const totalNext = entries.reduce((s, e) => s + (Number(e.penaltyNextYear) || 0), 0);

  // Build baseline editor
  const wrapper = document.createElement('div');

  const controls = document.createElement('div');
  controls.style.display = 'flex';
  controls.style.gap = '.5rem';
  controls.style.alignItems = 'center';
  controls.style.padding = '.5rem';
  controls.style.borderBottom = '1px solid #1f2937';
  controls.innerHTML = `
    <div style="color:var(--muted);">Baseline Dead Money (manual):</div>
    <label style="display:flex; align-items:center; gap:.25rem;">
      <span style="color:var(--muted); font-size:.9em;">This Year</span>
      <input type="number" step="100000" min="0" value="${Number(baseline.year0 || 0)}" style="background:#0b1324;color:var(--text);border:1px solid #334155;padding:.25rem .5rem;border-radius:.375rem;width:10rem;" data-dead="y0" />
    </label>
    <label style="display:flex; align-items:center; gap:.25rem;">
      <span style="color:var(--muted); font-size:.9em;">Next Year</span>
      <input type="number" step="100000" min="0" value="${Number(baseline.year1 || 0)}" style="background:#0b1324;color:var(--text);border:1px solid #334155;padding:.25rem .5rem;border-radius:.375rem;width:10rem;" data-dead="y1" />
    </label>
    <button class="btn" data-action="save">Save</button>
    <div style="margin-left:auto; color:var(--muted); font-size:.9em;">Totals — This Year: <span class="money-warn">${fmtMoney(baseline.year0 + totalCur)}</span> · Next Year: <span class="money-warn">${fmtMoney(baseline.year1 + totalNext)}</span></div>
  `;

  controls.querySelector('[data-action="save"]')?.addEventListener('click', () => {
    const y0 = Number(/** @type {HTMLInputElement} */(controls.querySelector('input[data-dead="y0"]')).value || 0);
    const y1 = Number(/** @type {HTMLInputElement} */(controls.querySelector('input[data-dead="y1"]')).value || 0);
    setBaselineDeadMoney({ year0: Math.max(0, Math.floor(y0)), year1: Math.max(0, Math.floor(y1)) });
  });

  const table = document.createElement('table');
  const thead = document.createElement('thead');
  const headRow = document.createElement('tr');
  ['When', 'Player', 'Move', 'This Year', 'Next Year', 'Total'].forEach((h) => {
    const th = document.createElement('th');
    th.textContent = h;
    headRow.appendChild(th);
  });
  thead.appendChild(headRow);

  const tbody = document.createElement('tbody');

  if (!entries.length) {
    const tr = document.createElement('tr');
    const td = document.createElement('td');
    td.colSpan = 6;
    td.textContent = 'No dead money from moves yet.';
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
      const tdCur = document.createElement('td'); tdCur.className = 'money-neg'; tdCur.textContent = fmtMoney(e.penaltyCurrentYear || 0);
      const tdNext = document.createElement('td'); tdNext.className = 'money-neg'; tdNext.textContent = fmtMoney(e.penaltyNextYear || 0);
      const tdTot = document.createElement('td'); tdTot.className = 'money-neg'; tdTot.textContent = fmtMoney((e.penaltyTotal || 0));
      tr.append(tdWhen, tdName, tdMove, tdCur, tdNext, tdTot);
      tbody.appendChild(tr);
    }
  }

  // Footer totals row
  const trTotal = document.createElement('tr');
  const tdLabel = document.createElement('td'); tdLabel.colSpan = 3; tdLabel.style.textAlign = 'right'; tdLabel.textContent = 'Totals (moves only):';
  const tdCurT = document.createElement('td'); tdCurT.className = 'money-neg'; tdCurT.textContent = fmtMoney(totalCur);
  const tdNextT = document.createElement('td'); tdNextT.className = 'money-neg'; tdNextT.textContent = fmtMoney(totalNext);
  const tdAll = document.createElement('td'); tdAll.className = 'money-neg'; tdAll.textContent = fmtMoney(totalCur + totalNext);
  trTotal.append(tdLabel, tdCurT, tdNextT, tdAll);
  tbody.appendChild(trTotal);

  table.appendChild(thead);
  table.appendChild(tbody);

  wrapper.innerHTML = '';
  wrapper.appendChild(controls);
  wrapper.appendChild(table);

  el.innerHTML = '';
  el.appendChild(wrapper);
}

export default { renderDeadMoneyTable };
