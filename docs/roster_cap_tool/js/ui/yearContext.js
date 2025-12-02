import { getYearContextForSelectedTeam, setYearContextForSelectedTeam, getContextLabel } from '../state.js';

/**
 * Mounts the Year Context selector (Y+0..Y+5) and label into the header.
 * @param {string} containerId
 */
export function mountYearContext(containerId = 'year-context') {
  const el = document.getElementById(containerId);
  if (!el) return;

  const current = getYearContextForSelectedTeam();

  // Build UI
  const frag = document.createDocumentFragment();

  const label = document.createElement('span');
  label.className = 'filters-label';
  label.setAttribute('data-testid', 'year-context-label');
  label.textContent = getContextLabel();
  label.title = 'Roster/Cap context year';
  frag.appendChild(label);

  // Render a compact set of options Y+0..Y+5
  const MAX_OFF = 5;
  for (let i = 0; i <= MAX_OFF; i++) {
    const btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'chip';
    if (i === current) btn.classList.add('is-active');
    btn.textContent = `Y+${i}`;
    btn.setAttribute('data-testid', `year-context-${i}`);
    btn.title = `View roster and cap as of Y+${i}`;
    btn.addEventListener('click', () => setYearContextForSelectedTeam(i));
    frag.appendChild(btn);
  }

  el.innerHTML = '';
  el.appendChild(frag);
}

export default { mountYearContext };

