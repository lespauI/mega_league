#!/usr/bin/env bash
set -euo pipefail

# Smoke test: generate Draft Class 2026 analytics and verify output.

YEAR=2026
PLAYERS=${PLAYERS:-MEGA_players.csv}
TEAMS=${TEAMS:-MEGA_teams.csv}
OUT=${OUT:-docs/draft_class_${YEAR}.html}

echo "[smoke] Generating Draft Class ${YEAR} analytics (Elites, XF/SS/Star/Normal)..." >&2
python3 scripts/generate_draft_class_analytics.py \
  --year "${YEAR}" \
  --players "${PLAYERS}" \
  --teams "${TEAMS}" \
  --out "${OUT}"

echo "[smoke] Generated: ${OUT}" >&2
echo "[smoke] Expect sections: KPIs (XF, SS, Star, Normal) + Elites share; Elites Spotlight (XF/SS only); Teams/Positions with dev columns; Dual Rounds (XF/SS/Star vs Elites-only)." >&2

echo "[smoke] Verifying Elites spotlight, dev tiers (XF/SS/Star/Normal), KPIs and rounds tables..." >&2
python3 scripts/verify_draft_class_analytics.py "${YEAR}" \
  --players "${PLAYERS}" \
  --teams "${TEAMS}" \
  --html "${OUT}"

echo "[smoke] OK — verification passed. HTML at ${OUT}" >&2
