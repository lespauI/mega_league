import { getState, setState, getCapSummary } from '../../state.js';
import { simulateConversion, MADDEN_BONUS_PRORATION_MAX_YEARS } from '../../capMath.js';
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
 * Open a <dialog> modal to convert base salary to signing bonus with proration.
 * Shows current vs new cap hit, cap impact (delta), per-year proration, and a simple
 * multi-year impact view. On confirm, applies move and updates the player's current
 * year cap hit only (snapshot), recording a 'convert' move.
 * @param {import('../../models.js').Player} player
 */
export function openConversionModal(player) {
  const st = getState();
  const team = st.teams.find((t) => t.abbrName === st.selectedTeam);
  if (!team) return;
  const baseYear = Number(team?.calendarYear || 0);

  const name = `${player.firstName || ''} ${player.lastName || ''}`.trim();

  // Heuristic defaults
  const contractYearsLeft = Number.isFinite(Number(player.contractYearsLeft)) ? Math.max(1, Math.floor(Number(player.contractYearsLeft))) : 3;
  const maxYears = Math.max(1, Math.min(MADDEN_BONUS_PRORATION_MAX_YEARS, contractYearsLeft));

  // Approx base salary = capHit - (bonus/yearsProrated)
  const bonus = Number(player.contractBonus || 0);
  const len = Math.max(1, Math.floor(Number(player.contractLength || contractYearsLeft || 1)));
  const bonusProrateYears = Math.min(len, MADDEN_BONUS_PRORATION_MAX_YEARS);
  const bonusPerYear = bonus ? (bonus / bonusProrateYears) : 0;
  const currentCapHit = Number(player.capHit || 0);
  const approxBase = Math.max(0, currentCapHit - bonusPerYear);

  let convertAmount = Math.min(approxBase, Math.round(Math.max(0, approxBase * 0.3))); // default ~30% of base
  if (!Number.isFinite(convertAmount) || convertAmount <= 0) convertAmount = Math.min(approxBase, 5000000);
  if (!Number.isFinite(convertAmount)) convertAmount = 0;
  let yearsRemaining = maxYears;

  const root = document.getElementById('modals-root') || document.body;
  const dlg = document.createElement('dialog');
  dlg.setAttribute('data-testid', 'modal-conversion');
  dlg.innerHTML = `
    <h3 style="margin-top:0">Convert Contract — ${name}</h3>
    <div class="grid" style="display:grid; grid-template-columns: 1fr 1fr; gap:.75rem; align-items:center;">
      <label>Convert Amount
        <input id="conv-amount" type="number" min="0" step="50000" value="${convertAmount}" style="width:100%" />
      </label>
      <div style="text-align:right; color:var(--muted)">${fmtMoney(convertAmount)} (max ~ ${fmtMoney(approxBase)})</div>

      <label>Proration Years
        <input id="conv-years" type="range" min="1" max="${maxYears}" step="1" value="${yearsRemaining}" style="width:100%" />
      </label>
      <div id="conv-years-val" style="text-align:right; color:var(--muted)">${yearsRemaining} year(s)</div>
    </div>

    <div style="margin-top:.75rem; display:grid; grid-template-columns: 1fr 1fr; gap:.5rem;">
      <div>
        <div style="color:var(--muted); font-size:.85em">Current Cap Hit</div>
        <div id="conv-old-cap" data-testid="conv-old-cap">${fmtMoney(currentCapHit)}</div>
      </div>
      <div>
        <div style="color:var(--muted); font-size:.85em">New Current-Year Cap Hit</div>
        <div id="conv-new-cap" class="money-warn" data-testid="conv-new-cap">$0</div>
      </div>
      <div>
        <div style="color:var(--muted); font-size:.85em">Cap Impact (This Year)</div>
        <div id="conv-delta" class="" data-testid="conv-delta">$0</div>
      </div>
      <div>
        <div style="color:var(--muted); font-size:.85em">Remaining Cap After</div>
        <div id="conv-remaining" class="" data-testid="conv-remaining">$0</div>
      </div>
    </div>

    <div style="margin-top:.5rem; border-top:1px solid #1f2937; padding-top:.5rem;">
      <div style="color:var(--muted); font-size:.85em; margin-bottom:.25rem">Future Years Increase (each)</div>
      <div id="conv-future" style="display:flex; gap:.5rem; flex-wrap:wrap;"></div>
    </div>

    <div id="conv-note" style="margin-top:.25rem; font-size:.85em; color: var(--yellow); display:none;">Note: Convert amount reduced to available base salary.</div>

    <div class="modal-actions">
      <button class="btn" data-action="cancel" data-testid="cancel-conversion">Cancel</button>
      <button class="btn primary" data-action="confirm" data-testid="confirm-conversion">Apply Conversion</button>
    </div>
  `;

  const amountEl = /** @type {HTMLInputElement} */(dlg.querySelector('#conv-amount'));
  const yearsEl = /** @type {HTMLInputElement} */(dlg.querySelector('#conv-years'));
  const yearsValEl = dlg.querySelector('#conv-years-val');
  const oldCapEl = dlg.querySelector('#conv-old-cap');
  const newCapEl = dlg.querySelector('#conv-new-cap');
  const deltaEl = dlg.querySelector('#conv-delta');
  const remainingEl = dlg.querySelector('#conv-remaining');
  const futureEl = dlg.querySelector('#conv-future');
  const noteEl = dlg.querySelector('#conv-note');

  function getInputs() {
    let amt = Math.max(0, toNum(amountEl.value));
    const yrs = Math.max(1, Math.min(maxYears, Math.floor(toNum(yearsEl.value) || yearsRemaining)));
    // Cap to approx base salary
    if (amt > approxBase) amt = approxBase;
    return { convertAmount: amt, yearsRemaining: yrs };
  }

  function recalcPreview() {
    const snap = getCapSummary();
    const inp = getInputs();
    if (yearsValEl) yearsValEl.textContent = `${inp.yearsRemaining} year(s)`;
    const sim = simulateConversion(player, inp);
    const delta = sim.capHitDelta; // negative saves cap this year
    const baseCap = Number.isFinite(Number(snap.capAvailableEffective)) ? Number(snap.capAvailableEffective) : (snap.capAvailable || 0);
    const remaining = baseCap - delta; // subtract negative = add cap space

    if (newCapEl) newCapEl.textContent = fmtMoney(sim.newCurrentYearCapHit);
    if (deltaEl) deltaEl.textContent = `${delta >= 0 ? '+' : ''}${fmtMoney(delta)}`;
    if (remainingEl) remainingEl.textContent = fmtMoney(remaining);
    if (oldCapEl) oldCapEl.textContent = fmtMoney(currentCapHit);

    // Color coding
    newCapEl.className = delta < 0 ? 'money-pos' : (delta > 0 ? 'money-neg' : '');
    deltaEl.className = delta < 0 ? 'money-pos' : (delta > 0 ? 'money-neg' : '');
    remainingEl.className = remaining >= 0 ? 'money-pos' : 'money-neg';

    // Future view
    if (futureEl) {
      futureEl.innerHTML = '';
      if (sim.futureYears && sim.futureYears.length) {
        sim.futureYears.forEach((inc, i) => {
          const chip = document.createElement('div');
          chip.className = 'badge';
          const yr = (Number.isFinite(baseYear) && baseYear > 0) ? String(baseYear + (i + 1)) : `Year +${i + 1}`;
          chip.textContent = `${yr}: +${fmtMoney(inc)}`;
          futureEl.appendChild(chip);
        });
      } else {
        const chip = document.createElement('div');
        chip.className = 'badge';
        chip.textContent = 'No future increase';
        futureEl.appendChild(chip);
      }
    }

    // Note if amount clamped
    if (noteEl) noteEl.style.display = (toNum(amountEl.value) > approxBase) ? 'block' : 'none';

    return { sim, remaining };
  }

  function close() {
    try { dlg.close(); } catch {}
    dlg.remove();
  }

  dlg.addEventListener('input', () => recalcPreview());
  dlg.addEventListener('click', (e) => {
    const r = dlg.getBoundingClientRect();
    if (e.target === dlg && (e.clientX < r.left || e.clientX > r.right || e.clientY < r.top || e.clientY > r.bottom)) {
      close();
    }
  });

  dlg.querySelector('[data-action="cancel"]')?.addEventListener('click', close);
  dlg.querySelector('[data-action="confirm"]')?.addEventListener('click', () => {
    const { sim, remaining } = recalcPreview();
    // If nothing to convert, do nothing
    if (!sim || !Number.isFinite(sim.capHitDelta)) return;

    const current = getState();
    const moves = [...current.moves, sim.move];
    const players = current.players.map((pl) => {
      if (pl.id !== player.id) return pl;
      return {
        ...pl,
        capHit: sim.newCurrentYearCapHit,
      };
    });
    setState({ moves, players });

    try {
      const afterSnap = getCapSummary();
      const afterCap = Number.isFinite(Number(afterSnap.capAvailableEffective)) ? Number(afterSnap.capAvailableEffective) : (afterSnap.capAvailable || 0);
      console.assert(Math.round(afterCap) === Math.round(remaining), '[convert] capAvailable matches preview');
    } catch {}

    close();
  });

  root.appendChild(dlg);
  enhanceDialog(dlg, { opener: document.activeElement });
  try { dlg.showModal(); } catch { dlg.show(); }
  // Initial preview
  recalcPreview();
}

export default { openConversionModal };
