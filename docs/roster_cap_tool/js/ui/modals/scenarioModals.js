import { getState, setState, saveScenario, listScenarios, loadScenario, deleteScenario } from '../../state.js';
import { calcCapSummary } from '../../capMath.js';
import { enhanceDialog } from '../a11y.js';

function fmtMoney(n) {
  return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 }).format(n || 0);
}

function closeAndRemove(dlg) {
  try { dlg.close(); } catch {}
  dlg.remove();
}

export function openScenarioSaveModal() {
  const st = getState();
  const team = st.teams.find((t) => t.abbrName === st.selectedTeam);
  const defaultName = `${team?.abbrName || 'TEAM'} Scenario ${new Date().toLocaleString()}`;

  const root = document.getElementById('modals-root') || document.body;
  const dlg = document.createElement('dialog');
  dlg.setAttribute('data-testid', 'modal-scn-save');
  dlg.innerHTML = `
    <h3 style="margin-top:0">Save Scenario</h3>
    <label style="display:block; margin:.25rem 0 .75rem;">
      Name
      <input id="scn-name" type="text" value="${defaultName}" style="width:100%; background:#0b1324; color:inherit; border:1px solid #334155; padding:.5rem; border-radius:.375rem;" />
    </label>
    <div class="modal-actions">
      <button class="btn" data-action="cancel" data-testid="cancel-scn-save">Cancel</button>
      <button class="btn primary" data-action="confirm" data-testid="confirm-scn-save">Save</button>
    </div>
  `;
  const nameEl = /** @type {HTMLInputElement} */(dlg.querySelector('#scn-name'));
  dlg.querySelector('[data-action="cancel"]')?.addEventListener('click', () => closeAndRemove(dlg));
  dlg.querySelector('[data-action="confirm"]')?.addEventListener('click', () => {
    saveScenario(nameEl?.value || 'Untitled Scenario');
    // Trigger re-render for controls
    setState({});
    closeAndRemove(dlg);
  });
  root.appendChild(dlg);
  enhanceDialog(dlg, { opener: document.activeElement });
  try { dlg.showModal(); } catch { dlg.show(); }
}

export function openScenarioLoadModal() {
  const st = getState();
  const teamAbbr = st.selectedTeam || '';
  let scenarios = listScenarios(teamAbbr);

  const root = document.getElementById('modals-root') || document.body;
  const dlg = document.createElement('dialog');
  dlg.setAttribute('data-testid', 'modal-scn-load');
  const renderList = () => {
    const rows = scenarios.map((s) => {
      const when = new Date(s.savedAt);
      const whenStr = isFinite(when.getTime()) ? when.toLocaleString() : '';
      const meta = `${s.rosterEdits?.length || 0} edits, ${s.moves?.length || 0} moves`;
      return `<tr>
        <td>${s.name}</td>
        <td>${whenStr}</td>
        <td>${meta}</td>
        <td style="text-align:right">
          <button class="btn primary" data-action="load" data-id="${s.id}" data-testid="scn-load-item">Load</button>
          <button class="btn danger" data-action="delete" data-id="${s.id}" data-testid="scn-delete-item">Delete</button>
        </td>
      </tr>`;
    }).join('');
    return rows || `<tr><td colspan="4">No saved scenarios for ${teamAbbr}.</td></tr>`;
  };

  dlg.innerHTML = `
    <h3 style="margin-top:0">Load Scenario — ${teamAbbr}</h3>
    <div class="table-container">
      <table>
        <thead><tr><th>Name</th><th>Saved</th><th>Summary</th><th></th></tr></thead>
        <tbody id="scn-list">${renderList()}</tbody>
      </table>
    </div>
    <div class="modal-actions">
      <button class="btn" data-action="close" data-testid="close-scn-load">Close</button>
    </div>
  `;

  dlg.addEventListener('click', (e) => {
    const btn = /** @type {HTMLElement} */(e.target.closest('button'));
    if (!btn) return;
    const act = btn.getAttribute('data-action');
    const id = btn.getAttribute('data-id');
    if (act === 'close') {
      closeAndRemove(dlg);
    } else if (act === 'load' && id) {
      loadScenario(id);
      closeAndRemove(dlg);
    } else if (act === 'delete' && id) {
      const ok = window.confirm('Delete this saved scenario?');
      if (!ok) return;
      deleteScenario(id);
      scenarios = listScenarios(teamAbbr);
      const body = dlg.querySelector('#scn-list');
      if (body) body.innerHTML = renderList();
    }
  });

  const rootEl = document.getElementById('modals-root') || document.body;
  rootEl.appendChild(dlg);
  enhanceDialog(dlg, { opener: document.activeElement });
  try { dlg.showModal(); } catch { dlg.show(); }
}

