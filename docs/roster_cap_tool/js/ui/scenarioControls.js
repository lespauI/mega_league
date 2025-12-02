import { getState, saveScenario, listScenarios, loadScenario, resetScenario, getScenarioEdits } from '../state.js';
import { openScenarioSaveModal, openScenarioLoadModal, openScenarioCompareModal } from './modals/scenarioModals.js';

/**
 * Mount Scenario controls (Save, Load, Reset, Compare) into header.
 * @param {string} containerId
 */
export function mountScenarioControls(containerId = 'scenario-controls') {
  const el = document.getElementById(containerId);
  if (!el) return;
  const st = getState();
  const team = st.teams.find((t) => t.abbrName === st.selectedTeam);
  const teamAbbr = team?.abbrName || '';
  const saved = listScenarios(teamAbbr);
  const edits = getScenarioEdits();
  const moveCount = (st.moves || []).length;
  const editCount = (edits || []).length;
  const hasChanges = moveCount > 0 || editCount > 0;

  el.innerHTML = '';
  const wrap = document.createElement('div');
  wrap.style.display = 'flex';
  wrap.style.alignItems = 'center';
  wrap.style.gap = '.5rem';

  const btnSave = document.createElement('button');
  btnSave.className = 'btn';
  btnSave.textContent = 'Save';
  btnSave.title = hasChanges ? '' : 'No changes to save';
  btnSave.disabled = !hasChanges;
  btnSave.addEventListener('click', () => openScenarioSaveModal());

  const btnLoad = document.createElement('button');
  btnLoad.className = 'btn';
  btnLoad.textContent = `Load (${saved.length})`;
  btnLoad.title = saved.length ? '' : 'No saved scenarios for this team';
  btnLoad.disabled = saved.length === 0;
  btnLoad.addEventListener('click', () => openScenarioLoadModal());

  const btnReset = document.createElement('button');
  btnReset.className = 'btn danger';
  btnReset.textContent = 'Reset';
  btnReset.title = hasChanges ? 'Reset to baseline roster' : 'Nothing to reset';
  btnReset.disabled = !hasChanges;
  btnReset.addEventListener('click', () => {
    if (!hasChanges) return;
    const ok = window.confirm('Reset scenario to baseline? This clears all moves.');
    if (ok) resetScenario();
  });

  const btnCompare = document.createElement('button');
  btnCompare.className = 'btn primary';
  btnCompare.textContent = 'Compare';
  btnCompare.addEventListener('click', () => openScenarioCompareModal());

  const chip = document.createElement('span');
  chip.className = 'badge';
  chip.title = 'Edits / Moves in current scenario';
  chip.textContent = `${editCount} edits, ${moveCount} moves`;

  wrap.append(btnSave, btnLoad, btnReset, btnCompare, chip);
  el.appendChild(wrap);
}

export default { mountScenarioControls };

