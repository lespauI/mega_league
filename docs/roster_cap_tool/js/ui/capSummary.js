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
  const avail = Number.isFinite(Number(snap.capAvailableEffective)) ? Number(snap.capAvailableEffective) : (snap.capAvailable || 0);
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

    // In-game Re-sign Available (X), applied as X + deltaAvailable to reflect live changes
    const snapNow = State.getCapSummary();
    const inGameReSign = State.getReSignInGameForSelectedTeam();
    const reSignReserve = Math.max(0, Number(inGameReSign || 0) + Number(snapNow?.deltaAvailable || 0));

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
        <span class="badge" title="Includes rookie reserve, baseline dead $, re-sign reserve, rollover, and any manual override">Y+1 <span class="${c1}">${fmtMoney(y1)}</span></span>
        <span class="badge">Y+2 <span class="${c2}">${fmtMoney(y2)}</span></span>
        <span class="badge">Y+3 <span class="${c3}">${fmtMoney(y3)}</span></span>
        <label class="label" for="rollover-input" style="margin-left:.75rem;">Rollover to Y+1</label>
        <input id="rollover-input" type="number" min="0" max="35000000" step="500000" value="${Math.max(0, Math.min(35000000, Number(rollover||0)))}" class="input-number" />
        <label class="label" for="resign-ingame-value" style="margin-left:.75rem;" title="Go to in game re-sign, and see how many money avaliabe nad adjust this to have proper calculations">Resign budget</label>
        <input id="resign-ingame-value" type="number" min="0" step="500000" value="${Math.max(0, Number(inGameReSign||0))}" class="input-number" placeholder="Enter in-game amount" title="Go to in game re-sign, and see how many money avaliabe nad adjust this to have proper calculations" />
        <span class="badge" title="Applied to Y+1 as X + ΔSpace">Applied: ${fmtMoney(reSignReserve)}</span>
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
    const inGameInput = /** @type {HTMLInputElement|null} */(el.querySelector('#resign-ingame-value'));
    if (inGameInput) {
      inGameInput.addEventListener('change', () => {
        const v = Math.max(0, Number(inGameInput.value||0));
        State.setReSignInGameForSelectedTeam(v);
        State.setState({});
      });
    }
    const capGrowth = /** @type {HTMLInputElement|null} */(el.querySelector('#cap-growth'));
    if (capGrowth) {
      capGrowth.addEventListener('input', () => {
        const v = Math.max(0, Math.min(0.15, Number(capGrowth.value||0)));
        try { localStorage.setItem('rosterCap.capGrowthRate', String(v)); } catch {}
        State.setState({});
      });
    }
    // Y+1 override input removed
  } catch {
    el.innerHTML = '';
  }
}

export default { mountCapSummary };
