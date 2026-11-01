# Data Inputs (CSV)

Purpose
- Define required input files and columns expected by analysis scripts.

Files in project root
- `MEGA_teams.csv`
- `MEGA_games.csv`
- `MEGA_rankings.csv`
- Optional for stats dashboards: `MEGA_passing.csv`, `MEGA_rushing.csv`, `MEGA_receiving.csv`, `MEGA_defense.csv`, `MEGA_punting.csv`, `MEGA_kicking.csv`

MEGA_teams.csv (required columns)
- displayName, teamName
- divisionName, conferenceName
- totalWins, totalLosses, totalTies (winPct optional; computed if missing)
- rank (optional; used for opponent rank displays)
- logoId (optional; used for CDN logos)
- Optional fields used by stats aggregation: off*/def* yard/point fields, tODiff, cap fields, etc.

MEGA_games.csv (required columns)
- id (NeonSportz page identity), gameId (game-source identity)
- homeTeam, awayTeam
- homeScore, awayScore
- status (1=scheduled; 2/3/4 are completed under the pipeline contract)
- weekIndex, seasonIndex, stageIndex
- home_fw, away_fw, is_superseded (explicit Boolean flags)

Performance calculations also require snapshot-bound game-box-score and historical
team evidence. See [Force Win exclusion](force_win_exclusion.md). Raw game results
remain the source for official standings and tiebreakers.

MEGA_rankings.csv (required columns)
- team, rank, prevRank
- ptsForRank, ptsAgainstRank
- offTotalYdsRank, offPassYdsRank, offRushYdsRank
- defTotalYdsRank, defPassYdsRank, defRushYdsRank
- weekIndex, seasonIndex, stageIndex

Notes
- CSVs must share the same team name keys (usually `displayName`).
- If your league prefix differs from `MEGA`, either rename files or update scripts to match.
- Export fresh data before running to keep outputs consistent with standings.

