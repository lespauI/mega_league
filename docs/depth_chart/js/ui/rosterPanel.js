import {
  clearPlayerFromAllDepthSlots,
  getPlayersForTeam,
  getFreeAgents,
  getState,
  setRosterEdit,
} from '../state.js';
import { getOvr } from '../slots.js';
import { formatName, getContractSummary } from './playerFormatting.js';
import { getDraftPicksForTeam, setDraftPicksForTeam } from '../draftPicks.js';

export function mountRosterPanel(containerId = 'roster-panel') {
  const el = document.getElementById(containerId);
  if (!el) return;

  const st = getState();
  const teamAbbr = st.selectedTeam;

  el.innerHTML = '';

  const doc = el.ownerDocument || document;
  const wrapper = doc.createElement('div');
  wrapper.className = 'roster-panel__inner';

  const header = doc.createElement('div');
  header.className = 'roster-panel__header';
  const title = doc.createElement('h2');
  title.className = 'roster-panel__title';
  title.textContent = 'Roster & FA Market';
  header.appendChild(title);
  wrapper.appendChild(header);

  if (!teamAbbr) {
    const empty = doc.createElement('div');
    empty.className = 'roster-panel__empty';
    empty.textContent = 'Select a team to manage its roster.';
    wrapper.appendChild(empty);
    el.appendChild(wrapper);
    return;
  }

  const faSection = doc.createElement('section');
  faSection.className = 'roster-panel__section';
  const faHeader = doc.createElement('div');
  faHeader.className = 'roster-panel__section-header';
  const faTitle = doc.createElement('h3');
  faTitle.className = 'roster-panel__section-title';
  faTitle.textContent = 'Free agents';
  faHeader.appendChild(faTitle);
  faSection.appendChild(faHeader);

  const faSearch = doc.createElement('input');
  faSearch.type = 'search';
  faSearch.className = 'roster-panel__search';
  faSearch.placeholder = 'Search FA by name';
  faSearch.setAttribute('aria-label', 'Search free agents by name');
  faSection.appendChild(faSearch);

  const faList = doc.createElement('div');
  faList.className = 'roster-panel__list';
  faSection.appendChild(faList);

  const allFa = getFreeAgents();

  function renderFaList() {
    faList.innerHTML = '';

    let candidates = allFa.slice();
    const query = faSearch.value.trim().toLowerCase();
    if (query) {
      candidates = candidates.filter((p) => {
        const name = `${p.firstName || ''} ${p.lastName || ''}`.toLowerCase();
        return name.includes(query);
      });
    }

    candidates.sort((a, b) => getOvr(b) - getOvr(a));

    if (!candidates.length) {
      const empty = doc.createElement('div');
      empty.className = 'roster-panel__empty';
      empty.textContent = 'No free agents available.';
      faList.appendChild(empty);
      return;
    }

    const visible = query ? candidates : candidates.slice(0, 5);

    for (const p of visible) {
      const row = doc.createElement('div');
      row.className = 'roster-panel__row';

      const main = doc.createElement('div');
      main.className = 'roster-panel__row-main';

      const name = doc.createElement('div');
      name.className = 'roster-panel__row-name';
      name.textContent = formatName(p);
      main.appendChild(name);

      const meta = doc.createElement('div');
      meta.className = 'roster-panel__row-meta';

      const posEl = doc.createElement('span');
      posEl.className = 'roster-panel__row-pos';
      posEl.textContent = String(p.position || '').toUpperCase();
      meta.appendChild(posEl);

      const ovrEl = doc.createElement('span');
      ovrEl.className = 'roster-panel__row-ovr';
      ovrEl.textContent = String(getOvr(p));
      meta.appendChild(ovrEl);

      const { label: contractLabel, isFaAfterSeason } = getContractSummary(p);
      if (contractLabel) {
        const contractEl = doc.createElement('span');
        contractEl.className = 'roster-panel__row-contract';
        contractEl.textContent = contractLabel;
        meta.appendChild(contractEl);
      }
      if (isFaAfterSeason) {
        const faEl = doc.createElement('span');
        faEl.className = 'roster-panel__row-fa';
        faEl.textContent = 'FA after season';
        meta.appendChild(faEl);
      }

      main.appendChild(meta);
      row.appendChild(main);

      const actions = doc.createElement('div');
      actions.className = 'roster-panel__row-actions';

      const signBtn = doc.createElement('button');
      signBtn.type = 'button';
      signBtn.className = 'roster-panel__btn roster-panel__btn--primary';
      signBtn.textContent = 'Sign to team';
      signBtn.addEventListener('click', () => {
        setRosterEdit(p.id, { isFreeAgent: false, team: teamAbbr });
      });

      actions.appendChild(signBtn);
      row.appendChild(actions);

      faList.appendChild(row);
    }

    if (!query && candidates.length > visible.length) {
      const more = doc.createElement('div');
      more.className = 'roster-panel__more';
      more.textContent = `Showing top ${visible.length} of ${candidates.length} free agents. Use search to see more.`;
      faList.appendChild(more);
    }
  }

  faSearch.addEventListener('input', () => {
    renderFaList();
  });

  renderFaList();

  wrapper.appendChild(faSection);

  const picksSection = doc.createElement('section');
  picksSection.className = 'roster-panel__section';

  const picksHeader = doc.createElement('div');
  picksHeader.className = 'roster-panel__section-header';

  const picksTitle = doc.createElement('h3');
  picksTitle.className = 'roster-panel__section-title';
  picksTitle.textContent = 'Draft picks';
  picksHeader.appendChild(picksTitle);

  picksSection.appendChild(picksHeader);

  const picksGrid = doc.createElement('div');
  picksGrid.className = 'roster-panel__picks';

  const picks = getDraftPicksForTeam(teamAbbr);
  /** @type {{[round:number]: HTMLInputElement}} */
  const pickInputs = {};

  function commitPicks() {
    const next = {};
    for (let r = 1; r <= 7; r++) {
      const input = pickInputs[r];
      if (!input) continue;
      const v = Number(input.value || 0);
      next[r] = Number.isFinite(v) && v >= 0 ? Math.floor(v) : 0;
    }
    setDraftPicksForTeam(teamAbbr, next);
  }

  for (let round = 1; round <= 7; round++) {
    const row = doc.createElement('div');
    row.className = 'roster-panel__pick-row';

    const label = doc.createElement('span');
    label.className = 'roster-panel__pick-label';
    label.textContent = `R${round}`;
    row.appendChild(label);

    const input = doc.createElement('input');
    input.type = 'number';
    input.min = '0';
    input.step = '1';
    input.value = String(picks[round] || 0);
    input.className = 'roster-panel__pick-input';
    input.addEventListener('change', commitPicks);
    pickInputs[round] = input;
    row.appendChild(input);

    picksGrid.appendChild(row);
  }

  picksSection.appendChild(picksGrid);
  wrapper.appendChild(picksSection);
  el.appendChild(wrapper);
}
