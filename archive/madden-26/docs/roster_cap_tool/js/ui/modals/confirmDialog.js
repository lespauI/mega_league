import { enhanceDialog } from '../a11y.js';

/**
 * Show an app-styled confirmation dialog using <dialog> and return a Promise<boolean>.
 * Options:
 * - title: string
 * - message: string (plain text; line breaks supported)
 * - confirmText?: string ('Confirm')
 * - cancelText?: string ('Cancel')
 * - danger?: boolean (styles confirm as destructive)
 * - rememberKey?: string (localStorage key to skip next time)
 * - rememberLabel?: string (label for the remember checkbox)
 *
 * Resolves true on confirm, false on cancel/close/error.
 */
export function confirmWithDialog(opts) {
  const {
    title,
    message,
    confirmText = 'Confirm',
    cancelText = 'Cancel',
    danger = false,
    rememberKey,
    rememberLabel = "Don't ask again",
  } = opts || {};

  // If user previously opted to skip this confirm, honor it safely.
  if (rememberKey) {
    try {
      const raw = localStorage.getItem(rememberKey);
      if (raw && (raw === 'true' || raw === '1')) {
        return Promise.resolve(true);
      }
    } catch {}
  }

  return new Promise((resolve) => {
    try {
      const root = document.getElementById('modals-root') || document.body;
      const dlg = document.createElement('dialog');
      dlg.innerHTML = `
        <h3 style="margin-top:0" data-dialog-title></h3>
        <div id="confirm-msg" style="white-space: pre-wrap; margin-top:.25rem;"></div>
        ${rememberKey ? `
          <label style=\"display:flex; align-items:center; gap:.5rem; margin-top:.75rem;\">
            <input id=\"confirm-remember\" type=\"checkbox\" />
            <span>${rememberLabel}</span>
          </label>
        ` : ''}
        <div class="modal-actions">
          <button class="btn" data-action="cancel"></button>
          <button class="btn ${danger ? 'danger' : 'primary'}" data-action="confirm"></button>
        </div>
      `;

      const titleEl = dlg.querySelector('[data-dialog-title]');
      const msgEl = dlg.querySelector('#confirm-msg');
      const btnCancel = dlg.querySelector('[data-action="cancel"]');
      const btnConfirm = dlg.querySelector('[data-action="confirm"]');
      const rememberEl = /** @type {HTMLInputElement|null} */(dlg.querySelector('#confirm-remember'));

      if (titleEl) titleEl.textContent = title || 'Confirm';
      if (msgEl) msgEl.textContent = message || '';
      if (btnCancel) btnCancel.textContent = cancelText || 'Cancel';
      if (btnConfirm) btnConfirm.textContent = confirmText || 'Confirm';

      const cleanup = () => { try { dlg.close(); } catch {}; dlg.remove(); };

      btnCancel?.addEventListener('click', () => { cleanup(); resolve(false); });
      btnConfirm?.addEventListener('click', () => {
        if (rememberKey && rememberEl?.checked) {
          try { localStorage.setItem(rememberKey, 'true'); } catch {}
        }
        cleanup();
        resolve(true);
      });

      // Click outside to cancel
      dlg.addEventListener('click', (e) => {
        const r = dlg.getBoundingClientRect();
        if (e.target === dlg && (e.clientX < r.left || e.clientX > r.right || e.clientY < r.top || e.clientY > r.bottom)) {
          cleanup();
          resolve(false);
        }
      });

      root.appendChild(dlg);
      enhanceDialog(/** @type {HTMLDialogElement} */(dlg), { opener: document.activeElement });
      try { dlg.showModal(); } catch { dlg.show(); }
    } catch (err) {
      // If anything goes wrong, fail safe by resolving false.
      resolve(false);
    }
  });
}

export default { confirmWithDialog };

