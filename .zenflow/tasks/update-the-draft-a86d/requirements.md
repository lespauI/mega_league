# Feature Specification: Draft Analysis Enhancements — First-Round Recap and Section Intro Text Blocks

## User Stories*

### User Story 1 - First-Round Recap With Grades and Photos
**As** a draft analysis consumer
**I want** a complete first-round recap appended to the generated analysis, showing each pick with NFL draft recap style, including team, player, position, grade, key attributes, trait highlights, and player photo
**So that** I can quickly understand the quality and context of Round 1 selections.

**Acceptance Scenarios**:
1. **Given** a generated draft analysis and a draft class with at least 32 first-round picks, **When** the analysis is generated, **Then** a “Round 1 Recap” section appears at the end listing picks 1–32 in order with team, player, position, grade, key attributes, trait highlights, and player photo (if available).
2. **Given** a pick with a valid `portraitId`, **When** the recap renders, **Then** the player photo loads from `https://ratings-images-prod.pulse.ea.com/madden-nfl-26/portraits/{portraitId}.png`.
3. **Given** missing `portraitId` or unreachable image, **When** the recap renders, **Then** the photo is omitted (or a neutral placeholder is shown) without breaking layout.

### User Story 2 - Attribute and Trait Highlights by Position
**As** a draft analysis consumer
**I want** the recap to surface key attributes and notable traits per position
**So that** I can evaluate fit and upside quickly without scanning all ratings.

**Acceptance Scenarios**:
1. **Given** a player and their position, **When** the recap renders, **Then** the displayed attributes match the “Key Attributes” list for that position (see Requirements) and show available numeric values.
2. **Given** a player with notable traits (e.g., clutchTrait, bigHitTrait), **When** the recap renders, **Then** the recap highlights those traits as badges or labeled markers.

### User Story 3 - Section Intro Text Blocks (Wrappable)
**As** an analyst authoring the report
**I want** a configurable text block at the top of each section (e.g., KPIs, Elites Spotlight, Team Draft Quality — by Avg OVR)
**So that** I can add narrative analysis with proper line wrapping.

**Acceptance Scenarios**:
1. **Given** a section that supports intro text, **When** the analysis is generated, **Then** a multi-line text block appears at the top of that section using a default placeholder when no custom text is provided.
2. **Given** long intro text, **When** the analysis is rendered, **Then** the text wraps across lines without clipping or layout overflow.

---

## Requirements*

Functional
- Round 1 Recap section
  - Append a new section titled “Round 1 Recap” after existing analysis output.
  - Include exactly one entry per pick (1–32) in order: Pick #, Team, Player, Position, optional School, optional Age, optional OVR.
  - Include NFL draft recap style elements per entry:
    - Grade on an A–F scale (A+, A, A-, …, F) with a one-sentence rationale.
    - Key attributes for the player’s position (see mapping below) with numeric values if available.
    - Trait highlights rendered as badges/labels.
    - Player photo loaded from `https://ratings-images-prod.pulse.ea.com/madden-nfl-26/portraits/{portraitId}.png` when `portraitId` is present.
  - Missing data handling: If a field (e.g., `portraitId`, an attribute, a trait) is missing, omit that element or render as `N/A` without failing the entry.

- Grades
  - Default scale: A+, A, A-, B+, B, B-, C+, C, C-, D+, D, D-, F.
  - [NEEDS CLARIFICATION: Should grades be author-provided, algorithmically derived, or a blend?]
  - If algorithmic: Use a rules-based heuristic combining player OVR/positional percentile, pick value (draft slot), and team roster needs at that position if available. If team needs are unavailable, fall back to OVR vs positional percentile and expected value per slot.
  - If insufficient inputs exist to compute, default to neutral `B` and include rationale “Insufficient inputs to compute grade; default applied.”

