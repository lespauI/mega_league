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

Build `scripts/generate_playoff_dashboard.py` (Python, stdlib only) that reads CSV/JSON and outputs `docs/data/playoff_dashboard.json`:
- **Teams**: 14 playoff teams from `MEGA_teams.csv` (seasonIndex=2, seed 1-7) with record, seed, division, OVR, ELO, off/def stats
- **Bracket**: Standard NFL 14-team bracket derived from seeds (2v7, 3v6, 4v5 per conference; 1-seed bye). Cross-reference `MEGA_games.csv` stageIndex=0 to fill in scores for any completed playoff games
- **Top players**: Per team — best QB, RB, WR, DEF from passing/rushing/receiving/defense CSVs, enriched with OVR from `MEGA_players.csv`
- **Head-to-head**: For each bracket matchup pair, all historical games across all 3 seasons from `MEGA_games.csv`
- **ELO**: From `mega_elo.csv`

Verify: run the script, check JSON has 14 teams, 6 WC matchups, correct H2H game counts.

---

### [ ] Step 2: Bracket Dashboard — HTML Structure and Full-Screen Bracket

Create `docs/playoff_dashboard.html` — single self-contained HTML file:
- **Dark blue football field aesthetic** (Madden-style): dark gradient background, grass texture at bottom, white/gold text
- **"MEGA PLAYOFFS 2027" header**
- **Full-screen bracket layout** using CSS grid:
  - AFC on left: Wild Card → Divisional → Conference Championship
  - NFC on right (mirrored): Wild Card → Divisional → Conference Championship
  - Super Bowl in center
  - 1-seed BYE badges with conference logos
- **Matchup cards**: team logo (Neon CDN), seed badge, team name; scores shown for completed games
- **Connector lines** between rounds (CSS borders)
- Load data from `docs/data/playoff_dashboard.json` via fetch()
- Bracket cards are clickable (wired up in next step)

Verify: open in browser, bracket renders with all 14 teams in correct positions, dark theme looks good.

---

### [ ] Step 3: Matchup Detail Modal

Implement the click-to-open modal when user clicks any matchup in the bracket:
- **Modal overlay** with dark backdrop, slides in or fades in
- **Team Stats Comparison**: side-by-side comparison bars for both teams — W-L, OVR, ELO, Pts For/Against, Off Pass Yds, Off Rush Yds, Def Pass Yds, Def Rush Yds
- **Best Players**: top QB, RB, WR, DEF for each team with name, key stat line, OVR badge
- **Head-to-Head History**: list of all past games between these two teams (all seasons) with season, week, home/away, score, winner highlight
- **Prediction Vote**: click a team logo to predict winner, stored in `localStorage`, visual highlight on selected team
- Close button (X) and click-outside-to-close

Verify: click matchup → modal opens with correct data for both teams, prediction click persists after page reload.

---

### [ ] Step 4: Polish, Responsive Design, and Integration

- **Responsive pass**: tablet/mobile layout (stack AFC above NFC on narrow screens)
- **Animations**: subtle hover effects on matchup cards, modal transitions
- **Empty state handling**: divisional/conference/super bowl slots show "TBD" placeholder until wild card results known
- Add playoff dashboard link to `index.html` Reports section
- Add entry to `docs/README.md` Playoff & SoS table
- Add Playwright E2E test in `tests/e2e/` verifying: page loads, bracket renders 6 WC matchups + 2 BYE badges, click matchup opens modal, modal shows stats/H2H/predictions, prediction persists in localStorage
- Run E2E tests
- Write completion report to `.zenflow/tasks/mega-playoff-season-3-dashboard-bc5e/report.md`
