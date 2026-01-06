# Technical Specification: ELO-Based Super Bowl Probability

## Task Complexity: Medium

## Overview
Update the Super Bowl probability calculation to be based purely on ELO ratings rather than the current multi-factor formula. This change will ensure that teams with higher ELO ratings have proportionally higher Super Bowl chances, regardless of their record.

## Current Implementation

**File**: `scripts/playoff_race_table.py`

**Current Formula** (lines 158-224):
```python
def calculate_superbowl_prob(playoff_prob, div_prob, bye_prob, quality_of_wins, is_top_seed, 
                             win_pct=0.5, past_sos=0.5, win_streak=0, power_rank=16):
    # Uses weighted factors:
    # - 50% win_pct
    # - 25% power_rank  
    # - 15% past_sos
    # - 10% quality_of_wins
    
    # Calculates team_rating from these factors
    # Applies streak bonuses/penalties
    # Simulates winning 3-4 playoff games
    # Multiplies by playoff_prob to get final SB probability
```

**Issues with Current Approach**:
1. Win percentage dominates (50%), making teams with same record have similar SB chances
2. Doesn't properly differentiate teams by strength when records are equal
3. ELO data exists (`mega_elo.csv`) but is not used for SB probability

## Desired Implementation

### New Approach
Super Bowl probability should be calculated using:
1. **Team's ELO rating** from `mega_elo.csv`
2. **Relative ELO strength** compared to other playoff contenders
3. **Tournament simulation** based on ELO matchups

### Formula Design

**Step 1**: Load ELO data
- Read from `mega_elo.csv` (already exists in codebase)
- Extract "Week 14+" column for latest ELO ratings
- Default to 1200 if team not found

**Step 2**: Calculate expected win probability in head-to-head ELO matchup
```
ELO Win Probability = 1 / (1 + 10^((opponent_elo - team_elo) / 400))
```

**Step 3**: Calculate conference championship probability
- Identify all playoff contenders in same conference (teams with playoff_prob > 0)
- Calculate average ELO of conference playoff field
- Use ELO formula to get probability of beating average playoff team
- Raise to power based on seeding:
  - Top seed (bye): 3 games needed → prob^3
  - Bye contender: 3 games needed → prob^3  
  - Division leader: 4 games needed → prob^4
  - Wild card: 4 games needed → prob^4

**Step 4**: Calculate Super Bowl win probability
- Calculate average ELO of both conferences' playoff fields
- Get probability of beating other conference champion
- Multiply conference championship probability by this

**Step 5**: Apply playoff probability multiplier
- Multiply by (playoff_prob / 100) to account for making playoffs

### Home Field Advantage
Retain existing home field bonuses:
- Top seed: +6% (3 home games)
- Division leader: +3% (1-2 home games)

These should be applied as ELO adjustments (~25 ELO points = 3.5% win probability increase)

### Seeding Benefits
Teams should benefit from better seeding through:
1. Fewer games needed (bye week → 3 games instead of 4)
2. Home field advantage throughout playoffs
3. (Implicitly) facing weaker opponents in early rounds

## Implementation Changes

### Files to Modify

**1. `scripts/playoff_race_table.py`**

Changes needed:
- Add ELO loading function (can reuse pattern from `calc_playoff_probabilities.py:23-36`)
- Completely rewrite `calculate_superbowl_prob()` function (lines 158-224)
- Update `get_superbowl_tooltip()` function (lines 298-342) to reflect new ELO-based calculation
- Pass ELO data to table generation function

### Function Signature
```python
def calculate_superbowl_prob_elo(
    playoff_prob,      # Probability of making playoffs (0-100)
    team_elo,          # Team's ELO rating
    conf_playoff_elos, # List of ELO ratings for all playoff contenders in conference
    is_top_seed,       # Boolean: is team the #1 seed
    bye_prob,          # Probability of getting bye (0-100)
    div_prob           # Probability of winning division (0-100)
):
    """
    Calculate Super Bowl probability using pure ELO-based approach.
    
    Returns probability of winning Super Bowl (0-45%).
    """
```

### Data Flow
1. Load ELO data in `read_standings()` function
2. Pass ELO data through to table generation
3. For each conference, build list of playoff contenders' ELOs
4. Call new SB probability function with team ELO and conference playoff field ELOs
5. Update tooltip to show ELO-based factors

## Verification Approach

### Manual Verification
1. Run `python scripts/playoff_race_table.py`
2. Open generated `docs/playoff_race_table.html`
3. Verify that:
   - Teams with higher ELO have higher SB probabilities (among teams with similar playoff chances)
   - Top ELO teams with 100% playoff odds have highest SB probabilities
   - Lower ELO teams with same records have appropriately lower SB probabilities
   - Tooltips describe ELO-based calculation accurately

### Test Cases to Check
- **Broncos** (ELO 1310): Should have highest SB probability
- **Giants** (ELO 1269): Should have 2nd/3rd highest SB probability
- Compare teams with similar records but different ELOs

### Formula Validation
Test the ELO win probability formula:
- Team with ELO 1300 vs Team with ELO 1200: ~64% win probability
- Team with ELO 1300 vs Team with ELO 1300: 50% win probability
- Team with ELO 1200 vs Team with ELO 1300: ~36% win probability

## Technical Context

**Language**: Python 3
**Dependencies**: 
- Standard library: `csv`, `collections`, `datetime`
- Data files: `mega_elo.csv`, `MEGA_teams.csv`, `MEGA_rankings.csv`, `output/ranked_sos_by_conference.csv`

**Existing Patterns**:
- ELO loading already implemented in `calc_playoff_probabilities.py:23-36`
- CSV reading patterns consistent throughout codebase
- Probability capping at 45% for SB (constant `SB_PROB_MAX`)

## Expected Outcome

After implementation:
1. Super Bowl probabilities driven purely by ELO strength
2. Teams with high ELO ratings properly recognized as stronger contenders
3. Clear differentiation between teams with same records but different ELO
4. Tooltip explanations updated to reflect ELO-based methodology
5. More accurate representation of championship chances based on team strength
