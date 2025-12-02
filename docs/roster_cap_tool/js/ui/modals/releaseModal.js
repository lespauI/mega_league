import { getState, setState, getCapSummary, getYearContextForSelectedTeam } from '../../state.js';
import { simulateRelease } from '../../capMath.js';
import { enhanceDialog } from '../a11y.js';
import { contextualizePlayer } from '../../context.js';

function fmtMoney(n) {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    maximumFractionDigits: 0,
  }).format(n || 0);
}

/**
 * Open a <dialog> modal to confirm releasing a player.
 * Shows Dead Cap Hit, Cap Savings, and New Cap Space preview.
 * On confirm, applies the move: marks player as FA and updates cap moves.
 * @param {import('../../models.js').Player} player
 */
export function openReleaseModal(player) {
  const st = getState();
  const team = st.teams.find((t) => t.abbrName === st.selectedTeam);
  if (!team) return;

  // If viewing a future Year Context, adjust the player numbers to that year
  const offset = getYearContextForSelectedTeam();
  const effPlayer = (() => {
    if (!offset || offset <= 0) return player;
    const pctx = contextualizePlayer(player, team, offset);
    return {
      ...player,
      capHit: Number(pctx.capHit_ctx || player.capHit || 0),
      contractYearsLeft: Number(pctx.contractYearsLeft_ctx != null ? pctx.contractYearsLeft_ctx : player.contractYearsLeft || 0),
      capReleasePenalty: Number(pctx.capReleasePenalty_ctx || player.capReleasePenalty || 0),
      capReleaseNetSavings: Number(pctx.capReleaseNetSavings_ctx || player.capReleaseNetSavings || 0),
      isFreeAgent: Boolean(pctx.isFreeAgent_ctx || player.isFreeAgent),
    };
  })();

  // Use current dynamic capAvailable from snapshot, not baseline
  const snap = getCapSummary();
  const baseCap = Number.isFinite(Number(snap.capAvailableEffective)) ? Number(snap.capAvailableEffective) : (snap.capAvailable || 0);
  const effectiveTeam = { ...team, capAvailable: baseCap };
  const sim = simulateRelease(effectiveTeam, effPlayer);

  const name = `${player.firstName || ''} ${player.lastName || ''}`.trim();

  const root = document.getElementById('modals-root') || document.body;
  const dlg = document.createElement('dialog');
  dlg.setAttribute('data-testid', 'modal-release');
  dlg.innerHTML = `
    <h3 style="margin-top:0">Release ${name}?</h3>
    <div class="grid" style="display:grid; grid-template-columns: 1fr 1fr; gap:.5rem;">
      <div><div style="color:var(--muted); font-size:.85em">Dead Cap Hit</div><div class="money-neg">${fmtMoney(effPlayer.capReleasePenalty || 0)}</div></div>
      <div><div style="color:var(--muted); font-size:.85em">Cap Savings</div><div class="money-pos">${fmtMoney(sim.savings || effPlayer.capReleaseNetSavings || 0)}</div></div>
      <div><div style="color:var(--muted); font-size:.85em">New Cap Space</div><div>${fmtMoney(sim.newCapSpace || 0)}</div></div>
    </div>
    <p style="margin:.5rem 0 0; color:var(--muted); font-size:.85em">This will remove the player from the active roster and apply current-year dead money.</p>
    <div class="modal-actions">
      <button class="btn" data-action="cancel" data-testid="cancel-release">Cancel</button>
      <button class="btn danger" data-action="confirm" data-testid="confirm-release">Confirm Release</button>
    </div>
  `;

  function close() {
    try { dlg.close(); } catch {}
    dlg.remove();
  }

  dlg.addEventListener('click', (e) => {
    // Close when clicking outside dialog content in supported browsers
    const r = dlg.getBoundingClientRect();
    if (e.target === dlg && (e.clientX < r.left || e.clientX > r.right || e.clientY < r.top || e.clientY > r.bottom)) {
      close();
    }
  });

  dlg.querySelector('[data-action="cancel"]')?.addEventListener('click', close);
  dlg.querySelector('[data-action="confirm"]')?.addEventListener('click', () => {
    // Recompute with latest snapshot just in case
    const latestSnap = getCapSummary();
    const baseCap2 = Number.isFinite(Number(latestSnap.capAvailableEffective)) ? Number(latestSnap.capAvailableEffective) : (latestSnap.capAvailable || 0);
    const effTeam = { ...team, capAvailable: baseCap2 };
    const res = simulateRelease(effTeam, effPlayer);

    // Apply move to state: push move, mark player FA and clear team
    const current = getState();
    const moves = [...current.moves, res.move];
    const players = current.players.map((p) => {
      if (p.id !== player.id) return p;
      return { ...p, isFreeAgent: true, team: '' };
    });
    const ledgerEntry = {
      playerId: player.id,
      name,
      type: 'release',
      penaltyCurrentYear: res.penaltyCurrentYear,
      penaltyNextYear: res.penaltyNextYear,
      penaltyTotal: res.penaltyTotal,
      at: Date.now(),
    };
    const deadMoneyLedger = Array.isArray(current.deadMoneyLedger) ? [...current.deadMoneyLedger, ledgerEntry] : [ledgerEntry];
    setState({ moves, players, deadMoneyLedger });

    const after = getCapSummary();
    const afterCap = Number.isFinite(Number(after.capAvailableEffective)) ? Number(after.capAvailableEffective) : (after.capAvailable || 0);
    console.assert(afterCap === res.newCapSpace, '[release] capAvailable matches previewed newCapSpace');
    close();
  });

  root.appendChild(dlg);
  enhanceDialog(dlg, { opener: document.activeElement });
  try { dlg.showModal(); } catch { dlg.show(); }
}

export default { openReleaseModal };
