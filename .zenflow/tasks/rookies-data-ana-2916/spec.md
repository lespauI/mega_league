# Technical Specification: Unhide Dev Traits in Draft Class Analytics

## Technical Context
- Language: Python 3.9+ (standard library only; no external deps)
- Primary scripts: `scripts/generate_draft_class_analytics.py`, `scripts/verify_draft_class_analytics.py`
- Inputs: `MEGA_players.csv` (required), `MEGA_teams.csv` (optional, for logos)
- Outputs: Single static HTML page (no build system)
- Existing behavior masks dev traits (3/2/1 => "Hidden"). This refactor removes masking and surfaces true tiers: X‑Factor, Superstar, Star, Normal.

## Technical Implementation Brief
- Remove UI masking for dev traits and render explicit badges for each tier: XF, SS, Star, Normal.
- Replace KPI block to report counts and percentages for XF, SS, Star, Normal and add an “Elites share” bar ((XF+SS)/Total). Add grading badges vs targets: XF ≥ 10%, SS ≥ 15% with labels On‑target / Near‑target (≥ 75% of target) / Below‑target.
- Rename “Hidden Spotlight” to “Elites Spotlight” and show X‑Factor + Superstar only (Stars excluded). Keep card UI; add explicit dev badges per player.
- Update team and position tables to include four dev columns (XF, SS, Star, Normal) and keep sortable behavior.
- Round analytics: keep the existing per‑team per‑round table logic for hits = non‑Normal (3/2/1). Add a second, parallel table for hits = Elites (3/2). Clearly label both.
- Adjust CSS to introduce dedicated classes for dev badges (`dev-xf`, `dev-ss`, `dev-star`, `dev-norm`) and for grading badges (`grade-on`, `grade-near`, `grade-below`) with accessible contrast.
- Update verification script to check the new KPIs, spotlight title, table headers, and presence of two rounds tables. Update smoke script accordingly.
- Backward compatibility: keep CLI flags and defaults; no masking mode retained. Remove “Hidden” terminology in UI and docs.

## Source Code Structure
- `scripts/generate_draft_class_analytics.py`
  - Constants
    - `DEV_LABELS`: keep mapping `{"3": "X-Factor", "2": "Superstar", "1": "Star", "0": "Normal"}`.
  - Data processing
    - `gather_rookies(...)`: unchanged contract; normalizes rookies and dev string in {"3","2","1","0"}.
    - `compute_analytics(rows) -> dict`:
      - Existing: returns `dev_counts`, `elite_count`, `elite_share_pct`, `teams{dev}`, `positions{dev}`, `team_rounds` (hits for 3/2/1).
      - Add: `dev_counts_norm` (already present), `xf_pct`, `ss_pct`, `star_pct`, `norm_pct` (floats with 1 decimal), `xf_grade`, `ss_grade` (enum `on|near|below`), `xf_grade_label`, `ss_grade_label` (strings), and `team_rounds_elites` (hits for 3/2 only). Retain `rounds_sorted`.
  - Rendering
    - `badge_for_dev(dev: str) -> str`: change to return explicit labels and classes:
      - 3 => label `X‑Factor`, class `dev-xf`; 2 => `Superstar`, `dev-ss`; 1 => `Star`, `dev-star`; 0 => `Normal`, `dev-norm`.
    - `generate_html(...) -> str`:
      - KPI block: replace Hidden/Normal KPIs with four KPIs (XF, SS, Star, Normal) and an “Elites share” progress bar. Display grading badges next to XF% and SS%.
      - Spotlight: change section title to “Elites Spotlight”; cards include explicit dev badge via `badge_for_dev`.
      - Team table: header `Team | # | Avg OVR | Best OVR | XF | SS | Star | Normal` and corresponding row counts from `teams[team]['dev']`.
      - “Most elites” table: rename and compute as `elites = XF+SS` per team; header `Team | Elites (XF+SS) | # | Avg OVR`.
      - Position table: header `Position | # | Avg OVR | XF | SS | Star | Normal`.
      - Rounds: keep existing non‑Normal hit table and add a second table for elites‑only with matching bar visualization and explicit notes.
      - Keep JS sorter and placeholders injection style; add new placeholders as needed.
    - CSS: add classes `.dev-xf`, `.dev-ss`, `.dev-star`, `.dev-norm`; add grading badge styles `.grade`, `.grade-on`, `.grade-near`, `.grade-below`.
- `scripts/verify_draft_class_analytics.py`
  - Replace Hidden KPIs parsing with four dev KPIs, elites share %, and presence of grading badges for XF and SS.
  - Verify spotlight section title equals “Elites Spotlight”.
  - Verify team and position table headers include the new dev columns.
  - Verify two rounds tables exist with correct subtitles/footnotes.
- `scripts/smoke_generate_draft_2026.sh`
  - No CLI change; update messaging.
  - Call the updated verify script.
- `README.md`
  - Update the Draft Class Analytics section to reflect unmasked dev tiers and new KPIs/tables.

