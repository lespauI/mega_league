import { enhanceDialog } from '../a11y.js';
import { getCustomContract, setCustomContract, resetCustomContract, setState } from '../../state.js';
import { computeDefaultDistribution } from '../../contractUtils.js';
import { formatMillions, toAbsoluteDollarsFromMillions } from '../../format.js';

/**
 * Open a side-drawer style contract distribution editor for a player.
 * Renders a column per contract year with Salary/Bonus inputs (millions).
 * Note: This step renders UI only; save/reset wiring is added in later steps.
 * @param {import('../../models.js').Player} player
 */
export function openContractEditor(player) {
  if (!player) return;

  const name = `${player.firstName || ''} ${player.lastName || ''}`.trim();

  // Build values map: prefer custom (if present), otherwise default 50/50
  /** @type {Record<number, { salary: number, bonus: number }>} */
  const defaults = computeDefaultDistribution(player) || {};
  /** @type {Record<number, { salary: number, bonus: number }>|null} */
  const custom = getCustomContract(player.id);
  /** @type {Record<number, { salary: number, bonus: number }>} */
  const values = { ...defaults };
  if (custom) {
    for (const y of Object.keys(custom)) {
      const yr = Number(y);
      const v = custom[yr] || { salary: 0, bonus: 0 };
      values[yr] = { salary: Number(v.salary || 0) || 0, bonus: Number(v.bonus || 0) || 0 };
    }
  }

  const years = Object.keys(values).map(Number).sort((a, b) => a - b);
  // Keep a mutable copy for in-dialog edits (absolute dollars)
  /** @type {Record<number, { salary: number, bonus: number }>} */
  const current = {};
  for (const yr of years) {
    current[yr] = {
      salary: Number(values[yr]?.salary || 0) || 0,
      bonus: Number(values[yr]?.bonus || 0) || 0,
    };
  }

  const root = document.getElementById('modals-root') || document.body;
  const dlg = document.createElement('dialog');
  dlg.setAttribute('data-testid', 'contract-editor');
  // Scoped class so CSS can style this drawer without affecting others
  dlg.classList.add('drawer', 'contract-editor');

  const headerHtml = `
    <div class="drawer__header">
      <div class="drawer__titlewrap">
        <h3 data-dialog-title>Contract Distribution — ${name}</h3>
        <div class="drawer__subtitle">Enter values in millions (e.g., 22.7 = $22.7M)</div>
      </div>
      <div class="drawer__actions">
        <button class="btn primary" data-testid="ce-save" data-action="save" title="Apply changes to projections">Save</button>
        <button class="btn" data-testid="ce-reset" data-action="reset" title="Restore default 50/50">Reset</button>
        <button class="btn" data-testid="ce-close" data-action="close">Close</button>
      </div>
    </div>
  `;

  const colsHtml = years.length
    ? years.map((yr) => {
        const sAbs = Number(values[yr]?.salary || 0) || 0;
        const bAbs = Number(values[yr]?.bonus || 0) || 0;
        const sM = (sAbs / 1_000_000).toFixed(1);
        const bM = (bAbs / 1_000_000).toFixed(1);
        return `
          <div class="ce-col">
            <div data-testid="ce-year">${yr}</div>
            <label class="field">
              <span class="field__label">Salary (M)</span>
              <input
                type="number"
                step="0.1"
                min="0"
                inputmode="decimal"
                aria-label="Salary in ${yr} (millions)"
                value="${sM}"
                data-testid="ce-input-salary"
                data-year="${yr}"
              />
              <div data-testid="ce-prev-salary" data-year="${yr}">${formatMillions(sAbs)}</div>
            </label>
            <label class="field">
              <span class="field__label">Bonus (M)</span>
              <input
                type="number"
                step="0.1"
                min="0"
                inputmode="decimal"
                aria-label="Bonus in ${yr} (millions)"
                value="${bM}"
                data-testid="ce-input-bonus"
                data-year="${yr}"
              />
              <div data-testid="ce-prev-bonus" data-year="${yr}">${formatMillions(bAbs)}</div>
            </label>
          </div>
        `;
      }).join('')
    : `<div class="muted">No remaining contract years.</div>`;

  const gridHtml = `
    <div class="ce-grid">
      ${colsHtml}
    </div>
  `;

  dlg.innerHTML = headerHtml + gridHtml;

  // Helper to persist changes and update previews
  const persistAndRender = (yr, kind, millionsValue) => {
    const abs = Math.max(0, toAbsoluteDollarsFromMillions(millionsValue));
    if (!current[yr]) current[yr] = { salary: 0, bonus: 0 };
    current[yr][kind] = abs;
    // Persist player's custom map (session-only) and notify subscribers
    try {
      setCustomContract(String(player.id), current);
      // Trigger projections / cap summary recompute immediately
      setState({});
    } catch {}
    // Update preview
    const sel = kind === 'salary' ? `[data-testid="ce-prev-salary"][data-year="${yr}"]` : `[data-testid="ce-prev-bonus"][data-year="${yr}"]`;
    const el = dlg.querySelector(sel);
    if (el) el.textContent = formatMillions(abs);
  };

  // Click outside content to close
  dlg.addEventListener('click', (e) => {
    const r = dlg.getBoundingClientRect();
    if (e.target === dlg && (e.clientX < r.left || e.clientX > r.right || e.clientY < r.top || e.clientY > r.bottom)) {
      try { dlg.close(); } catch {}
      dlg.remove();
    }
  });

  dlg.querySelector('[data-action="close"]')?.addEventListener('click', () => {
    try { dlg.close(); } catch {}
    dlg.remove();
  });

  // Save: persist current map and trigger global recompute, then close
  dlg.querySelector('[data-action="save"]')?.addEventListener('click', (e) => {
    e.preventDefault();
    try { setCustomContract(String(player.id), current); } catch {}
    try { setState({}); } catch {}
    try { dlg.close(); } catch {}
    dlg.remove();
  });

  // Reset to default 50/50 split and clear custom map
  dlg.querySelector('[data-action="reset"]')?.addEventListener('click', (e) => {
    e.preventDefault();
    try { resetCustomContract(String(player.id)); } catch {}
    // Recompute defaults and update the in-dialog state and inputs/previews
    const def = computeDefaultDistribution(player) || {};
    for (const yr of years) {
      const sAbs = Number(def[yr]?.salary || 0) || 0;
      const bAbs = Number(def[yr]?.bonus || 0) || 0;
      current[yr] = { salary: sAbs, bonus: bAbs };
      // Update input fields (millions)
      const sInp = dlg.querySelector(`input[data-testid="ce-input-salary"][data-year="${yr}"]`);
      const bInp = dlg.querySelector(`input[data-testid="ce-input-bonus"][data-year="${yr}"]`);
      if (sInp) sInp.value = (sAbs / 1_000_000).toFixed(1);
      if (bInp) bInp.value = (bAbs / 1_000_000).toFixed(1);
      // Update previews
      const sPrev = dlg.querySelector(`[data-testid="ce-prev-salary"][data-year="${yr}"]`);
      const bPrev = dlg.querySelector(`[data-testid="ce-prev-bonus"][data-year="${yr}"]`);
      if (sPrev) sPrev.textContent = formatMillions(sAbs);
      if (bPrev) bPrev.textContent = formatMillions(bAbs);
    }
    // Notify subscribers so projections/cap views recompute on reset
    try { setState({}); } catch {}
  });

  // Wire inputs to auto-save on input/change
  dlg.querySelectorAll('[data-testid="ce-input-salary"]').forEach((inp) => {
    const yr = Number(inp.getAttribute('data-year'));
    const handler = (e) => {
      const v = /** @type {HTMLInputElement} */(e.currentTarget).value;
      persistAndRender(yr, 'salary', v);
    };
    inp.addEventListener('input', handler);
    inp.addEventListener('change', handler);
  });
  dlg.querySelectorAll('[data-testid="ce-input-bonus"]').forEach((inp) => {
    const yr = Number(inp.getAttribute('data-year'));
    const handler = (e) => {
      const v = /** @type {HTMLInputElement} */(e.currentTarget).value;
      persistAndRender(yr, 'bonus', v);
    };
    inp.addEventListener('input', handler);
    inp.addEventListener('change', handler);
  });

  root.appendChild(dlg);
  enhanceDialog(/** @type {HTMLDialogElement} */(dlg), { opener: document.activeElement });
  try { dlg.showModal(); } catch { dlg.show(); }
}

export default { openContractEditor };
