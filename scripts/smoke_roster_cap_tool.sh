#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR=$(cd "$(dirname "$0")/.." && pwd)
DOCS_DIR="$ROOT_DIR/docs/roster_cap_tool"

echo "[smoke] Checking required assets..."
need_files=(
  "$DOCS_DIR/index.html"
  "$DOCS_DIR/js/capMath.js"
  "$DOCS_DIR/js/state.js"
  "$DOCS_DIR/js/ui/playerTable.js"
  "$DOCS_DIR/js/ui/modals/releaseModal.js"
  "$DOCS_DIR/js/ui/modals/offerModal.js"
  "$DOCS_DIR/js/ui/modals/extensionModal.js"
  "$DOCS_DIR/js/ui/modals/conversionModal.js"
  "$DOCS_DIR/data/MEGA_teams.csv"
  "$DOCS_DIR/data/MEGA_players.csv"
)
for f in "${need_files[@]}"; do
  if [[ ! -f "$f" ]]; then
    echo "error: missing required asset: $f" >&2
    exit 1
  fi
done

echo "[smoke] Starting local HTTP server..."
cd "$ROOT_DIR"
python3 -m http.server 8000 --bind 127.0.0.1 >/tmp/roster_cap_tool.http.log 2>&1 &
SERVE_PID=$!
cleanup() {
  kill "$SERVE_PID" >/dev/null 2>&1 || true
}
trap cleanup EXIT

# Wait briefly for server to start
for i in {1..10}; do
  if curl -fsS "http://127.0.0.1:8000/" >/dev/null 2>&1; then
    break
  fi
  sleep 0.3
done

echo "[smoke] Fetching app HTML and CSVs..."
curl -fsS "http://127.0.0.1:8000/docs/roster_cap_tool/index.html" >/tmp/roster_cap_tool.index.html
curl -fsS "http://127.0.0.1:8000/docs/roster_cap_tool/data/MEGA_teams.csv" >/tmp/roster_cap_tool.teams.csv
curl -fsS "http://127.0.0.1:8000/docs/roster_cap_tool/data/MEGA_players.csv" >/tmp/roster_cap_tool.players.csv

if ! grep -qi "Cap" "/tmp/roster_cap_tool.index.html"; then
  echo "error: index.html does not appear to contain Cap UI text" >&2
  exit 1
fi

echo "[smoke] PASS: docs/roster_cap_tool served with required assets."

