import {
  clearPlayerFromAllDepthSlots,
  getPlayersForTeam,
  getFreeAgents,
  getState,
  setRosterEdit,
} from '../state.js';
import { getOvr } from '../slots.js';
import { formatName, getContractSummary } from './playerFormatting.js';

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

  const rosterSection = doc.createElement('section');
  rosterSection.className = 'roster-panel__section';
  const rosterHeader = doc.createElement('div');
  rosterHeader.className = 'roster-panel__section-header';
  const rosterTitle = doc.createElement('h3');
  rosterTitle.className = 'roster-panel__section-title';
  rosterTitle.textContent = 'Team roster';
  rosterHeader.appendChild(rosterTitle);
  rosterSection.appendChild(rosterHeader);

  const rosterList = doc.createElement('div');
  rosterList.className = 'roster-panel__list';

  const rosterPlayers = getPlayersForTeam(teamAbbr).slice().sort((a, b) => {
    const posA = String(a.position || '').toUpperCase();
    const posB = String(b.position || '').toUpperCase();
    if (posA === posB) return getOvr(b) - getOvr(a);
    return posA.localeCompare(posB);
  });

  if (!rosterPlayers.length) {
    const empty = doc.createElement('div');
    empty.className = 'roster-panel__empty';
    empty.textContent = 'No players on this team.';
    rosterList.appendChild(empty);
  } else {
    for (const p of rosterPlayers) {
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

      const cutBtn = doc.createElement('button');
      cutBtn.type = 'button';
      cutBtn.className = 'roster-panel__btn roster-panel__btn--danger';
      cutBtn.textContent = 'Cut to FA';
      cutBtn.addEventListener('click', () => {
        clearPlayerFromAllDepthSlots(p.id);
        setRosterEdit(p.id, { isFreeAgent: true, team: '' });
      });
      actions.appendChild(cutBtn);

      if (st.teams && st.teams.length > 1) {
        const tradeSelect = doc.createElement('select');
        tradeSelect.className = 'roster-panel__trade-select';

        const tradePlaceholder = doc.createElement('option');
        tradePlaceholder.value = '';
        tradePlaceholder.textContent = 'Trade to...';
        tradeSelect.appendChild(tradePlaceholder);

        for (const t of st.teams) {
          if (!t || t.abbrName === teamAbbr) continue;
          const opt = doc.createElement('option');
          opt.value = t.abbrName;
          opt.textContent = t.abbrName;
          tradeSelect.appendChild(opt);
        }

        tradeSelect.addEventListener('change', () => {
          const target = tradeSelect.value;
          if (!target || target === teamAbbr) return;
          clearPlayerFromAllDepthSlots(p.id);
          setRosterEdit(p.id, { isFreeAgent: false, team: target });
          tradeSelect.value = '';
        });

        actions.appendChild(tradeSelect);
      }

      row.appendChild(actions);
      rosterList.appendChild(row);
    }
  }

  rosterSection.appendChild(rosterList);
  wrapper.appendChild(rosterSection);

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

    for (const p of candidates) {
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
  }

  faSearch.addEventListener('input', () => {
    renderFaList();
  });

  renderFaList();

  wrapper.appendChild(faSection);
  el.appendChild(wrapper);
}

