# Technical Specification: E2E Playwright Tests for Roster Cap Management Tool

## Technical Context
- App: Static, client‑side web app under `docs/roster_cap_tool/` (no bundler, no backend).
  - JS modules: CSV loading/validation, cap math, simple state store, UI tabs/tables/modals.
  - Data: `docs/roster_cap_tool/data/MEGA_players.csv`, `MEGA_teams.csv` (committed).
  - External: PapaParse via CDN inside the app HTML.
- Tests: Playwright (TypeScript) E2E.
  - Node.js: v18+ recommended (LTS). NPM or PNPM acceptable; default to npm in scripts.
  - Playwright: ^1.45 (or latest stable).
  - Local server: `python3 -m http.server 8000` from repo root; Playwright `webServer` manages lifecycle.
- CI: GitHub Actions (Ubuntu) with Playwright browsers cache. Chromium required; Firefox/WebKit optional matrix.
- OS dependencies: Python 3.8+ available on runners; no DB/browser plugins required.

## Technical Implementation Brief
- Add a standalone Playwright test harness to the repo without changing how the app builds/ships.
  - Create `package.json` with devDeps: `@playwright/test` and `playwright`.
  - Create `playwright.config.ts` that:
    - Sets `use.baseURL` to `http://127.0.0.1:8000` and a test helper `gotoTool(page)` that navigates to `/docs/roster_cap_tool/`.
    - Defines `webServer` to run `python3 -m http.server 8000` in repo root, `reuseExistingServer: true`.
    - Enables headless by default; allow headed runs via `HEADFUL=1` env.
    - Uses timeouts tuned for CSV parse + render (e.g., 30s per test, 60s expect timeout on first load).
  - Organize tests per feature flow with small helpers for resilient selectors and common steps.
- Make selectors resilient:
  - Prefer role/name (getByRole) and visible text.
  - Introduce minimal `data-testid` attributes at key surfaces to stabilize tests across refactors (see Contracts).
  - Avoid DOM index‑based selectors.
- Determinism: assert numeric changes by comparing against modal preview values (already computed in UI) then check that Cap Summary reflects the same value (exact or integer rounding). Do not hardcode absolute numbers from CSVs.
- State isolation: create a new browser context per test; clear `localStorage` before starting each test via fixture.
- Accessibility spot checks: capture `page.accessibility.snapshot()` for key dialogs; ensure roles present (tabs have `role=tab`, dialogs have `role=dialog`), but do not fail tests for minor issues.
- CI: add a workflow to install Node, Playwright browsers, run tests (Chromium by default). Attach traces on failure.

## Source Code Structure
- Root additions
  - `package.json` — Playwright dev setup and scripts.
  - `playwright.config.ts` — server, baseURL, projects, retries, reporter (list + HTML for local; GitHub on CI).
  - `.github/workflows/e2e.yml` — CI workflow (optional if approved).
  - `tests/e2e/README.md` — how to run locally, debug, CI tips.
- Tests and helpers
  - `tests/e2e/fixtures.ts` — base test with per‑test context, `gotoTool(page)`, `clearStorage(page)`.
  - `tests/e2e/utils/selectors.ts` — central selectors (roles/text + testids), e.g., `teamSelect`, `capAvailable`, `tab(name)`.
  - `tests/e2e/utils/flows.ts` — UI flows: `releaseFirstRosterPlayer`, `signFirstFreeAgent`, `tradeQuick`, `extendFirst`, `convertFirst`.
  - `tests/e2e/smoke.spec.ts` — load app, basic Cap Summary, tabs switch.
  - `tests/e2e/release.spec.ts` — release flow + dead money row + cap summary delta.
  - `tests/e2e/signing.spec.ts` — FA offer/confirm + cap summary delta.
  - `tests/e2e/trade.spec.ts` — trade (quick) flow + dead money.
  - `tests/e2e/extend_convert.spec.ts` — extension + conversion previews and effects.
  - `tests/e2e/filters_tabs.spec.ts` — position filters toggle/persist across re‑renders and tabs.
  - `tests/e2e/projections.spec.ts` — rollover/re‑sign inputs update projections; values persist.
  - `tests/e2e/scenarios.spec.ts` — save, load, reset; chip counts; load list.
