#!/usr/bin/env bash
set -euo pipefail

# Smoke test: generate Draft Class 2026 analytics and verify output.

YEAR=2026
PLAYERS=${PLAYERS:-MEGA_players.csv}
TEAMS=${TEAMS:-MEGA_teams.csv}
OUT=${OUT:-docs/draft_class_${YEAR}.html}

echo "[smoke] Generating analytics HTML for year ${YEAR}..." >&2
python3 scripts/generate_draft_class_analytics.py \
  --year "${YEAR}" \
  --players "${PLAYERS}" \
  --teams "${TEAMS}" \
  --out "${OUT}"

echo "[smoke] Generated: ${OUT}" >&2

echo "[smoke] Verifying generated HTML against CSV KPIs..." >&2
python3 scripts/verify_draft_class_analytics.py "${YEAR}" \
  --players "${PLAYERS}" \
  --teams "${TEAMS}" \
  --html "${OUT}"

echo "[smoke] OK — HTML at ${OUT}" >&2

