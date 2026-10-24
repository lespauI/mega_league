# Link Table Implementation Report

## Summary
Added cross-linking functionality between the playoff race table and team scenarios pages.

## Changes Made

### 1. playoff_race_table.html
- **Styling**: Added cursor pointer and hover effects to team names
  - Team names now change color and underline on hover
  - Clear visual indication that teams are clickable
  
- **JavaScript**: Added click handlers to team cells
  - Clicking a team redirects to `team_scenarios.html?team=TeamName`
  - Team name is URL-encoded for safe transmission

### 2. team_scenarios.html
- **UI**: Added "Back to Playoff Race" button
  - Located at the top of the header section
  - Styled to match the page design
  - Links back to `playoff_race_table.html`
  
- **JavaScript**: Added URL parameter handling
  - Reads the `team` parameter from the URL on page load
  - Auto-selects the specified team in the dropdown
  - Triggers the team data display automatically

## User Flow
1. User views playoff race table
2. User clicks on any team name
3. Redirected to team scenarios page with that team pre-selected
4. User can click "Back to Playoff Race" to return to the main table
