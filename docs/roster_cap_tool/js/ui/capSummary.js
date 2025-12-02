import { getCapSummary } from '../state.js';

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
  `;
}

export default { mountCapSummary };
