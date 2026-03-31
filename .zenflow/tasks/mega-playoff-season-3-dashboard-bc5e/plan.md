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

### [x] Step 1: Data Pre-computation Script
<!-- chat-id: 99e61999-192c-4410-91fa-45655ecf4c75 -->

Build `scripts/generate_playoff_dashboard.py` (Python, stdlib only) that reads CSV/JSON and outputs `docs/data/playoff_dashboard.json`:
- **Teams**: 14 playoff teams from `MEGA_teams.csv` (seasonIndex=2, seed 1-7) with record, seed, division, OVR, ELO, off/def stats
- **Bracket**: Standard NFL 14-team bracket derived from seeds (2v7, 3v6, 4v5 per conference; 1-seed bye). Cross-reference `MEGA_games.csv` stageIndex=0 to fill in scores for any completed playoff games
- **Win probabilities**: For each matchup, compute `homeWinPct` using the same formula from `calc_playoff_probabilities.py` (ELO 50%, win% 25%, SOS 15%, SOV 10% + home field advantage + streak modifiers, clamped [0.25, 0.75]). Reuse the logic, not the module — keep it self-contained.
- **Top players**: Per team — best QB, RB, WR, DEF from passing/rushing/receiving/defense CSVs, enriched with OVR from `MEGA_players.csv`
- **Head-to-head**: For each bracket matchup pair, all historical games across all 3 seasons from `MEGA_games.csv`
- **ELO**: From `mega_elo.csv`

Verify: run the script, check JSON has 14 teams, 6 WC matchups, correct H2H game counts.

---

### [x] Step 2: Bracket Dashboard — HTML Structure and Full-Screen Bracket
<!-- chat-id: d6e8bc40-c590-4dde-bf36-e3944be80fcd -->

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

### [x] Step 3: Matchup Detail Modal
<!-- chat-id: 6ab497e3-0add-4941-a3c5-273096e98c86 -->

Implement the click-to-open modal when user clicks any matchup in the bracket:
- **Modal overlay** with dark backdrop, slides in or fades in
- **Win Probability Bar**: horizontal split bar showing each team's win % (e.g. "Raiders 62% — 38% Titans"), color-coded by team
- **Team Stats Comparison**: side-by-side comparison bars for both teams — W-L, OVR, ELO, Pts For/Against, Off Pass Yds, Off Rush Yds, Def Pass Yds, Def Rush Yds
- **Best Players**: top QB, RB, WR, DEF for each team with name, key stat line, OVR badge
- **Head-to-Head History**: list of all past games between these two teams (all seasons) with season, week, home/away, score, winner highlight
- **Community Prediction Vote**: click a team logo to predict winner. User gets anonymous UUID in `localStorage`. Votes read/written to JSONBin.io (bin `69cbb01436566621a8663829`, X-Access-Key in code). Aggregate vote counts shown as split bar. One vote per user per matchup.
- Close button (X) and click-outside-to-close

Verify: click matchup → modal opens with correct data for both teams, prediction click persists after page reload.

---

### [ ] Step 4: Polish, Responsive Design, and Integration
<!-- chat-id: 66faf696-daf6-4717-8890-94916affaa70 -->

- **Responsive pass**: tablet/mobile layout (stack AFC above NFC on narrow screens)
- **Animations**: subtle hover effects on matchup cards, modal transitions
- **Empty state handling**: divisional/conference/super bowl slots show "TBD" placeholder until wild card results known
- Add playoff dashboard link to `index.html` Reports section
- Add entry to `docs/README.md` Playoff & SoS table
- Add Playwright E2E test in `tests/e2e/` verifying: page loads, bracket renders 6 WC matchups + 2 BYE badges, click matchup opens modal, modal shows win probability + stats + H2H + community vote UI
- Run E2E tests
- Write completion report to `.zenflow/tasks/mega-playoff-season-3-dashboard-bc5e/report.md`



### [ ] Step: Responsive design

Most probably this page would be open on mobile phone we need to take responsive design into account for every page
