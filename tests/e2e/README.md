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
 - By default tests run headless; traces attach on first retry.
- If the server is already running, Playwright reuses it.

Troubleshooting
- Port conflicts: the harness uses port `8000`. If occupied locally, stop the other server or change `webServer.port` and `use.baseURL` consistently.
- Missing browsers: run `npm run pw:install` to install Playwright browsers and system deps.
- Traces: to inspect a local failure captured on retry, open the trace via `npx playwright show-trace <path-to-trace.zip>` found in `test-results/`.
