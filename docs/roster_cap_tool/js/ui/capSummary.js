import * as State from '../state.js';
import { projectTeamCaps, estimateRookieReserveForPicks } from '../capMath.js';

function fmtMoney(n) {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    maximumFractionDigits: 0,
  }).format(n || 0);
}

/**
 * Renders the sticky Cap Summary panel with progress bar and delta.
 * Shows Original/Current Cap (capRoom), Cap Spent, Cap Space, Gain/Loss and a progress bar of Spent/Cap.
 * @param {string} containerId
 */
export function mountCapSummary(containerId = 'cap-summary') {
  const el = document.getElementById(containerId);
  if (!el) return;
  const snap = State.getCapSummary();
  const room = snap.capRoom || 0;
  const spent = snap.capSpent || 0;
  const avail = snap.capAvailable || 0;
  const deltaAvail = snap.deltaAvailable || 0; // + means gained cap space
  const pct = room > 0 ? Math.max(0, Math.min(100, Math.round((spent / room) * 100))) : 0;

  const deltaClass = deltaAvail > 0 ? 'money-pos' : deltaAvail < 0 ? 'money-neg' : 'money-warn';
  const deltaPrefix = deltaAvail > 0 ? '+' : '';

  // Read-only Rookie Reserve for next year (does not affect current year)
  let rookieNext = 0;
  try {
    const picks = State.getDraftPicksForSelectedTeam();
    rookieNext = estimateRookieReserveForPicks(picks);
  } catch {}

  el.innerHTML = `
    <div class="metric"><span class="label">Original Cap</span><span class="value">${fmtMoney(room)}</span></div>
    <div class="metric"><span class="label">Current Cap</span><span class="value">${fmtMoney(room)}</span></div>
    <div class="metric"><span class="label">Cap Spent</span><span class="value">${fmtMoney(spent)}</span></div>
    <div class="metric"><span class="label">Cap Space</span><span class="value">${fmtMoney(avail)}</span></div>
    <div class="metric"><span class="label">Rookie Reserve (next year)</span><span class="value">${fmtMoney(rookieNext)}</span></div>
    <div class="metric"><span class="label">Cap Gain/Loss</span><span class="value ${deltaClass}">${deltaPrefix}${fmtMoney(deltaAvail)}</span></div>
    <div class="metric"><span class="label">Spent / Cap</span>
      <div class="progress"><div class="bar" style="width:${pct}%"></div></div>
    </div>
  `;
}

/**
 * Renders the compact 3-year projections (after rookies) strip into a separate
 * header-bottom container so it’s always visible below the header controls.
 */
