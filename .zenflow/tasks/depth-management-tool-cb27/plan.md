# Full SDD workflow

## Configuration
- **Artifacts Path**: {@artifacts_path} → `.zenflow/tasks/{task_id}`

---

## Workflow Steps

### [x] Step: Requirements
<!-- chat-id: 04997dd2-cd79-44e9-b6c3-cf70af3b8327 -->

Create a Product Requirements Document (PRD) based on the feature description.

1. Review existing codebase to understand current architecture and patterns
2. Analyze the feature definition and identify unclear aspects
3. Ask the user for clarifications on aspects that significantly impact scope or user experience
4. Make reasonable decisions for minor details based on context and conventions
5. If user can't clarify, make a decision, state the assumption, and continue

Save the PRD to `{@artifacts_path}/requirements.md`.

### [x] Step: Technical Specification
<!-- chat-id: 04c8f8aa-d932-48ef-a0f4-9a499e4cad17 -->

Create a technical specification based on the PRD in `{@artifacts_path}/requirements.md`.

1. Review existing codebase architecture and identify reusable components
2. Define the implementation approach

Save to `{@artifacts_path}/spec.md` with:
- Technical context (language, dependencies)
- Implementation approach referencing existing code patterns
- Source code structure changes
- Data model / API / interface changes
- Delivery phases (incremental, testable milestones)
- Verification approach using project lint/test commands

### [x] Step: Planning
<!-- chat-id: 4f5f8a5f-3b4e-4930-826b-68ae2ab3da3a -->

Create a detailed implementation plan based on `{@artifacts_path}/spec.md`.

1. Break down the work into concrete tasks
2. Each task should reference relevant contracts and include verification steps
3. Replace the Implementation step below with the planned tasks

Rule of thumb for step size: each step should represent a coherent unit of work (e.g., implement a component, add an API endpoint, write tests for a module). Avoid steps that are too granular (single function) or too broad (entire feature).

If the feature is trivial and doesn't warrant full specification, update this workflow to remove unnecessary steps and explain the reasoning to the user.

Save to `{@artifacts_path}/plan.md`.

### [x] Step: Data alignment
<!-- chat-id: 9cdd0a2e-95b6-4249-b579-fd3b23045ce6 -->

Implement the shared player model and baseline roster loading for the depth tool (spec section 3.1, 4.1).

1. Update `docs/depth_chart/js/csv.js` and `docs/depth_chart/js/state.js` to reuse `normalizePlayerRow` and expose `baselinePlayers` / `playersById`.
2. Ensure the depth chart still renders read-only depth using the updated data shape.
3. Wire depth chart state so that future `DepthPlan` work can read from `baselinePlayers`.
4. Verification: run `npm test -- depth_chart` (or the closest existing depth-chart tests) if present, and manually open `/docs/depth_chart/` to confirm the current layout still works and player/contract data match the cap tool.

### [x] Step: Depth plan model & persistence
<!-- chat-id: 23e70fab-afa2-4be3-a651-7cd340ab1dcd -->

Introduce the `DepthPlan` data structure, editing helpers, and `localStorage` wiring (spec sections 3.2, 3.3, 4.3, 7).

1. Define `DepthPlan`, `DepthSlotAssignment`, and acquisition type enums in `docs/depth_chart/js/state.js` (or a new shared module) based on the spec.
2. Implement helpers: `buildInitialDepthPlanForTeam`, `ensureDepthPlanForTeam`, `updateDepthSlot`, `clearDepthSlot`, and `resetTeamRosterAndPlan`.
3. Add roster edit helpers (`setRosterEdit`, `getPlayersForTeam`, `getFreeAgents`) and connect them to `DepthPlan` updates.
4. Persist `rosterEdits` and `depthPlans` in `localStorage` under the versioned keys defined in the spec.
5. Temporarily keep the existing table layout but render from `DepthPlan` instead of recomputing from players each time.
6. Verification: manually change depth ordering and assignments for a team, reload the page, and confirm the same `DepthPlan` is restored from `localStorage`.

### [x] Step: Game-like layout & contract display
<!-- chat-id: b374ea6e-fd46-4555-b039-7e819d3863ec -->

Replace the table layout with the game-like offense/defense/special formations and surface contract/FA information (spec sections 3.4, 3.5, 4.2, 5.2).