- Optional helper scripts
  - `scripts/serve_roster_tool.sh` — runs local server for manual debugging.
  - `scripts/e2e_smoke.sh` — installs deps, runs a small subset (`npx playwright test tests/e2e/smoke.spec.ts`).

## Contracts
Introduce stable `data-testid` attributes where role/text is insufficiently unique. Keep attributes minimal and non‑intrusive.

Targets and attributes to add:
- Team selector
  - `#team-selector select` → `data-testid="team-select"`.
- Cap Summary (`docs/roster_cap_tool/js/ui/capSummary.js`)
  - Container `#cap-summary` → `data-testid="cap-summary"` on the root element created by `mountCapSummary`.
  - Inline spans with `data-testid`:
    - `cap-room`, `cap-spent`, `cap-available`, `cap-available-effective`, `delta-available`.
- Tabs (`docs/roster_cap_tool/index.html` and `js/main.js`)
  - Each tab button: `data-testid="tab-active-roster" | "tab-injured-reserve" | "tab-dead-money" | "tab-projections" | "tab-draft-picks" | "tab-free-agents"`.
- Roster tables (`docs/roster_cap_tool/js/ui/playerTable.js`)
  - Table root for active roster: `data-testid="table-active-roster"`; free agents: `data-testid="table-free-agents"`.
  - Each row for a player: `data-testid="player-row"` and `data-player-id="<id>"`.
  - Action buttons per row:
    - Active roster: `data-testid="action-release"`, `data-testid="action-trade-quick"`, `data-testid="action-extend"`, `data-testid="action-convert"`.
    - Free agents: `data-testid="action-make-offer"`.
- Modals (`docs/roster_cap_tool/js/ui/modals/*.js`)
  - Release: dialog `data-testid="modal-release"`, confirm `data-testid="confirm-release"`.
  - Offer: `data-testid="modal-offer"`, confirm `data-testid="confirm-offer"`; lowball warning element `data-testid="offer-lowball-warning"` if rendered.
  - Extension: `data-testid="modal-extend"`, confirm `data-testid="confirm-extend"`.
  - Conversion: `data-testid="modal-convert"`, confirm `data-testid="confirm-convert"`.
  - Trade In: `data-testid="modal-tradein"`.
- Scenario controls (`docs/roster_cap_tool/js/ui/scenarioControls.js`)
  - Buttons: `data-testid="btn-save"`, `btn-load`, `btn-reset`, `btn-compare`, `btn-trade-in`.
  - Edits/moves chip: `data-testid="chip-edits-moves"`.
- Projections (`docs/roster_cap_tool/js/ui/projections.js`)
  - Horizon slider: `data-testid="projections-horizon"` (on `input[data-horizon]`).
  - Re‑sign input: `data-testid="projections-resign-input"` (on `#proj-resign-ingame-value`).
- Dead Money (`docs/roster_cap_tool/js/ui/deadMoneyTable.js`)
  - Baseline inputs: `data-testid="dead-baseline-y0"` and `data-testid="dead-baseline-y1"` (on the existing inputs with `data-dead`).
  - Save button: `data-testid="dead-save"` (existing `[data-action="save"]`).

Notes:
- Where roles/text are stable (e.g., buttons labeled “Confirm Release”), tests will continue using `getByRole('button', { name: 'Confirm Release' })`. TestIDs are a fallback when UI copy changes.
- No API/DB contracts change; only DOM attributes added for test resilience.

## Delivery Phases
1) Harness setup (minimal viable):
   - Add `package.json`, `playwright.config.ts`, `tests/e2e/fixtures.ts`, `tests/e2e/smoke.spec.ts`.
   - Verify app loads and Cap Summary fields render with numbers.
2) Instrumentation for selectors:
   - Add proposed `data-testid` attributes in UI modules and HTML tabs.
   - Add `tests/e2e/utils/selectors.ts` + `flows.ts` to centralize selectors and flows.
