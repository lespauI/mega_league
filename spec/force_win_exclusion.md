# Force Win exclusion in production

## Policy and boundaries

A game with `home_fw` or `away_fw` set is excluded for both teams from performance
statistics, recent form, analytical SoS, performance rankings, and predictive
strength inputs. Its official completion status never changes. Standings, playoff
qualification/tiebreakers, the Week 18 simulator, and draft-order results retain
all official results. External ELO remains the declared Week 8 source, explicitly
labeled as an unadjusted external reference; model weights are unchanged.

## Reproducible evidence

`data/performance_evidence/` contains exactly two versioned inputs:
`manifest.json` and `snapshot.tar.gz`. The archive contains the complete game and
history evidence; the manifest binds those records to the raw export byte
hashes and import metadata. The first validated API snapshot covered all 214 completed regular-
season games, including 23 Force Wins, and the histories of 15 players with
duplicated source-stat identities. Gzip timestamps, tar metadata and member order
are fixed, so identical evidence produces identical archive bytes. The packed
snapshot is about 0.5 MB, compared with 7.2 MB / 259,000 lines of expanded JSON.
Expanded files are automatically restored to `.cache/performance/evidence/`, are
ignored by Git, and may be deleted without losing source evidence. A clean checkout
can build entirely offline from the two versioned files. Archive and per-member
hashes are verified before use; damaged local caches are rebuilt from the bundle.

Retain only game/stat identities, numeric box-score fields, category
membership, player names/IDs and team-history tables. Never retain authentication,
account state, unrelated page state, or full player profiles.

Run `scripts/fetch_performance_evidence.py` after each CSV import. It reads the
public JSON API directly using Python's standard library, without a browser,
cookies, token, or login. Incremental acquisition is the default: only new,
changed or uncached completed games are fetched, including Force Wins. Missing or
damaged expanded cache files are restored from the verified local bundle first.
It uses these endpoints (using the CSV `id`, not `gameId`):

- `/api/leagues/MEGA/games/<id>/`
- `/api/leagues/MEGA/games/<id>/stats/teams/`
- `/api/leagues/MEGA/games/<id>/stats/players/`
- `/api/leagues/MEGA/players/<rosterId>/history/` for duplicated source-stat identities.

Each `games/<id>.json` retains game identity, two teams' game statistics, category
row-ID inventories and player-game records. Only explicitly selected calculation
fields and identities are stored; nested player/team profiles are discarded.
These JSON members live inside the archive and in the disposable expanded cache.
`sourceUrl` remains the human-readable source identity; `apiUrls` and
`acquisition: api` record how the evidence was obtained. Category membership uses
non-null source participation fields, including zero attempts. Required histories
include every pagination page and preserve explicit free-agent checkpoints.

An unchanged run reuses all hash-verified API captures and makes no network
requests. Cached game identity, teams, scores, week, completion status and flags
must match the current CSV, and season/calendar-year scope must match. Required
player histories are reused only while that player's game-stat inventory is
unchanged; new or changed inventories refresh their history. Removed, superseded
and out-of-cycle games are omitted from the new snapshot. All season totals are
reconciled even when every game was reused.

The CSV does not expose a per-game box-score revision number. A historical stat
edit with unchanged game fields cannot be identified directly. If it makes cached
totals disagree with the fresh exports, acquisition stops and recommends
`--full-refresh`; the previous evidence remains installed. Use a full refresh for
known historical corrections or a deliberate complete source audit, including
changes that cancel out in season totals.

The importer uses at most three concurrent requests by default (`--workers 1` to
`4`), bounded timeouts and retries for transient server/network failures. A rate
limit, access error, invalid response, export mismatch or failed reconciliation
stops the refresh. Acquisition and validation happen in a temporary directory;
the current evidence is replaced only after all checks pass. Changed raw inputs
during acquisition also prevent installation. The temporary directory is removed
on success or failure. No partial refresh is installed.

```bash
python3 scripts/fetch_performance_evidence.py  # incremental; default
python3 scripts/run_all.py --season-index 0

# Deliberately refetch every completed game and required history:
python3 scripts/fetch_performance_evidence.py --full-refresh
```

