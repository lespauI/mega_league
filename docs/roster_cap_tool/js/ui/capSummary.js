import { getCapSummary, getState, getDraftPicksForSelectedTeam } from '../state.js';
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
  const snap = getCapSummary();
  const room = snap.capRoom || 0;
  const spent = snap.capSpent || 0;
  const avail = snap.capAvailable || 0;
  const rookies = snap.rookieReserveEstimate || 0;
  const effAvail = (snap.capAfterRookies != null) ? snap.capAfterRookies : (avail - rookies);
  const deltaAvail = snap.deltaAvailable || 0; // + means gained cap space
  const pct = room > 0 ? Math.max(0, Math.min(100, Math.round((spent / room) * 100))) : 0;

  const deltaClass = deltaAvail > 0 ? 'money-pos' : deltaAvail < 0 ? 'money-neg' : 'money-warn';
  const deltaPrefix = deltaAvail > 0 ? '+' : '';

  // Build a 3-year projection summary (Y+1..Y+3) showing Cap Space AFTER rookies
  let projBadges = '';
  try {
    const st = getState();
    const team = st.teams.find((t) => t.abbrName === st.selectedTeam);
    if (team) {
      const horizon = 4; // year 0..3, we display 1..3
      const nextYearPicks = getDraftPicksForSelectedTeam();
      const defaultOneEach = { 1:1,2:1,3:1,4:1,5:1,6:1,7:1 };
      const rr0 = 0;
      const rr1 = estimateRookieReserveForPicks(nextYearPicks);
      const rr2 = estimateRookieReserveForPicks(defaultOneEach);
      const rr3 = rr2; // same assumption
      const proj = projectTeamCaps(team, st.players, st.moves, horizon, { rookieReserveByYear: [rr0, rr1, rr2, rr3] });
      const y1 = proj[1]?.capSpace ?? 0;
      const y2 = proj[2]?.capSpace ?? 0;
      const y3 = proj[3]?.capSpace ?? 0;
      const c1 = y1 >= 0 ? 'money-pos' : 'money-neg';
      const c2 = y2 >= 0 ? 'money-pos' : 'money-neg';
      const c3 = y3 >= 0 ? 'money-pos' : 'money-neg';
      projBadges = `
        <div class="metric"><span class="label">Proj Cap (after rookies)</span>
          <div>
            <span class="badge">Y+1 <span class="${c1}">${fmtMoney(y1)}</span></span>
            <span class="badge">Y+2 <span class="${c2}">${fmtMoney(y2)}</span></span>
            <span class="badge">Y+3 <span class="${c3}">${fmtMoney(y3)}</span></span>
          </div>
        </div>`;
    }
  } catch {}

  el.innerHTML = `
    <div class="metric"><span class="label">Original Cap</span><span class="value">${fmtMoney(room)}</span></div>
    <div class="metric"><span class="label">Current Cap</span><span class="value">${fmtMoney(room)}</span></div>
    <div class="metric"><span class="label">Cap Spent</span><span class="value">${fmtMoney(spent)}</span></div>
    <div class="metric"><span class="label">Cap Space</span><span class="value">${fmtMoney(avail)}</span></div>
    <div class="metric"><span class="label">Rookie Reserve (est)</span><span class="value">${fmtMoney(rookies)}</span></div>
    <div class="metric"><span class="label">Cap After Rookies</span><span class="value">${fmtMoney(effAvail)}</span></div>
    <div class="metric"><span class="label">Cap Gain/Loss</span><span class="value ${deltaClass}">${deltaPrefix}${fmtMoney(deltaAvail)}</span></div>
    <div class="metric"><span class="label">Spent / Cap</span>
      <div class="progress"><div class="bar" style="width:${pct}%"></div></div>
    </div>
    ${projBadges}
  `;
}

export default { mountCapSummary };