1. Update `docs/depth_chart/js/ui/depthChart.js` to render offense, defense, and special teams as position cards laid out on “field” containers driven by `DepthPlan`.
2. Implement or reuse a `getContractSummary` helper to show contract length, years left, and “FA after season” flags in depth rows, roster lists, and FA search results.
3. Update `docs/depth_chart/css/styles.css` to add `.depth-layout`, offense/defense/special field grids, `.position-card`, depth-row styles, and acquisition/FA badges that match the spec’s formations.
4. Keep or adapt existing team selector wiring so that changing teams reloads the corresponding `DepthPlan`.
5. Verification: visually confirm the new layout for offense/defense/special teams matches the requested formation for a few sample teams and that contract/FA markers appear where expected.

### [x] Step: Editing interactions, FA search & roster panel
<!-- chat-id: 9d7c7d58-667e-40bb-a548-508c9ff47c44 -->

Add interactive editing for depth slots, free-agent search, and roster management (spec sections 2.1–2.5, 3.4, 5.1, 5.3, 5.4).

1. Implement `docs/depth_chart/js/ui/slotEditor.js` to allow selecting current roster players, searching FAs, choosing placeholders (`Draft R1`, `Draft R2`, `Trade`, `FA`), and clearing slots, all backed by `updateDepthSlot` and `setRosterEdit`.
2. Add an optional but recommended `docs/depth_chart/js/ui/rosterPanel.js` that shows current team roster and FA pool with controls for cut, sign, and trade operations.
3. Wire click handlers from each depth slot row in `depthChart.js` to open the slot editor with the correct `slotId` and `depthIndex`.
4. Ensure that assigning a FA player updates both roster state (moves from FA to team) and the appropriate `DepthPlan` slot.
5. Handle edge cases such as duplicate assignments (a player appearing in multiple slots or teams) by clearing previous slots when a player is reassigned.
6. Verification: manually perform flows to cut a player to FA, sign a FA into a slot, mark draft/trade/FA placeholders, and confirm state is persisted across reloads.

### [x] Step: Depth ordering controls & CSV export
<!-- chat-id: 4459fb69-1b7d-4ddb-ae9c-6cb9fe2e3eae -->

Support manual depth reordering and exporting the current team plan to CSV (spec sections 3.3, 5.5, 5.6, 4.4).

1. Add up/down controls (or similar) on depth rows in `depthChart.js` to reorder `DepthSlotAssignment` entries within a slot and persist the new order via `DepthPlan`.
2. Implement a CSV builder (`docs/depth_chart/js/csvExport.js` or equivalent) that produces rows with the columns described in the spec (`team`, `side`, `positionSlot`, `depth`, `playerName`, `acquisition`, `ovr`, `contractLength`, `contractYearsLeft`, `faAfterSeason`).
3. Add an “Export CSV” button near the depth chart header that builds CSV for the currently selected team and triggers a download (e.g., `depth-plan-{TEAM}.csv`).
4. Verification: change depth ordering, export CSV, and open the file to confirm rows reflect the current plan and acquisition/contract fields are correct.

### [x] Step: Polish, reset flows & automated tests
<!-- chat-id: d40f5922-75d1-42fa-a5fe-6f93a155c807 -->

Finalize UX, reset behavior, and automated coverage for the depth management tool (spec sections 3.3, 3.4, 6, 7).

1. Implement a “Reset to baseline” control per team that clears `rosterEdits` and `DepthPlan` for that team and rebuilds from baseline players.
2. Harden state management against malformed or missing `localStorage` entries, absent teams, or unexpected CSV data.
3. Ensure basic accessibility for interactive elements: focus handling for the slot editor, keyboard navigation for primary actions, and ARIA labels where appropriate.
4. Update or extend Playwright E2E tests in `tests/e2e/depth_chart.spec.ts` to cover new layout, slot editing, FA search, persistence, reset, and CSV export.
5. Verification: run `npm run test:e2e -- tests/e2e/depth_chart.spec.ts` (or the appropriate command from the spec) and confirm all depth-chart tests pass, then do a final manual sanity pass through key user flows.

### [x] Step: Style absolutly terrible
<!-- chat-id: 18b9005d-ba34-48d0-87c4-c9da5c6db217 -->

This is amaizing how bad it is from css perspective, i cant belive, check the scrrenshot i attached and refactor styling

### [x] Step: Run playwright and get the screenshot
<!-- chat-id: 1771d2a7-924f-4cc5-b9f5-d2ef945836d8 -->

I would like you to get a screenshot of the app, and check if its human readable. If no, plan the adjsutment and do again, until you will not success with the results

### [x] Step: get latest main and rebase 
as we already merge part of the work into master, you need to rebase your worktree branch