- Key Attributes by Position (displayed values where available)
  - QB: throwAccShort, throwAccMid, throwAccDeep, throwPower, throwUnderPressure, throwOnRun, playAction, awareRating, speedRating, breakSackRating
  - HB/RB: speedRating, accelRating, agilityRating, breakTackleRating, truckRating, jukeMoveRating, spinMoveRating, stiffArmRating, carryRating, catchRating, bCVRating
  - FB: runBlockRating, leadBlockRating, impactBlockRating, strengthRating, truckRating, catchRating
  - WR: catchRating, specCatchRating, cITRating, speedRating, routeRunShort, routeRunMed, routeRunDeep, releaseRating, agilityRating, changeOfDirectionRating
  - TE: catchRating, cITRating, runBlockRating, passBlockRating, speedRating, routeRunShort, routeRunMed, strengthRating, specCatchRating
  - OL (T/G/C): passBlockRating, passBlockPower, passBlockFinesse, runBlockRating, runBlockPower, runBlockFinesse, strengthRating, awareRating, impactBlockRating
  - DE: powerMovesRating, finesseMovesRating, blockShedRating, pursuitRating, tackleRating, strengthRating, speedRating, hitPowerRating
  - DT: powerMovesRating, blockShedRating, strengthRating, tackleRating, pursuitRating, hitPowerRating
  - LB: tackleRating, pursuitRating, hitPowerRating, blockShedRating, playRecRating, zoneCoverRating, manCoverRating, speedRating, awareRating
  - CB: manCoverRating, zoneCoverRating, speedRating, accelRating, agilityRating, pressRating, playRecRating, catchRating, changeOfDirectionRating
  - S (FS/SS): zoneCoverRating, tackleRating, hitPowerRating, speedRating, playRecRating, pursuitRating, manCoverRating, awareRating, catchRating
  - K: kickPowerRating, kickAccRating
  - P: kickPowerRating, kickAccRating
  - Display limit: Up to 8–10 attributes per player; if more are listed above, prioritize by order listed.

- Key Traits to Highlight (render as badges/labels)
  - QB: clutchTrait, sensePressureTrait, throwAwayTrait, tightSpiralTrait, forcePassTrait
  - Ball Carriers: coverBallTrait, fightForYardsTrait, runStyle
  - Receivers: feetInBoundsTrait, specCatchTrait, posCatchTrait, yACCatchTrait, dropOpenPassTrait
  - Defenders: bigHitTrait, stripBallTrait, playBallTrait
  - DL: dLBullRushTrait, dLSpinTrait, dLSwimTrait
  - If a trait value is boolean, show presence only; if enumerated (e.g., runStyle), show value.

- Player Photos
  - Construct image URL using `portraitId` at: `https://ratings-images-prod.pulse.ea.com/madden-nfl-26/portraits/{portraitId}.png`.
  - [NEEDS CLARIFICATION: Should photos be embedded (HTML/Markdown images) or linked only if output is non-HTML?]
  - Missing/invalid `portraitId`: omit image or use neutral placeholder.

- Section Intro Text Blocks (wrapping)
  - For each supported section (e.g., “KPIs”, “Elites Spotlight”, “Team Draft Quality — by Avg OVR”), render a multi-line text block at the top of the section.
  - Default text (if none provided): `Analysis: Add your insights about this section here.`
  - Text must wrap to available width; no overflow/clipping.
  - Configuration
    - [NEEDS CLARIFICATION: Where should custom intro text be provided—config file, CLI argument, or UI input?]
    - Persistable between runs if provided (e.g., via config file).

- Output Format
  - [NEEDS CLARIFICATION: What is the current output medium—HTML page, Markdown report, PDF, or console?]
  - If HTML: render recap entries as cards with image, attributes, traits, and grade badge.
  - If Markdown: use headings, tables for attributes, and inline image links.
  - If console/terminal: render text-only; omit images; maintain clear labeling.

Non-Functional
- Reliability: Missing attributes/traits/images must not fail generation.
- Performance: Handle a typical draft class (<300 players) and generate in under 2 seconds on a modern laptop (guideline; depends on environment).
- Extensibility: Adding additional sections or changing attribute/trait mappings should be data-driven where possible.
- Accessibility (if HTML): Provide alt text for images (player name and team).

Assumptions
- The draft class generation script already outputs an analysis artifact; this enhancement appends to it without breaking existing sections.
- Player records include `position` with values that map to the lists above and include attributes/traits under the specified keys when available.
- `portraitId` corresponds to Madden NFL 26 portrait assets.

## Success Criteria*

- Round 1 Recap renders 32 entries in order with team, player, position, grade, attributes, and trait highlights; images load for entries with valid `portraitId`.
- For at least three predefined sections (“KPIs”, “Elites Spotlight”, “Team Draft Quality — by Avg OVR”), an intro text block appears at the top with default placeholder text and wraps long content correctly.
- Attributes shown per player match the position mapping and are capped to a readable subset (8–10 items), prioritizing the listed order.
- Trait highlights appear as badges/labels for present traits; non-present traits are not shown.
- When `portraitId` is missing/invalid, the recap still renders without broken layout (image omitted or placeholder used).
- The enhancement does not remove or alter existing analysis sections except to add the intro text block where applicable.

