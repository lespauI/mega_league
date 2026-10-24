/**
 * Accessibility helpers for dialogs and focus management.
 */

/**
 * Return focusable elements within a container.
 * @param {HTMLElement} root
 */
export function getFocusable(root) {
  const sel = [
    'a[href]',
    'area[href]',
    'button:not([disabled])',
    'input:not([disabled]):not([type="hidden"])',
    'select:not([disabled])',
    'textarea:not([disabled])',
    '[tabindex]:not([tabindex="-1"])',
    'summary'
  ].join(',');
  return /** @type {HTMLElement[]} */(Array.from(root.querySelectorAll(sel)).filter((el) => {
    const he = /** @type {HTMLElement} */(el);
    const style = window.getComputedStyle(he);
    return style.visibility !== 'hidden' && style.display !== 'none';
  }));
}

/**
 * Enhance a native <dialog> with focus trapping and accessible attributes.
 * - Restores focus to opener on close
 * - Traps Tab within dialog
 * - Sets role/aria-modal and aria-labelledby
 * @param {HTMLDialogElement} dlg
 * @param {{ opener?: Element|null, labelledBySelector?: string }} [opts]
 */
export function enhanceDialog(dlg, opts = {}) {
  const opener = opts.opener || document.activeElement;

  // A11y attributes
  dlg.setAttribute('role', 'dialog');
  dlg.setAttribute('aria-modal', 'true');
  const titleEl = dlg.querySelector(opts.labelledBySelector || 'h3, h2, [data-dialog-title]');
  if (titleEl) {
    if (!titleEl.id) titleEl.id = `dlg-title-${Date.now()}-${Math.floor(Math.random()*1000)}`;
    dlg.setAttribute('aria-labelledby', titleEl.id);
  }

  // Initial focus
  const focusables = getFocusable(dlg);
  const toFocus = /** @type {HTMLElement} */(focusables[0] || dlg);
  queueMicrotask(() => toFocus.focus());

  function handleKeydown(e) {
    if (e.key === 'Tab') {
      const items = getFocusable(dlg);
      if (!items.length) return;
      const first = items[0];
      const last = items[items.length - 1];
      if (e.shiftKey) {
        if (document.activeElement === first) {
          last.focus();
          e.preventDefault();
        }
      } else {
        if (document.activeElement === last) {
          first.focus();
          e.preventDefault();
        }
      }
    } else if (e.key === 'Escape') {
      try { dlg.close(); } catch {}
    }
  }

  dlg.addEventListener('keydown', handleKeydown);
  const restore = () => {
    dlg.removeEventListener('keydown', handleKeydown);
    if (opener && (/** @type {HTMLElement} */(opener)).focus) {
      /** @type {HTMLElement} */(opener).focus();
    }
  };
  dlg.addEventListener('close', restore, { once: true });
  dlg.addEventListener('cancel', restore, { once: true });
}

export default { enhanceDialog, getFocusable };

