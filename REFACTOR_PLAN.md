# MEGA League refactor plan

Prepared 2026-10-24. Planning only; no implementation is authorized by this document.

## Recommendation

Keep the file-based Python pipeline and static JavaScript website. They fit this project. Refactor incrementally around reliable imports, reproducible calculations, and clear ownership of generated files. A framework rewrite, database, or application server would add migration work without solving the problems found here.

The biggest maintenance cost is the mixing of source code, current data, generated reports, and season-specific configuration. Large files contribute, but file length alone is not a reason to split or remove a feature.

Madden 26 data is already archived. Do not repeat that cleanup or delete the archive. Focus on the active implementation and its remaining historical assumptions.

## Scope and protected behavior

- Preserve formulas, weights, tiebreakers, cap calculations, OVR coefficients, trained models, and trade-aware aggregation. Any proposed mathematical correction belongs in a separate change with explicit authorization.
- Preserve the immutable `archive/madden-26/` snapshot and its manifest hashes.
- Keep the current Madden 27 baseline: season 1 / CSV `seasonIndex=0`, results through Week 12, supplied Week 8 ELO. Export week index and displayed game week are separate fields.
- Preserve the distinction between GM labels and NeonSportz usernames. The screenshot-derived labels must not overwrite raw export identities.
- Retain existing public URLs and CLI entry points during migration, using small compatibility wrappers where necessary.
- Preserve browser-saved cap and depth-chart scenarios. Never clear storage as part of cleanup.
- Keep the existing export procedure, including both ZIPs and the Git/PR steps. This plan does not request email access, exports, commits, pushes, or merges.

## Findings from the repository

| Priority | Evidence | Consequence | Proposed treatment |
| --- | --- | --- | --- |
| P0 | `scripts/run_all.py` and `run_all_stats.py` aggregate stats, then `generate_index.py` runs the same four aggregation steps again | Rendering navigation unexpectedly changes analytical data and repeats work | One task definition per calculation; index generation only renders navigation |
| P0 | `stats_scripts/stats_common.py:load_csv` catches every exception and returns an empty list | Missing or malformed input can resemble legitimate empty statistics | Validate inputs and distinguish required data, permitted empty datasets, and invalid data |
| P0 | `scripts/run_utils.py:run_script` treats every optional-step failure as a successful skip | A code defect can be reported as missing dependencies | Explicit disabled/skipped/failed states; dependency preflight; preserve actual errors |
| P0 | Runners continue after failures; generators write directly into live paths; `publish_browser_data` silently skips missing files | A refresh can mix old and new artifacts | Staged build, dependency-aware execution, complete validation before publication |
| P0 | `tests/test_snapshots.py` runs scripts at import, references a machine-specific path, uses historical seasons, and expects ignored snapshots | Broad test discovery is unsafe and cannot establish a dependable baseline | Replace with isolated fixture-based tests that write only to temporary directories |
| P0 | `scripts/verify_sos_elo.py` contains successful stub checks | A green verification result proves nothing | Implement real contract/invariant checks before using it as a gate |
| P1 | ELO SoS uses human season numbers and row offsets; other scripts use zero-based CSV indices; bracket generator fixes `SEASON_INDEX = 3` | New seasons require scattered edits and can select unintended data | One explicit cycle context; filter by season/stage values instead of row position |
| P1 | `docs/` contains both applications and generated HTML; `output/` contains generated data plus irreplaceable formula/model artifacts | Bulk cleanup or rebuilding a folder is unsafe | Separate source, assets, build intermediates, and the published site |
| P1 | `output/` is ignored while some browser-consumed outputs are tracked; pages read root CSVs, `output/`, and `docs/data/` | Build and publishing requirements are implicit | Declare artifact ownership and a single browser data manifest |
| P1 | `sos_season1/2/3/4.html`, multiple `sos_graphs_season*.html`, and season-specific CLI wrappers | Each season creates additional copies and drift | Parameterized pages and CLI; preserve historical URLs as adapters |
| P1 | `week18_simulator.py` has its own game loading and standings code; scenario reports already reuse portions of the playoff engine | Some domain behavior is shared and some can drift | Compare implementations before extracting common logic; preserve intentional variants |
| P1 | `rosterCap.*` and `depthChartPlanner.v1` storage keys are not scoped by Madden edition | Old browser scenarios can be applied to new rosters | Versioned, cycle-aware storage with explicit export/import and migration |
| P2 | `power_rankings_roster.py` is 2,635 lines; draft analytics 1,701; matchup page 1,686; week-18 simulator 1,484 | Loading, calculation, formatting, and UI are difficult to change separately | Extract along responsibilities after baseline coverage exists |
| P2 | README files and `spec/` mix current instructions with historical seasons and implementation plans | Readers cannot reliably distinguish current contracts from old proposals | Consolidate current operational docs and classify older design documents |

