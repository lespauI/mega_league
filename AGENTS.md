# Repository Guidelines

## Project Structure & Module Organization

This is a Madden NFL fantasy league analytics platform (MEGA League) with four domains:

- **Playoff + draft race** — Monte Carlo playoff probabilities, SOS calculations, draft pick projections. Orchestrated by `scripts/run_all_playoff_analysis.py`.
- **Stats aggregation** — Trade-aware team/player stats from `MEGA_*.csv` exports. Orchestrated by `scripts/run_all_stats.py`.
- **SoS Season 2 (ELO)** — ELO-based strength of schedule. Run via `scripts/calc_sos_season2_elo.py`.
- **Roster / cap tool** — Spotrac-style interactive salary cap manager in `docs/roster_cap_tool/` (vanilla JS, no framework).

Data flows: `MEGA_*.csv` (root) → Python scripts → `output/` (CSV/JSON) → `docs/` (HTML dashboards served via GitHub Pages). The `stats_scripts/` directory contains stats-specific aggregation modules shared by `scripts/run_all_stats.py`.

## Build, Test, and Development Commands

```bash
# Full pipeline (SoS S2 + playoff/draft + stats + index page)
python3 scripts/run_all.py

# Playoff + draft race only
python3 scripts/run_all_playoff_analysis.py

# Stats only (team/player usage + rankings joins)
python3 scripts/run_all_stats.py

# Python unit tests
python3 -m unittest
python3 -m unittest tests/test_power_rankings_roster.py   # single file

# Playwright E2E tests (roster cap tool)
npm install && npm run pw:install
npm run test:e2e                         # full suite, headless
npm run test:e2e -- --grep cap           # filtered subset
npm run test:e2e:headed                  # headed mode
npm run pw:report                        # view last report

# Local dev server (serves docs + root CSVs)
python3 -m http.server 8000
```

## Testing Guidelines

- **Python unit tests** use `unittest` (stdlib only). Tests live in `tests/`. Run with `python3 -m unittest`.
- **E2E tests** use Playwright (TypeScript) in `tests/e2e/`. Config: `playwright.config.ts`. Playwright auto-starts a local HTTP server on port 8000. Tests run in Chromium with two projects: one clears storage, one persists it.
- **Verification scripts** (`scripts/verify_*.py`) validate data pipeline outputs. Run after generating new data.
- **Smoke tests** live in `scripts/smoke/`.

## Coding Style & Naming Conventions

- Python scripts use stdlib only (no pip dependencies for core functionality). A virtualenv (`myenv/`) exists for optional ML work (`numpy`, `scipy`, `sklearn`).
- JavaScript in `docs/` is vanilla ES modules (`"type": "module"` in `docs/roster_cap_tool/js/package.json`).
- No linter/formatter configs are enforced. Follow existing patterns in the codebase.

## Commit & Pull Request Guidelines

Commit messages are short, lowercase descriptions of the change (e.g., "Flames bug fix", "stats update", "matchup details analytics text"). Feature branches use descriptive kebab-case names and are merged via PR with squash or merge commits. Branch naming pattern: `mega-<feature>-<short-id>`.