3) Release flow E2E:
   - Select team; capture Cap Summary (available); open first roster row actions; Release; confirm.
   - Assert player removed from Active, appears in FA, Dead Money shows a row; Cap Available equals modal preview.
4) Free‑agent signing E2E:
   - Switch to Free Agents; open first “Make Offer”; accept defaults; confirm.
   - Assert player appears in Active; Cap Available reduced by preview amount.
5) Trade (Quick) E2E:
   - From Active, trade quick on a player; confirm; verify dead money row and cap change.
6) Extension and Conversion E2E:
   - Open Extension modal on a player; tweak inputs minimally; apply; verify cap delta and contract field updates (visible cap hit/new cap).
   - Open Conversion modal; apply default conversion; verify cap delta and future proration badges.
7) Filters and Tabs E2E:
   - Toggle 1–2 position chips for Active & FA tables; verify rows filtered; switch tabs and back; filters persist.
8) Projections E2E:
   - Set Re‑sign budget; horizon slider to 3/5; ensure cap space row values change accordingly and persist while navigating.
9) Scenario Save/Load/Reset E2E:
   - After making edits/moves, Save scenario (generated name), Load it, then Reset; verify counts and roster restore.
10) CI workflow + docs:
   - Add GitHub Actions job; default Chromium. Upload traces/screenshots on failure. Add `tests/e2e/README.md`.

## Verification Strategy
- Local quick checks
  - Sanity: `bash scripts/smoke_roster_cap_tool.sh` — verifies server and assets.
  - Install + run tests:
    - `npm i` (adds Playwright dev deps)
    - `npx playwright install --with-deps`
    - `npx playwright test` (headless) or `HEADFUL=1 npx playwright test`.
  - Debug a single file: `npx playwright test tests/e2e/release.spec.ts --project=chromium --headed --debug`.
- Test patterns
  - Always `await page.goto('/docs/roster_cap_tool/')` via `gotoTool(page)`.
  - Wait for app readiness: Cap Summary container visible and non‑zero numbers present before proceeding.
  - For numeric assertions: read modal preview values (e.g., “New Cap Space”/“Remaining Cap After”), then assert Cap Summary reflects the same value (use `Math.round` or ±$2 tolerance to accommodate formatting).
  - Clear `localStorage` in a `beforeEach` fixture: `await page.evaluate(() => localStorage.clear())`.
  - Accessibility spot check: `await page.accessibility.snapshot()` for a tab and a modal (non‑asserting unless critical attrs missing).
- CI
  - Workflow steps: checkout → setup Node → install deps → `npx playwright install --with-deps` → `npx playwright test --project=chromium`.
  - Artifacts: upload `playwright-report` and traces on failure.
- Helper scripts to add (simple bash):
  - `scripts/serve_roster_tool.sh`: starts the Python HTTP server bound to `127.0.0.1:8000` and prints URL.
  - `scripts/e2e_smoke.sh`: installs deps and runs `tests/e2e/smoke.spec.ts` in Chromium.
- MCP servers to assist verification (optional for agent workflows):
  - Filesystem server — read/write project files to confirm generated artifacts and reports.
  - Shell/Process server — execute npm/playwright commands and Python http.server.
  - Git server — verify changed files and diffs for review.
  - HTTP server — simple GETs to check that `index.html` and CSVs are reachable during smoke steps.
- Sample input artifacts
  - Primary CSVs already committed under `docs/roster_cap_tool/data/` (used by tests).
  - No additional fixtures required; tests may create synthetic in‑memory players via `page.evaluate` only if needed for determinism.

## Appendix: Key Selectors (planned)
- Cap Available: `data-testid="cap-available"` or `page.getByText(/Cap Space/i)` fallback.
- Team select: `data-testid="team-select"`.
- Tab buttons: `data-testid="tab-active-roster"`, `...-free-agents`, etc., or `getByRole('tab', { name: 'Active Roster' })`.
- Row actions on first player (Active): within `data-testid="table-active-roster"` → first `data-testid="player-row"` → buttons per action.
- Modals: dialog with corresponding `data-testid` and confirm button by role/name.

