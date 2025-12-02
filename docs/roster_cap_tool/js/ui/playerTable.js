import { getState, setState, getCapSummary } from '../state.js';
import { simulateTradeQuick } from '../capMath.js';
import { openReleaseModal } from './modals/releaseModal.js';
import { openExtensionModal } from './modals/extensionModal.js';
import { openConversionModal } from './modals/conversionModal.js';
import { openOfferModal } from './modals/offerModal.js';

function fmtMoney(n) {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    maximumFractionDigits: 0,
  }).format(n || 0);
}

function fmtPlayerCell(p) {
  const name = `${p.firstName || ''} ${p.lastName || ''}`.trim();
  const posBadge = `<span class="badge pos-${(p.position || '').toUpperCase()}">${p.position || ''}</span>`;
  const meta = [
    typeof p.age === 'number' ? `${p.age}y` : null,
    p.height ? p.height : null,
    typeof p.weight === 'number' ? `${p.weight} lb` : null,
  ].filter(Boolean).join(' · ');
  return `
    <div><strong>${name}</strong> ${posBadge}</div>
    <div style="color:var(--muted); font-size:.8em">${meta}</div>
  `;
}

function calcFaYear(p, seasonIndex) {
  const left = typeof p.contractYearsLeft === 'number' ? p.contractYearsLeft : null;
  const season = typeof seasonIndex === 'number' ? seasonIndex : null;
  if (left == null || season == null) return '-';
  try { return String(season + left); } catch { return '-'; }
}

/**
 * Render a roster-like table into a container.
 * @param {string} containerId
 * @param {Array<Object>} players
 * @param {{ type: 'active'|'fa', sortKey?: string, sortDir?: 'asc'|'desc', onSortChange?: (key:string, dir:'asc'|'desc')=>void }} options
 */
