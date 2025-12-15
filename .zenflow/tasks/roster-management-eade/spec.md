# Technical Specification: Madden Roster Cap Management Tool

## Technical Context
- App type: Static web app (SPA) compiled to `docs/roster_cap_tool/` for GitHub Pages
- Languages: TypeScript 5.x, HTML, CSS
- UI framework: React 18 + Vite 5
- State management: Zustand (simple, minimal boilerplate) or Redux Toolkit if team prefers
- Styling: Tailwind CSS + CSS variables for theme colors (Spotrac-inspired scheme)
- Data parsing: PapaParse for CSV → JS objects; Zod for schema validation/coercion
- Charts/indicators: Lightweight progress bars via CSS; optional Recharts/D3 for Phase 2
- Date/time/ids: `nanoid` for scenario ids; `dayjs` optional
- Testing: Vitest + React Testing Library (unit), Playwright (E2E smoke)
- Verification helpers: Python 3.x scripts (pandas optional) for cap math cross-check
- Hosting: Output placed under `docs/roster_cap_tool/` to align with existing repo’s GitHub Pages
- Primary data: `MEGA_players.csv`, `MEGA_teams.csv` from repo root
- Canonical cap rules: `spec/Salary Cap Works in Madden.md` (normative reference for calculations)

Notes:
- MVP prioritizes client-side parsing of CSV and local state updates. No backend required.
- All computations are deterministic and performed in-browser; scenario persistence via `localStorage` (feature-flagged).

## Technical Implementation Brief
Core decisions and MVP scope:

1) Data ingestion and normalization
- Load `MEGA_teams.csv` and `MEGA_players.csv` on app start (or team selection).
- Normalize into canonical models: `Team`, `Player`, `Contract`, `CapSnapshot`.
- Validate/transform fields with Zod (numeric coercion for dollar fields; booleans for `isFreeAgent`).
- Join `players.team` to `teams.abbrName` as per PRD. Provide fallbacks for missing/unknown teams.

2) Cap math and rules
- Use dataset fields when provided as single sources of truth for release/trade effects:
  - `capReleaseNetSavings` → Cap savings if released
  - `capReleasePenalty` → Dead money if released/traded (Quick)
- Derive Cap Summary live:
  - `capRoom`: from `teams.capRoom` (constant per season)
  - `capSpent`: sum of active roster `capHit` + accumulated `deadMoney`
  - `capAvailable = capRoom - capSpent`
  - `capGainLoss = capAvailable - baselineCapAvailable` (baseline = initial on load)
- Extensions (MVP simplified): new year-1 cap = `(newSalary + newBonusProrated)` where `newBonusProrated = newBonus / min(newYears, 5)`; optionally allow override for “exact Madden proration” later.
- Conversion (restructure): reduce current year base by `convertAmount * (1 - 1 / min(yearsRemaining, 5))`; increase future years by `convertAmount / min(yearsRemaining, 5)` apportionment.
- Trade (Quick): remove player, apply full `capReleasePenalty`, same as release for MVP unless dataset provides trade-specific values.
- Reference and align with `spec/Salary Cap Works in Madden.md` for proration max 5 years and penalty handling.

3) State model
- `RosterState` holds: selected team id, baseline cap snapshot, live cap snapshot, rosters (active, IR, dead money, FA), pending scenario edits, and an action history for undo.
- Use optimistic updates; modals compute preview deltas prior to commit.
- Optional `localStorage` persistence under key `madden-cap-scenarios-{team}` (toggle via settings or feature flag).

4) UI/UX
- Layout: sticky Cap Summary header; left Team Selector; Tabbed content (Active, IR, Dead Money, Draft Picks, Free Agents).
- Tables: virtualized list (if needed in Phase 2) or simple table for MVP; default sort by `capHit` desc.
- Row Action menu per player with contextual items (Release, Trade, Extension, Conversion).
- Modals show: inputs, live cap preview (before/after), validation messages (errors/warnings), confirm/cancel.
- Color system: green (savings), red (dead money), yellow (warnings), blue (extensions/mods). CSS vars: `--cap-green`, `--cap-red`, `--cap-yellow`, `--cap-blue`.
- Responsive: Desktop full table; Tablet collapsible contract details; Mobile card layout with essential fields and action sheet.

5) Data safety and reproducibility
- Never mutate source CSV records directly; form edits produce derived state overlays.
- Provide “Reset to baseline” and “Undo last change”.
- Provide “Export scenario” as JSON (Phase 2) including cap snapshots and move ledger.

MVP completeness criteria:
- Can select a team, see Cap Summary, browse Active Roster and Free Agents.
- Can Release a player (with confirmation) and see cap update.
- Can open Free Agent “Make Offer,” validate cap hit and sign if valid; cap updates and player moves to Active Roster.

