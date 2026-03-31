# Technical Specification: Mega Playoff Season 3 Dashboard

## Difficulty: Hard

Interactive playoff bracket dashboard with Madden-style dark-blue aesthetic. Bracket is the main view; clicking any matchup opens a rich detail modal with team stats comparison, best players, head-to-head history, and prediction voting. No probability calculations — bracket is already determined.

---

## Technical Context

- **Language**: HTML/CSS/JavaScript (vanilla, no build step — matches existing codebase)
- **Data format**: CSV files at project root (`MEGA_*.csv`) + pre-computed JSON/CSV under `docs/data/`
- **Hosting**: Static site via `python3 -m http.server` or GitHub Pages
- **Dependencies**: None required beyond vanilla JS. No D3 needed — bracket is CSS grid.
- **Team logos**: Neon Sports CDN — `https://neonsportz.com/logos/{logoId}.png`
- **Testing**: Playwright E2E tests (`package.json` already configured)

---

## Data Sources

### CSV Files (root)
| File | Key columns | Purpose |
|------|------------|---------|
| `MEGA_teams.csv` | displayName, abbrName, conferenceName, divName, totalWins, totalLosses, seed, playoffStatus, logoId, seasonIndex, ovrRating, offPassYds, offRushYds, defPassYds, defRushYds, ptsFor, ptsAgainst | Team standings, seeding, stats |
| `MEGA_games.csv` | homeTeam, awayTeam, homeScore, awayScore, seasonIndex, stageIndex, weekIndex, status | Game results; stageIndex=0 → playoff, stageIndex=1 → regular season |
| `MEGA_passing.csv` | player__fullName, team__abbrName, team__logoId, passTotalYds, passTotalTDs, passTotalInts, passerAvgRating | Passing stats per player |
| `MEGA_rushing.csv` | player__fullName, team__abbrName, rushTotalYds, rushTotalTDs, rushAvgYdsPerAtt | Rushing stats |
| `MEGA_receiving.csv` | player__fullName, team__abbrName, recTotalYds, recTotalTDs, recTotalCatches | Receiving stats |
| `MEGA_defense.csv` | player__fullName, team__abbrName, defTotalSacks, defTotalInts, defTotalTackles | Defensive stats |
| `MEGA_players.csv` | fullName, team, position, playerBestOvr, devTrait | Player OVR ratings |
| `mega_elo.csv` | Team, Coach, Week 14+ (ELO rating) | Team ELO ratings |

