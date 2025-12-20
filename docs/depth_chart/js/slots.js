export const OFFENSE_SLOT_IDS = ['LT', 'LG', 'C', 'RG', 'RT', 'QB', 'HB', 'FB', 'WR1', 'WR2', 'TE'];

export const DEFENSE_SLOT_IDS = [
  'FS',
  'SS',
  'CB1',
  'CB2',
  'SAM',
  'MIKE',
  'WILL',
  'DT1',
  'DT2',
  'EDGE1',
  'EDGE2',
];

export const SPECIAL_SLOT_IDS = ['K', 'P', 'LS'];

export const DEPTH_CHART_SLOTS = [
  { id: 'QB', label: 'QB', positions: ['QB'], max: 3 },
  { id: 'HB', label: 'HB', positions: ['HB', 'RB'], max: 3 },
  { id: 'FB', label: 'FB', positions: ['FB'], max: 1 },
  { id: 'WR1', label: 'WR1', positions: ['WR'], max: 4, split: 0 },
  { id: 'WR2', label: 'WR2', positions: ['WR'], max: 4, split: 1 },
  { id: 'TE', label: 'TE', positions: ['TE'], max: 4 },
  { id: 'LT', label: 'LT', positions: ['LT'], max: 2 },
  { id: 'LG', label: 'LG', positions: ['LG'], max: 2 },
  { id: 'C', label: 'C', positions: ['C'], max: 2 },
  { id: 'RG', label: 'RG', positions: ['RG'], max: 2 },
  { id: 'RT', label: 'RT', positions: ['RT'], max: 2 },
  { id: 'EDGE1', label: 'EDGE', positions: ['LEDGE', 'REDGE', 'LE', 'RE'], max: 3, split: 0 },
  { id: 'EDGE2', label: 'EDGE', positions: ['LEDGE', 'REDGE', 'LE', 'RE'], max: 3, split: 1 },
  { id: 'DT1', label: 'DT', positions: ['DT'], max: 3, split: 0 },
  { id: 'DT2', label: 'DT', positions: ['DT'], max: 3, split: 1 },
  { id: 'SAM', label: 'SAM', positions: ['ROLB', 'SAM'], max: 2 },
  { id: 'MIKE', label: 'MIKE', positions: ['MLB', 'MIKE'], max: 2 },
  { id: 'WILL', label: 'WILL', positions: ['LOLB', 'WILL'], max: 2 },
  { id: 'CB1', label: 'CB1', positions: ['CB'], max: 4, split: 0 },
  { id: 'CB2', label: 'CB2', positions: ['CB'], max: 4, split: 1 },
  { id: 'FS', label: 'FS', positions: ['FS'], max: 2 },
  { id: 'SS', label: 'SS', positions: ['SS'], max: 2 },
  { id: 'K', label: 'K', positions: ['K'], max: 1 },
  { id: 'P', label: 'P', positions: ['P'], max: 1 },
  { id: 'LS', label: 'LS', positions: ['LS'], max: 1 },
];

export const POSITION_GROUPS = [
  { name: 'Offense Skill', slots: ['QB', 'HB', 'FB', 'WR1', 'WR2', 'TE'] },
  { name: 'Offensive Line', slots: ['LT', 'LG', 'C', 'RG', 'RT'] },
  { name: 'Edge Rushers', slots: ['EDGE1', 'EDGE2'] },
  { name: 'Interior DL', slots: ['DT1', 'DT2'] },
  { name: 'Linebackers', slots: ['SAM', 'MIKE', 'WILL'] },
  { name: 'Secondary', slots: ['CB1', 'CB2', 'FS', 'SS'] },
  { name: 'Specialists', slots: ['K', 'P', 'LS'] },
];

export function getOvr(player) {
  if (!player) return 0;
  if (typeof player.ovr === 'number') return player.ovr;
  return player.playerBestOvr || player.playerSchemeOvr || 0;
}

export function getSlotSide(slotId) {
  if (!slotId) return '';
  if (OFFENSE_SLOT_IDS.includes(slotId)) return 'Offense';
  if (DEFENSE_SLOT_IDS.includes(slotId)) return 'Defense';
  if (SPECIAL_SLOT_IDS.includes(slotId)) return 'Special Teams';
  return '';
}

export function getPlayersForSlot(slot, allPlayers) {
  const matched = (allPlayers || []).filter((p) =>
    slot.positions.some((pos) => String(p.position || '').toUpperCase() === pos.toUpperCase())
  );
  matched.sort((a, b) => getOvr(b) - getOvr(a));

  if (slot.split !== undefined) {
    const half = Math.ceil(matched.length / 2);
    return slot.split === 0 ? matched.slice(0, half) : matched.slice(half);
  }

  return matched;
}
