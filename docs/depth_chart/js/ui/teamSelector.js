import { getState, setState } from '../state.js';

export function mountTeamSelector(containerId = 'team-selector') {
  const el = document.getElementById(containerId);
  if (!el) return;
  el.innerHTML = '';

  const st = getState();
  const sel = document.createElement('select');
  sel.setAttribute('data-testid', 'team-select');
  sel.setAttribute('aria-label', 'Select Team');

  st.teams.forEach((t) => {
    const opt = document.createElement('option');
    opt.value = t.abbrName;
    opt.textContent = `${t.abbrName} — ${t.displayName}`;
    if (t.abbrName === st.selectedTeam) opt.selected = true;
    sel.appendChild(opt);
  });

  sel.addEventListener('change', () => setState({ selectedTeam: sel.value }));
  el.appendChild(sel);
}