### Season 3 Playoff State (seasonIndex=2)
- **14 playoff teams** (7 AFC, 7 NFC), seeds 1-7 per conference
- **1-seeds get first-round bye**: Bengals (AFC), Seahawks (NFC)
- **Standard NFL bracket**: 6 Wild Card games → 4 Divisional → 2 Conference Championship → Super Bowl
- **playoffStatus**: 4=bye seed, 3=division winner, 2=wild card
- **16 total playoff games** in `MEGA_games.csv` stageIndex=0 (includes non-bracket matchups from Madden scheduling — we'll map the actual bracket from seeds)

### AFC Bracket (from seeding)
| Wild Card | Matchup |
|-----------|---------|
| 2 vs 7 | Raiders vs Titans |
| 3 vs 6 | Colts vs Ravens |
| 4 vs 5 | Patriots vs Broncos |
| BYE | Bengals (1-seed) |

### NFC Bracket (from seeding)
| Wild Card | Matchup |
|-----------|---------|
| 2 vs 7 | Commanders vs Cowboys |
| 3 vs 6 | Saints vs Panthers |
| 4 vs 5 | Lions vs Rams |
| BYE | Seahawks (1-seed) |

---

## Architecture: Bracket-First Design

### Main View: Full-Screen Bracket
The page is dominated by the bracket visualization — Madden NFL Playoffs style:

```
        AFC                                           NFC
   WILD CARD  DIVISIONAL  CONF CHAMP  SUPER BOWL  CONF CHAMP  DIVISIONAL  WILD CARD
   
   2 Raiders ─┐
              ├── Winner ─┐
   7 Titans  ─┘           │
                          ├── AFC Champ ─┐
   3 Colts   ─┐           │              │
              ├── Winner ─┘              │
   6 Ravens  ─┘                          │
                                         ├── SUPER BOWL
   1 Bengals ──── BYE ── Winner ─┐       │
                                 │       │
   4 Patriots ─┐                 │       │
               ├── Winner ──────┘       │
   5 Broncos  ─┘                         │
                                         │
   (NFC mirror on right side)           ─┘
```

### Click-to-Open Matchup Modal
Clicking any matchup card in the bracket opens a full detail modal containing:

1. **Team Stats Comparison** — side-by-side bars: W-L, OVR, ELO, Pts For/Against, Off Pass/Rush Yds, Def Pass/Rush Yds
2. **Best Players** — top QB, RB, WR, DEF for each team with name, key stat, OVR
3. **Head-to-Head History** — all past games between these two teams across all 3 seasons with scores
4. **Prediction Vote** — click a team logo to predict the winner, stored in localStorage

### Visual Design
- **Dark blue background** with football field grass texture at bottom (like Madden screenshot)
- **Team logo cards** in bracket slots with seed number badges
- **Connector lines** between rounds (CSS borders or SVG)
- **"NFL PLAYOFFS 2027"** title header
- **"1ST ROUND BYE"** badge for 1-seeds with AFC/NFC conference logos
- **Gold/yellow accents** for completed games with scores
- **Responsive**: scales down for tablet/mobile (stacked conferences)

---

## Source Code Changes

### New Files
| File | Description |
|------|-------------|
| `docs/playoff_dashboard.html` | Main playoff bracket dashboard (single self-contained HTML) |
| `scripts/generate_playoff_dashboard.py` | Python script to pre-compute `docs/data/playoff_dashboard.json` |

### Modified Files
| File | Change |
|------|--------|
| `index.html` | Add link to playoff dashboard in Reports section |
| `docs/README.md` | Add entry for playoff_dashboard.html |

### Generated Data
| File | Content |
|------|---------|
| `docs/data/playoff_dashboard.json` | Bracket structure, team data, top players, head-to-head history |

---

## Data Model: playoff_dashboard.json

```json
{
  "generated_at": "...",
  "season_index": 2,
  "teams": {
    "Bengals": {
      "abbr": "CIN",
      "displayName": "Bengals",
      "logoId": 1,
      "conference": "AFC",
      "division": "AFC North",
      "seed": 1,
      "wins": 14,
      "losses": 3,
      "playoffStatus": 4,
      "ovrRating": 92,
      "elo": 1270.0,
      "ptsFor": 29,
      "ptsAgainst": 16,
      "offPassYds": 4200,
      "offRushYds": 1298,
      "offTotalYds": 5498,
      "defPassYds": 2821,
      "defRushYds": 1358,
      "defTotalYds": 4179,
      "topPlayers": {
        "QB": { "name": "Joe Burrow", "yards": 3500, "tds": 30, "ints": 8, "rating": 105.2, "ovr": 95 },
        "RB": { "name": "...", "yards": 800, "tds": 6, "ovr": 85 },
        "WR": { "name": "Ja'Marr Chase", "yards": 1200, "tds": 10, "catches": 80, "ovr": 99 },
        "DEF": { "name": "...", "sacks": 8.0, "ints": 3, "tackles": 50, "ovr": 90 }
      }
    }
  },
  "bracket": {
    "AFC": {
      "wildcard": [
        {
          "matchupId": "afc_wc_1",
          "homeSeed": 2, "home": "Raiders",
          "awaySeed": 7, "away": "Titans",
          "homeScore": null, "awayScore": null,
          "status": "scheduled", "winner": null
        },
        { "matchupId": "afc_wc_2", "homeSeed": 3, "home": "Colts", "awaySeed": 6, "away": "Ravens", ... },
        { "matchupId": "afc_wc_3", "homeSeed": 4, "home": "Patriots", "awaySeed": 5, "away": "Broncos", ... }
      ],
      "divisional": [
        { "matchupId": "afc_div_1", "home": null, "away": null, "feedsFrom": ["afc_wc_1"], "byeTeam": "Bengals", ... },
        { "matchupId": "afc_div_2", "home": null, "away": null, "feedsFrom": ["afc_wc_2", "afc_wc_3"], ... }
      ],
      "championship": { "matchupId": "afc_champ", ... },
      "byeTeam": "Bengals"
    },
    "NFC": { ... }
  },
  "super_bowl": { "matchupId": "super_bowl", ... },
  "head_to_head": {
    "Raiders_vs_Titans": [
      { "season": 0, "week": 5, "home": "Raiders", "away": "Titans", "homeScore": 28, "awayScore": 17 },
      ...
    ]
  }
}
```

---

## Verification

1. **Python script**: Run `python3 scripts/generate_playoff_dashboard.py`, verify valid JSON with 14 teams, correct bracket matchups
2. **Browser**: Open `docs/playoff_dashboard.html` via local server, verify bracket renders, click matchup opens modal
3. **Playwright E2E**: Page loads, bracket has 6 WC + 2 BYE slots visible, clicking matchup opens modal with stats/H2H/predictions, prediction persists in localStorage
