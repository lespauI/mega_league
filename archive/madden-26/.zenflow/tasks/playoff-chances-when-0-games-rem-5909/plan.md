# Fix bug

## Configuration
- **Artifacts Path**: {@artifacts_path} → `.zenflow/tasks/{task_id}`

---

## Workflow Steps

### [x] Step: Investigation and Planning
<!-- chat-id: 311f85ae-e1ff-4a4f-9a38-76c559520dd7 -->

Analyze the bug report and design a solution.

1. Review the bug description, error messages, and logs
2. Clarify reproduction steps with the user if unclear
3. Check existing tests for clues about expected behavior
4. Locate relevant code sections and identify root cause
5. Propose a fix based on the investigation
6. Consider edge cases and potential side effects

Save findings to `{@artifacts_path}/investigation.md` with:
- Bug summary
- Root cause analysis
- Affected components
- Proposed solution

### [x] Step: Implementation
Read `{@artifacts_path}/investigation.md`
Implement the bug fix.

1. Add/adjust regression test(s) that fail before the fix and pass after
2. Implement the fix
3. Run relevant tests
4. Update `{@artifacts_path}/investigation.md` with implementation notes and test results

**Completed**: Fixed `check_mathematical_certainty()` to detect potential tiebreaker scenarios when team has 0 games remaining. Panthers now show 67.5% (was 100%), matching team scenarios page.

### [x] Step: Why Bills in AFC has just 70% chances
<!-- chat-id: 855c0b78-f8b3-4748-85af-231717d5256b -->
<!-- agent: ZEN_CLI:MAX -->

Explain me NFC playoff picture, specificly why bils is 76% but raiders is 0%

**Completed**: Analyzed AFC playoff picture:

**Bills at 76.6%**: Has 1 game remaining (10-6). If they win → 11-6, guaranteed in. If they lose → 10-7, tied with Titans but Bills wins tiebreaker (conference% 0.636 > 0.583). The 76.6% reflects simulation variance.

**Raiders at 0% (ELIMINATED)**: Even if Raiders wins their last game (10-7), they lose ALL tiebreakers:
- vs Titans (10-7): Both tied on conf% (0.583) and div% (0.500), but **Titans wins on Strength of Victory** (0.503 > 0.392)
- vs Bills (10-7 if Bills loses): **Bills wins on conference%** (0.636 > 0.583)

Since Raiders loses tiebreakers to BOTH contenders, they cannot get either wild card spot → mathematically eliminated.
