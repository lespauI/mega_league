import {
  clearDepthSlot,
  getDepthPlanForSelectedTeam,
  clearPlayerFromAllDepthSlots,
  getFreeAgents,
  getPlayersForTeam,
  getState,
  updateDepthSlot,
  setRosterEdit,
} from '../state.js';
import { DEPTH_CHART_SLOTS, getOvr } from '../slots.js';
import { formatName, getContractSummary } from './playerFormatting.js';
import { getDraftPicksForTeam } from '../draftPicks.js';

let backdropEl = null;
let panelEl = null;

function ensureRoot() {
  if (backdropEl && panelEl) return;

  const doc = document;
  backdropEl = doc.createElement('div');
  backdropEl.className = 'slot-editor-backdrop';
  backdropEl.setAttribute('role', 'dialog');
  backdropEl.setAttribute('aria-modal', 'true');
  backdropEl.setAttribute('aria-labelledby', 'slot-editor-title');

  panelEl = doc.createElement('div');
  panelEl.className = 'slot-editor';
  backdropEl.appendChild(panelEl);

  backdropEl.addEventListener('click', (event) => {
    if (event.target === backdropEl) {
      closeSlotEditor();
    }
  });

  backdropEl.addEventListener('keydown', (event) => {
    if (event.key === 'Escape') {
      event.stopPropagation();
      closeSlotEditor();
    }
  });

  doc.body.appendChild(backdropEl);
}

export function closeSlotEditor() {
  if (!backdropEl) return;
  backdropEl.classList.remove('is-open');
  if (panelEl) {
    panelEl.innerHTML = '';
  }
}

function findSlotDefinition(slotId) {
  return DEPTH_CHART_SLOTS.find((s) => s.id === slotId) || null;
}

function getCurrentAssignment(slotId, depthIndex) {
  const plan = getDepthPlanForSelectedTeam();
  if (!plan || !plan.slots || !Array.isArray(plan.slots[slotId])) return { assignment: null, player: null };

  const planSlot = plan.slots[slotId].filter(Boolean);
  const assignment =
    planSlot.find((a) => a && a.depthIndex === depthIndex) || planSlot[depthIndex - 1] || null;

  if (!assignment || !assignment.playerId) {
    return { assignment, player: null };
  }

  const { playersById = {} } = getState();
  const player = playersById[assignment.playerId] || null;
  return { assignment, player };
}

function createPlayerRow(doc, player, options) {
  const { actionLabel, onClick } = options;
  const row = doc.createElement('button');
  row.type = 'button';
  row.className = 'slot-editor__option';

  const main = doc.createElement('div');
  main.className = 'slot-editor__option-main';

  const name = doc.createElement('div');
  name.className = 'slot-editor__option-name';
  name.textContent = formatName(player);
  main.appendChild(name);

  const meta = doc.createElement('div');
  meta.className = 'slot-editor__option-meta';

  const posEl = doc.createElement('span');
  posEl.className = 'slot-editor__option-pos';
  posEl.textContent = String(player.position || '').toUpperCase();
  meta.appendChild(posEl);

  const ovrEl = doc.createElement('span');
  ovrEl.className = 'slot-editor__option-ovr';
  ovrEl.textContent = String(getOvr(player));
  meta.appendChild(ovrEl);

  const { label: contractLabel, isFaAfterSeason } = getContractSummary(player);
  if (contractLabel) {
    const contractEl = doc.createElement('span');
    contractEl.className = 'slot-editor__option-contract';
    contractEl.textContent = contractLabel;
    meta.appendChild(contractEl);
  }

  if (isFaAfterSeason) {
    const faEl = doc.createElement('span');
    faEl.className = 'slot-editor__option-fa';
    faEl.textContent = 'FA after season';
    meta.appendChild(faEl);
  }

  main.appendChild(meta);
  row.appendChild(main);

  const action = doc.createElement('span');
  action.className = 'slot-editor__option-action';
  action.textContent = actionLabel;
  row.appendChild(action);

  row.addEventListener('click', () => {
    onClick();
  });

  return row;
}

