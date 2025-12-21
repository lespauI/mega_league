import {
  OFFENSE_SLOT_IDS,
  DEFENSE_SLOT_IDS,
  SPECIAL_SLOT_IDS,
  getOvr,
  getSlotSide,
} from './slots.js';
import { formatName, getContractSummary } from './ui/playerFormatting.js';

const OFFENSE_SET = new Set(OFFENSE_SLOT_IDS);
const DEFENSE_SET = new Set(DEFENSE_SLOT_IDS);
const SPECIAL_SET = new Set(SPECIAL_SLOT_IDS);

function getSlotOrderWeight(slotId) {
  if (OFFENSE_SET.has(slotId)) return 0;
  if (DEFENSE_SET.has(slotId)) return 1;
  if (SPECIAL_SET.has(slotId)) return 2;
  return 3;
}

function sortSlotIds(slotIds) {
  const allOrder = [...OFFENSE_SLOT_IDS, ...DEFENSE_SLOT_IDS, ...SPECIAL_SLOT_IDS];
  return slotIds.slice().sort((a, b) => {
    const sideDiff = getSlotOrderWeight(a) - getSlotOrderWeight(b);
    if (sideDiff !== 0) return sideDiff;
    const ia = allOrder.indexOf(a);
    const ib = allOrder.indexOf(b);
    if (ia !== -1 && ib !== -1 && ia !== ib) return ia - ib;
    return a.localeCompare(b);
  });
}

function escapeCsvValue(value) {
  if (value === null || value === undefined) return '';
  const str = String(value);
  if (str.includes('"') || str.includes(',') || str.includes('\n') || str.includes('\r')) {
    return `"${str.replace(/"/g, '""')}"`;
  }
  return str;
}

function getAcquisitionLabelForCsv(acquisition) {
  switch (acquisition) {
    case 'existing':
      return 'Existing';
    case 'faPlayer':
      return 'FA Player';
    case 'draftR1':
      return 'Draft R1';
    case 'draftR2':
      return 'Draft R2';
    case 'draftR3':
      return 'Draft R3';
    case 'draftR4':
      return 'Draft R4';
    case 'draftR5':
      return 'Draft R5';
    case 'draftR6':
      return 'Draft R6';
    case 'draftR7':
      return 'Draft R7';
    case 'trade':
      return 'Trade';
    case 'faPlaceholder':
      return 'FA Placeholder';
    default:
      return '';
  }
}

export function buildDepthCsvForTeam(teamAbbr, depthPlan, playersById) {
  if (!teamAbbr || !depthPlan || !depthPlan.slots) return '';

  const header = [
    'team',
    'side',
    'positionSlot',
    'depth',
    'playerName',
    'acquisition',
    'ovr',
    'contractLength',
    'contractYearsLeft',
    'faAfterSeason',
  ].join(',');

  const rows = [header];
  const slots = depthPlan.slots || {};
  const playersMap = playersById || {};

  const slotIds = sortSlotIds(Object.keys(slots));

  for (const slotId of slotIds) {
    const side = getSlotSide(slotId);
    const assignments = Array.isArray(slots[slotId]) ? slots[slotId].filter(Boolean) : [];
    if (!assignments.length) continue;

    assignments.sort((a, b) => {
      const da = a && typeof a.depthIndex === 'number' ? a.depthIndex : 0;
      const db = b && typeof b.depthIndex === 'number' ? b.depthIndex : 0;
      return da - db;
    });

    for (const assignment of assignments) {
      if (!assignment) continue;

      const depth = assignment.depthIndex || '';
      const acqLabel = getAcquisitionLabelForCsv(assignment.acquisition);

      let playerName = '';
      let ovr = '';
      let contractLength = '';
      let contractYearsLeft = '';
      let faAfterSeason = '';

      const player =
        assignment.playerId && playersMap[assignment.playerId]
          ? playersMap[assignment.playerId]
          : null;

      if (player) {
        playerName = formatName(player);
        ovr = String(getOvr(player));
        const { isFaAfterSeason } = getContractSummary(player);
        contractLength =
          player.contractLength !== undefined && player.contractLength !== null
            ? String(player.contractLength)
            : '';
        contractYearsLeft =
          player.contractYearsLeft !== undefined && player.contractYearsLeft !== null
            ? String(player.contractYearsLeft)
            : '';
        faAfterSeason = isFaAfterSeason ? 'true' : 'false';
      } else if (assignment.placeholder) {
        playerName = assignment.placeholder;
      }

      const row = [
        teamAbbr,
        side,
        slotId,
        depth,
        playerName,
        acqLabel,
        ovr,
        contractLength,
        contractYearsLeft,
        faAfterSeason,
      ]
        .map(escapeCsvValue)
        .join(',');

      rows.push(row);
    }
  }

  return rows.join('\n');
}

export function downloadCsv(filename, csvText) {
  if (!csvText) return;

  try {
    const blob = new Blob([csvText], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = filename || 'depth-plan.csv';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  } catch {
    // Best-effort only; if this fails, we silently ignore.
  }
}