These are code findings, not a claim that all listed features are unused. No production usage analytics were reviewed, and this planning pass did not rerun pipelines or the complete test suite.

## Proposed architecture

```text
Two NeonSportz ZIPs + ELO/GM inputs
    → validate and record an import snapshot
    → load a normalized dataset for one explicit cycle
    → run domain calculations in dependency order
    → validate outputs
    → render reports and assemble a static site in staging
    → publish the complete validated site
```

Suggested eventual layout, introduced gradually:

```text
config/                 active cycle and enabled feature configuration
data/raw/<snapshot>/    canonical imported inputs and provenance
assets/formulas/        preserved formula references
assets/models/          preserved models and calibration provenance
mega/                   importable Python package
  io/                   CSV parsing, schemas, identity mapping
  stats/                stints and team/player/rankings aggregation
  playoffs/             standings, simulations, scenarios, draft race
  sos/                  separate ELO and rankings-based models
  roster/               roster rankings and draft analysis
  reporting/            templates and formatting
  pipeline/             tasks, validation, artifact manifest
scripts/                thin CLI entry points and compatibility wrappers
web/                    maintained HTML, JavaScript, CSS, templates
tests/                  unit, contract, integration, browser fixtures
build/                  disposable intermediates and staged site; ignored
archive/madden-26/      unchanged historical snapshot
```

Initially keep the existing root `index.html`, `docs/`, and browser data URLs as the publication surface. Do not change hosting configuration as part of a directory move. First make the build produce those paths consistently; a later deployment change may publish the staged site directly.

Use plain Python modules and vanilla JavaScript ES modules. Share infrastructure such as CSV loading and chart setup, while keeping distinct analytical models separate. ELO SoS and rankings-based SoS are different features, not duplicate calculations.

## Implementation sequence and acceptance gates

### 1. Establish a trustworthy baseline — P0

1. Inventory every supported page and command: its source, required inputs, generator, outputs, and current/seasonal/experimental status. Start with the existing architecture guide rather than creating competing documentation.
2. Repair the snapshot harness so importing tests never runs a pipeline. Use temporary output directories and committed small fixtures; remove machine-specific paths.
3. Capture current deterministic results and seeded simulation results. Record seed, simulation count, input hashes, and runtime version. Keep fixture expectations distinct from production exports.
4. Add missing contract coverage for traded players, ties, postseason exclusion, multiple seasons, missing ELO, and empty-but-valid trades. The current empty trades export is insufficient to test trade allocation.
5. Replace the SoS verifier stubs with checks that can actually fail.

Acceptance: ordinary test discovery has no production-file side effects; corrupt/missing required inputs fail; deterministic calculations match the baseline. Archive and protected formula/model hashes remain unchanged.

Existing cap-tool projection failures in scenarios B/C/D were recorded during the earlier import work. Reproduce and classify them separately; do not adjust formulas or blindly update expectations to get a green baseline. Any temporary exclusion must be named, visible, and narrowly scoped.

### 2. Centralize cycle configuration and input validation — P0/P1

1. Define a cycle context containing edition, CSV season index, display season, franchise calendar year, export snapshot, completed game week, ELO source week, and enabled features. Derive display values where reliable and verify consistency.
2. Create an import command that validates both ZIP contents before changing active data. Record required schemas, IDs, season/stage coverage, team joins, and source provenance. Reject duplicate/conflicting inputs and incomplete imports; permit documented optional empty exports.
3. Separate source-byte hashes from normalized working-file hashes so Git newline conversion cannot invalidate provenance ambiguously.
4. Replace row-offset season selection with explicit season/stage filtering. Keep existing flags as temporary adapters with clear warnings.
5. Establish one identity mapping for team IDs/names/abbreviations, player IDs, GM labels, and exported usernames. Missing joins must be reported, not silently discarded.

