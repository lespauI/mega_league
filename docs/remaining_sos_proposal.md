**Remaining SoS Calculation — Proposal**

- Goal: Compute each team’s remaining Strength of Schedule (SoS) using scheduled games (`status = 1`) from `MEGA_games.csv`, and opponents’ current records from `MEGA_teams.csv`, with results split by conference (NFC/AFC).

**CSV Schemas (observed)**

- `MEGA_games.csv`
  - Key fields: `homeTeam`, `awayTeam`, `status` (values observed: 1, 2, 3, blank)
  - Meaning for this task: Use rows where `status = 1` as remaining (future) games. Team names in these columns match `MEGA_teams.csv` `displayName`/`teamName` values (e.g., "Eagles", "Cowboys").

- `MEGA_teams.csv`
  - Key fields: `displayName`, `teamName`, `abbrName`, `conferenceName`, `totalWins`, `totalLosses`, `totalTies`, `winPct`
  - `conferenceName` is either `AFC` or `NFC` (used to split outputs by conference).
  - `winPct` exists, but we can recompute as `(wins + 0.5 * ties) / (wins + losses + ties)` for robustness.

- `MEGA_rankings.csv`
  - Key fields: `team`, `totalWins`, `totalLosses`, `totalTies`, ranks by various stats.
  - Not strictly required if we rely on `MEGA_teams.csv` for records and conference. We can ignore unless a tie‑breaker or cross‑validation is needed.

**Assumptions**

- Remaining games are exactly the rows with `status = 1` in `MEGA_games.csv`.
- Team name matching uses `displayName`/`teamName` from `MEGA_teams.csv` to match `homeTeam`/`awayTeam` in `MEGA_games.csv`.
- SoS definition: average of opponent current win percentage across all remaining games (counting repeat opponents multiple times). If a team has no remaining games, SoS is 0.0 and remaining_games is 0.
- Records used for SoS are current snapshot values from `MEGA_teams.csv` (not projected forward).

**Algorithm**

1. Load `MEGA_teams.csv` and build a map: `team -> {conference, wins, losses, ties, win_pct}`.
2. Load `MEGA_games.csv`, filter rows with `status == 1`.
3. Build remaining opponent lists:
   - For each remaining game (`homeTeam`, `awayTeam`), add `awayTeam` to `homeTeam`’s opponent list and `homeTeam` to `awayTeam`’s opponent list.
4. Compute remaining SoS per team:
   - For each team: `remaining_sos_avg = mean(opponent.win_pct for each remaining opponent)`.
   - Also compute `remaining_games` and `remaining_sos_sum` for reference.
5. Split by `conferenceName` and sort within each conference by `remaining_sos_avg` (desc).
6. Output a CSV with at least: `team,conference,remaining_games,remaining_sos_avg,remaining_sos_sum`.

**Edge Cases & Data Hygiene**

- Missing teams/opponents: Skip opponents not present in `MEGA_teams.csv` (log and ignore).
- Zero remaining games: output 0.0 SoS.
- Ties: accounted for in computed `win_pct` as 0.5.
- Whitespace/case: strip whitespace; treat names case‑sensitively as observed; trim as needed.

**Deliverables**

- Python script: `scripts/calc_remaining_sos.py` that reads the three CSVs from the current directory and writes `output/remaining_sos_by_conference.csv`.
- Optional stdout preview of top/bottom teams per conference.

**Complexity & Rationale**

- O(G + T) where G is remaining games and T is teams.
- No external dependencies (pure Python `csv`), to avoid environment issues.

**Next Steps**

- Implement the script as outlined and run it to produce the final CSV.

