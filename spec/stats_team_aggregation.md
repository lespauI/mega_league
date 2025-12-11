# Team Statistics Aggregation

Script
- `stats_scripts/aggregate_team_stats.py`

Purpose
- Aggregate player-level CSVs into team-level metrics (counts, rates, efficiencies) to power visualizations.

Inputs
- `MEGA_passing.csv`, `MEGA_rushing.csv`, `MEGA_receiving.csv`, `MEGA_defense.csv`, `MEGA_punting.csv`, `MEGA_kicking.csv`, `MEGA_teams.csv`
- `output/player_team_stints.csv` (trade-aware per-team/per-player stints; raw and adjusted layers)
 - Shared helpers from `stats_scripts/stats_common.py` (notably `normalize_team_display`).

Outputs
- `output/team_aggregated_stats.csv` with columns including (non-exhaustive):
  - pass_att, pass_comp, pass_yds, pass_tds, pass_ints, pass_sacks, qb_rating
  - turnover debug fields: pass_ints_raw (unadjusted INT sum), pass_ints_adjustment (delta applied)
  - rush_att, rush_yds, rush_tds, rush_fum, rush_broken_tackles, rush_yac, rush_20plus
  - rec_catches, rec_yds, rec_tds, rec_drops, rec_yac
  - def_sacks, def_ints, def_fum_forced, def_fum_rec
  - punts, punts_in_20, fg_att/made, fg_50plus_att/made, xp_att/made
  - totals and derived: total_off_plays/yds/tds, total_turnovers/takeaways
  - rates: pass_yds_per_att, rush_yds_per_att, pass_comp_pct, pass_td_pct, pass_int_pct, sack_rate
  - more derived: rush_td_pct, rush_broken_tackle_rate, rec_yac_pct, td_per_play, yds_per_play, turnover_diff,
    per-game splits and ratios, pass_rush_ratio

Behavior
- Joins per-team across all CSVs using a **canonical team display name**, derived by `normalize_team_display`:
  - Strips whitespace.
  - Removes any leading numeric index and colon from stat rows (e.g., `"11:Browns"` → `"Browns"`), so they match `MEGA_teams.displayName`.
- Computes offensive volume stats (passing, rushing, receiving) by summing the **adjusted** fields from
  `output/player_team_stints.csv`:
  - Each stint row is trade-aware and may be scaled for multi-team players so that team-level offensive yardage
    (`offPassYds`, `offRushYds`) matches `MEGA_teams` for those teams.
  - Raw per-stint values (`*_raw` columns) remain a direct aggregation of the MEGA stat CSVs and are exposed via
    debug fields such as `pass_ints_raw`.
- Defensive, punting, and kicking stats continue to come directly from their respective MEGA CSVs, joined by
  canonical team name.
- Team games and record context still come from `MEGA_teams.csv` (wins/losses/ties), rather than per-player
  “per game” averages.
- For turnover metrics:
  - `pass_ints_raw` is the direct sum of `passTotalInts_raw` from `output/player_team_stints.csv` (unaltered raw MEGA values).
  - `pass_ints` is the sum of adjusted `passTotalInts` from stints and is used for all turnover-based metrics.
  - `pass_ints_adjustment = pass_ints - pass_ints_raw` captures the net effect of trade-aware scaling for that team.
  - `total_turnovers`, `total_takeaways`, `turnover_diff` and all per-game / percentage metrics are derived from the
    adjusted layer.
- Treats **traded / multi-team players** via the stint layer:
  - Each stint row contributes only to the canonical team on that row.
  - When a player has multiple teams in a season, their offensive stats are split and, if necessary, scaled across
    those teams according to `output/player_team_stints.csv`.
  - Combined with `scripts/verify_trade_stats.py`, this ensures no double-counting of production across teams while
    keeping team-level stats consistent with MEGA team summaries for core offensive yardage.

Run
- `python3 stats_scripts/aggregate_team_stats.py`

Acceptance Criteria
- CSV exists with one row per team and >60 metrics.
- Numeric fields parseable; win_pct derived from W/L/T when present.
- For non-turnover metrics, values are consistent with the adjusted sums from `player_team_stints.csv` and track
  MEGA team offensive yardage for teams with traded players.
- For turnovers, `pass_ints_raw` matches the raw player-level sum; `pass_ints`, `total_turnovers`, and `turnover_diff`
  are derived from the adjusted stint layer and remain internally consistent across all dashboards.
