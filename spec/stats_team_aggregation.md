# Team Statistics Aggregation

Script
- `stats_scripts/aggregate_team_stats.py`

Purpose
- Aggregate player-level CSVs into team-level metrics (counts, rates, efficiencies) to power visualizations.

Inputs
- `MEGA_passing.csv`, `MEGA_rushing.csv`, `MEGA_receiving.csv`, `MEGA_defense.csv`, `MEGA_punting.csv`, `MEGA_kicking.csv`, `MEGA_teams.csv`

Outputs
- `output/team_aggregated_stats.csv` with columns including (non-exhaustive):
  - pass_att, pass_comp, pass_yds, pass_tds, pass_ints, pass_sacks, qb_rating
  - rush_att, rush_yds, rush_tds, rush_fum, rush_broken_tackles, rush_yac, rush_20plus
  - rec_catches, rec_yds, rec_tds, rec_drops, rec_yac
  - def_sacks, def_ints, def_fum_forced, def_fum_rec
  - punts, punts_in_20, fg_att/made, fg_50plus_att/made, xp_att/made
  - totals and derived: total_off_plays/yds/tds, total_turnovers/takeaways
  - rates: pass_yds_per_att, rush_yds_per_att, pass_comp_pct, pass_td_pct, pass_int_pct, sack_rate
  - more derived: rush_td_pct, rush_broken_tackle_rate, rec_yac_pct, td_per_play, yds_per_play, turnover_diff,
    per-game splits and ratios, pass_rush_ratio

Behavior
- Joins per-team across all CSVs via `team__displayName`.
- Computes per-team totals, per-play rates, per-game and percentage metrics.

Run
- `python3 stats_scripts/aggregate_team_stats.py`

Acceptance Criteria
- CSV exists with one row per team and >60 metrics.
- Numeric fields parseable; win_pct derived from W/L/T when present.
- Values consistent with raw sums from source CSVs.