export function openScenarioCompareModal() {
  const st = getState();
  const team = st.teams.find((t) => t.abbrName === st.selectedTeam);
  if (!team) return;
  const snapCurrent = /** @type {import('../../models.js').CapSnapshot} */(st ? null : null); // type hint only
  const current = {
    room: st ? (st.snapshot?.capRoom ?? team.capRoom) : team.capRoom,
  };
  // Baseline = team with no moves
  const baseline = calcCapSummary(team, []);
  // Current from selector
  const now = (function(){
    // getCapSummary not imported here; emulate by reusing current state through capMath with moves
    // but we don't need to recompute: mount cap summary updates. For isolation, compute here:
    return calcCapSummary(team, st.moves || []);
  })();

  const deltaAvail = (now.capAvailable || 0) - (baseline.capAvailable || 0);
  const deltaSpent = (now.capSpent || 0) - (baseline.capSpent || 0);

  const dlg = document.createElement('dialog');
  dlg.setAttribute('data-testid', 'modal-scn-compare');
  dlg.innerHTML = `
    <h3 style="margin-top:0">Scenario Compare — ${team.abbrName}</h3>
    <div style="display:grid; grid-template-columns: 1fr 1fr; gap: 1rem;">
      <div>
        <div style="color:var(--muted); font-size:.85em">Baseline Cap Space</div>
        <div>${fmtMoney(baseline.capAvailable || 0)}</div>
        <div style="color:var(--muted); font-size:.85em; margin-top:.5rem">Baseline Spent</div>
        <div>${fmtMoney(baseline.capSpent || 0)}</div>
      </div>
      <div>
        <div style="color:var(--muted); font-size:.85em">Current Cap Space</div>
        <div>${fmtMoney(now.capAvailable || 0)}</div>
        <div style="color:var(--muted); font-size:.85em; margin-top:.5rem">Current Spent</div>
        <div>${fmtMoney(now.capSpent || 0)}</div>
      </div>
    </div>
    <div style="margin-top:.75rem; display:grid; grid-template-columns: 1fr 1fr; gap:1rem;">
      <div>
        <div style="color:var(--muted); font-size:.85em">Cap Space Delta</div>
        <div class="${deltaAvail >= 0 ? 'money-pos' : 'money-neg'}">${deltaAvail >= 0 ? '+' : ''}${fmtMoney(deltaAvail)}</div>
      </div>
      <div>
        <div style="color:var(--muted); font-size:.85em">Spent Delta</div>
        <div class="${deltaSpent <= 0 ? 'money-pos' : 'money-neg'}">${deltaSpent >= 0 ? '+' : ''}${fmtMoney(deltaSpent)}</div>
      </div>
    </div>
    <div class="modal-actions">
      <button class="btn" data-action="close" data-testid="close-scn-compare">Close</button>
    </div>
  `;
  dlg.querySelector('[data-action="close"]')?.addEventListener('click', () => closeAndRemove(dlg));
  const root = document.getElementById('modals-root') || document.body;
  root.appendChild(dlg);
  enhanceDialog(dlg, { opener: document.activeElement });
  try { dlg.showModal(); } catch { dlg.show(); }
}

export default { openScenarioSaveModal, openScenarioLoadModal, openScenarioCompareModal };
