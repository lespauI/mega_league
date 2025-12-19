import { getTeamPlayers } from '../state.js';

const DEPTH_CHART_SLOTS = [
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
];

const POSITION_GROUPS = [
  { name: 'Offense Skill', slots: ['QB', 'HB', 'FB', 'WR1', 'WR2', 'TE'] },
  { name: 'Offensive Line', slots: ['LT', 'LG', 'C', 'RG', 'RT'] },
  { name: 'Edge Rushers', slots: ['EDGE1', 'EDGE2'] },
  { name: 'Interior DL', slots: ['DT1', 'DT2'] },
  { name: 'Linebackers', slots: ['SAM', 'MIKE', 'WILL'] },
  { name: 'Secondary', slots: ['CB1', 'CB2', 'FS', 'SS'] },
  { name: 'Specialists', slots: ['K', 'P'] },
];

function getOvr(player) {
  return player.playerBestOvr || player.playerSchemeOvr || 0;
}

function formatName(player) {
  const first = player.firstName || '';
  const last = player.lastName || '';
  const initial = first.charAt(0);
  return initial ? `${initial}.${last}` : last;
}

function getPlayersForSlot(slot, allPlayers) {
  const matched = allPlayers.filter((p) =>
    slot.positions.some((pos) => p.position.toUpperCase() === pos.toUpperCase())
  );
  matched.sort((a, b) => getOvr(b) - getOvr(a));

  if (slot.split !== undefined) {
    const half = Math.ceil(matched.length / 2);
    return slot.split === 0 ? matched.slice(0, half) : matched.slice(half);
  }
  return matched;
}

export function mountDepthChart(containerId = 'depth-chart-grid') {
  const el = document.getElementById(containerId);
  if (!el) return;

  const players = getTeamPlayers();
  el.innerHTML = '';

  for (const group of POSITION_GROUPS) {
    const groupDiv = document.createElement('div');
    groupDiv.className = 'depth-group';

    const header = document.createElement('div');
    header.className = 'depth-group__header';
    header.textContent = group.name;
    groupDiv.appendChild(header);

    const table = document.createElement('table');
    table.className = 'depth-table';

    const thead = document.createElement('thead');
    const headerRow = document.createElement('tr');
    headerRow.innerHTML = '<th>Pos</th><th>1</th><th>2</th><th>3</th><th>4</th>';
    thead.appendChild(headerRow);
    table.appendChild(thead);

    const tbody = document.createElement('tbody');

    for (const slotId of group.slots) {
      const slot = DEPTH_CHART_SLOTS.find((s) => s.id === slotId);
      if (!slot) continue;

      const slotPlayers = getPlayersForSlot(slot, players);
      const row = document.createElement('tr');

      const posCell = document.createElement('td');
      posCell.className = 'depth-cell depth-cell--pos';
      posCell.textContent = slot.label;
      row.appendChild(posCell);

      for (let i = 0; i < 4; i++) {
        const cell = document.createElement('td');
        cell.className = 'depth-cell';

        if (i < slotPlayers.length) {
          const p = slotPlayers[i];
          const ovr = getOvr(p);
          cell.innerHTML = `<span class="player-name">${formatName(p)}</span><span class="player-ovr">${ovr}</span>`;
        } else if (i < slot.max) {
          cell.className += ' depth-cell--need';
          cell.textContent = '—';
        } else {
          cell.textContent = '';
        }

        row.appendChild(cell);
      }

      tbody.appendChild(row);
    }

    table.appendChild(tbody);
    groupDiv.appendChild(table);
    el.appendChild(groupDiv);
  }
}
