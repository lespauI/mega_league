# Player Usage Aggregation

Script
- `stats_scripts/aggregate_player_usage.py`

Purpose
- Calculate team-level distribution metrics for passing targets and rushing attempts; attach selected efficiency stats.

Inputs
- `MEGA_receiving.csv`, `MEGA_rushing.csv`, `MEGA_teams.csv`
- `output/team_aggregated_stats.csv` (for efficiency fields like qb_rating, sack_rate, etc.)

Outputs
- `output/team_player_usage.csv` with columns including:
  - wr/te/rb target shares, WR1/WR2/WR3 shares & names, top3_share
  - pass_concentration (HHI*10000), rush_concentration (HHI*10000)
  - TE1 name/catches, RB1/RB2 shares, RBBC flag
  - derived styles: pass_distribution_style, rush_distribution_style
  - selected efficiency joins: qb_rating, pass_int_pct, sack_rate, pass_td_pct, pass_comp_pct,
    rush_broken_tackle_rate, rush_yds_per_att, pass_yds_per_att, yds_per_play, td_per_play,
    turnover_diff, explosive_plays_per_game, def_sacks_per_game, rush_td_pct, drop_rate,
    rec_yac_pct, total_turnovers, pass_rush_ratio

Behavior
- Aggregates per-team catch/rush totals by position; computes shares and concentration indices.
- Determines usage style heuristics (Concentrated/Balanced/Spread; Bellcow/RBBC/Feature Back).

Run
- `python3 stats_scripts/aggregate_player_usage.py`

Acceptance Criteria
- CSV exists with one row per team.
- Shares sum logically (e.g., WR/TE/RB target shares ≈ 100% when data present).
- Joins to aggregated team stats populate efficiency fields when available.

