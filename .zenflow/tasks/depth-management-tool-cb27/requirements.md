# Depth Management Tool – Product Requirements Document (PRD)

## 1. Problem Statement & Goals

The existing depth chart tool under `docs/depth_chart` is a read‑only visualization of the current roster, driven from the shared CSV data used by the roster cap tool. It does not let users manipulate rosters, plan off‑season moves, or see contract/FA timing in context of their depth chart.

The goal of this improvement is to turn the depth chart into an interactive depth management tool that helps users:

- Understand how their team will look in future seasons.
- Plan roster moves across draft, free agency, and trades.
- See contract length and impending free agents directly on the depth chart.
- Export their planned depth chart for offline analysis or sharing.

The design should feel similar in data model and behavior to the existing cap management tool, but focused on roster/depth planning rather than cap math.

## 2. In‑Scope Functionality

### 2.1 Roster Editing

- Allow users to edit the active roster for the selected team within the depth chart tool.
- Core edit operations (at minimum):
  - Add a player from the free‑agent pool to the selected team.
  - Remove a player from the team (move to free‑agent pool / unassigned).
  - Change a player’s team to simulate a trade (reassign between teams).
  - Mark draft placeholders (see 2.3) as occupying depth slots without needing a real player record yet.
- Edited rosters should be reflected immediately in the depth chart view.
- Changes should be local to the browser (no server) and persist across page reloads via `localStorage` scoped to this tool.

### 2.2 Contract Visibility & Future Free Agents

- Surface contract information for players in the depth chart, based on the same CSV and normalization logic used by the roster cap tool:
  - Contract length (`contractLength`).
  - Years remaining on contract (`contractYearsLeft`).
  - Cap‑tool–consistent notion of “becomes a free agent at the end of this season”.
- For each player shown in the depth chart:
  - Display a concise contract summary (e.g., `3 yrs (2 left)`).
  - Indicate if the player is expected to be a free agent at the end of the current season (e.g., tag like `FA after season` or icon).
- Depth chart data loading must reuse or align with `normalizePlayerRow` and any contract/year‑context behavior already implemented in the cap tool, to avoid diverging calculations or field names.

### 2.3 Depth Slot Acquisition Type (Draft / Trade / FA / Existing)

- Each depth chart “slot” (position + depth level) must support specifying how that slot is planned to be filled:
  - Existing player (current roster member).
  - `Draft R1` – placeholder representing a planned Round 1 draft pick at that position.
  - `Draft R2` – placeholder representing a planned Round 2 draft pick at that position.
  - `Trade` – placeholder representing a player to be acquired via trade.
  - `FA` – placeholder representing a free‑agent signing not yet tied to a specific player.
  - Free‑agent player selected from the current free‑agent pool.
- For each depth slot cell, users should be able to:
  - Assign a current roster player eligible for that position.
  - Open a “Free Agent” search to pick an actual player (see 2.4).
  - Choose one of the placeholder acquisition tags (`Draft R1`, `Draft R2`, `Trade`, `FA`).
  - Clear the slot (return it to “need”/empty state).
- Acquisition type should be visible directly in the cell (e.g., badge or label) so users can scan which depth spots are planned via draft/FA/trade vs. existing players.

### 2.4 Free‑Agent Market Search & Assignment

- Expose the free‑agent market (players where `isFreeAgent === true`) within the depth chart tool.
- Provide a UI to:
  - Search free agents by name.
  - Filter free agents by position (matching the depth slot’s position group by default).
  - Optionally filter by OVR range.
- From the FA search UI, allow the user to:
  - Assign a free agent to the selected team (changing their `team` and clearing `isFreeAgent`).
  - Optionally assign them directly into a specific depth slot (the slot that triggered the search).
- Once assigned, the player should appear as part of the team’s roster and participate in depth chart ordering.

### 2.5 Editable Depth Ordering

- Users should be able to control depth ordering rather than relying only on auto‑sorted OVR:
  - Reorder players within a position’s depth chart (e.g., drag‑and‑drop or arrow controls).
  - Override auto‑ordering while still showing OVR for reference.
- Depth ordering edits must persist locally per team in `localStorage`.
- Even for placeholder acquisitions (Draft/Trade/FA), users can control which depth level they occupy (1st, 2nd, 3rd, 4th).

### 2.6 CSV Export

- Provide an “Export CSV” action for the current team’s depth plan.
- Export format should be flat and analysis‑friendly (one row per depth slot), including at least:
  - Team abbreviation.
  - Side (`Offense`, `Defense`, `Special Teams`).
  - Position slot identifier (e.g., `QB`, `WR1`, `CB2`, `EDGE1`).
  - Depth rank (1–4).
  - Player name (or placeholder label such as `Draft R1`, `Trade`).
  - Acquisition type (`Existing`, `Draft R1`, `Draft R2`, `Trade`, `FA Placeholder`, `FA Player`).
  - Player OVR being used (best or scheme).
  - Contract length and years left (if applicable).
  - Flag for “FA at end of season” (boolean) where applicable.
- CSV export should reflect the currently planned roster and depth decisions, not just the baseline CSV data.

### 2.7 Layout & Visual Design (“Like in a Game”)

The current implementation groups positions into tables. The new layout should visually approximate an on‑field game view, while still being desktop‑friendly and readable.

**Offense layout (relative positioning):**

- Offensive line (LT, LG, C, RG, RT) in a horizontal row at the top of the offensive area.
- QB centered directly behind the Center (`C`).
- HB/RB aligned slightly behind and to the right of the QB.
- WR1 aligned to the far left side of the offensive formation.
- WR2 aligned to the far right side of the formation.
- TE aligned to the right side of the offensive line (adjacent to RT).

**Defense layout:**

