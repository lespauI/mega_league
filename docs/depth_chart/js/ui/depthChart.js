import {
  getDepthPlanForSelectedTeam,
  getState,
  reorderDepthSlot,
  resetTeamRosterAndPlan,
} from '../state.js';
import {
  DEPTH_CHART_SLOTS,
  OFFENSE_SLOT_IDS,
  DEFENSE_SLOT_IDS,
  SPECIAL_SLOT_IDS,
  getOvr,
} from '../slots.js';
import { formatName, getContractSummary } from './playerFormatting.js';
import { openSlotEditor } from './slotEditor.js';
import { buildDepthCsvForTeam, downloadCsv } from '../csvExport.js';

const OFFENSE_SLOTS = OFFENSE_SLOT_IDS;
const DEFENSE_SLOTS = DEFENSE_SLOT_IDS;
const SPECIAL_SLOTS = SPECIAL_SLOT_IDS;

function getSlotDefinition(slotId) {
  return DEPTH_CHART_SLOTS.find((s) => s.id === slotId) || null;
}

function getPositionClassForSlot(slot) {
  if (!slot) return '';
  if (slot.id === 'WR1' || slot.id === 'WR2') return 'WR';
  if (slot.id === 'EDGE1' || slot.id === 'EDGE2') return 'EDGE';
  if (slot.id === 'DT1' || slot.id === 'DT2') return 'DT';
  if (slot.id === 'CB1' || slot.id === 'CB2') return 'CB';
  if (Array.isArray(slot.positions) && slot.positions.length > 0) {
    return slot.positions[0];
  }
  return slot.id;
}

function getAcquisitionLabel(assignment) {
  if (!assignment || !assignment.acquisition) return '';
  switch (assignment.acquisition) {
    case 'existing':
      return 'Existing';
    case 'faPlayer':
      return 'FA Player';
    case 'draftR1':
      return 'Draft R1';
    case 'draftR2':
      return 'Draft R2';
    case 'trade':
      return 'Trade';
    case 'faPlaceholder':
      return 'FA';
    default:
      return '';
  }
}

