# Synthetic MEGA fixtures for roster power rankings

This folder contains a tiny, synthetic MEGA-style dataset that can be
used for fast verification of the roster-based power rankings pipeline
without running against the full league CSVs.

## Files

- `tiny_MEGA_teams.csv` – 4 mock teams (BUF, KC, NYJ, CHI) with the
  minimal columns expected by `read_teams`.
- `tiny_MEGA_players.csv` – a small set of players for those teams,
  including positions, overall ratings, and dev traits. Attribute
  columns are omitted on purpose so the scoring logic falls back to
  overall rating, keeping the fixture compact.

## Quick verification workflow

From the project root, you can run the full pipeline and verification
helpers against these fixtures by overriding the `--players` and
`--teams` inputs:

```bash
python3 scripts/power_rankings_roster.py \
  --players .zenflow/tasks/power-rankings-b-df6a/fixtures/tiny_MEGA_players.csv \
  --teams .zenflow/tasks/power-rankings-b-df6a/fixtures/tiny_MEGA_teams.csv \
  --out-csv output/power_rankings_roster_tiny.csv \
  --out-html docs/power_rankings_roster_tiny.html

python3 scripts/verify_team_rosters_export.py \
  --teams .zenflow/tasks/power-rankings-b-df6a/fixtures/tiny_MEGA_teams.csv \
  --rosters-dir output/team_rosters

python3 scripts/verify_power_rankings_roster_csv.py \
  --csv output/power_rankings_roster_tiny.csv

python3 scripts/verify_power_rankings_roster_html.py \
  --html docs/power_rankings_roster_tiny.html \
  --csv output/power_rankings_roster_tiny.csv
```

These commands provide a fast regression-check path for future changes
to the scoring logic or HTML report structure.

