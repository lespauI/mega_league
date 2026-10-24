/** Shared PapaParse-backed CSV transport for the browser tools. */
export function loadCsvRows(url, parser = globalThis.Papa) {
  if (!parser || typeof parser.parse !== 'function') {
    return Promise.reject(new Error('The CSV parser did not load.'));
  }
  return new Promise((resolve, reject) => {
    parser.parse(url, {
      download: true,
      header: true,
      skipEmptyLines: true,
      complete: (result) => {
        const errors = Array.isArray(result?.errors) ? result.errors : [];
        if (errors.length) {
          reject(new Error(`CSV parse failed for ${url}: ${errors.map((entry) => entry.message || entry.code || 'invalid row').join('; ')}`));
          return;
        }
        resolve(Array.isArray(result?.data) ? result.data : []);
      },
      error: (error) => reject(error instanceof Error ? error : new Error(String(error))),
    });
  });
}
