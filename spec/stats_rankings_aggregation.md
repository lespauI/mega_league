# Rankings + Team Stats Aggregation

Script
- `stats_scripts/aggregate_rankings_stats.py`

Purpose
- Combine latest team rankings from `MEGA_rankings.csv` with team metadata/stats to produce a single CSV for correlations.

Inputs
- `MEGA_rankings.csv`, `MEGA_teams.csv`

Outputs
- `output/team_rankings_stats.csv` with columns including:
  - team, conference, division, logoId, teamOvr
  - record: totalWins, totalLosses, totalTies, winPct; home/away splits & win pct
  - raw offense/defense yardage and points; turnovers; cap; schemes
  - latest ranks: rank, off*/def* ranks, ptsForRank, ptsAgainstRank
  - volatility/trend: rankVolatility, earlySeasonRank, lateSeasonRank, rankImprovement
  - derived: offDefRankDiff, combinedRank, offPassRushDiff, defPassRushDiff,
    offYdsPerPt, defYdsPerPt, passRushRatio, defPassRushRatio, offYdsPct, defYdsPct,
    winsPerMillion, ovrPerMillion, ptsRankEfficiency, defRankEfficiency

Behavior
- Picks the latest ranking per team by (seasonIndex, stageIndex, weekIndex); computes intra-season rank volatility and trends.
- Joins team metadata and calculates derived ratios and efficiencies.

Run
- `python3 stats_scripts/aggregate_rankings_stats.py`

Acceptance Criteria
- CSV exists and includes all teams present in `MEGA_teams.csv`.
- Latest week selection matches highest weekIndex per team.
- Derived fields present and numeric.