export function renderPlayerTable(containerId, players, options = {}) {
  const { type = 'active', sortKey = 'capHit', sortDir = 'desc', onSortChange } = options;
  const el = document.getElementById(containerId);
  if (!el) return;

  const st = getState();
  const team = st.teams.find((t) => t.abbrName === st.selectedTeam);

  // Sort copy of players
  const list = [...players];
  list.sort((a, b) => {
    const av = Number(a?.[sortKey] || 0);
    const bv = Number(b?.[sortKey] || 0);
    return sortDir === 'asc' ? av - bv : bv - av;
  });

  // Build header based on type
  const headers = type === 'fa'
    ? ['Player', 'Desired Salary', 'Desired Bonus', 'Desired Length', 'Total Value', 'Action']
    : ['#', 'Player', '2025 Cap', 'Dead Cap (Release)', 'Dead Cap (Trade)', 'Contract', 'FA Year', 'Action'];

  const sortableIdx = type === 'fa' ? 1 : 2; // index of sortable money column

  const table = document.createElement('table');
  const thead = document.createElement('thead');
  const headRow = document.createElement('tr');
  headers.forEach((h, idx) => {
    const th = document.createElement('th');
    th.textContent = h;
    if (idx === sortableIdx) {
      th.style.cursor = 'pointer';
      th.title = 'Click to sort';
      th.addEventListener('click', () => {
        const newDir = sortDir === 'asc' ? 'desc' : 'asc';
        onSortChange && onSortChange(type === 'fa' ? 'desiredSalary' : 'capHit', newDir);
      });
    }
    headRow.appendChild(th);
  });
  thead.appendChild(headRow);

  const tbody = document.createElement('tbody');

  list.forEach((p, i) => {
    const tr = document.createElement('tr');

    if (type !== 'fa') {
      // Row number
      const tdIdx = document.createElement('td');
      tdIdx.textContent = String(i + 1);
      tr.appendChild(tdIdx);
    }

    // Player cell
    const tdPlayer = document.createElement('td');
    tdPlayer.innerHTML = fmtPlayerCell(p);
    tr.appendChild(tdPlayer);

    if (type === 'fa') {
      const desiredSalary = Number(p.desiredSalary || 0);
      const desiredBonus = Number(p.desiredBonus || 0);
      const desiredLength = Number(p.desiredLength || 0);
      const totalValue = (desiredSalary * desiredLength) + desiredBonus;

      const c1 = document.createElement('td'); c1.textContent = fmtMoney(desiredSalary);
      const c2 = document.createElement('td'); c2.textContent = fmtMoney(desiredBonus);
      const c3 = document.createElement('td'); c3.textContent = desiredLength ? String(desiredLength) : '-';
      const c4 = document.createElement('td'); c4.textContent = fmtMoney(totalValue);
      tr.append(c1, c2, c3, c4);

      const action = document.createElement('td');
      const btn = document.createElement('button');
      btn.className = 'btn primary';
      btn.textContent = 'Make Offer';
      btn.addEventListener('click', () => openOfferModal(p));
      action.appendChild(btn);
      tr.appendChild(action);
    } else {
      // Active roster columns
      const tdCap = document.createElement('td');
      tdCap.textContent = fmtMoney(p.capHit || 0);
      const tdDeadRel = document.createElement('td');
      // Per PRD mapping for column, using capReleaseNetSavings here
      tdDeadRel.textContent = p.capReleaseNetSavings != null ? fmtMoney(p.capReleaseNetSavings) : '-';
      const tdDeadTrade = document.createElement('td');
      tdDeadTrade.textContent = p.capReleasePenalty != null ? fmtMoney(p.capReleasePenalty) : '-';
      const tdContract = document.createElement('td');
      const len = p.contractLength; const sal = p.contractSalary;
      tdContract.textContent = (len && sal) ? `${len} yrs, ${fmtMoney(sal)}` : '-';
      const tdFaYear = document.createElement('td');
      tdFaYear.textContent = calcFaYear(p, team?.seasonIndex);
      tr.append(tdCap, tdDeadRel, tdDeadTrade, tdContract, tdFaYear);

      const tdAction = document.createElement('td');
      const sel = document.createElement('select');
      const opt0 = document.createElement('option'); opt0.value = ''; opt0.textContent = 'Select…'; sel.appendChild(opt0);
      const addOpt = (val, label, enabled = true) => {
        const o = document.createElement('option'); o.value = val; o.textContent = label; if (!enabled) o.disabled = true; sel.appendChild(o);
      };
      addOpt('release', 'Release');
      addOpt('tradeQuick', 'Trade (Quick)');
      const canExtend = typeof p.contractYearsLeft === 'number' ? p.contractYearsLeft <= 2 : false;
      addOpt('extend', 'Extension', canExtend);
      addOpt('convert', 'Conversion');
      sel.addEventListener('change', () => {
        if (!sel.value) return;
        const action = sel.value;
        console.log('[action]', action, { playerId: p.id, name: `${p.firstName} ${p.lastName}` });
        if (action === 'release') {
          openReleaseModal(p);
        } else if (action === 'tradeQuick') {
          // Quick trade: confirm, then remove player and apply trade dead money savings/penalty
          const stNow = getState();
          const team = stNow.teams.find((t) => t.abbrName === stNow.selectedTeam);
          if (!team) { sel.value = ''; return; }
          const snap = getCapSummary();
          const effTeam = { ...team, capAvailable: snap.capAvailable };
          const res = simulateTradeQuick(effTeam, p);
          const name = `${p.firstName || ''} ${p.lastName || ''}`.trim();
          const ok = window.confirm(`Trade (Quick) ${name}?\n\nDead Cap This Year: ${fmtMoney(res.penaltyCurrentYear)}\nSavings: ${fmtMoney(res.savings || 0)}\nNew Cap Space: ${fmtMoney(res.newCapSpace || 0)}`);
          if (!ok) { sel.value = ''; return; }
          // Apply move; also add ledger entry for dead money
          const moves = [...stNow.moves, res.move];
          const players = stNow.players.map((pl) => pl.id === p.id ? { ...pl, isFreeAgent: true, team: '' } : pl);
          const ledgerEntry = { playerId: p.id, name, type: 'tradeQuick', penalty: res.penaltyCurrentYear, at: Date.now() };
          const deadMoneyLedger = Array.isArray(stNow.deadMoneyLedger) ? [...stNow.deadMoneyLedger, ledgerEntry] : [ledgerEntry];
          setState({ moves, players, deadMoneyLedger });
          // Sanity assert
          try { console.assert(getCapSummary().capAvailable === res.newCapSpace, '[tradeQuick] capAvailable matches preview'); } catch {}
        } else if (action === 'extend') {
          openExtensionModal(p);
        } else if (action === 'convert') {
          openConversionModal(p);
        }
        sel.value = '';
      });
      tdAction.appendChild(sel);
      tr.appendChild(tdAction);
    }

    tbody.appendChild(tr);
  });

  table.appendChild(thead);
  table.appendChild(tbody);

  // Mount
  el.innerHTML = '';
  el.appendChild(table);
}

export default { renderPlayerTable };
