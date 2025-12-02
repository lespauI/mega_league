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

  // Helper to compute sort values per column
  const getActiveSortValue = (p, key, originalPlayers) => {
    switch (key) {
      case 'index': {
        const idx = originalPlayers.indexOf(p);
        return idx === -1 ? Number.MAX_SAFE_INTEGER : idx;
      }
      case 'player': {
        const ln = (p.lastName || '').toString().toLowerCase();
        const fn = (p.firstName || '').toString().toLowerCase();
        return `${ln},${fn}`;
      }
      case 'capHit': return Number(p.capHit || 0);
      case 'deadRelease': return Number(p.capReleaseNetSavings || 0);
      case 'deadTrade': return Number(p.capReleasePenalty || 0);
      case 'contract': return Number(p.contractSalary || 0);
      case 'faYear': {
        const left = typeof p.contractYearsLeft === 'number' ? p.contractYearsLeft : null;
        const season = typeof team?.seasonIndex === 'number' ? team.seasonIndex : null;
        if (left == null || season == null) return Number.MAX_SAFE_INTEGER;
        return Number(season + left);
      }
      case 'action': {
        const canExtend = typeof p.contractYearsLeft === 'number' ? p.contractYearsLeft <= 2 : false;
        return canExtend ? 1 : 0;
      }
      default: return Number(p[sortKey] || 0);
    }
  };

  const getFaSortValue = (p, key) => {
    switch (key) {
      case 'player': {
        const ln = (p.lastName || '').toString().toLowerCase();
        const fn = (p.firstName || '').toString().toLowerCase();
        return `${ln},${fn}`;
      }
      case 'desiredSalary': return Number(p.desiredSalary || 0);
      case 'desiredBonus': return Number(p.desiredBonus || 0);
      case 'desiredLength': return Number(p.desiredLength || 0);
      case 'totalValue': {
        const s = Number(p.desiredSalary || 0);
        const b = Number(p.desiredBonus || 0);
        const y = Number(p.desiredLength || 0);
        return (s * y) + b;
      }
      case 'action': return 0; // identical buttons; keep stable
      default: return Number(p[sortKey] || 0);
    }
  };

  // Sort copy of players using selected column
  const list = [...players];
  const originalPlayers = players;
  const valFn = type === 'fa'
    ? (p) => getFaSortValue(p, sortKey)
    : (p) => getActiveSortValue(p, sortKey, originalPlayers);
  list.sort((a, b) => {
    const av = valFn(a);
    const bv = valFn(b);
    const isString = (v) => typeof v === 'string';
    let cmp = 0;
    if (isString(av) || isString(bv)) {
      cmp = String(av).localeCompare(String(bv));
    } else {
      cmp = Number(av) - Number(bv);
    }
    return sortDir === 'asc' ? cmp : -cmp;
  });

  // Build header metadata based on type
  const headerMeta = type === 'fa'
    ? [
        { label: 'Player', key: 'player' },
        { label: 'Desired Salary', key: 'desiredSalary' },
        { label: 'Desired Bonus', key: 'desiredBonus' },
        { label: 'Desired Length', key: 'desiredLength' },
        { label: 'Total Value', key: 'totalValue' },
        { label: 'Action', key: 'action' },
      ]
    : [
        { label: '#', key: 'index' },
        { label: 'Player', key: 'player' },
        { label: '2025 Cap', key: 'capHit' },
        { label: 'Free cap after release', key: 'deadRelease' },
        { label: 'Dead Cap (Trade)', key: 'deadTrade' },
        { label: 'Contract', key: 'contract' },
        { label: 'FA Year', key: 'faYear' },
        { label: 'Action', key: 'action' },
      ];

  const table = document.createElement('table');
  const thead = document.createElement('thead');
  const headRow = document.createElement('tr');
  headerMeta.forEach((meta) => {
    const th = document.createElement('th');
    th.textContent = meta.label;
    th.style.cursor = 'pointer';
    th.title = 'Click to sort';
    th.addEventListener('click', () => {
      const nextDir = (sortKey === meta.key) ? (sortDir === 'asc' ? 'desc' : 'asc') : 'desc';
      onSortChange && onSortChange(meta.key, nextDir);
    });
    headRow.appendChild(th);
  });
  thead.appendChild(headRow);

  const tbody = document.createElement('tbody');

  list.forEach((p, i) => {
    const tr = document.createElement('tr');

    if (type !== 'fa') {
      // Row number
      const tdIdx = document.createElement('td');
      // Show the visual index (1-based after sorting)
      tdIdx.textContent = String(i + 1);
      tdIdx.setAttribute('data-label', '#');
      tr.appendChild(tdIdx);
    }

    // Player cell
    const tdPlayer = document.createElement('td');
    tdPlayer.classList.add('cell-player');
    tdPlayer.setAttribute('data-label', 'Player');
    tdPlayer.innerHTML = fmtPlayerCell(p);
    tr.appendChild(tdPlayer);

    if (type === 'fa') {
      const desiredSalary = Number(p.desiredSalary || 0);
      const desiredBonus = Number(p.desiredBonus || 0);
      const desiredLength = Number(p.desiredLength || 0);
      const totalValue = (desiredSalary * desiredLength) + desiredBonus;

      const c1 = document.createElement('td'); c1.textContent = fmtMoney(desiredSalary); c1.setAttribute('data-label', 'Desired Salary');
      const c2 = document.createElement('td'); c2.textContent = fmtMoney(desiredBonus); c2.setAttribute('data-label', 'Desired Bonus');
      const c3 = document.createElement('td'); c3.textContent = desiredLength ? String(desiredLength) : '-'; c3.setAttribute('data-label', 'Desired Length');
      const c4 = document.createElement('td'); c4.textContent = fmtMoney(totalValue); c4.setAttribute('data-label', 'Total Value');
      tr.append(c1, c2, c3, c4);

      const action = document.createElement('td');
      action.setAttribute('data-label', 'Action');
      action.classList.add('cell-action');
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
      tdCap.setAttribute('data-label', '2025 Cap');
      const tdDeadRel = document.createElement('td');
      // Per PRD mapping for column, using capReleaseNetSavings here
      tdDeadRel.textContent = p.capReleaseNetSavings != null ? fmtMoney(p.capReleaseNetSavings) : '-';
      tdDeadRel.setAttribute('data-label', 'Free cap after release');
      const tdDeadTrade = document.createElement('td');
      tdDeadTrade.textContent = p.capReleasePenalty != null ? fmtMoney(p.capReleasePenalty) : '-';
      tdDeadTrade.setAttribute('data-label', 'Dead Cap (Trade)');
      const tdContract = document.createElement('td');
      const len = p.contractLength; const sal = p.contractSalary;
      tdContract.textContent = (len && sal) ? `${len} yrs, ${fmtMoney(sal)}` : (len ? `${len} yrs` : '-');
      tdContract.setAttribute('data-label', 'Contract');
      const tdFaYear = document.createElement('td');
      tdFaYear.textContent = calcFaYear(p, team?.seasonIndex);
      tdFaYear.setAttribute('data-label', 'FA Year');
      tr.append(tdCap, tdDeadRel, tdDeadTrade, tdContract, tdFaYear);

      const tdAction = document.createElement('td');
      tdAction.setAttribute('data-label', 'Action');
      tdAction.classList.add('cell-action');
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
          const ledgerEntry = {
            playerId: p.id,
            name,
            type: 'tradeQuick',
            penaltyCurrentYear: res.penaltyCurrentYear,
            penaltyNextYear: res.penaltyNextYear,
            penaltyTotal: res.penaltyTotal,
            at: Date.now(),
          };
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
