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

CI
- Workflow: `.github/workflows/e2e.yml` runs on push/PR using `ubuntu-latest`.
- Steps: `npm ci` → `npx playwright install --with-deps` → `npx playwright test --project=chromium --reporter=github`.
- Artifacts: on failure, `test-results/**/trace*.zip` are uploaded for debugging.
- Node: uses Node 20 with npm cache; Python 3 is preinstalled on GitHub runners for the static server.

Troubleshooting
- Port conflicts: the harness uses port `8000`. If occupied locally, stop the other server or change `webServer.port` and `use.baseURL` consistently.
- Missing browsers: run `npm run pw:install` to install Playwright browsers and system deps.
- Traces: when a CI failure occurs, download the `playwright-traces` artifact and open the trace via `npx playwright show-trace <trace.zip>`.
