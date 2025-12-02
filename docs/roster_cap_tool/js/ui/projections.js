import * as State from '../state.js';
import { projectTeamCaps, estimateRookieReserveForPicks } from '../capMath.js';

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

  const st = State.getState();
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

  // Build Rookie Reserve schedule and apply rollover to next year
  const nextYearPicks = State.getDraftPicksForSelectedTeam();
  const defaultOneEach = { 1:1,2:1,3:1,4:1,5:1,6:1,7:1 };
  const rrByYear = Array.from({ length: years }, (_, i) => {
    if (i === 0) return 0;
    if (i === 1) return estimateRookieReserveForPicks(nextYearPicks);
    return estimateRookieReserveForPicks(defaultOneEach);
  });
  const rollover = State.getRolloverForSelectedTeam();
  const y1Override = State.getY1CapOverrideForSelectedTeam();
  const dmBase = State.getBaselineDeadMoney();
  const baselineDMByYear = Array.from({ length: years }, (_, i) => {
    if (i === 0) return Number(dmBase?.year0 || 0) || 0;
    if (i === 1) return Number(dmBase?.year1 || 0) || 0;
    return 0;
  });
  // Re-sign reserve from in-game input, adjusted by delta cap space: applied = X + ΔSpace
  const snapNow = State.getCapSummary();
  const inGameReSign = State.getReSignInGameForSelectedTeam();
  const reSignReserve = Math.max(0, Number(inGameReSign || 0) + Number(snapNow?.deltaAvailable || 0));

  const extraSpendingByYear = Array.from({ length: years }, (_, i) => (i === 1 ? reSignReserve : 0));

  const proj = projectTeamCaps(team, st.players, st.moves, years, {
    rookieReserveByYear: rrByYear,
    baselineDeadMoneyByYear: baselineDMByYear,
    extraSpendingByYear,
    rolloverToNext: rollover,
    rolloverMax: 35_000_000,
    overrideY1CapSpace: (y1Override !== null) ? Number(y1Override) : undefined,
  });

  // Build controls + table
  const controls = `
    <div style="display:flex; align-items:center; gap:.75rem; margin:.25rem .25rem .5rem;">
      <div style="color:var(--muted)">Horizon</div>
      <input type="range" min="3" max="5" step="1" value="${years}" data-horizon style="width:160px" />
      <div id="proj-years-label" class="badge">${years} year(s)</div>
      <div style="width:1px; height:20px; background:var(--border); margin:0 .5rem;"></div>
      <label class="label" for="proj-resign-ingame-value">Use in-game “Re-sign Available”</label>
      <input id="proj-resign-ingame-value" type="number" min="0" step="500000" value="${Math.max(0, Number(inGameReSign||0))}" class="input-number" placeholder="Enter in-game amount" />
      <span class="badge" title="Applied to Y+1 as X + ΔSpace">Applied: ${fmtMoney(reSignReserve)}</span>
    </div>
    <div style="margin:.25rem; color:var(--muted); font-size:12px;">
      Note: Year 1 is anchored to the in-game snapshot (capSpent/capAvailable). Rookie Reserve applied to Y+1 and beyond. Re-sign uses in-game “Re-sign Available” adjusted by current ΔSpace (X + ΔSpace). Out-years approximate base = salary/length and bonus prorated up to 5 years. Rollover up to $35M from current year increases Y+1 Cap Space.
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
  const inGame = /** @type {HTMLInputElement|null} */(el.querySelector('#proj-resign-ingame-value'));
  if (inGame) {
    inGame.addEventListener('change', () => {
      const v = Math.max(0, Number(inGame.value||0));
      State.setReSignInGameForSelectedTeam(v);
      State.setState({});
    });
  }
}

export default { mountProjections };
