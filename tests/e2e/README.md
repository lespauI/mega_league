End-to-End Tests — Playwright

Quick start
- Install deps: `npm i && npx playwright install --with-deps`
- Run tests: `npx playwright test`
- Headed mode: `npm run test:e2e:headed`
- UI mode: `npm run test:e2e:ui`

Harness details
- Base URL: `http://127.0.0.1:8000`
- Static server: Playwright starts `python3 -m http.server 8000` automatically.
- Target app: `http://127.0.0.1:8000/docs/roster_cap_tool/`

Notes
- The tests do not require a build; the tool is a static app under `docs/`.
- On CI, Chromium-only tests run headless; traces attach on first retry.
- If the server is already running, Playwright reuses it.