export function mountHeaderProjections(containerId = 'header-projections') {
  const el = document.getElementById(containerId);
  if (!el) return;
  try {
    const st = State.getState();
    const team = st.teams.find((t) => t.abbrName === st.selectedTeam);
    if (!team) { el.innerHTML = ''; return; }

    const horizon = 4; // show Y+1..Y+3
    const nextYearPicks = State.getDraftPicksForSelectedTeam();
    const defaultOneEach = { 1:1,2:1,3:1,4:1,5:1,6:1,7:1 };
    const rr0 = 0;
    const rr1 = estimateRookieReserveForPicks(nextYearPicks);
    const rr2 = estimateRookieReserveForPicks(defaultOneEach);
    const rr3 = rr2;
    const rollover = State.getRolloverForSelectedTeam();

    // Baseline dead money from the Dead Money tab (This Year and Next Year)
    const dmBase = State.getBaselineDeadMoney();
    const baselineDMByYear = [
      Number(dmBase?.year0 || 0) || 0,
      Number(dmBase?.year1 || 0) || 0,
      0,
      0,
    ];

    // Estimate re-sign cost from roster to show as a helper; not used unless applied.
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
    // Settings per team: manual reserve, toggle to use in-game value, and the in-game value itself.
    const reConf = State.getReSignSettingsForSelectedTeam();
    const reSignReserve = Math.max(0, Number(reConf.useInGame ? reConf.inGameValue : reConf.reserve) || 0);

    // Cap growth rate tunable (persisted)
    const capGrowthRate = (() => {
      try { const raw = localStorage.getItem('rosterCap.capGrowthRate'); const v = Number(raw); if (Number.isFinite(v)) return v; } catch {}
      return 0.09;
    })();

    const proj = projectTeamCaps(team, st.players, st.moves, horizon, {
      rookieReserveByYear: [rr0, rr1, rr2, rr3],
      baselineDeadMoneyByYear: baselineDMByYear,
      extraSpendingByYear: [0, reSignReserve, 0, 0],
      rolloverToNext: rollover,
      rolloverMax: 35_000_000,
      capGrowthRate,
    });
    const y1 = proj[1]?.capSpace ?? 0;
    const y2 = proj[2]?.capSpace ?? 0;
    const y3 = proj[3]?.capSpace ?? 0;
    const c1 = y1 >= 0 ? 'money-pos' : 'money-neg';
    const c2 = y2 >= 0 ? 'money-pos' : 'money-neg';
    const c3 = y3 >= 0 ? 'money-pos' : 'money-neg';

    el.innerHTML = `
      <div class="proj-strip">
        <span class="label">Proj Cap (after rookies):</span>
        <span class="badge" title="Includes rookie reserve, baseline dead $, and re-sign reserve">Y+1 <span class="${c1}">${fmtMoney(y1)}</span></span>
        <span class="badge">Y+2 <span class="${c2}">${fmtMoney(y2)}</span></span>
        <span class="badge">Y+3 <span class="${c3}">${fmtMoney(y3)}</span></span>
        <label class="label" for="rollover-input" style="margin-left:.75rem;">Rollover to Y+1</label>
        <input id="rollover-input" type="number" min="0" max="35000000" step="500000" value="${Math.max(0, Math.min(35000000, Number(rollover||0)))}" class="input-number" />
        <label class="label" for="resign-reserve" style="margin-left:.75rem;">Re-sign reserve (Y+1)</label>
        <input id="resign-reserve" type="number" min="0" step="500000" value="${Math.max(0, Number(reConf.reserve||0))}" class="input-number" ${reConf.useInGame ? 'disabled' : ''} />
        <span class="badge" title="Current value used in projections">Using: ${fmtMoney(reSignReserve)}</span>
        <button id="resign-use-estimate" class="btn" title="Set reserve to estimated cost">Use Estimate (${fmtMoney(estReSign)})</button>
        <label class="label" for="resign-use-ingame" style="margin-left:.5rem;">Use in-game “Re-sign Available”</label>
        <input id="resign-use-ingame" type="checkbox" ${reConf.useInGame ? 'checked' : ''} />
        <input id="resign-ingame-value" type="number" min="0" step="500000" value="${Math.max(0, Number(reConf.inGameValue||0))}" class="input-number" ${reConf.useInGame ? '' : ''} placeholder="Enter in-game amount" />
        <label class="label" for="cap-growth" style="margin-left:.75rem;">Cap growth</label>
        <input id="cap-growth" type="range" min="0" max="0.15" step="0.01" value="${capGrowthRate}" class="input-range" />
        <span class="badge">${(capGrowthRate*100).toFixed(0)}%</span>
      </div>
    `;
    const input = /** @type {HTMLInputElement|null} */(el.querySelector('#rollover-input'));
    if (input) {
      input.addEventListener('change', () => {
        const v = Math.max(0, Math.min(35_000_000, Number(input.value||0)));
        State.setRolloverForSelectedTeam(v);
      });
    }
    const reInput = /** @type {HTMLInputElement|null} */(el.querySelector('#resign-reserve'));
    if (reInput) {
      reInput.addEventListener('change', () => {
        const v = Math.max(0, Number(reInput.value||0));
        State.setReSignSettingsForSelectedTeam({ reserve: v });
      });
    }
    const btnEstimate = /** @type {HTMLButtonElement|null} */(el.querySelector('#resign-use-estimate'));
    if (btnEstimate) {
      btnEstimate.addEventListener('click', () => {
        State.setReSignSettingsForSelectedTeam({ reserve: Math.max(0, Number(estReSign||0)) });
      });
    }
    const chkUseInGame = /** @type {HTMLInputElement|null} */(el.querySelector('#resign-use-ingame'));
    const inGameInput = /** @type {HTMLInputElement|null} */(el.querySelector('#resign-ingame-value'));
    if (chkUseInGame) {
      chkUseInGame.addEventListener('change', () => {
        const use = !!chkUseInGame.checked;
        State.setReSignSettingsForSelectedTeam({ useInGame: use });
      });
    }
    if (inGameInput) {
      inGameInput.addEventListener('change', () => {
        const v = Math.max(0, Number(inGameInput.value||0));
        State.setReSignSettingsForSelectedTeam({ inGameValue: v });
      });
    }
    const capGrowth = /** @type {HTMLInputElement|null} */(el.querySelector('#cap-growth'));
    if (capGrowth) {
      capGrowth.addEventListener('input', () => {
        const v = Math.max(0, Math.min(0.15, Number(capGrowth.value||0)));
        try { localStorage.setItem('rosterCap.capGrowthRate', String(v)); } catch {}
        setState({});
      });
    }
  } catch {
    el.innerHTML = '';
  }
}

export default { mountCapSummary };