## Contracts
- Data model (rows from `gather_rookies`):
  - Keys: `id|name|team|position|ovr:int|dev:str|draft_round:int|draft_pick:int|college:str` (unchanged).
- Analytics dict (output of `compute_analytics`):
  - Existing keys preserved: `total:int`, `avg_ovr:float`, `dev_counts:Counter`, `dev_counts_norm:dict[str,int]`, `elite_count:int`, `elite_share_pct:float`, `elites:list[dict]`, `teams:dict[str,dict]`, `positions:dict[str,dict]`, `rounds_sorted:list[int]`.
  - Team aggregate: `teams[team] = {count:int, avg_ovr:float, best_ovr:int, dev:{'3','2','1','0' -> int}}`.
  - Position aggregate: `positions[pos] = {count:int, avg_ovr:float, dev:{'3','2','1','0' -> int}}`.
  - New keys:
    - Percentages (1 decimal strings in render): `xf_pct`, `ss_pct`, `star_pct`, `norm_pct`.
    - Grading: `xf_grade`|`ss_grade` in {`on`,`near`,`below`}; labels: `xf_grade_label`|`ss_grade_label` in {`On‑target`,`Near‑target`,`Below‑target`}.
    - Rounds (elites): `team_rounds_elites: dict[team, dict[int, {'hit':int, 'total':int}]]`.
- Rendering helpers:
  - `badge_for_dev(dev) -> str` returns `<span class="dev-badge dev-<tier>">Label</span>`.
  - New helper `grade_badge(tier: str, pct: float, target: float) -> tuple[str,str]` returning `(label, css_class)` where css_class in `grade-on|grade-near|grade-below`.

## Delivery Phases
1) Unmask and Spotlight
   - Implement `badge_for_dev` changes and update spotlight title and card dev badges.
   - Add dev badge CSS classes.
   - End-to-end: HTML shows real dev labels; spotlight excludes Stars.

2) KPI Overhaul
   - Replace Hidden/Normal KPIs with XF/SS/Star/Normal and “Elites share” bar; implement grading badges.
   - Update HTML placeholders and injection code accordingly.

3) Tables Update
   - Update team and positions tables to include four dev columns; rename “Most hiddens” to “Most elites (XF+SS) — by team”.

4) Rounds Dual Tables
   - Keep existing non‑Normal hits table; add elites‑only hits table and notes. Limit to first 10 rounds.

5) Verification & Docs
   - Update `scripts/verify_draft_class_analytics.py` to new KPIs, spotlight title, table headers, and two rounds tables; adjust smoke script messaging.
   - Update README Draft Class Analytics section.

## Verification Strategy
- Built-in commands
  - Generate for a known year: `python3 scripts/generate_draft_class_analytics.py --year 2026 --out docs/draft_class_2026_test.html`
  - Run verifier: `python3 scripts/verify_draft_class_analytics.py 2026 --html docs/draft_class_2026_test.html`
  - Smoke: `bash scripts/smoke_generate_draft_2026.sh`

- Verifier updates (to implement)
  - Compute XF/SS/Star/Normal counts from CSV.
  - Parse HTML to extract:
    - Four KPIs (counts) and their percentages where applicable.
    - Elites share bar percentage.
    - Presence and label of grading badges for XF and SS (regex on `class="grade-(on|near|below)"`).
    - Section title equals “Elites Spotlight”.
    - Team table headers include XF/SS/Star/Normal; same for positions table.
    - Two rounds tables present: titles include “Hit = XF/SS/Star” and “Hit = Elites (XF/SS)”.
    - No unresolved placeholders (`__[A-Z_]+__`).

- Helper scripts to add in Phase 1
  - `scripts/fixtures/generate_tiny_draft.py`: generate a tiny synthetic `players.csv` with a handful of rookies spanning all dev tiers and known rounds/picks, to make verifier deterministic. The agent can invoke it to produce `output/tiny_players.csv` for local verification and speed.
    - Inputs: none. Outputs: CSV with columns used by the generator (`rookieYear, fullName, team, position, playerBestOvr, devTrait, draftRound, draftPick, college`).
    - This artifact can be generated by the agent (no user input).

- MCP servers to recommend for agent verification
  - `filesystem` (read/write files reliably during verification)
  - `shell` (invoke Python and bash scripts)
  - `git` (optional, diff and blame while adjusting code)
  - `fetch/http` (optional; not required for core verification, useful to sanity-check remote logo URLs)

- Sample inputs
  - a) Provided in repo: `MEGA_players.csv`, `MEGA_teams.csv` (sufficient for realistic verification)
  - b) Generated by agent: `output/tiny_players.csv` via the helper script for fast checks
  - c) None required from the user

Notes
- Keep injection approach (template placeholders + `.replace`) to minimize refactor scope.
- Ensure numbers are formatted consistently: counts as ints; percentages as one decimal; averages with two decimals as today.
- Maintain performance; operations are O(n) over rookies.