Acceptance: importing an invalid snapshot leaves active data intact; season selection remains correct with shuffled rows and multiple seasons; Week 8 ELO retains its label alongside Week 12 results. A new season requires configuration and new inputs, with no source edits.

### 3. Make pipeline execution and publication reliable — P0

1. Define task dependencies once. Keep `run_all.py`, stats-only, and playoff-only commands as selectors over the same tasks.
2. Remove calculations from `generate_index.py`. Use a declared page/artifact inventory instead of inferring availability solely from files left on disk.
3. Run prerequisites once; stop dependent work after a failure. Distinguish intentional feature skips from errors in enabled features.
4. Generate into a temporary build directory and validate required artifacts before updating the published tree. Publish a complete artifact set, with rollback to the last good set on failure.
5. Give outputs a build/snapshot identifier and schema version through a manifest or sidecar, avoiding breaking existing team-keyed JSON structures. Ensure subset runs cannot publish outputs from incompatible snapshots.
6. Replace “copy if present” with explicit required/optional artifact rules. Remove obsolete generated files only when the manifest owns them; never clean maintained sources or user files by glob.

Acceptance: each aggregation runs once; rendering navigation changes no analytical data; an injected failure leaves the previous published site unchanged; no page mixes snapshots. Full and subset commands produce equivalent results for shared tasks.

### 4. Extract the Python domain code — P1

1. Move parsing, normalization, configuration, and output writing into shared modules, keeping command wrappers working.
2. Separate pure calculations from file access and HTML/report formatting. Start with stats, then SoS, then roster/draft reporting; handle playoff simulations after their baseline is strongest.
3. Compare duplicate standings/game loaders before consolidation. Explicitly document differences such as completed-game status handling. Resolve semantic differences separately instead of silently choosing one implementation.
4. Reuse calculation results across report formats where they already represent the same computation. Preserve random draw order during structural extraction; any change to simulation strategy or sampling receives its own validation change.
5. Extract templates from the largest generators. Keep optional OVR research dependencies outside the core pipeline.

Acceptance: deterministic numerical outputs and row membership match; seeded simulations match under the recorded runtime; CLI compatibility tests pass. Existing quirks remain documented until intentionally corrected.

### 5. Consolidate frontend sources and protect saved scenarios — P1/P2

1. Move maintained source into `web/` incrementally; generate the existing public paths from it.
2. Introduce shared CSV/data loading, team identity, formatting, error display, and chart setup modules. Replace repeated implementations page by page, not in one site-wide rewrite.
3. Replace season-specific SoS page copies with one implementation per analytical view. Preserve older URLs and distinguish ELO from rankings SoS.
4. Read a browser manifest for data paths and snapshot labels. Missing data should show a clear unavailable state, without historical fallbacks or plausible zero charts.
5. Scope cap/depth-chart storage by edition and schema, with explicit season applicability where scenarios span years. Keep legacy entries recoverable; require a deliberate migration/import rather than assigning ambiguous old state to Madden 27.
6. Treat playoff community predictions as a separate integration. Keep the legacy remote store disabled for the current cycle until a separate store and configuration are deliberately provisioned.

Acceptance: browser checks cover player usage, stats/trades, SoS, playoff reports, roster rankings, cap scenarios, and depth charts. Filters, exports, mobile layouts, and saved-state reloads still work. Old links resolve; saved scenarios remain exportable; current and archived pages cannot overwrite each other's state.

### 6. Remove proven redundancy and finish the operating workflow — P2

