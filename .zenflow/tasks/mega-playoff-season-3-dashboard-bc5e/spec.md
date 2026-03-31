# Technical Specification: Mega Playoff Season 3 Dashboard

## Difficulty: Hard

Complex feature involving multiple interactive UI sections, bracket visualization, voting/prediction system, data aggregation from many CSV sources, and head-to-head history computation. Architectural considerations around state management (client-side only), responsive design, and performance with large datasets.

---

## Technical Context

- **Language**: HTML/CSS/JavaScript (vanilla, no build step — matches existing codebase)
- **Data format**: CSV files at project root (`MEGA_*.csv`) + pre-computed JSON/CSV under `docs/data/` and `output/`
- **Hosting**: Static site via `python3 -m http.server` or GitHub Pages
- **Dependencies**: None required (existing pages use vanilla JS + optional D3 from CDN). We will use D3.js (CDN) for bracket visualization.
- **Team logos**: Neon Sports CDN — `https://neonsportz.com/logos/{logoId}.png` (pattern used in existing pages)
- **Testing**: Playwright E2E tests (`package.json` already configured)

---

## Data Sources Available

### CSV Files (root)
| File | Key columns | Rows | Purpose |
|------|------------|------|---------|
| `MEGA_teams.csv` | displayName, abbrName, conferenceName, divName, totalWins, totalLosses, seed, playoffStatus, logoId, seasonIndex, ovrRating | 32 teams (season 2 = Season 3) | Team standings, conference, seeding |
| `MEGA_games.csv` | homeTeam, awayTeam, homeScore, awayScore, seasonIndex, stageIndex, weekIndex, status | 926 rows, 3 seasons | Game results; stageIndex=0 → playoff, stageIndex=1 → regular season |
| `MEGA_passing.csv` | player__fullName, team__abbrName, passTotalYds, passTotalTDs, passTotalInts, passerAvgRating | 77 rows | Passing stats |
| `MEGA_rushing.csv` | player__fullName, team__abbrName, rushTotalYds, rushTotalTDs, rushAvgYdsPerAtt | ~rows | Rushing stats |
| `MEGA_receiving.csv` | player__fullName, team__abbrName, recTotalYds, recTotalTDs, recTotalCatches | ~rows | Receiving stats |
| `MEGA_defense.csv` | player__fullName, team__abbrName, defTotalSacks, defTotalInts, defTotalTackles | ~rows | Defensive stats |
| `MEGA_players.csv` | fullName, team, position, playerBestOvr, devTrait, age, draftRound | 3107 rows | Full player database with OVR ratings |
| `mega_elo.csv` | Team, Coach, Week 14+ (ELO rating) | 32 rows | Team ELO ratings |

### Pre-computed (docs/data/)
| File | Content |
|------|---------|
| `playoff_probabilities.json` | Per-team: W, L, conference, division, playoff_probability, division_win_probability, bye_probability, clinched, eliminated |
| `ranked_sos_by_conference_season3.csv` | SoS rankings per team |
| `season3_elo.csv` | Season 3 ELO-based SoS |
| `schedules_season3.json` | Per-team remaining schedule details |

### Season 3 Playoff State
- **14 playoff teams** (7 AFC, 7 NFC) — seeds 1-7 each conference
- **playoffStatus values**: 4 = 1st seed/bye, 3 = division winner, 2 = wild card, 0 = eliminated/not in
- **16 playoff games** at stageIndex=0 — mostly status=1 (scheduled, not played), 1 game completed (Steelers vs Buccaneers 35-38)
- Playoff bracket structure: Wild Card (12 games) → Divisional → Conference Championship → Super Bowl

---

## Implementation Approach

Build a single-page `docs/playoff_dashboard.html` file (self-contained HTML with embedded CSS/JS, matching existing page pattern) that serves as the ultimate Season 3 Playoff Dashboard. Data is loaded client-side from CSV/JSON files using `fetch()`.

### Dashboard Sections

#### 1. Playoff Bracket Visualization
- Visual bracket for AFC and NFC (Wild Card → Divisional → Conference → Super Bowl)
- Show team logos, seeds, and scores for completed games
- Highlight current round / upcoming matchups
- Color-code by game status (completed, scheduled, TBD)

#### 2. Team Cards (Playoff Teams)
- For each of the 14 playoff teams: logo, record, seed, conference rank, ELO rating, OVR rating
- Click to expand for detailed roster/stats
- Division winners badge, wild card indicator