## Source Code Structure
Proposed tree under `web/` with build output to `docs/roster_cap_tool/`:

```
web/
  package.json
  vite.config.ts
  tsconfig.json
  tailwind.config.js
  src/
    main.tsx
    App.tsx
    routes/
      RosterTool.tsx
    components/
      CapSummary.tsx
      TeamSelector.tsx
      Tabs.tsx
      PlayerTable.tsx
      PlayerRow.tsx
      ActionMenu.tsx
      Modals/
        ReleaseModal.tsx
        TradeModal.tsx
        ExtensionModal.tsx
        ConversionModal.tsx
        OfferModal.tsx
    state/
      store.ts (Zustand)
      selectors.ts
      actions.ts
      persist.ts
    lib/
      csv.ts (PapaParse + Zod coercion)
      capMath.ts (all formulas, canonical)
      filters.ts
      sort.ts
      format.ts (money, percents)
      maddenRules.ts (helpers aligned with spec doc)
    types/
      schema.ts (Zod schemas)
      models.ts (TS types/interfaces)
    assets/
      styles.css
  public/
    favicon.svg
```

Build: `vite build` → emits to `docs/roster_cap_tool/`. Root `index.html` (existing) can link to this tool.

## Contracts

1) Data models (TypeScript)
- `Team`: `{ abbrName: string; displayName: string; capRoom: number; capSpent: number; capAvailable: number; seasonIndex: number; weekIndex: number; }`
- `Player`: `{ id: string; firstName: string; lastName: string; position: string; age?: number; height?: string; weight?: number; team?: string; isFreeAgent: boolean; yearsPro?: number; capHit: number; capReleaseNetSavings?: number; capReleasePenalty?: number; contractSalary?: number; contractBonus?: number; contractLength?: number; contractYearsLeft?: number; desiredSalary?: number; desiredBonus?: number; desiredLength?: number; reSignStatus?: number; }`
- `CapSnapshot`: `{ capRoom: number; capSpent: number; capAvailable: number; deadMoney: number; baselineAvailable: number; deltaAvailable: number; }`
- `ScenarioMove`: discriminated union: `ReleaseMove`, `TradeMove`, `ExtensionMove`, `ConversionMove`, `SignMove` with timestamps and diffs.

2) CSV contracts (Zod)
- Zod schemas for `teamsCsvRow` and `playersCsvRow` with numeric coercion: `z.preprocess((v)=>Number(v))` for money fields; boolean coercion for `isFreeAgent` from `0/1`, `true/false`, or `"true"/"false"` strings.
- Row-level validation errors surface to a non-blocking warning panel; invalid rows are skipped but counted.

3) Cap math functions (lib/capMath.ts)
- `calcCapSummary(team: Team, players: Player[], deadMoney: number): CapSnapshot`
- `simulateRelease(p: Player, snapshot: CapSnapshot): { next: CapSnapshot; deadMoneyDelta: number }`
- `simulateTradeQuick(p: Player, snapshot: CapSnapshot): { next: CapSnapshot; deadMoneyDelta: number }`
- `simulateExtension(p: Player, years: number, salary: number, bonus: number, snapshot: CapSnapshot): { next: CapSnapshot; capHitDelta: number }`
- `simulateConversion(p: Player, convertAmount: number, yearsRemaining: number, snapshot: CapSnapshot): { next: CapSnapshot; capHitDelta: number }`
- `simulateSigning(p: Player, years: number, salary: number, bonus: number, snapshot: CapSnapshot): { next: CapSnapshot; year1CapHit: number }`
- All functions are pure and side-effect free, referencing proration max 5 years per `spec/Salary Cap Works in Madden.md`.

4) UI contracts
- Action modals accept a `Player` and produce a `ScenarioMove` on confirm; store applies the move via `actions.applyMove(move)`.
- Store exposes derived selectors: `selectCapSummary`, `selectActiveRoster`, `selectFreeAgents`, `selectByTeam`.

5) Scenario persistence (optional MVP)
- Interface: `Scenario { id: string; team: string; createdAt: string; moves: ScenarioMove[]; finalSnapshot: CapSnapshot }`
- Persistence adapters: in-memory; `localStorage` (feature-flag); file export/import (Phase 2).

## Delivery Phases

Phase 0 — Scaffolding and data loading (1 day)
- Scaffold Vite + React + TS + Tailwind + Zustand; wire PapaParse and Zod.
- Implement CSV loaders and normalization with validation.
- Render Team Selector and Cap Summary (baseline read-only).

