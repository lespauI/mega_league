import { getState, setState, getCapSummary } from '../../state.js';
import { simulateSigning } from '../../capMath.js';
import { toNum } from '../../validation.js';
import { enhanceDialog } from '../a11y.js';

function fmtMoney(n) {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    maximumFractionDigits: 0,
  }).format(n || 0);
}

/**
 * Open a <dialog> modal to make an offer to a free agent.
 * Provides years/salary/bonus inputs, live cap preview, lowball warning, and validation.
 * On confirm, signs the player, updates state.moves and marks player isFreeAgent = false with contract fields.
 * @param {import('../../models.js').Player} player
 */
export function openOfferModal(player) {
  const st = getState();
  const team = st.teams.find((t) => t.abbrName === st.selectedTeam);
  if (!team) return;

  const name = `${player.firstName || ''} ${player.lastName || ''}`.trim();

  // Defaults from desired terms
  let years = Math.max(1, Math.min(7, Math.floor(Number(player.desiredLength || 1))));
  let salary = Math.max(0, Number(player.desiredSalary || 0));
  let bonus = Math.max(0, Number(player.desiredBonus || 0));

  const root = document.getElementById('modals-root') || document.body;
  const dlg = document.createElement('dialog');
  dlg.innerHTML = `
    <h3 style="margin-top:0">Offer to ${name}</h3>
    <div class="grid" style="display:grid; grid-template-columns: 1fr 1fr; gap:.75rem; align-items:center;">
      <label>Years
        <input id="offer-years" type="range" min="1" max="7" step="1" value="${years}" style="width:100%" />
      </label>
      <div id="offer-years-val" style="text-align:right; color:var(--muted)">${years} year(s)</div>

      <label>Annual Salary
        <input id="offer-salary" type="number" min="0" step="50000" value="${salary}" style="width:100%" />
      </label>
      <div style="text-align:right">${fmtMoney(salary)}</div>

      <label>Signing Bonus
        <input id="offer-bonus" type="number" min="0" step="50000" value="${bonus}" style="width:100%" />
      </label>
      <div style="text-align:right">${fmtMoney(bonus)}</div>
    </div>

    <div style="margin-top:.75rem; display:grid; grid-template-columns: 1fr 1fr; gap:.5rem;">
      <div>
        <div style="color:var(--muted); font-size:.85em">Year 1 Cap Hit</div>
        <div id="offer-cap-hit" class="money-warn">$0</div>
      </div>
      <div>
        <div style="color:var(--muted); font-size:.85em">Remaining Cap After</div>
        <div id="offer-remaining" class="">$0</div>
      </div>
    </div>
    <div id="offer-warning" style="margin-top:.25rem; font-size:.9em; color: var(--yellow); display:none;">Warning: Offer is below 90% of desired terms.</div>
    <div id="offer-error" style="margin-top:.25rem; font-size:.9em; color: var(--red); display:none;">Insufficient cap space for this offer.</div>

    <div class="modal-actions">
      <button class="btn" data-action="cancel">Cancel</button>
      <button class="btn primary" data-action="confirm">Confirm Signing</button>
    </div>
  `;

  const yearsEl = dlg.querySelector('#offer-years');
  const yearsValEl = dlg.querySelector('#offer-years-val');
  const salaryEl = dlg.querySelector('#offer-salary');
  const bonusEl = dlg.querySelector('#offer-bonus');
  const capHitEl = dlg.querySelector('#offer-cap-hit');
  const remainingEl = dlg.querySelector('#offer-remaining');
  const warnEl = dlg.querySelector('#offer-warning');
  const errEl = dlg.querySelector('#offer-error');
  const confirmBtn = dlg.querySelector('[data-action="confirm"]');

  function getOffer() {
    const y = Math.max(1, Math.min(7, Math.floor(toNum(/** @type {HTMLInputElement} */(yearsEl).value) || years)));
    const s = Math.max(0, toNum(/** @type {HTMLInputElement} */(salaryEl).value));
    const b = Math.max(0, toNum(/** @type {HTMLInputElement} */(bonusEl).value));
    return { years: y, salary: s, bonus: b };
  }

  function recalcPreview() {
    const snap = getCapSummary();
    const effTeam = { ...team, capAvailable: snap.capAvailable };
    const offer = getOffer();
    yearsValEl.textContent = `${offer.years} year(s)`;
    const sim = simulateSigning(effTeam, player, offer);
    capHitEl.textContent = fmtMoney(sim.year1CapHit);
    remainingEl.textContent = fmtMoney(sim.remainingCapAfter);
    // Color coding
    capHitEl.className = sim.year1CapHit > 0 ? 'money-neg' : 'money-pos';
    remainingEl.className = sim.remainingCapAfter >= 0 ? 'money-pos' : 'money-neg';
    // Warning and error
    warnEl.style.display = sim.warnLowball ? 'block' : 'none';
    const noCap = !sim.canSign;
    errEl.style.display = noCap ? 'block' : 'none';
    if (confirmBtn) /** @type {HTMLButtonElement} */(confirmBtn).disabled = noCap;
    return sim;
  }

  function close() {
    try { dlg.close(); } catch {}
    dlg.remove();
  }

  dlg.addEventListener('input', () => recalcPreview());
  dlg.addEventListener('click', (e) => {
    // Close when clicking backdrop area (outside content bounds)
    const r = dlg.getBoundingClientRect();
    if (e.target === dlg && (e.clientX < r.left || e.clientX > r.right || e.clientY < r.top || e.clientY > r.bottom)) {
      close();
    }
  });

  dlg.querySelector('[data-action="cancel"]').addEventListener('click', close);
  dlg.querySelector('[data-action="confirm"]').addEventListener('click', () => {
    const snap = getCapSummary();
    const effTeam = { ...team, capAvailable: snap.capAvailable };
    const offer = getOffer();
    const sim = simulateSigning(effTeam, player, offer);
    if (!sim.canSign) return; // should be disabled already

    // Apply move: add to moves and convert player to roster member
    const current = getState();
    const moves = [...current.moves, sim.move];
    const players = current.players.map((p) => {
      if (p.id !== player.id) return p;
      // Update basic contract fields and capHit for current season
      return {
        ...p,
        isFreeAgent: false,
        team: current.selectedTeam,
        contractLength: offer.years,
        contractYearsLeft: offer.years,
        contractSalary: offer.salary * offer.years,
        contractBonus: offer.bonus,
        capHit: sim.year1CapHit,
      };
    });
    setState({ moves, players });

    // Sanity assert that summary matches preview
    console.assert(Math.round(getCapSummary().capAvailable) === Math.round(sim.remainingCapAfter), '[sign] capAvailable matches previewed remaining cap');
    close();
  });

  root.appendChild(dlg);
  enhanceDialog(dlg, { opener: document.activeElement });
  try { dlg.showModal(); } catch { dlg.show(); }
  // Initial preview
  recalcPreview();
}

export default { openOfferModal };
