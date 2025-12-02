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
  const dmBase = State.getBaselineDeadMoney();
  const baselineDMByYear = Array.from({ length: years }, (_, i) => {
    if (i === 0) return Number(dmBase?.year0 || 0) || 0;
    if (i === 1) return Number(dmBase?.year1 || 0) || 0;
    return 0;
  });
  // Re-sign reserve: use settings (manual value or in-game toggle)
  let estReSign = 0;
  try {
    const pyears = (len) => Math.max(1, Math.min(5, Math.floor(Number(len) || 3)));
    for (const p of st.players || []) {
      if (!p || p.isFreeAgent || p.team !== team.abbrName) continue;
      const yl = Number(p.contractYearsLeft || 0);
      const rs = Number(p.reSignStatus || 0);
      if ((Number.isFinite(yl) && yl <= 0) || (Number.isFinite(rs) && rs !== 0)) {
        const ds = Number(p.desiredSalary || 0) || 0;
        const db = Number(p.desiredBonus || 0) || 0;
        const dl = Number(p.desiredLength || 0) || 3;
        const y1 = ds + (db / pyears(dl));
        if (y1 > 0) estReSign += y1;
      }
    }
  } catch {}
  const reConf = State.getReSignSettingsForSelectedTeam();
  const reSignReserve = Math.max(0, Number(reConf.useInGame ? reConf.inGameValue : reConf.reserve) || 0);

  const extraSpendingByYear = Array.from({ length: years }, (_, i) => (i === 1 ? reSignReserve : 0));

  const proj = projectTeamCaps(team, st.players, st.moves, years, {
    rookieReserveByYear: rrByYear,
    baselineDeadMoneyByYear: baselineDMByYear,
    extraSpendingByYear,
    rolloverToNext: rollover,
    rolloverMax: 35_000_000,
  });

  // Build controls + table
  const controls = `
    <div style="display:flex; align-items:center; gap:.75rem; margin:.25rem .25rem .5rem;">
      <div style="color:var(--muted)">Horizon</div>
      <input type="range" min="3" max="5" step="1" value="${years}" data-horizon style="width:160px" />
      <div id="proj-years-label" class="badge">${years} year(s)</div>
      <div style="width:1px; height:20px; background:var(--border); margin:0 .5rem;"></div>
      <label class="label" for="proj-resign-reserve">Re-sign reserve (Y+1)</label>
      <input id="proj-resign-reserve" type="number" min="0" step="500000" value="${Math.max(0, Number(reConf.reserve||0))}" class="input-number" ${reConf.useInGame ? 'disabled' : ''} />
      <button id="proj-resign-use-estimate" class="btn" title="Set reserve to estimated cost">Use Estimate (${fmtMoney(estReSign)})</button>
      <label class="label" for="proj-resign-use-ingame">Use in-game “Re-sign Available”</label>
      <input id="proj-resign-use-ingame" type="checkbox" ${reConf.useInGame ? 'checked' : ''} />
      <input id="proj-resign-ingame-value" type="number" min="0" step="500000" value="${Math.max(0, Number(reConf.inGameValue||0))}" class="input-number" placeholder="Enter in-game amount" />
    </div>
    <div style="margin:.25rem; color:var(--muted); font-size:12px;">
      Note: Year 1 is anchored to the in-game snapshot (capSpent/capAvailable). Rookie Reserve applied to Y+1 and beyond. Re-sign reserve is applied to Y+1 totals. Out-years approximate base = salary/length and bonus prorated up to 5 years. Rollover up to $35M from current year increases Y+1 Cap Space.
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
  const reInput = /** @type {HTMLInputElement|null} */(el.querySelector('#proj-resign-reserve'));
  if (reInput) {
    reInput.addEventListener('change', () => {
      const v = Math.max(0, Number(reInput.value||0));
      State.setReSignSettingsForSelectedTeam({ reserve: v });
    });
  }
  const btnEst = /** @type {HTMLButtonElement|null} */(el.querySelector('#proj-resign-use-estimate'));
  if (btnEst) {
    btnEst.addEventListener('click', () => {
      State.setReSignSettingsForSelectedTeam({ reserve: Math.max(0, Number(estReSign||0)) });
    });
  }
  const chkUse = /** @type {HTMLInputElement|null} */(el.querySelector('#proj-resign-use-ingame'));
  if (chkUse) {
    chkUse.addEventListener('change', () => {
      State.setReSignSettingsForSelectedTeam({ useInGame: !!chkUse.checked });
    });
  }
  const inGame = /** @type {HTMLInputElement|null} */(el.querySelector('#proj-resign-ingame-value'));
  if (inGame) {
    inGame.addEventListener('change', () => {
      const v = Math.max(0, Number(inGame.value||0));
      State.setReSignSettingsForSelectedTeam({ inGameValue: v });
    });
  }
}

export default { mountProjections };