#### 3. Fan Predictions / Voting
- For each upcoming/unplayed matchup, users can click to predict a winner
- Predictions stored in `localStorage` (no backend needed)
- Show community-style prediction bar (user's own picks since no server)
- Track prediction accuracy once games complete

#### 4. Team Season Statistics
- Per-team stats panel: total offense, total defense, passing/rushing splits
- Source from `MEGA_teams.csv` columns (offPassYds, offRushYds, defPassYds, defRushYds, ptsFor, ptsAgainst, etc.)
- Visual bars/charts comparing playoff teams

#### 5. Best Players per Team
- Top QB (passing yards/TDs), Top RB (rushing yards), Top WR (receiving yards), Top DEF (sacks/INTs)
- Source from `MEGA_passing.csv`, `MEGA_rushing.csv`, `MEGA_receiving.csv`, `MEGA_defense.csv`
- Player cards with position, stats, OVR from `MEGA_players.csv`

#### 6. Head-to-Head History
- For each playoff matchup: show all past games between the two teams across all 3 seasons
- Win/loss record, scores, home/away
- Source from `MEGA_games.csv` filtered by both teams and status >= 2

#### 7. Conference Standings Summary
- AFC and NFC standings table with W-L, win%, seed, SoS, ELO
- Clinch/eliminate badges from playoff_probabilities.json

---

## Source Code Changes

### New Files
| File | Description |
|------|-------------|
| `docs/playoff_dashboard.html` | Main playoff dashboard (single self-contained HTML page) |
| `scripts/generate_playoff_dashboard.py` | Python script to pre-compute playoff bracket data and team stats into `docs/data/playoff_dashboard.json` for fast client-side loading |

### Modified Files
| File | Change |
|------|--------|
| `index.html` | Add link to the new playoff dashboard in the Reports & Visualizations section |
| `docs/README.md` | Add entry for playoff_dashboard.html in the Playoff & SoS table |

### Generated Data
| File | Content |
|------|---------|
| `docs/data/playoff_dashboard.json` | Pre-computed JSON with: bracket structure, team cards, per-team top players, head-to-head history, team stats |

---

## Data Model: playoff_dashboard.json

```json
{
  "generated_at": "2026-03-31T...",
  "season_index": 2,
  "conferences": {
    "AFC": {
      "teams": [
        {
          "name": "Bengals",
          "abbr": "CIN",
          "logoId": 1,
          "seed": 1,
          "wins": 14,
          "losses": 3,
          "playoffStatus": 4,
          "division": "AFC North",
          "ovrRating": 92,
          "elo": 1270.0,
          "ptsFor": 29,
          "ptsAgainst": 16,
          "offPassYds": 4200,
          "offRushYds": 1298,
          "defPassYds": 2821,
          "defRushYds": 1358,
          "topPlayers": {
            "QB": { "name": "...", "yards": 0, "tds": 0, "ovr": 0 },
            "RB": { "name": "...", "yards": 0, "tds": 0, "ovr": 0 },
            "WR": { "name": "...", "yards": 0, "tds": 0, "ovr": 0 },
            "DEF": { "name": "...", "sacks": 0, "ints": 0, "tackles": 0, "ovr": 0 }
          }
        }
      ]
    },
    "NFC": { ... }
  },
  "bracket": {
    "AFC": {
      "wildcard": [
        { "home": "Patriots", "away": "Titans", "homeSeed": 4, "awaySeed": 7, "homeScore": null, "awayScore": null, "status": "scheduled", "weekIndex": 2 }
      ],
      "divisional": [],
      "conference_championship": null
    },
    "NFC": { ... },
    "super_bowl": null
  },
  "head_to_head": {
    "Bengals_vs_Raiders": [
      { "season": 1, "week": 4, "home": "Bengals", "away": "Raiders", "homeScore": 42, "awayScore": 39 }
    ]
  }
}
```

---

## UI Design

- **Style**: Match existing project aesthetic — gradient background (`#667eea → #764ba2`), white card containers, rounded corners, shadow, system font stack
- **Layout**: Single page with sticky navigation tabs at top (Bracket | Teams | Predictions | Stats | Head-to-Head)
- **Responsive**: CSS grid with breakpoints for mobile (single column) and desktop (multi-column)
- **Bracket**: SVG-based bracket lines connecting matchup cards, or CSS grid bracket layout
- **Team logos**: `https://neonsportz.com/logos/{logoId}.png` (32x32 or 48x48)
- **Colors**: Conference colors (AFC blue, NFC red), seed-based highlighting
- **Predictions UI**: Toggle buttons on each matchup card, localStorage persistence

---

## Verification Approach

1. **Python script smoke test**: Run `python3 scripts/generate_playoff_dashboard.py` and verify `docs/data/playoff_dashboard.json` is valid JSON with expected structure
2. **Manual browser test**: Open `docs/playoff_dashboard.html` via `python3 -m http.server 8000`, verify all sections render
3. **Playwright E2E test**: Add test in `tests/e2e/` that:
   - Loads the dashboard page
   - Verifies bracket renders with correct number of matchups
   - Verifies team cards display for all 14 playoff teams
   - Verifies prediction click stores in localStorage
   - Verifies head-to-head section shows historical games
4. **Lint**: Verify Python script with existing project conventions (no external deps, standard library only)
