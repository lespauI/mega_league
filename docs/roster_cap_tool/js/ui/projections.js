import { getState } from '../state.js';
import { projectTeamCaps } from '../capMath.js';

function fmtMoney(n) {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    maximumFractionDigits: 0,
  }).format(Number.isFinite(n) ? n : 0);
}

function yearLabel(offset, team) {
  // Use simple labels: Year 1 (Current), Year 2, ...
  if (offset === 0) return 'Year 1 (Current)';
  return `Year ${offset + 1}`;
}

/** Render projections table for selected team */
export function mountProjections() {
  const el = document.getElementById('projections-view');
  if (!el) return;

  const st = getState();
  const team = st.teams.find((t) => t.abbrName === st.selectedTeam);
  if (!team) {
    el.innerHTML = '<div style="padding:.75rem; color:var(--muted)">No team selected.</div>';
    return;
  }

  // Read current desired horizon from existing control if present; default 5
  let years = 5;
  const prior = el.querySelector('input[data-horizon]');
  if (prior) {
    const v = Number(/** @type {HTMLInputElement} */(prior).value);
    if (Number.isFinite(v) && v >= 3 && v <= 5) years = Math.floor(v);
  }

  const proj = projectTeamCaps(team, st.players, st.moves, years);

  // Build controls + table
  const controls = `
    <div style="display:flex; align-items:center; gap:.75rem; margin:.25rem .25rem .5rem;">
      <div style="color:var(--muted)">Horizon</div>
      <input type="range" min="3" max="5" step="1" value="${years}" data-horizon style="width:160px" />
      <div id="proj-years-label" class="badge">${years} year(s)</div>
    </div>
    <div style="margin:.25rem; color:var(--muted); font-size:12px;">
      Note: Year 1 is anchored to the in-game snapshot (capSpent/capAvailable). Roster Cap is derived; Dead Money reflects only scenario moves. Out-years are approximated from contract totals (salary ÷ length, bonus prorated up to 5 years). If contract details are missing, projections infer base from current cap hit and proration from release penalty.
    </div>
  `;

  let rows = '';
  for (const y of proj) {
    const capClass = (y.capSpace >= 0) ? 'money-pos' : 'money-neg';
    rows += `
      <tr>
        <td>${yearLabel(y.yearOffset, team)}</td>
        <td>${fmtMoney(y.capRoom)}</td>
        <td>${fmtMoney(y.rosterCap)}</td>
        <td class="money-warn">${fmtMoney(y.deadMoney)}</td>
        <td>${fmtMoney(y.totalSpent)}</td>
        <td class="${capClass}">${fmtMoney(y.capSpace)}</td>
      </tr>
    `;
  }

  el.innerHTML = `
    ${controls}
    <table>
      <thead>
        <tr>
          <th>Year</th>
          <th>Cap Total</th>
          <th>Roster Cap</th>
          <th>Dead Money</th>
          <th>Total Spent</th>
          <th>Cap Space</th>
        </tr>
      </thead>
      <tbody>
        ${rows}
      </tbody>
    </table>
  `;

  // Wire slider to re-render quickly
  const slider = el.querySelector('input[data-horizon]');
  const label = el.querySelector('#proj-years-label');
  if (slider) {
    slider.addEventListener('input', (e) => {
      const val = Math.max(3, Math.min(5, Math.floor(Number(/** @type {HTMLInputElement} */(e.target).value || 5))));
      if (label) label.textContent = `${val} year(s)`;
    });
    slider.addEventListener('change', () => mountProjections());
  }
}

export default { mountProjections };