function renderDepthRow(doc, slot, depthIndex, assignment, player) {
  const row = doc.createElement('button');
  row.type = 'button';
  row.className = 'depth-row';
  row.dataset.slotId = slot.id;
  row.dataset.depthIndex = String(depthIndex);

  const maxDepthForNeed = slot.max || 4;

  const contentLeft = doc.createElement('span');
  contentLeft.className = 'depth-row__name';

  const contentRight = doc.createElement('span');
  contentRight.className = 'depth-row__meta';

  const controls = doc.createElement('span');
  controls.className = 'depth-row__controls';

  const canMove = !!assignment && (assignment.playerId || assignment.placeholder);

  if (canMove) {
    const moveUp = doc.createElement('button');
    moveUp.type = 'button';
    moveUp.className = 'depth-row__btn depth-row__btn--up';
    moveUp.textContent = '↑';
    moveUp.title = 'Move up';
    moveUp.setAttribute('aria-label', 'Move up in depth order');
    moveUp.addEventListener('click', (event) => {
      event.stopPropagation();
      reorderDepthSlot({
        slotId: slot.id,
        depthIndex,
        direction: 'up',
      });
    });

    const moveDown = doc.createElement('button');
    moveDown.type = 'button';
    moveDown.className = 'depth-row__btn depth-row__btn--down';
    moveDown.textContent = '↓';
    moveDown.title = 'Move down';
    moveDown.setAttribute('aria-label', 'Move down in depth order');
    moveDown.addEventListener('click', (event) => {
      event.stopPropagation();
      reorderDepthSlot({
        slotId: slot.id,
        depthIndex,
        direction: 'down',
      });
    });

    controls.appendChild(moveUp);
    controls.appendChild(moveDown);
  }

  let ariaDetail = '';

  if (player) {
    row.classList.add('depth-row--player');

    contentLeft.classList.add('player-name');
    contentLeft.textContent = formatName(player);

    ariaDetail = `Assigned to ${formatName(player)} (OVR ${getOvr(player)})`;

    const ovrEl = doc.createElement('span');
    ovrEl.className = 'depth-row__ovr player-ovr';
    ovrEl.textContent = String(getOvr(player));
    contentRight.appendChild(ovrEl);

    const { label: contractLabel, isFaAfterSeason } = getContractSummary(player);
    if (contractLabel) {
      const contractEl = doc.createElement('span');
      contractEl.className = 'depth-row__contract';
      contractEl.textContent = contractLabel;
      contentRight.appendChild(contractEl);
    }

    const acqLabel = getAcquisitionLabel(assignment);
    if (acqLabel) {
      const badge = doc.createElement('span');
      badge.className = `badge badge--acq badge--acq-${assignment.acquisition}`;
      badge.textContent = acqLabel;
      contentRight.appendChild(badge);
    }

    if (isFaAfterSeason) {
      const faBadge = doc.createElement('span');
      faBadge.className = 'badge badge--fa-after';
      faBadge.textContent = 'FA after season';
      contentRight.appendChild(faBadge);
    }
  } else if (assignment && assignment.placeholder) {
    row.classList.add('depth-row--placeholder');
    contentLeft.textContent = assignment.placeholder;

    ariaDetail = `Placeholder ${assignment.placeholder}`;

    const acqLabel = getAcquisitionLabel(assignment);
    if (acqLabel) {
      const badge = doc.createElement('span');
      badge.className = `badge badge--acq badge--acq-${assignment.acquisition}`;
      badge.textContent = acqLabel;
      contentRight.appendChild(badge);
    }
  } else if (depthIndex <= maxDepthForNeed) {
    row.classList.add('depth-row--need');
    const empty = doc.createElement('span');
    empty.className = 'depth-row__empty';
    empty.textContent = '—';
    contentLeft.appendChild(empty);
    ariaDetail = 'Empty need slot';
  } else {
    row.classList.add('depth-row--optional');
    const empty = doc.createElement('span');
    empty.className = 'depth-row__empty';
    empty.textContent = '';
    contentLeft.appendChild(empty);
    ariaDetail = 'Empty optional slot';
  }

  const baseLabel = `${slot.label} depth ${depthIndex}`;
  row.setAttribute('aria-label', ariaDetail ? `${baseLabel}. ${ariaDetail}.` : baseLabel);

  row.appendChild(contentLeft);
  row.appendChild(contentRight);
  row.appendChild(controls);

  row.addEventListener('click', () => {
    openSlotEditor({
      slotId: slot.id,
      depthIndex,
    });
  });

  return row;
}

function renderPositionCard(doc, slotId, depthPlan, playersById) {
  const slot = getSlotDefinition(slotId);
  if (!slot) return null;

  const card = doc.createElement('div');
  card.className = `position-card slot-${slot.id}`;
  card.dataset.slotId = slot.id;

  const header = doc.createElement('div');
  header.className = 'position-card__header';

  const posLabel = doc.createElement('span');
  const posClass = getPositionClassForSlot(slot);
  posLabel.className = 'position-card__label';
  if (posClass) {
    posLabel.classList.add(`pos-${posClass}`);
  }
  posLabel.textContent = slot.label;
  header.appendChild(posLabel);

  card.appendChild(header);

  const body = doc.createElement('div');
  body.className = 'position-card__body';

  const planSlot =
    depthPlan && depthPlan.slots && Array.isArray(depthPlan.slots[slot.id])
      ? depthPlan.slots[slot.id].filter(Boolean)
      : [];

  const maxDepthRows = 4;
  for (let i = 0; i < maxDepthRows; i++) {
    const depthIndex = i + 1;
    const assignment =
      planSlot.find((a) => a && a.depthIndex === depthIndex) || planSlot[i] || null;
    const player =
      assignment && assignment.playerId && playersById[assignment.playerId]
        ? playersById[assignment.playerId]
        : null;

    const row = renderDepthRow(doc, slot, depthIndex, assignment, player);
    body.appendChild(row);
  }

  card.appendChild(body);
  return card;
}