The fetch command seals hashes and runs the full performance reconciliation before
installing evidence. The regular pipeline rebuilds from that evidence offline;
network acquisition is never an implicit build dependency. For offline checks use
`python3 scripts/build_performance.py --season-index 0`. The manual
`seal_performance_evidence.py` compatibility helper performs offline validation
and rebinding; it fails if new API data is required.

The endpoints are the site's internal API rather than a versioned integration
contract. Unexpected schema changes fail validation instead of publishing partial
statistics. A successful refresh does not require keeping NeonSportz open.

The build independently
checks every completed game against the CSV, each player/category/team inventory,
all counting statistics, longest plays, participation counts, and all six team
season-yardage fields against the unfiltered exports before applying exclusions.
Existing cross-source discrepancies are recorded in `sourceReconciliationNotes`;
independently reconciled team and player figures remain separate and are not scaled.
A different export requires rerunning the incremental importer and validation;
there is no raw-season-stat fallback.

## Trade attribution

NeonSportz can copy a player's early game statistics into a later team's game
records. The copied records have different database row IDs but the same immutable
source `statId`. They can contaminate both game pages and season exports, so a
visible game log alone is insufficient evidence.

Records sharing player ID and source stat ID must have identical mapped statistics
and belong to the same week. Captured historical team changes select the original
team, using the earliest observed team as the baseline before its first checkpoint.
An explicit free-agent checkpoint remains a gap; it never assigns a team. Exactly
one matching team record must exist, otherwise the build stops. Corrected entries
are discarded before filtering Force Wins. No proportional scaling or repeated
subtraction is applied. The initial evidence resolves 24 duplicated player-game
records, including both sides of the Skattebo/Achane trade.

## Pipeline and consumers

`performance` is the first pipeline task. `mega/stats/performance.py` rebuilds the
six positional-stat CSVs, team performance records and weekly performance rankings
under `.cache/performance/inputs/`. These internal files are recreated in every
clean staged build. The existing aggregation formulas consume them through
`mega/inputs/performance.py`, which checks input/policy/evidence/cache hashes.
Official-result readers continue to use the raw CSVs. Legacy trade scaling is
bypassed for already reconciled performance inputs.

Counts and maxima come from eligible player-game records. Per-player denominators
are verified category participation counts. Rates are recalculated; passer rating
is used only when its formula reconciles with the export. Unsupported fields are
blank with a reason in the manifest, never replaced with zero. Player/category rows
with no eligible appearances are omitted. Per-team rates use eligible team games.

Weekly analytical ranks use per-game offense/defense yardage and scoring ranks;
overall rank uses the existing `teamStrengthIndex` scoring z-score definition.
Exported historical ranks do not enter performance strength. The existing SoS
weights are unchanged. Analytical SoS excludes flagged matchups; official W/L/T
columns remain report context. Draft reporting uses a separate official SoS file,
retaining its original ranking/schedule inputs and ordering.

Registered public artifacts are `output/performance/teams.csv`, `games.csv` and
`manifest.json`. The provenance manifest records source/input/output hashes,
exclusions, duplicate resolutions and unavailable fields. Browser data keys are
`performance_teams`, `performance_games`, and `performance_provenance`. Performance
pages explain the scope; blank metrics are rejected as numeric chart values.
ELO schedule entries retain their true week indexes after exclusions.

Subset builds require matching snapshot, policy and evidence identities. Full
builds validate and publish generated files transactionally. Git publication is a
separate, user-authorized workflow.

## Validation

Run `python3 scripts/check.py --allow-known-cap-failures --site` and the current-
cycle browser smoke suite after a full build. `tests/test_performance.py` uses only
temporary fixture directories and checks exclusion for both teams, unchanged raw
results, participation/maxima rebuilding, duplicate attribution, and stale/missing
source rejection. Browser tests check the public eligible-game inventory and policy
label. Preserve the six recorded cap B/C/D failures separately.

`tests/test_performance_api.py` covers acquisition without credentials, pagination,
trade/free-agent history, minimal retained fields, transient-error retries and
preservation of the current evidence after failed or inconsistent refreshes. It
also verifies zero-request repeat runs, selective new/changed/missing/corrupt-game
fetches, full-refresh bypass and rejection of hidden box-score inconsistencies.
`tests/test_evidence_bundle.py` checks deterministic packing, a cold-cache offline
build with identical calculations, cache repair, tampered archives and unsafe or
incomplete archive inventories.
