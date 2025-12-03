import { enhanceDialog } from '../a11y.js';
import { getCustomContract, setCustomContract, resetCustomContract } from '../../state.js';
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
  dlg.classList.add('drawer');

  const headerHtml = `
    <h3 style="margin:0" data-dialog-title>Contract Distribution — ${name}</h3>
    <div style="color:var(--muted); font-size:.875rem; margin:.25rem 0 .75rem">Enter values in millions (e.g., 22.7 = $22.7M)</div>
  `;

  const colsHtml = years.length
    ? years.map((yr) => {
        const sAbs = Number(values[yr]?.salary || 0) || 0;
        const bAbs = Number(values[yr]?.bonus || 0) || 0;
        const sM = (sAbs / 1_000_000).toFixed(1);
        const bM = (bAbs / 1_000_000).toFixed(1);
        return `
          <div class="ce-col" style="display:grid; gap:.375rem; min-width: 140px;">
            <div data-testid="ce-year" style="font-weight:600; text-align:center;">${yr}</div>
            <label style="display:grid; gap:.25rem;">
              <span style="color:var(--muted); font-size:.85em;">Salary (M)</span>
              <input
                type="number"
                step="0.1"
                min="0"
                inputmode="decimal"
                aria-label="Salary in ${yr} (millions)"
                value="${sM}"
                data-testid="ce-input-salary"
                data-year="${yr}"
                style="background:#0b1324;color:var(--text);border:1px solid #334155;border-radius:.375rem;padding:.375rem .5rem;"
              />
              <div data-testid="ce-prev-salary" data-year="${yr}" style="color:var(--muted); font-size:.8em; text-align:right;">${formatMillions(sAbs)}</div>
            </label>
            <label style="display:grid; gap:.25rem;">
              <span style="color:var(--muted); font-size:.85em;">Bonus (M)</span>
              <input
                type="number"
                step="0.1"
                min="0"
                inputmode="decimal"
                aria-label="Bonus in ${yr} (millions)"
                value="${bM}"
                data-testid="ce-input-bonus"
                data-year="${yr}"
                style="background:#0b1324;color:var(--text);border:1px solid #334155;border-radius:.375rem;padding:.375rem .5rem;"
              />
              <div data-testid="ce-prev-bonus" data-year="${yr}" style="color:var(--muted); font-size:.8em; text-align:right;">${formatMillions(bAbs)}</div>
            </label>
          </div>
        `;
      }).join('')
    : `<div style="color:var(--muted);">No remaining contract years.</div>`;

  const gridHtml = `
    <div class="ce-grid" style="display:grid; grid-auto-flow: column; gap:.75rem; overflow:auto; padding-bottom:.25rem;">
      ${colsHtml}
    </div>
  `;

  const actionsHtml = `
    <div class="modal-actions">
      <button class="btn" data-testid="ce-reset" data-action="reset">Reset</button>
      <button class="btn" data-testid="ce-close" data-action="close">Close</button>
    </div>
  `;

  dlg.innerHTML = headerHtml + gridHtml + actionsHtml;

  // Helper to persist changes and update previews
  const persistAndRender = (yr, kind, millionsValue) => {
    const abs = Math.max(0, toAbsoluteDollarsFromMillions(millionsValue));
    if (!current[yr]) current[yr] = { salary: 0, bonus: 0 };
    current[yr][kind] = abs;
    // Persist player's custom map (session-only)
    try { setCustomContract(String(player.id), current); } catch {}
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