Phase 1 — Roster + Release + Free Agent signing (MVP) (2–3 days)
- Active Roster and Free Agents tabs with sortable tables.
- Action menu: Release (with modal preview and confirmation).
- Free Agent Offer modal: inputs, cap preview, validation, confirm to sign.
- Live Cap Summary updates; baseline delta shown.

Phase 2 — Extensions and Conversions (2 days)
- Extension modal: years slider (1–7), salary/bonus inputs, preview, apply simplified cap hit.
- Conversion modal: convert base → bonus; show current vs future impact.

Phase 3 — Trade (Quick) and IR/Dead Money views (2 days)
- Trade Quick action: apply `capReleasePenalty`, remove player from roster; update Dead Money tab.
- IR view (filter by injury status if available; else informational subset by `reSignStatus`/flags).
- Dead Money tab lists penalties accumulated.

Phase 4 — Projections, Scenario, and UX polish (stretch) (3–5 days)
- Multi-year projection (3–5 seasons): show cap impacts based on `contractYearsLeft` and proration rules.
- Scenario save/load (localStorage) and compare scenarios.
- Performance (virtualized rows), accessibility review, mobile polish.

Deliverable of each phase is a build deployed under `docs/roster_cap_tool/` with smoke tests.

## Verification Strategy

General commands
- Build: `cd web && npm ci && npm run build` (emits to `../docs/roster_cap_tool/`)
- Preview (optional): `npm run preview` or open `docs/roster_cap_tool/index.html`

Unit tests (Vitest)
- `cd web && npm run test` — covers `lib/capMath.ts` functions with fixtures.
- Include tests for:
  - Release math: `capAvailable'` increases by `capReleaseNetSavings` and dead money ledger increases by `capReleasePenalty` where applicable.
  - Signing math: `year1CapHit = salary + bonus / min(years, 5)`; block if `capAvailable < year1CapHit`.
  - Extension/conversion calculations against examples from `spec/Salary Cap Works in Madden.md`.

E2E smoke (Playwright)
- `cd web && npx playwright test` runs a single scenario:
  1) Load team → observe baseline cap.
  2) Release a top-3 cap hit player → confirm → cap increases accordingly.
  3) Sign a FA with offer equal to desired → cap decreases by previewed Year 1 cap hit.
  4) Assert Cap Summary deltas and table row counts.

Python cross-check scripts (repo `scripts/`)
- `scripts/verify_cap_math.py` (to be added):
  - Inputs: `MEGA_players.csv`, `MEGA_teams.csv`, and `scripts/fixtures/cap_scenarios.json` (simple scenario list: release/sign/extend/convert/tradeQuick).
  - Computes expected `capAvailable`, `capSpent`, and `deadMoney` after applying scenario moves using the same formulas.
  - Outputs: `output/cap_tool_verification.json` with per-step and final snapshots.
  - Run: `python3 scripts/verify_cap_math.py`
- `scripts/smoke/smoke_roster_cap_tool.sh` (to be added):
  - Builds the web app, validates artifacts exist under `docs/roster_cap_tool/`, greps for app mount point.
  - Optionally launches a local static server (python `http.server`) and curls root to ensure bundle loads.

MCP servers to install for agents (recommendations)
- `filesystem` (fs): read/write fixtures and outputs for verification.
- `bash` (process): run npm, python, and shell scripts.
- `playwright`/`browser`: drive UI flows for E2E smoke.
- `git`: confirm file diffs and ensure build artifacts are generated in the correct path.
- `curl` (optional): fetch local preview pages or remote assets if needed.

Sample input artifacts
- Primary: `MEGA_players.csv`, `MEGA_teams.csv` — already in repo root (c: provided by user).
- Tiny test set: `output/tiny_players.csv` (exists) and add `output/tiny_teams.csv` (to be generated by helper script) (a: generated by agent) for fast unit tests.
- Scenario fixture: `scripts/fixtures/cap_scenarios.json` with simple deterministic cases (a: generated by agent).

Verification per phase
- Phase 0: `csv.ts` unit tests ensure CSV fields parse and coerce correctly; run build, confirm `docs/roster_cap_tool/` contains `index.html` and JS/CSS bundles.
- Phase 1: Unit tests for release/signing; Playwright smoke executes release + signing flow; Python script cross-checks cap math deltas for 1–2 simple scenarios.
- Phase 2: Add unit tests for extension/conversion; Playwright opens modal previews and confirms delta math.
- Phase 3: Add unit test for tradeQuick; verify Dead Money tab list grows; Python script matches expected dead money accumulation.
- Phase 4: Projection unit tests for proration beyond current year; localStorage scenario save/load tested with RTL (mock storage) and a simple Playwright step.

## References
- Cap rules source of truth: `spec/Salary Cap Works in Madden.md`
- PRD: `.zenflow/tasks/roster-management-eade/requirements.md`
