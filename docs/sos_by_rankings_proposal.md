**SoS by Rankings — Proposal**

- Goal: Evaluate Strength of Schedule (SoS) using team strength from rankings/stats in `MEGA_rankings.csv` instead of win/loss results, and apply that to remaining and past schedules from `MEGA_games.csv`. Output split by conference using `MEGA_teams.csv`.

**CSV Schemas (observed)**

- `MEGA_rankings.csv`
  - Columns: `team`, `totalWins`, `totalLosses`, `totalTies`, `rank`, `prevRank`, `ptsAgainstRank`, `ptsForRank`, `offPassYdsRank`, `offRushYdsRank`, `offTotalYdsRank`, `defPassYdsRank`, `defRushYdsRank`, `defTotalYdsRank`, plus season/week indices.
  - Ranks are 1..32 where 1 is best. Lower rank means better performance.

- `MEGA_games.csv`
  - Columns include: `homeTeam`, `awayTeam`, `status` (1=future, 2/3=completed, blank/other=ignore).
  - Team names match `MEGA_rankings.csv.team` and `MEGA_teams.csv.displayName/teamName`.

- `MEGA_teams.csv`
  - Columns include: `displayName`, `teamName`, `conferenceName` (AFC/NFC), current W/L/T.
  - Used for conference split and optional record display.

**Core Idea**

- Build a single numeric `strength_score` per team from rankings/stats. Then:
  - Remaining SoS (ranked): average/sum of opponents’ `strength_score` for `status=1` games.
  - Past SoS (ranked): average/sum of opponents’ `strength_score` for completed games (`status in {2,3}`).
  - Total SoS (ranked): sum of past + remaining sums.

**Strength Score Design**

- Convert each rank to a normalized score where higher is better:
  - `norm(rank) = (33 - rank) / 32` → 1.000 for rank 1, ~0.031 for rank 32.
- Group metrics and weight them:
  - Offense metrics: `ptsForRank`, `offTotalYdsRank`, `offPassYdsRank`, `offRushYdsRank`.
  - Defense metrics: `ptsAgainstRank`, `defTotalYdsRank`, `defPassYdsRank`, `defRushYdsRank`.
  - Optional team rank/trend: `rank` and `prevRank` (captures overall form and momentum).
- Proposed weights (tunable):
  - Offense group: 0.4
  - Defense group: 0.4
  - Overall rank group (rank + prevRank): 0.2
    - Within each group, average the normalized metrics equally.

Formula sketch:

- `off_score = mean(norm(off ranks))`
- `def_score = mean(norm(def ranks))`
- `overall_score = mean(norm(rank), norm(prevRank))` (if `prevRank` missing, use `rank` only)
- `strength_score = 0.4*off_score + 0.4*def_score + 0.2*overall_score`

Notes:
- If any rank is missing or non-numeric, skip it in the group average. If an entire group is missing, drop its weight and renormalize remaining weights.
- This keeps the score in [0,1], where 1 is strongest.

**SoS Calculation (rank-based)**

- For each team T:
  - `remaining_opponents = opponents from games with status=1`
  - `past_opponents = opponents from games with status in {2,3}`
  - `ranked_sos_sum = Σ strength_score(opponent) over remaining_opponents`
  - `ranked_sos_avg = ranked_sos_sum / len(remaining_opponents)` (0 if none)
  - `past_ranked_sos_sum = Σ strength_score(opponent) over past_opponents`
  - `past_ranked_sos_avg = past_ranked_sos_sum / len(past_opponents)` (0 if none)
  - `total_ranked_sos = ranked_sos_sum + past_ranked_sos_sum`

**Output Schema (proposed)**

- `team`
- `conference`
- `W` / `L` (optional but useful context; from `MEGA_teams.csv`)
- `remaining_games`
- `ranked_sos_avg` (by rankings)
- `ranked_sos_sum` (by rankings)
- `past_ranked_sos_avg`
- `total_ranked_sos`

Sorting: by `conference`, then `ranked_sos_avg` desc.

**Edge Cases & Hygiene**

- Name mapping: strip whitespace; prefer exact match of `rankings.team` with `games.homeTeam/awayTeam`. If not found, try `teams.displayName`/`teamName`.
- Missing ranks: skip per-metric and reweight groups as described.
- Multiple rows in rankings: pick latest by `seasonIndex`, `stageIndex`, `weekIndex` (max) per team.
- Teams with no remaining games: set `ranked_sos_avg=0`, `remaining_games=0`.

**Script Plan**

- File: `scripts/calc_sos_by_rankings.py`
- Steps:
  1. Load latest ranking row per team from `MEGA_rankings.csv` and compute `strength_score`.
  2. Load `MEGA_games.csv` and split into remaining (status=1) and past (status in {2,3}).
  3. Load `MEGA_teams.csv` for `conferenceName` (and W/L if included).
  4. Build opponent lists and compute ranked SoS metrics per team.
  5. Write `output/ranked_sos_by_conference.csv` with the proposed schema and a console preview.

**Configurability (optional)**

- CLI args to tweak group weights (e.g., `--w-off 0.4 --w-def 0.4 --w-rank 0.2`).
- Flag to include/exclude W/L columns.
- Output both average and sum metrics.

If you approve, I’ll implement `scripts/calc_sos_by_rankings.py` per this design.

