import { getState, saveScenario, listScenarios, loadScenario, resetScenario, getScenarioEdits } from '../state.js';
import { openScenarioSaveModal, openScenarioLoadModal, openScenarioCompareModal } from './modals/scenarioModals.js';
import { openTradeInModal } from './modals/tradeInModal.js';
import { confirmWithDialog } from './modals/confirmDialog.js';

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
  btnSave.setAttribute('data-testid', 'btn-scn-save');
  btnSave.title = hasChanges ? '' : 'No changes to save';
  btnSave.disabled = !hasChanges;
  btnSave.addEventListener('click', () => openScenarioSaveModal());

  const btnLoad = document.createElement('button');
  btnLoad.className = 'btn';
  btnLoad.textContent = `Load (${saved.length})`;
  btnLoad.setAttribute('data-testid', 'btn-scn-load');
  btnLoad.title = saved.length ? '' : 'No saved scenarios for this team';
  btnLoad.disabled = saved.length === 0;
  btnLoad.addEventListener('click', () => openScenarioLoadModal());

  const btnReset = document.createElement('button');
  btnReset.className = 'btn danger';
  btnReset.textContent = 'Reset';
  btnReset.setAttribute('data-testid', 'btn-scn-reset');
  btnReset.title = hasChanges ? 'Reset to baseline roster' : 'Nothing to reset';
  btnReset.disabled = !hasChanges;
  btnReset.addEventListener('click', async () => {
    if (!hasChanges) return;
    const rememberKey = `rosterCap.skipConfirm.resetScenario.${teamAbbr}`;
    const ok = await confirmWithDialog({
      title: 'Reset Scenario?',
      message: 'This clears all moves and roster edits.',
      confirmText: 'Reset',
      cancelText: 'Cancel',
      danger: true,
      rememberKey,
      rememberLabel: "Don't ask again for this team",
    });
    if (ok) resetScenario();
  });

  const btnCompare = document.createElement('button');
  btnCompare.className = 'btn primary';
  btnCompare.textContent = 'Compare';
  btnCompare.setAttribute('data-testid', 'btn-scn-compare');
  btnCompare.addEventListener('click', () => openScenarioCompareModal());

  const btnTradeIn = document.createElement('button');
  btnTradeIn.className = 'btn';
  btnTradeIn.textContent = 'Trade In';
  btnTradeIn.title = 'Acquire a player from another roster';
  btnTradeIn.setAttribute('data-testid', 'btn-trade-in');
  btnTradeIn.addEventListener('click', () => openTradeInModal());

  const chip = document.createElement('span');
  chip.className = 'badge';
  chip.title = 'Edits / Moves in current scenario';
  chip.textContent = `${editCount} edits, ${moveCount} moves`;

  wrap.append(btnSave, btnLoad, btnReset, btnCompare, btnTradeIn, chip);
  el.appendChild(wrap);
}

export default { mountScenarioControls };
