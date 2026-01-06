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
<!-- chat-id: e5d2ccaa-7d34-4456-9be3-15c8eac98ec8 -->

**Complexity**: Medium

Created comprehensive technical specification in `spec.md` documenting:
- Current multi-factor formula (win%, power_rank, past_sos, quality_of_wins)
- New ELO-based approach using tournament simulation
- Implementation details and formula design
- Files to modify and verification approach

---

### [x] Step: Add ELO Data Loading
<!-- chat-id: 68c06515-30b3-4978-98b2-a4cbade4f833 -->

Add function to load ELO ratings from `mega_elo.csv` in `playoff_race_table.py`.
- Reuse pattern from `calc_playoff_probabilities.py`
- Return dictionary mapping team names to ELO ratings
- Handle missing teams with default ELO of 1200

**Verification**: Print loaded ELO data to verify correct parsing

---

### [x] Step: Implement ELO-Based Super Bowl Probability Function
<!-- chat-id: 239f8767-92ea-4f66-9833-f76b1efe5c89 -->

Create new `calculate_superbowl_prob_elo()` function to replace existing logic.
- Calculate ELO win probability using standard formula: 1 / (1 + 10^((opp_elo - team_elo) / 400))
- Determine playoff field average ELO for conference
- Apply home field advantage as ELO boost
- Simulate tournament (3-4 games based on seeding)
- Apply playoff probability multiplier
- Cap at 45% (SB_PROB_MAX)

**Verification**: Test with known ELO values (e.g., 1300 vs 1200 should give ~64% win prob) ✓

---

### [x] Step: Update Table Generation to Use ELO

Modify table generation flow in `create_html_table()` function.
- Load ELO data in `read_standings()`
- Pass ELO data through to table generation
- Build list of playoff contenders' ELOs for each conference
- Call new ELO-based function instead of old one
- Ensure all parameters are passed correctly

**Verification**: Script runs without errors ✓

---

### [x] Step: Update Tooltip Descriptions

Rewrite `get_superbowl_tooltip()` function to reflect ELO-based methodology.
- Remove references to win%, past_sos, quality_of_wins weights
- Add ELO rating display
- Explain ELO-based tournament simulation
- Show relative strength vs playoff field
- Keep playoff%, division%, bye% references

**Verification**: Tooltip HTML renders correctly in browser ✓

---

### [x] Step: Manual Testing and Verification
<!-- chat-id: d7dd1428-289c-4aea-a8b7-b7fdcf428602 -->

Generate playoff race table and verify results.
- Run `python scripts/playoff_race_table.py` ✓
- Open `docs/playoff_race_table.html` ✓
- Verify high ELO teams (Broncos 1310, Giants 1269) have highest SB probabilities ✓
- Verify teams with similar records but different ELO are properly differentiated ✓
- Check all tooltips display correctly and make sense ✓
- Validate formula: compare a few manual calculations with output ✓

**Verification**: All checks pass, results are logical and ELO-driven ✓

**Results Summary:**
- **Broncos** (11-2, ELO 1310): 20.2% SB probability - Highest in league
- **Giants** (11-1-1, ELO 1269): 17.0% SB probability - Second highest
- **Browns** (11-3, ELO 1247): 5.3% SB probability - Lower despite similar record to Broncos
- **Patriots** (9-4, ELO 1255): 3.3% SB probability
- **Bills** (9-5, ELO 1205): 2.6% SB probability - Lower than Patriots due to lower ELO
- Tooltips display ELO ratings and explain tournament simulation correctly
- Formula verified: 1 / (1 + 10^((opp_elo - team_elo) / 400)) produces expected results

---

### [x] Step: Create Implementation Report
<!-- chat-id: f151e398-7026-4a54-ba18-a51632f4c19d -->

Document the implementation in `{@artifacts_path}/report.md`:
- What was implemented
- How the solution was tested
- Any challenges encountered
- Example results showing ELO-based differentiation

**Completed**: Created comprehensive implementation report documenting the ELO-based Super Bowl probability calculation, including results, testing methodology, and technical details.

---

### [x] Step: Enhanced with Monte Carlo Simulation
<!-- chat-id: enhanced-monte-carlo -->

**Issue**: Initial ELO-based formula produced too low probabilities (top teams <20% SB chance) because:
- Used average opponent ELO (didn't account for seeding)
- Tournament probability multiplication was too pessimistic
- 75% win probability cap was too restrictive
- Didn't reflect actual bracket structure

**Solution**: Implemented Monte Carlo simulation (1000 iterations) that:
- Simulates actual playoff bracket structure
- Higher seeds face weaker opponents in early rounds
- Each matchup uses ELO-based win probability
- Home field advantage applied as ELO boost (75 for bye seeds, 40 for division leaders)
- Tracks Super Bowl wins across simulations

**Results** (Monte Carlo vs Original):
- **Broncos** (ELO 1310, top seed): **~26%** (was 18.5%)
- **Giants** (ELO 1269, top seed): **~26%** (was 15.8%)
- **Patriots** (ELO 1255, not top seed): **~5.7%** (was 2.8%)

**Benefits**:
- More realistic probabilities for elite teams
- Better differentiation based on ELO and seeding
- Accounts for tournament structure naturally
- Consistent with playoff probability methodology

**Verification**: ✓ Script runs successfully, probabilities are realistic and ELO-driven