export function mountDepthChart(containerId = 'depth-chart-grid') {
  const el = document.getElementById(containerId);
  if (!el) return;

  const container = document.getElementById('depth-chart-container');

  const depthPlan = getDepthPlanForSelectedTeam();
  const { playersById = {}, selectedTeam } = getState();
  el.innerHTML = '';

  const doc = el.ownerDocument || document;

  if (container) {
    let toolbar = container.querySelector('.depth-chart-toolbar');
    if (!toolbar) {
      toolbar = doc.createElement('div');
      toolbar.className = 'depth-chart-toolbar';

      const spacer = doc.createElement('div');
      spacer.className = 'depth-chart-toolbar__spacer';
      toolbar.appendChild(spacer);

      const actions = doc.createElement('div');
      actions.className = 'depth-chart-toolbar__actions';

      const exportBtn = doc.createElement('button');
      exportBtn.type = 'button';
      exportBtn.className = 'depth-chart-toolbar__btn';
      exportBtn.textContent = 'Export CSV';
      exportBtn.setAttribute('aria-label', 'Export current team depth plan as CSV');
      exportBtn.addEventListener('click', () => {
        const { selectedTeam: currentTeam, playersById: currentPlayersById = {} } = getState();
        const currentPlan = getDepthPlanForSelectedTeam();
        if (!currentTeam || !currentPlan) return;
        const csv = buildDepthCsvForTeam(currentTeam, currentPlan, currentPlayersById);
        if (!csv) return;
        const filename = `depth-plan-${currentTeam}.csv`;
        downloadCsv(filename, csv);
      });

      const resetBtn = doc.createElement('button');
      resetBtn.type = 'button';
      resetBtn.className = 'depth-chart-toolbar__btn depth-chart-toolbar__btn--reset';
      resetBtn.textContent = 'Reset to baseline';
      resetBtn.setAttribute(
        'aria-label',
        'Reset this team roster and depth chart to baseline'
      );
      resetBtn.addEventListener('click', () => {
        const { selectedTeam: currentTeam } = getState();
        if (!currentTeam) return;
        resetTeamRosterAndPlan(currentTeam);
      });

      actions.appendChild(resetBtn);
      actions.appendChild(exportBtn);
      toolbar.appendChild(actions);
      container.insertBefore(toolbar, container.firstChild);
    }
  }

  const layout = doc.createElement('div');
  layout.className = 'depth-layout';

  const offenseSection = doc.createElement('section');
  offenseSection.className = 'depth-side depth-side--offense';
  const offenseHeader = doc.createElement('div');
  offenseHeader.className = 'depth-side__header';
  offenseHeader.textContent = 'Offense';
  offenseSection.appendChild(offenseHeader);
  const offenseField = doc.createElement('div');
  offenseField.className = 'field field--offense';
  for (const slotId of OFFENSE_SLOTS) {
    const card = renderPositionCard(doc, slotId, depthPlan, playersById);
    if (card) offenseField.appendChild(card);
  }
  offenseSection.appendChild(offenseField);
  layout.appendChild(offenseSection);

  const defenseSection = doc.createElement('section');
  defenseSection.className = 'depth-side depth-side--defense';
  const defenseHeader = doc.createElement('div');
  defenseHeader.className = 'depth-side__header';
  defenseHeader.textContent = 'Defense';
  defenseSection.appendChild(defenseHeader);
  const defenseField = doc.createElement('div');
  defenseField.className = 'field field--defense';
  for (const slotId of DEFENSE_SLOTS) {
    const card = renderPositionCard(doc, slotId, depthPlan, playersById);
    if (card) defenseField.appendChild(card);
  }
  defenseSection.appendChild(defenseField);
  layout.appendChild(defenseSection);

  const specialSection = doc.createElement('section');
  specialSection.className = 'depth-side depth-side--special';
  const specialHeader = doc.createElement('div');
  specialHeader.className = 'depth-side__header';
  specialHeader.textContent = 'Special Teams';
  specialSection.appendChild(specialHeader);
  const specialBody = doc.createElement('div');
  specialBody.className = 'depth-side__body depth-side__body--special';
  for (const slotId of SPECIAL_SLOTS) {
    const card = renderPositionCard(doc, slotId, depthPlan, playersById);
    if (card) specialBody.appendChild(card);
  }
  specialSection.appendChild(specialBody);
  layout.appendChild(specialSection);

  el.appendChild(layout);
}