- Safeties (FS, SS) positioned at the top of the defensive area (deep).
- Linebackers (SAM, MIKE, WILL) aligned in the middle layer.
- Defensive tackles (DT1, DT2) and edges (EDGE1, EDGE2) at the bottom (closest to the line of scrimmage).
- Cornerbacks (CB1, CB2) placed on left and right edges of the formation, aligned roughly with linebackers or safeties (exact Y‑position can be tuned for clarity).

**Special teams:**

- Provide a compact section for K, P, LS – layout can remain tabular or simple row; no “field” realism required.

**General layout requirements:**

- Maintain responsiveness on typical desktop/laptop viewports.
- Ensure labels (position, player name, acquisition tag, contract markers) remain readable without overflowing.
- Keep visual style consistent with existing `docs/depth_chart` aesthetics (colors, typography, etc.).

### 2.8 Integration & Data Consistency

- Player and team data should continue to be sourced from the shared CSVs used by `docs/roster_cap_tool`:
  - `MEGA_teams.csv` for team metadata.
  - `MEGA_players.csv` for player metadata, including contract fields.
- Any additional fields used for contracts or FA timing must align with the cap tool’s understanding of:
  - `contractLength`
  - `contractYearsLeft`
  - Current calendar year / season context (where needed to compute “FA at end of season”).
- Depth management changes (local edits, assignments, placeholders) are **local to this tool** and do not modify the underlying CSVs.

## 3. Out‑of‑Scope / Non‑Goals

- No cap calculation, dead money analysis, or multi‑year cap projections beyond reusing contract fields for display.
- No server‑side persistence or multi‑user sharing; all edits are per‑browser, stored in `localStorage`.
- No enforcement of league rules (e.g., 53‑man limit, position minimums) beyond the existing max depth slots per position.
- No complex scenario management UI (saving multiple named scenarios, comparing plans), unless later required; the initial scope is a single per‑team planned roster snapshot.
- No live synchronization with the cap management tool UI; both tools share CSV data and concepts but operate independently in the browser.

## 4. Users & Primary Use Cases

**Primary user:** A franchise mode player or analyst planning their off‑season moves and depth chart for future seasons.

Key use cases:

1. **Plan off‑season depth chart:**
   - User selects their team, reviews current depth chart, and fills empty/weak spots with Draft/FA/Trade placeholders and free‑agent targets.
2. **Evaluate contract risk by position:**
   - User quickly sees which starters or key backups are entering free agency after the season and where depth is thin long‑term.
3. **Compare draft vs. free agency approach at specific positions:**
   - User marks WR2 as `Draft R1` and EDGE2 as `FA`, and sees how the overall depth looks under that plan.
4. **Export plan to spreadsheet:**
   - User exports current depth chart as CSV to document their plan, share it, or integrate into other analysis workflows.

## 5. UX & Interaction Requirements

- **Team selection:**
  - Keep the existing team selector component and behavior (single selected team, reactive updates).
- **Depth slot interaction:**
  - Clicking a depth slot cell opens a small panel or menu with options:
    - Choose from current roster players at that position.
    - Search free agents at that position.
    - Set acquisition type to `Draft R1`, `Draft R2`, `Trade`, or generic `FA` placeholder.
    - Clear the slot.
- **Roster panel (optional but recommended):**
  - A side panel or overlay listing the current team roster, with the ability to:
    - Toggle players as cut (move to FA pool).
    - Move players between teams for trades.
    - See contract length / FA timing at a glance.
- **Feedback & safety:**
  - When editing rosters or assigning/removing players, updates should be immediate and visually clear (updated depth cells, FA pool, etc.).
  - Provide a simple “Reset to baseline roster” action to discard local changes and reload from CSV.

## 6. Data Model & Persistence Requirements (Conceptual)

- Extend the depth chart’s internal player representation to include:
  - Player `id` from `normalizePlayerRow`.
  - Contract fields (`contractLength`, `contractYearsLeft`, plus any basic salary/bonus fields if needed for FA timing).
- Represent each depth slot with:
  - Position slot id (e.g., `QB`, `WR1`, `EDGE1`).
  - Depth index (1–4).
  - Assigned entity:
    - `playerId` for an actual player (on team or FA).
    - `placeholderType` for `Draft R1`, `Draft R2`, `Trade`, `FA`.
  - Acquisition source (`existingRoster`, `freeAgent`, `draft`, `trade`, `faPlaceholder`).
- Persist per‑team depth chart plans and roster edits using `localStorage` under a namespaced key (e.g., `depthChartPlanner.{teamAbbr}`).

## 7. Constraints & Performance

- Entire tool runs client‑side in the browser; no backend.
- Must handle full‑league CSVs (`MEGA_players.csv`, `MEGA_teams.csv`) without noticeable UI lag on typical modern desktops.
- Avoid heavy re‑rendering; updates should be scoped to affected parts of the layout where possible.

## 8. Assumptions & Open Questions

### 8.1 Assumptions

- Users are comfortable with basic depth chart concepts and terminology.
- A player may appear in multiple depth slots (e.g., start at one position and serve as backup elsewhere); we will allow this in the first version rather than enforcing uniqueness.
- Contract length and “FA at end of season” calculations can reuse the same year context assumptions as the cap tool, without new inputs from the user.
- One per‑team plan is sufficient for now; multiple named scenarios are not required in this task.

### 8.2 Open Questions (for future clarification)

- Should we support multiple saved scenarios per team (similar to the cap tool’s what‑if mode)?
- Should depth chart edits influence any values or projections back in the cap tool, or remain completely separate?
- Do users want position‑specific draft round planning beyond Round 1 and Round 2 (e.g., R3–R7)?
- Are there any league‑specific constraints (e.g., minimum number of players per position, practice squad) that should be enforced or at least surfaced?

