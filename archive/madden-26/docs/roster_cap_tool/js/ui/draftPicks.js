import { getState, getDraftPicksForSelectedTeam, setDraftPicksForSelectedTeam, getRookieReserveEstimate } from '../state.js';
import { estimateRookieYear1ForSlot } from '../capMath.js';

function fmtMoney(n) {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    maximumFractionDigits: 0,
  }).format(n || 0);
}

/**
 * Render the Draft Picks setup and Rookie Reserve estimate.
 * Allows per-round pick counts and shows per-pick mid-round Year 1 estimate and totals.
 * @param {string} containerId
 */
export function mountDraftPicks(containerId = 'draft-picks-table') {
  const el = document.getElementById(containerId);
  if (!el) return;
  const st = getState();
  const team = st.teams.find((t) => t.abbrName === st.selectedTeam);
  const baseYear = Number(team?.calendarYear || 0);
  const rookieYearLabel = (Number.isFinite(baseYear) && baseYear > 0) ? String(baseYear + 1) : 'Year 1';
  const picks = getDraftPicksForSelectedTeam();

  const table = document.createElement('table');
  const thead = document.createElement('thead');
  const header = document.createElement('tr');
  ;['Round', 'Picks', `Est. Per Pick (${rookieYearLabel})`, 'Est. Round Total'].forEach((h) => {
    const th = document.createElement('th');
    th.textContent = h;
    header.appendChild(th);
  });
  thead.appendChild(header);

  const tbody = document.createElement('tbody');
  let grandTotal = 0;

  const inputs = {};

  for (let r = 1; r <= 7; r++) {
    const tr = document.createElement('tr');
    const tdRound = document.createElement('td');
    tdRound.textContent = String(r);
    tdRound.setAttribute('data-label', 'Round');

    const tdCount = document.createElement('td');
    tdCount.setAttribute('data-label', 'Picks');
    const inp = document.createElement('input');
    inp.type = 'number';
    inp.min = '0';
    inp.step = '1';
    inp.value = String(picks[r] || 0);
    inp.style.width = '6rem';
    inp.addEventListener('change', () => {
      const next = { ...getDraftPicksForSelectedTeam() };
      next[r] = Math.max(0, Math.floor(Number(inp.value) || 0));
      setDraftPicksForSelectedTeam(next);
    });
    inputs[r] = inp;
    tdCount.appendChild(inp);

    const tdPer = document.createElement('td');
    tdPer.setAttribute('data-label', `Est. Per Pick (${rookieYearLabel})`);
    const per = estimateRookieYear1ForSlot(r, 16);
    tdPer.textContent = fmtMoney(per);

    const tdRoundTotal = document.createElement('td');
    tdRoundTotal.setAttribute('data-label', 'Est. Round Total');
    const roundTotal = per * (Number(picks[r] || 0));
    grandTotal += roundTotal;
    tdRoundTotal.textContent = fmtMoney(roundTotal);

    tr.append(tdRound, tdCount, tdPer, tdRoundTotal);
    tbody.appendChild(tr);
  }

  const foot = document.createElement('tr');
  const tdLabel = document.createElement('td');
  tdLabel.colSpan = 3;
  tdLabel.style.textAlign = 'right';
  tdLabel.innerHTML = `<strong>Estimated Rookie Reserve (${rookieYearLabel})</strong>`;
  const tdTotal = document.createElement('td');
  tdTotal.innerHTML = `<strong>${fmtMoney(getRookieReserveEstimate())}</strong>`;
  foot.append(tdLabel, tdTotal);
  tbody.appendChild(foot);

  table.appendChild(thead);
  table.appendChild(tbody);

  const wrap = document.createElement('div');
  // Controls row
  const controls = document.createElement('div');
  controls.style.display = 'flex';
  controls.style.gap = '.5rem';
  controls.style.padding = '.5rem';

  const btnReset = document.createElement('button');
  btnReset.className = 'btn danger';
  btnReset.textContent = 'Reset Picks';
  btnReset.addEventListener('click', () => {
    const zero = { 1:0,2:0,3:0,4:0,5:0,6:0,7:0 };
    setDraftPicksForSelectedTeam(zero);
  });

  const btnDefault = document.createElement('button');
  btnDefault.className = 'btn';
  btnDefault.textContent = 'Default (1 per round)';
  btnDefault.addEventListener('click', () => {
    const def = { 1:1,2:1,3:1,4:1,5:1,6:1,7:1 };
    setDraftPicksForSelectedTeam(def);
  });

  const note = document.createElement('div');
  note.style.marginLeft = 'auto';
  note.style.color = 'var(--muted)';
  note.style.fontSize = '.85rem';
  note.textContent = 'Estimates use mid-round slot values; advisory only.';

  controls.append(btnReset, btnDefault, note);

  wrap.appendChild(controls);
  wrap.appendChild(table);

  el.innerHTML = '';
  el.appendChild(wrap);
}

export default { mountDraftPicks };
