# Spec and build

## Configuration
- **Artifacts Path**: {@artifacts_path} → `.zenflow/tasks/{task_id}`

---

## Agent Instructions

Ask the user questions when anything is unclear or needs their input. This includes:
- Ambiguous or incomplete requirements
- Technical decisions that affect architecture or user experience
- Trade-offs that require business context

Do not make assumptions on important decisions — get clarification first.

---

## Workflow Steps

### [x] Step: Technical Specification

Spec saved to `.zenflow/tasks/mega-playoff-season-3-dashboard-bc5e/spec.md`.

Difficulty: **Hard** — multi-section interactive dashboard with bracket visualization, predictions/voting, player stats aggregation, head-to-head history, all from CSV data sources.

---

### [ ] Step 1: Data Pre-computation Script

Build `scripts/generate_playoff_dashboard.py` that reads all CSV/JSON sources and outputs `docs/data/playoff_dashboard.json` with:
- Bracket structure (AFC/NFC wild card, divisional, conference championship, super bowl) from `MEGA_games.csv` stageIndex=0
- Team cards for all 14 playoff teams (record, seed, division, OVR, ELO, offensive/defensive stats) from `MEGA_teams.csv`
- Top players per team (QB, RB, WR, DEF) from passing/rushing/receiving/defense CSVs + OVR from `MEGA_players.csv`
- Head-to-head history between each playoff matchup pair across all 3 seasons from `MEGA_games.csv`
- Conference standings from `MEGA_teams.csv` + `playoff_probabilities.json`

Verify: run the script, validate JSON output structure, ensure all 14 teams present, bracket has correct matchup count.

---

### [ ] Step 2: Dashboard HTML Shell and Bracket Section

Create `docs/playoff_dashboard.html` with:
- Page structure matching existing project style (gradient bg, white container, system fonts)
- Sticky tab navigation: Bracket | Teams | Predictions | Stats | Head-to-Head
- Bracket section: visual AFC and NFC brackets (Wild Card → Divisional → Conference → Super Bowl)
- Team logos via Neon CDN, seed badges, scores for completed games
- CSS grid bracket layout with connector lines
- Load data from `docs/data/playoff_dashboard.json` via fetch()

Verify: open in browser, confirm bracket renders with correct matchups and team logos.

---

### [ ] Step 3: Team Cards and Conference Standings

Add to the dashboard:
- Team Cards tab: grid of 14 playoff team cards with logo, name, record, seed, division, OVR, ELO, pts scored/allowed
- Click-to-expand detail panel showing offensive/defensive stats breakdown
- Conference Standings tab content: AFC and NFC tables with W-L, win%, seed, SoS, ELO, clinch/eliminate badges
- Division winner badges, wild card indicators, color-coded by seed

Verify: all 14 teams display correctly, stats match CSV data.

---

### [ ] Step 4: Best Players and Team Stats Sections

Add to the dashboard:
- Stats tab: per-team offensive/defensive comparison bars for playoff teams (pass yds, rush yds, pts for/against)
- Best Players section: for each playoff team show top QB, RB, WR, DEF player with name, key stat, OVR rating
- Player mini-cards with position badge and stats

Verify: top players match expected leaders from CSV data.

---

### [ ] Step 5: Head-to-Head History and Predictions

Add to the dashboard:
- Head-to-Head tab: for each current playoff matchup, show all historical games between the two teams (all 3 seasons)
- Game cards with season, week, home/away, score, winner highlight
- Predictions section: for each unplayed matchup, clickable team logos to predict winner
- Predictions stored in localStorage, visual feedback on selection
- Prediction summary panel showing user's bracket picks

Verify: head-to-head shows correct game history, predictions persist across page reload.

---

### [ ] Step 6: Integration, Polish, and Index Update

- Add playoff dashboard link to `index.html` Reports section
- Add entry to `docs/README.md` Playoff & SoS table
- Responsive design pass: mobile layout (single column), tablet, desktop
- Add Playwright E2E test in `tests/e2e/` verifying: page loads, bracket renders, team cards present, prediction click works, head-to-head displays
- Run E2E tests
- Write completion report to `.zenflow/tasks/mega-playoff-season-3-dashboard-bc5e/report.md`
