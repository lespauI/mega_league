# Orchestration and publication contract

Current implementation: `mega/pipeline/execution.py`; compatible API: `scripts/pipeline_tasks.py`.

## Commands

- `python3 scripts/run_all.py --season-index 0`: full staged build and local publication.
- `python3 scripts/run_all.py --season-index 0 --validate-only`: identical staged calculations/checks, without publication.
- `python3 scripts/run_all_stats.py`: stats task selection after a successful full build for the same input snapshot.
- `python3 scripts/run_all_playoff_analysis.py --season-index 0`: playoff task selection with the same prerequisite.
- `python3 scripts/verify_site.py --root PATH`: read-only validation of an assembled publication root.
- `python3 scripts/check.py`: fixture and Node checks; add `--build`, `--site`, or `--browser` as needed. The existing cap B/C/D baseline stays visible; `--allow-known-cap-failures` permits only its exact six recorded assertions.

Use the zero-based CSV season index. ELO artifact names use the one-based display season, derived from validated cycle metadata. The active export week and ELO source week remain separate.

## Execution

`TASKS` and `GROUPS` in `mega/pipeline/execution.py` are the authoritative dependency graph; do not copy task sequences into operational documentation. Stints precede dependent statistics. Each prerequisite runs once. A failed enabled task stops subsequent work, including optional-feature execution errors. Only deliberately disabled features may be skipped.

All full-build output is generated in a clean temporary workspace. Archive data and previous generated results cannot serve as calculation inputs. The build preserves formula/model assets and checks their hashes. Subset builds copy forward only verified same-snapshot artifacts from a completed full-build manifest.

## Artifact and browser contract

`mega/pipeline/artifacts.py` registers producer outputs, generated path ownership, and logical browser dataset keys. `docs/site_manifest.json` declares page artifact requirements (`requires`), browser keys (`requiresData`), feature flags, and season applicability.

Registered generated text files are normalized to LF before hashing, matching `.gitattributes`; committing and checking out the publication therefore preserves manifest hashes. Raw inputs and protected assets are not changed by this assembly step.

Every successful full build produces:

- `output/build_manifest.json`: snapshot identity, runtime, simulation seed, selected tasks, artifact hashes.
- `docs/data/build_manifest.json`: browser copy of the build manifest.
- `docs/data/data_manifest.json`: schema, snapshot/cycle identity, and logical dataset URLs relative to this manifest.

The browser loader resolves URLs relative to the manifest, preserving project-subpath hosting. Missing data is an error. Retained season pages reject a mismatched active cycle instead of loading current data under a historical label. Community predictions remain disabled unless deliberately configured for the current edition.

## Publication gates

1. Required producer outputs exist.
2. SoS verification checks complete, reciprocal schedules and matching CSV/JSON data.
3. Browser datasets and page requirements resolve for the active snapshot.
4. The complete site has local HTML assets and nested JS module dependencies.
5. Generated files match the build hashes; protected assets retain their bytes.

Only registry-owned files can be published or removed. On a publication error, already-replaced files are rolled back. A validation-only build cleans its temporary workspace and does not change live output. Navigation generation only renders `index.html` after checking manifests.

Keep publication manifests and required generated files together in Git for the current repository-root hosting setup. External deployment, changing hosting configuration, and Git publication require their own authorization.
