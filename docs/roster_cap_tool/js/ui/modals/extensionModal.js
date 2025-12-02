import { getState, setState, getCapSummary } from '../../state.js';
import { simulateExtension } from '../../capMath.js';
import { toNum } from '../../validation.js';

function fmtMoney(n) {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    maximumFractionDigits: 0,
  }).format(n || 0);
}

/**
 * Open a <dialog> modal to build a contract extension for an active player.
 * Shows years slider (1–7), total salary, signing bonus, and live preview of
 * New Cap Hit, Cap Impact (delta), and Remaining Cap After applying delta.
 * On confirm, updates the player's contract fields and pushes an 'extend' move.
 * @param {import('../../models.js').Player} player
 */
export function openExtensionModal(player) {
  const st = getState();
  const team = st.teams.find((t) => t.abbrName === st.selectedTeam);
  if (!team) return;

  const name = `${player.firstName || ''} ${player.lastName || ''}`.trim();

  // Initial defaults from player contract if available
  let years = Math.max(1, Math.min(7, Math.floor(Number(player.contractLength || player.contractYearsLeft || 3))));
  let totalSalary = Math.max(0, Number(player.contractSalary || ((player.capHit || 0) * years)));
  let signingBonus = Math.max(0, Number(player.contractBonus || 0));

  const root = document.getElementById('modals-root') || document.body;
  const dlg = document.createElement('dialog');
  dlg.innerHTML = `
    <h3 style="margin-top:0">Extend ${name}</h3>
    <div class="grid" style="display:grid; grid-template-columns: 1fr 1fr; gap:.75rem; align-items:center;">
      <label>Years
        <input id="ext-years" type="range" min="1" max="7" step="1" value="${years}" style="width:100%" />
      </label>
      <div id="ext-years-val" style="text-align:right; color:var(--muted)">${years} year(s)</div>

      <label>Total Salary
        <input id="ext-salary" type="number" min="0" step="50000" value="${totalSalary}" style="width:100%" />
      </label>
      <div style="text-align:right">${fmtMoney(totalSalary)}</div>

      <label>Signing Bonus
        <input id="ext-bonus" type="number" min="0" step="50000" value="${signingBonus}" style="width:100%" />
      </label>
      <div style="text-align:right">${fmtMoney(signingBonus)}</div>
    </div>

    <div style="margin-top:.75rem; display:grid; grid-template-columns: 1fr 1fr; gap:.5rem;">
      <div>
        <div style="color:var(--muted); font-size:.85em">Current Cap Hit</div>
        <div id="ext-old-cap" class="">${fmtMoney(player.capHit || 0)}</div>
      </div>
      <div>
        <div style="color:var(--muted); font-size:.85em">New Cap Hit</div>
        <div id="ext-new-cap" class="money-warn">$0</div>
      </div>
      <div>
        <div style="color:var(--muted); font-size:.85em">Cap Impact</div>
        <div id="ext-delta" class="">$0</div>
      </div>
      <div>
        <div style="color:var(--muted); font-size:.85em">Remaining Cap After</div>
        <div id="ext-remaining" class="">$0</div>
      </div>
    </div>

    <div class="modal-actions">
      <button class="btn" data-action="cancel">Cancel</button>
      <button class="btn primary" data-action="confirm">Apply Extension</button>
    </div>
  `;

  const yearsEl = dlg.querySelector('#ext-years');
  const yearsValEl = dlg.querySelector('#ext-years-val');
  const salaryEl = dlg.querySelector('#ext-salary');
  const bonusEl = dlg.querySelector('#ext-bonus');
  const oldCapEl = dlg.querySelector('#ext-old-cap');
  const newCapEl = dlg.querySelector('#ext-new-cap');
  const deltaEl = dlg.querySelector('#ext-delta');
  const remainingEl = dlg.querySelector('#ext-remaining');

  function getInputs() {
    const y = Math.max(1, Math.min(7, Math.floor(toNum(/** @type {HTMLInputElement} */(yearsEl).value) || years)));
    const s = Math.max(0, toNum(/** @type {HTMLInputElement} */(salaryEl).value));
    const b = Math.max(0, toNum(/** @type {HTMLInputElement} */(bonusEl).value));
    return { years: y, totalSalary: s, signingBonus: b };
  }

  function recalcPreview() {
    const snap = getCapSummary();
    const { years, totalSalary, signingBonus } = getInputs();
    yearsValEl.textContent = `${years} year(s)`;
    const sim = simulateExtension(player, { years, totalSalary, signingBonus });
    const oldCap = Number(player.capHit || 0);
    const newCap = sim.newCapHit;
    const delta = sim.capHitDelta; // positive = more spending (worse for cap), negative = savings
    const remaining = (snap.capAvailable || 0) - delta;

    if (newCapEl) newCapEl.textContent = fmtMoney(newCap);
    if (deltaEl) deltaEl.textContent = `${delta >= 0 ? '+' : ''}${fmtMoney(delta)}`;
    if (remainingEl) remainingEl.textContent = fmtMoney(remaining);
    if (oldCapEl) oldCapEl.textContent = fmtMoney(oldCap);

    // Color coding
    newCapEl.className = delta > 0 ? 'money-neg' : (delta < 0 ? 'money-pos' : '');
    deltaEl.className = delta > 0 ? 'money-neg' : (delta < 0 ? 'money-pos' : '');
    remainingEl.className = remaining >= 0 ? 'money-pos' : 'money-neg';

    return { sim, remaining };
  }

  function close() {
    try { dlg.close(); } catch {}
    dlg.remove();
  }

  dlg.addEventListener('input', () => recalcPreview());
  dlg.addEventListener('click', (e) => {
    // Close when clicking outside dialog content
    const r = dlg.getBoundingClientRect();
    if (e.target === dlg && (e.clientX < r.left || e.clientX > r.right || e.clientY < r.top || e.clientY > r.bottom)) {
      close();
    }
  });

  dlg.querySelector('[data-action="cancel"]')?.addEventListener('click', close);
  dlg.querySelector('[data-action="confirm"]')?.addEventListener('click', () => {
    // Recompute with latest snapshot
    const { years, totalSalary, signingBonus } = getInputs();
    const { sim, remaining } = recalcPreview();

    // Apply move and update player contract fields
    const current = getState();
    const moves = [...current.moves, sim.move];
    const players = current.players.map((pl) => {
      if (pl.id !== player.id) return pl;
      return {
        ...pl,
        contractLength: years,
        contractYearsLeft: years,
        contractSalary: totalSalary,
        contractBonus: signingBonus,
        capHit: sim.newCapHit,
      };
    });
    setState({ moves, players });

    // Sanity assert: capAvailable reflects previewed remaining
    try {
      const after = getCapSummary().capAvailable;
      console.assert(Math.round(after) === Math.round(remaining), '[extend] capAvailable matches preview');
    } catch {}

    close();
  });

  root.appendChild(dlg);
  try { dlg.showModal(); } catch { dlg.show(); }
  // Initial preview
  recalcPreview();
}

export default { openExtensionModal };