export function openSlotEditor({ slotId, depthIndex }) {
  const st = getState();
  const teamAbbr = st.selectedTeam;
  if (!teamAbbr || !slotId || !depthIndex) return;

  ensureRoot();

  const doc = panelEl.ownerDocument || document;
  panelEl.innerHTML = '';
  backdropEl.classList.add('is-open');

  const slot = findSlotDefinition(slotId);
  const { assignment, player: currentPlayer } = getCurrentAssignment(slotId, depthIndex);

  const depthPlan = getDepthPlanForSelectedTeam();

  const header = doc.createElement('div');
  header.className = 'slot-editor__header';

  const title = doc.createElement('h2');
  title.className = 'slot-editor__title';
  title.id = 'slot-editor-title';
  title.textContent = `${slot ? slot.label : slotId} — Depth ${depthIndex}`;
  header.appendChild(title);

  const closeBtn = doc.createElement('button');
  closeBtn.type = 'button';
  closeBtn.className = 'slot-editor__close';
  closeBtn.textContent = '×';
  closeBtn.setAttribute('aria-label', 'Close slot editor');
  closeBtn.addEventListener('click', () => {
    closeSlotEditor();
  });
  header.appendChild(closeBtn);

  panelEl.appendChild(header);

  // Placeholders (Draft picks / Trade / FA) — shown at the top for quick access
  const placeholdersSectionTop = doc.createElement('section');
  placeholdersSectionTop.className = 'slot-editor__section';

  const placeholdersHeadingTop = doc.createElement('h3');
  placeholdersHeadingTop.className = 'slot-editor__section-title';
  placeholdersHeadingTop.textContent = 'Placeholders';
  placeholdersSectionTop.appendChild(placeholdersHeadingTop);

  const placeholdersRowTop = doc.createElement('div');
  placeholdersRowTop.className = 'slot-editor__placeholders';

  const draftPicks = getDraftPicksForTeam(teamAbbr);
  /** @type {{[round:number]:number}} */
  const usedByRound = { 1: 0, 2: 0, 3: 0, 4: 0, 5: 0, 6: 0, 7: 0 };

  if (depthPlan && depthPlan.slots) {
    for (const slotKey of Object.keys(depthPlan.slots)) {
      const arr = depthPlan.slots[slotKey];
      if (!Array.isArray(arr)) continue;
      for (const entry of arr) {
        if (!entry || !entry.acquisition) continue;
        const acq = String(entry.acquisition);
        if (acq.startsWith('draftR')) {
          const round = Number(acq.slice(6));
          if (round >= 1 && round <= 7) {
            usedByRound[round] = (usedByRound[round] || 0) + 1;
          }
        }
      }
    }
  }

  const placeholderDefsTop = [];
  for (let r = 1; r <= 7; r++) {
    placeholderDefsTop.push({
      label: `Draft R${r}`,
      acquisition: /** @type {import('../state.js').AcquisitionType} */ (`draftR${r}`),
      placeholder: `Draft R${r}`,
      round: r,
    });
  }
  placeholderDefsTop.push(
    { label: 'Trade', acquisition: 'trade', placeholder: 'Trade' },
    { label: 'FA', acquisition: 'faPlaceholder', placeholder: 'FA' },
  );

  for (const item of placeholderDefsTop) {
    const btn = doc.createElement('button');
    btn.type = 'button';
    btn.className = 'slot-editor__pill';

    let label = item.label;
    /** @type {number|undefined} */
    let remaining;

    if (Object.prototype.hasOwnProperty.call(item, 'round')) {
      const round = /** @type {number} */ (item.round);
      const total = Number(draftPicks[round] || 0);
      const used = Number(usedByRound[round] || 0);
      const isCurrent =
        assignment && assignment.acquisition === item.acquisition ? 1 : 0;
      remaining = Math.max(0, total - (used - isCurrent));
      if (total > 0 && remaining >= 0 && remaining < total) {
        label = `${label} (${remaining} left)`;
      }
      if (!total || remaining <= 0) {
        btn.disabled = !isCurrent;
      }
      btn.title = `Round ${round} draft placeholder`;
    }

    btn.textContent = label;

    btn.addEventListener('click', () => {
      if (btn.disabled) return;
      updateDepthSlot({
        teamAbbr,
        slotId,
        depthIndex,
        assignment: {
          acquisition: item.acquisition,
          placeholder: item.placeholder,
        },
      });
      closeSlotEditor();
    });
    placeholdersRowTop.appendChild(btn);
  }

  placeholdersSectionTop.appendChild(placeholdersRowTop);
  panelEl.appendChild(placeholdersSectionTop);

  if (currentPlayer || (assignment && assignment.placeholder)) {
    const current = doc.createElement('div');
    current.className = 'slot-editor__current';

    const label = doc.createElement('div');
    label.className = 'slot-editor__current-label';
    label.textContent = 'Current assignment';
    current.appendChild(label);

    const value = doc.createElement('div');
    value.className = 'slot-editor__current-value';
    if (currentPlayer) {
      value.textContent = formatName(currentPlayer);
    } else if (assignment && assignment.placeholder) {
      value.textContent = assignment.placeholder;
    }
    current.appendChild(value);

    panelEl.appendChild(current);
  }

  const rosterSection = doc.createElement('section');
  rosterSection.className = 'slot-editor__section';

  const rosterHeading = doc.createElement('h3');
  rosterHeading.className = 'slot-editor__section-title';
  rosterHeading.textContent = 'Team roster';
  rosterSection.appendChild(rosterHeading);

  const rosterList = doc.createElement('div');
  rosterList.className = 'slot-editor__list';

  const teamPlayers = getPlayersForTeam(teamAbbr);
  const rosterCandidates = slot ? getEligiblePlayersForSlot(slot, teamPlayers) : teamPlayers;

  if (rosterCandidates.length === 0) {
    const empty = doc.createElement('div');
    empty.className = 'slot-editor__empty';
    empty.textContent = 'No eligible players on roster for this position.';
    rosterList.appendChild(empty);
  } else {
    for (const p of rosterCandidates) {
      const row = createPlayerRow(doc, p, {
        actionLabel: 'Assign',
        onClick: () => {
          updateDepthSlot({
            teamAbbr,
            slotId,
            depthIndex,
            assignment: {
              acquisition: 'existing',
              playerId: String(p.id),
            },
          });
          closeSlotEditor();
        },
      });
      rosterList.appendChild(row);
    }
  }

  rosterSection.appendChild(rosterList);
  panelEl.appendChild(rosterSection);

  const faSection = doc.createElement('section');
  faSection.className = 'slot-editor__section';

  const faHeading = doc.createElement('h3');
  faHeading.className = 'slot-editor__section-title';
  faHeading.textContent = 'Free agents';
  faSection.appendChild(faHeading);

  const faFilters = doc.createElement('div');
  faFilters.className = 'slot-editor__filters';

  const searchInput = doc.createElement('input');
  searchInput.type = 'search';
  searchInput.className = 'slot-editor__search';
  searchInput.placeholder = 'Search FA by name';
  searchInput.setAttribute('aria-label', 'Search free agents by name');
  faFilters.appendChild(searchInput);

  const posSelect = doc.createElement('select');
  posSelect.className = 'slot-editor__position-filter';
  const optionSlot = doc.createElement('option');
  optionSlot.value = 'slot';
  optionSlot.textContent = 'Slot positions';
  posSelect.appendChild(optionSlot);
  const optionAll = doc.createElement('option');
  optionAll.value = 'all';
  optionAll.textContent = 'All positions';
  posSelect.appendChild(optionAll);
  posSelect.value = 'slot';
  faFilters.appendChild(posSelect);

  faSection.appendChild(faFilters);

  const faList = doc.createElement('div');
  faList.className = 'slot-editor__list';
  faSection.appendChild(faList);

  const allFa = getFreeAgents();

  function renderFaList() {
    faList.innerHTML = '';
    let candidates;
    if (slot && posSelect.value === 'slot') {
      candidates = getEligiblePlayersForSlot(slot, allFa);
    } else if (slot) {
      candidates = [...allFa];
    } else {
      candidates = [...allFa];
    }

    const query = searchInput.value.trim().toLowerCase();
    if (query) {
      candidates = candidates.filter((p) => {
        const name = `${p.firstName || ''} ${p.lastName || ''}`.toLowerCase();
        return name.includes(query);
      });
    }

    candidates.sort((a, b) => getOvr(b) - getOvr(a));

    if (!candidates.length) {
      const empty = doc.createElement('div');
      empty.className = 'slot-editor__empty';
      empty.textContent = 'No free agents match the filters.';
      faList.appendChild(empty);
      return;
    }

    const visible = query ? candidates : candidates.slice(0, 5);

    for (const p of visible) {
      const row = createPlayerRow(doc, p, {
        actionLabel: 'Sign & assign',
        onClick: () => {
          setRosterEdit(p.id, { isFreeAgent: false, team: teamAbbr });
          updateDepthSlot({
            teamAbbr,
            slotId,
            depthIndex,
            assignment: {
              acquisition: 'faPlayer',
              playerId: String(p.id),
            },
          });
          closeSlotEditor();
        },
      });
      faList.appendChild(row);
    }

    if (!query && candidates.length > visible.length) {
      const more = doc.createElement('div');
      more.className = 'slot-editor__more';
      more.textContent = `Showing top ${visible.length} of ${candidates.length} free agents. Use search or position filter to see more.`;
      faList.appendChild(more);
    }
  }

  searchInput.addEventListener('input', () => {
    renderFaList();
  });
  posSelect.addEventListener('change', () => {
    renderFaList();
  });

  renderFaList();

  panelEl.appendChild(faSection);
  const footer = doc.createElement('div');
  footer.className = 'slot-editor__footer';

  if (currentPlayer) {
    const cutBtn = doc.createElement('button');
    cutBtn.type = 'button';
    cutBtn.className = 'slot-editor__cut';
    cutBtn.textContent = 'Cut to FA';
    cutBtn.addEventListener('click', () => {
      clearPlayerFromAllDepthSlots(currentPlayer.id);
      setRosterEdit(currentPlayer.id, { isFreeAgent: true, team: '' });
      closeSlotEditor();
    });
    footer.appendChild(cutBtn);
  }

  const clearBtn = doc.createElement('button');
  clearBtn.type = 'button';
  clearBtn.className = 'slot-editor__clear';
  clearBtn.textContent = 'Clear slot';
  clearBtn.addEventListener('click', () => {
    clearDepthSlot({ teamAbbr, slotId, depthIndex });
    closeSlotEditor();
  });
  footer.appendChild(clearBtn);

  panelEl.appendChild(footer);

  const focusTarget =
    panelEl.querySelector('button.slot-editor__pill') ||
    panelEl.querySelector('button.slot-editor__close') ||
    panelEl.querySelector('button.slot-editor__option');
  if (focusTarget && typeof focusTarget.focus === 'function') {
    focusTarget.focus();
  }
}

function getEligiblePlayersForSlot(slot, players) {
  if (!slot) return players || [];
  const primaryPositions = slot.positions || [];
  if (!primaryPositions.length) return players || [];
  const normalizedPositions = primaryPositions.map((p) => String(p || '').toUpperCase());
  return (players || []).filter((p) =>
    normalizedPositions.includes(String(p.position || '').toUpperCase())
  );
}
