# Depth Chart tool

The depth chart reads `MEGA_teams.csv`, `MEGA_players.csv`, and the active cycle identity in `docs/data/import_metadata.json` from the repository root. Serve the repository root over HTTP to use the page and its CSV export.

Roster edits, depth plans, selected team, and draft picks are stored per game edition, CSV season, and calendar year. Existing unscoped entries remain unchanged. Use the storage panel to export a backup, deliberately copy legacy data into the active cycle, or import a backup. Copy/import skips values already stored for that cycle.

The depth chart has a separate saved-data panel for draft picks shared with the Roster Cap Tool. Use that panel to migrate or back up picks; both tools read and write the same cycle-scoped draft-pick value.
