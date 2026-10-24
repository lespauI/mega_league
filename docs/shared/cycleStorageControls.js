import {
  copyLegacyEntries,
  currentCycleIdentity,
  exportStorageBackup,
  importStorageBackup,
  legacyEntries,
} from './cycleStorage.js';

function button(label, action) {
  const element = document.createElement('button');
  element.type = 'button';
  element.textContent = label;
  element.addEventListener('click', action);
  return element;
}

function downloadBackup(namespace, keys) {
  const text = exportStorageBackup(namespace, keys);
  const blob = new Blob([text], { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = `${namespace}-saved-data.json`;
  link.click();
  URL.revokeObjectURL(url);
}

export function mountCycleStorageControls(containerId, { namespace, legacyKeys, title }) {
  const container = document.getElementById(containerId);
  if (!container) return;
  const cycle = currentCycleIdentity();
  if (!cycle) throw new Error('Cycle storage was not configured before controls mounted.');
  container.replaceChildren();
  container.style.cssText = 'margin:.75rem 0;padding:.65rem .8rem;border:1px solid #64748b55;border-radius:.5rem;font-size:.9rem;';

  const heading = document.createElement('strong');
  heading.textContent = `${title} saved data · ${cycle.label}`;
  const text = document.createElement('p');
  text.textContent = 'Saved data is stored per edition, season, and calendar year. Legacy entries are kept until you explicitly copy or export them.';
  text.style.margin = '.35rem 0 .5rem';
  const status = document.createElement('span');
  status.setAttribute('role', 'status');
  status.style.marginLeft = '.5rem';
  container.append(heading, text);

  const oldKeys = legacyEntries(namespace, legacyKeys);
  if (oldKeys.length) {
    const copy = button(`Copy ${oldKeys.length} legacy item${oldKeys.length === 1 ? '' : 's'} into this cycle`, () => {
      const confirmed = window.confirm(`Copy old ${title} saved data into ${cycle.label}? The old entries will remain unchanged. Review whether they apply to this roster before continuing.`);
      if (!confirmed) return;
      try {
        const result = copyLegacyEntries(namespace, legacyKeys);
        status.textContent = `Copied ${result.copied}; left ${result.skipped} existing cycle entries unchanged. Reloading…`;
        window.location.reload();
      } catch (error) { status.textContent = String(error.message || error); }
    });
    container.append(copy);
  }

  container.append(button('Export backup', () => {
    try { downloadBackup(namespace, legacyKeys); status.textContent = 'Backup downloaded.'; }
    catch (error) { status.textContent = String(error.message || error); }
  }));

  const file = document.createElement('input');
  file.type = 'file';
  file.accept = 'application/json,.json';
  file.setAttribute('aria-label', `Import ${title} saved-data backup`);
  file.addEventListener('change', async () => {
    const selected = file.files?.[0];
    if (!selected) return;
    if (!window.confirm(`Copy values from ${selected.name} into ${cycle.label}? Existing cycle values and all legacy entries will be preserved.`)) {
      file.value = '';
      return;
    }
    try {
      const result = importStorageBackup(await selected.text(), namespace, legacyKeys);
      status.textContent = `Imported ${result.imported}; skipped ${result.skipped} existing cycle entries. Reloading…`;
      window.location.reload();
    } catch (error) { status.textContent = String(error.message || error); }
    file.value = '';
  });
  container.append(file, status);
}
