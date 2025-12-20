import { getDepthPlanForSelectedTeam, getState } from '../state.js';
import { DEPTH_CHART_SLOTS, POSITION_GROUPS, getOvr } from '../slots.js';

function formatName(player) {
  const first = player.firstName || '';
  const last = player.lastName || '';
  const initial = first.charAt(0);
  return initial ? `${initial}.${last}` : last;
}

export function mountDepthChart(containerId = 'depth-chart-grid') {
  const el = document.getElementById(containerId);
  if (!el) return;

  const depthPlan = getDepthPlanForSelectedTeam();
  const { playersById } = getState();
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

      const planSlot =
        depthPlan && depthPlan.slots && depthPlan.slots[slotId] ? depthPlan.slots[slotId] : [];
      const row = document.createElement('tr');

      const posCell = document.createElement('td');
      posCell.className = 'depth-cell depth-cell--pos';
      posCell.textContent = slot.label;
      row.appendChild(posCell);

      for (let i = 0; i < 4; i++) {
        const cell = document.createElement('td');
        cell.className = 'depth-cell';

        const depthIndex = i + 1;
        // We expect planSlot to be an array of DepthSlotAssignment entries.
        // Prefer depthIndex match if provided; otherwise fall back to array index.
        let assignment =
          planSlot.find((a) => a && a.depthIndex === depthIndex) || planSlot[i] || null;

        if (assignment && assignment.playerId && playersById[assignment.playerId]) {
          const p = playersById[assignment.playerId];
          const ovr = getOvr(p);
          cell.innerHTML = `<span class="player-name">${formatName(
            p
          )}</span><span class="player-ovr">${ovr}</span>`;
        } else if (assignment && assignment.placeholder) {
          cell.textContent = assignment.placeholder;
        } else if (depthIndex <= slot.max) {
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