1. Apply the disposition list below only after replacements and compatibility checks pass.
2. Move protected formula/model artifacts out of the disposable output directory, updating every consumer and proving byte-for-byte preservation.
3. Establish a Git policy: track maintained source, canonical input snapshots, required assets, fixtures, and the files needed by the current hosting method. Ignore temporary builds, logs, and test reports. Stop relying on force-add for routine publication.
4. Keep committed publication artifacts during the initial migration. Consider artifact-based site deployment only as a separate change after verifying actual GitHub Pages settings and reproducing the existing site.
5. Update README export/build instructions, AGENTS architecture, and domain contracts. Fold completed design plans into current documentation or rely on Git history for superseded material.
6. Add automated gates for fixture tests, import validation, staged builds, browser smoke tests, broken local links/data paths, and archive integrity.

Acceptance: a clean checkout can follow one documented setup/import/build/check procedure; a weekly refresh needs no hand-editing of seasons or file lists; the published site needs no ignored local files. Every retained file category has a clear owner and purpose.

## What to keep, consolidate, or consider retiring

| Item | Planned disposition | Evidence required before removal |
| --- | --- | --- |
| Madden 26 archive | Keep unchanged | No removal proposed |
| Current raw exports, ELO, GM mapping, source image, import metadata | Keep; centralize provenance and paths | All readers migrated before removing old path copies |
| Formula references and trained OVR models | Keep; move out of disposable output later | Hash parity and updated consumers; Madden 27 calibration remains a separate question |
| Stats, trade, playoff, draft-race, SoS, roster, cap, and depth-chart features | Keep by default | User usage/retirement decision before removing a feature |
| Season-specific SoS wrappers and HTML copies | Consolidate | Generalized replacements pass parity checks; old commands/URLs remain usable |
| Broken snapshot harness and SoS verifier stubs | Replace | Working tests/checks cover their intended contract |
| Week-18 simulator and playoff bracket | Retain as seasonal tools pending modernization | Confirm desired future use; absence from the current weekly runner proves nothing |
| `browns-gameplan/index.html` | Preserve as an independent feature | Owner/use review before integrating or retiring |
| OVR training/research scripts | Isolate as optional research | No removal based on missing production references |
| Duplicate manual browser helpers, one-off page patch utilities, obsolete smoke commands | Retirement candidates | Search imports, shell calls, docs, package scripts, and external/manual usage; identify replacement coverage |
| Old `spec/*PLAN.md` and exploratory documents | Review and consolidate | Retain useful formulas/contracts and unresolved requirements; remove only superseded prose |
| Generated reports and duplicate browser data copies | Regenerate or consolidate | Build reproduces them; all consumers updated; publication no longer depends on old copies |

A file is removable only when it has no retained consumer or documented manual workflow, has a tested replacement or confirmed obsolete purpose, and is recoverable through Git. “Not imported” is insufficient for standalone commands and pages.

## Verification and completion criteria

- Use the current snapshot as a baseline: 32 teams, 272 regular-season games, 179 completed and 93 remaining, with 17 scheduled games per team. These are fixture expectations, not universal validation constants for all future exports.
- Verify game-derived W/L/T against exported standings and trade-aware player/team totals against league totals.
- Require exact parity for deterministic calculations; compare floats using documented numerical tolerances only where serialization/representation requires it. Seeded simulations should remain identical for structural moves. Statistical equivalence is a separate gate if sampling is intentionally redesigned.
- Keep probability display quirks separate from this refactor. Existing clamping of division/bye probabilities can make displayed totals exceed their theoretical aggregate; do not alter formulas under a cleanup commit.
- Check both clean builds and failure cases: missing files, invalid schema, mixed seasons, stale outputs, an interrupted task, and an optional feature with a real execution error.
- Serve and test the staged publication tree, including all browser data requests. A page loading successfully is insufficient if its charts silently lack data.
- Compare archive and protected asset hashes after each migration; ensure tests write only into temporary locations.

Suggested delivery is one focused PR per numbered phase, splitting Python/frontend extraction further by domain. Complete phases 1–3 first: they provide the largest reliability improvement and make later cleanup reviewable. Do not combine formula corrections, feature deletion, a visual redesign, and deployment migration into those PRs.

The refactor is complete when a new weekly export can be validated, built, checked, and published through one documented workflow; a new season needs only data/configuration changes; calculations retain their verified behavior; and every active page consumes artifacts from an identifiable, consistent snapshot.
