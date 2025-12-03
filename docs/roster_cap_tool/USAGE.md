# Roster Cap Management Tool — Usage

Interactive, Spotrac‑style salary cap manager for Madden. Runs as a static web app (no build, no backend). Loads `MEGA_players.csv` and `MEGA_teams.csv` from the `docs/roster_cap_tool/data/` folder and updates cap figures in real time as you release, trade, extend, convert, and sign players.

## Requirements
- Modern browser (Chrome, Edge, Firefox, Safari)
- CSV data in `docs/roster_cap_tool/data/`:
  - `MEGA_players.csv`
  - `MEGA_teams.csv`
- Optional helper scripts (local verification):
  - `scripts/sync_data_to_docs.sh`
  - `scripts/verify_cap_math.py`
  - `scripts/smoke_roster_cap_tool.sh`

## Data Setup
Place fresh CSV exports at the repo root, then sync them into the Pages data folder:

```bash
bash scripts/sync_data_to_docs.sh          # copies MEGA_players.csv + MEGA_teams.csv
# or
bash scripts/sync_data_to_docs.sh --all    # copies all MEGA_*.csv to docs/roster_cap_tool/data
```

This populates:
- `docs/roster_cap_tool/data/MEGA_players.csv`
- `docs/roster_cap_tool/data/MEGA_teams.csv`

## Run Locally
```bash
# from repo root
python3 -m http.server 8000

# open the app
http://localhost:8000/docs/roster_cap_tool/

# optional: open the browser smoke tests
http://localhost:8000/docs/roster_cap_tool/test.html
```

The smoke tests print PASS/FAIL lines that sanity‑check core math and flows (release → sign → extension → conversion).

## GitHub Pages
1) Commit/push the repo to GitHub (ensure `docs/roster_cap_tool/` and its `data/` CSVs are committed)
2) In repository Settings → Pages, set Source to “Deploy from a branch”, folder `/docs`
3) Visit `https://<username>.github.io/<repo>/docs/roster_cap_tool/`

Note: GitHub Pages serves only committed files. If you update root CSVs, re‑run the sync script and commit the updated files under `docs/roster_cap_tool/data/`.

## Verify Functionality
- Browser smoke tests: `docs/roster_cap_tool/test.html`
- Math parity report (writes `output/cap_tool_verification.json`):
  ```bash
  python3 scripts/verify_cap_math.py \
    --teams docs/roster_cap_tool/data/MEGA_teams.csv \
    --players docs/roster_cap_tool/data/MEGA_players.csv \
    --out output/cap_tool_verification.json
  ```
- Page + assets availability smoke:
  ```bash
  bash scripts/smoke_roster_cap_tool.sh
  ```

## Year Context (Calendar Years)
- Use the Year Context selector in the header to view future seasons using real years (e.g., 2026, 2027, …). Default is the current year for the franchise file (2026 in this dataset).
- When a future year is selected:
  - Rosters and Free Agents reflect expiring contracts for that future year.
  - Cap summary and penalties/savings are calculated for that context year.
  - Actions (Release/Trade/Extend/Convert/Sign) preview and apply math as if you are in that year.
  - Column headers include the context label (e.g., “Cap (2026)”, “Cap (2027)”).
- Scenarios save and restore the selected Year Context; Reset clears edits/moves but keeps your current context.
- Behavior under the current year is unchanged from previous versions.

## Contract Distribution Editor
- Open: click a player’s name in the Active Roster table (or pick “Contract Distribution” from the Action menu) to open a right‑side drawer.
- Layout: one column per remaining contract year (e.g., 2026, 2027, …). Each column has two inputs: Salary (M) and Bonus (M).
- Units and formatting:
  - Enter values in millions; decimals supported (e.g., 22.7 means $22.7M).
  - Values display as currency with one decimal place (e.g., $22.7M).
- Defaults: if no custom values exist, each year is initialized to a 50/50 split of the player’s average annual value:
  - Per‑year total = (contractSalary + contractBonus) / contractLength
  - Salary = Bonus = per‑year total × 0.5 (rounded to dollars)
- Auto‑save: changes update immediately in the UI and are stored for the session. Closing and reopening the editor for the same player shows your edits.
- Reset: click Reset to clear any custom values and restore the default 50/50 distribution for that player.
- Persistence: values are kept in memory only (no localStorage/database). Reloading the page clears custom distributions.
- Constraints: no validation is enforced on totals; zero and any positive values are allowed.

## Financial Rules Reference (Madden)
Core formulas and edge‑cases come from: `spec/Salary Cap Works in Madden.md`.

- Year 1 Cap Hit = Base Salary + (Signing Bonus / Contract Length) + Roster Bonus
- Release (simplified):
  - Savings = `capReleaseNetSavings`
  - Dead Money = `capReleasePenalty`
  - If multi‑year: current year dead money ≈ 60% of penalty, remainder next year
- Bonus proration capped at 5 years (Madden rule)
  - Zero-dead-money releases (e.g., acquired via trade): releasing a player with no signing bonus on your team frees the full salary for the current year and all remaining years; projections reflect this by removing their out‑year cap hits (no add‑backs) and only applying dead money where applicable (which is $0 in this case).

## Data Notes
- CSV source field inversion (cut penalty): Some CSV exports label “Penalty Year 1” and “Penalty Year 2”, but in‑game application is reversed. In practice, what the CSV calls “Year 2” applies to the current season, and what it calls “Year 1” applies to the following season. The tool normalizes this by allocating multi‑year dead money as ~60% to the current year and ~40% to next year, matching in‑game behavior. This change was made to correct mismatches observed between CSV labels and actual cap outcomes in the game.

## Architecture (Pure JS)
- No bundler, no Node runtime — served as static files
- Modules in `docs/roster_cap_tool/js/`:
  - `csv.js` – loads/parses CSV via PapaParse (CDN)
  - `validation.js` – coercion and row normalization
  - `models.js` – JSDoc typedefs for Team/Player/Scenario
  - `state.js` – simple pub/sub store and derived selectors
  - `capMath.js` – pure functions for cap math and projections
  - `ui/*` – team selector, cap summary, tabs/tables, modals:
    - Modals: release, trade (quick), extension, conversion, offer/signing
    - Projections and scenario save/load included

## Troubleshooting
- Blank tables: confirm both CSVs exist under `docs/roster_cap_tool/data/`
- CORS/file errors: use a local web server (see “Run Locally”)
- Cap math mismatch: run `scripts/verify_cap_math.py` and review `output/cap_tool_verification.json`
- Pages not updating: ensure CSVs were synced, committed, and Pages deployed

## Example Flow
1) Select a team in the header
2) Release a player → modal previews Dead Cap, Savings, and New Cap Space
3) Sign a Free Agent → offer builder previews Year 1 Cap Hit and Remaining Cap
4) Optional: Extension/Conversion for targeted cap adjustments

For an in‑depth explanation of Madden’s cap mechanics, see `spec/Salary Cap Works in Madden.md`.
