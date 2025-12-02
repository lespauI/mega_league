import { getState, setState, getCapSummary } from '../../state.js';
import { simulateTradeIn } from '../../capMath.js';
import { enhanceDialog } from '../a11y.js';
import { confirmWithDialog } from './confirmDialog.js';

function fmtMoney(n) {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    maximumFractionDigits: 0,
  }).format(n || 0);
}

function playerName(p) {
  return `${p.firstName || ''} ${p.lastName || ''}`.trim();
}

/**
 * Open a modal to search and trade in a player from another roster.
 * Shows acquiring team's Year 1 cap hit (salary-only, no bonus proration).
 */
export function openTradeInModal() {
  const st = getState();
  const team = st.teams.find((t) => t.abbrName === st.selectedTeam);
  if (!team) return;

  const root = document.getElementById('modals-root') || document.body;
  const dlg = document.createElement('dialog');
  dlg.style.maxWidth = '900px';
  dlg.innerHTML = `
    <h3 style="margin-top:0">Trade In Player</h3>
    <div style="display:flex; gap:.5rem; align-items:center; margin-bottom:.5rem;">
      <input id="tradein-search" type="text" placeholder="Search by name (e.g., 'Allen' or 'Josh Allen')" style="flex:1; padding:.5rem;" />
      <button class="btn" data-action="clear">Clear</button>
    </div>
    <div style="max-height: 50vh; overflow:auto; border:1px solid var(--line); border-radius:6px;">
      <table style="width:100%">
        <thead>
          <tr>
            <th>Action</th>
            <th>Player</th>
            <th>From Team</th>
            <th>Pos</th>
            <th>Year 1 (Salary Only)</th>
            <th>Contract</th>
          </tr>
        </thead>
        <tbody id="tradein-results"></tbody>
      </table>
    </div>
    <div class="modal-actions">
      <button class="btn" data-action="close">Close</button>
    </div>
  `;

  const searchEl = dlg.querySelector('#tradein-search');
  const resultsEl = dlg.querySelector('#tradein-results');

  function computeYear1(p) {
    const snap = getCapSummary();
    const effTeam = { ...team, capAvailable: snap.capAvailable };
    const sim = simulateTradeIn(effTeam, p);
    return sim.year1CapHit || 0;
  }

  async function applyTradeIn(p) {
    const snap = getCapSummary();
    const effTeam = { ...team, capAvailable: snap.capAvailable };
    const sim = simulateTradeIn(effTeam, p);
    const name = playerName(p);
    const rememberKey = `rosterCap.skipConfirm.tradeIn.${team.abbrName}`;
    const ok = await confirmWithDialog({
      title: `Trade In — ${name}`,
      message: `Year 1 Cap Hit (salary only): ${fmtMoney(sim.year1CapHit)}\nCap After Trade: ${fmtMoney(sim.remainingCapAfter)}`,
      confirmText: 'Trade In',
      cancelText: 'Cancel',
      danger: false,
      rememberKey,
      rememberLabel: "Don't ask again for this team",
    });
    if (!ok) return;

    const current = getState();
    const moves = [...current.moves, sim.move];
    const players = current.players.map((pl) => {
      if (pl.id !== p.id) return pl;
      // Move player to selected team. Set bonus to 0 so future years reflect no bonus proration for acquiring team.
      // Set current year capHit to acquiring-year salary-only estimate.
      return {
        ...pl,
        isFreeAgent: false,
        team: current.selectedTeam,
        contractBonus: 0,
        capHit: sim.year1CapHit,
      };
    });
    setState({ moves, players });
  }

  function renderList(filterText = '') {
    const q = filterText.trim().toLowerCase();
    const list = (st.players || []).filter((p) => !p.isFreeAgent && p.team !== st.selectedTeam);
    const filtered = q
      ? list.filter((p) => {
          const name = `${(p.firstName || '').toLowerCase()} ${(p.lastName || '').toLowerCase()}`;
          const nameComma = `${(p.lastName || '').toLowerCase()}, ${(p.firstName || '').toLowerCase()}`;
          return name.includes(q) || nameComma.includes(q);
        })
      : list.slice(0, 200); // cap initial rows for performance

    resultsEl.innerHTML = '';
    for (const p of filtered) {
      const tr = document.createElement('tr');
      const tdAct = document.createElement('td');
      const btn = document.createElement('button');
      btn.className = 'btn primary';
      btn.textContent = 'Trade In';
      btn.addEventListener('click', () => applyTradeIn(p));
      tdAct.appendChild(btn);

      const tdName = document.createElement('td');
      tdName.innerHTML = `<div><strong>${playerName(p)}</strong></div>`;
      const tdFrom = document.createElement('td');
      tdFrom.textContent = p.team || '-';
      const tdPos = document.createElement('td');
      tdPos.textContent = p.position || '-';
      const tdY1 = document.createElement('td');
      tdY1.textContent = fmtMoney(computeYear1(p));
      const tdContract = document.createElement('td');
      const len = p.contractLength; const sal = p.contractSalary; const bon = p.contractBonus;
      const parts = [];
      if (len) parts.push(`${len} yrs`);
      if (sal) parts.push(fmtMoney(sal));
      if (bon) parts.push(`+ bonus ${fmtMoney(bon)}`);
      tdContract.textContent = parts.length ? parts.join(', ') : '-';
      tr.append(tdAct, tdName, tdFrom, tdPos, tdY1, tdContract);
      resultsEl.appendChild(tr);
    }
  }

  dlg.addEventListener('input', () => {
    renderList(/** @type {HTMLInputElement} */(searchEl).value || '');
  });
  dlg.querySelector('[data-action="clear"]').addEventListener('click', () => {
    /** @type {HTMLInputElement} */(searchEl).value = '';
    renderList('');
  });
  dlg.querySelector('[data-action="close"]').addEventListener('click', () => { try { dlg.close(); } catch {}; dlg.remove(); });
  dlg.addEventListener('click', (e) => {
    const r = dlg.getBoundingClientRect();
    if (e.target === dlg && (e.clientX < r.left || e.clientX > r.right || e.clientY < r.top || e.clientY > r.bottom)) {
      try { dlg.close(); } catch {}
      dlg.remove();
    }
  });

  root.appendChild(dlg);
  enhanceDialog(dlg, { opener: document.activeElement });
  try { dlg.showModal(); } catch { dlg.show(); }
  renderList('');
}

export default { openTradeInModal };
