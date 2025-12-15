#!/usr/bin/env bash
set -euo pipefail

# Sync selected CSVs into the GitHub Pages data directory.
# Default: players and teams CSVs. Use --all to copy all MEGA_*.csv files.
# Usage:
#   bash scripts/tools/sync_data_to_docs.sh          # copy players+teams
#   bash scripts/tools/sync_data_to_docs.sh --all    # copy all MEGA_*.csv

REPO_ROOT_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
DEST_DIR="$REPO_ROOT_DIR/docs/roster_cap_tool/data"

mkdir -p "$DEST_DIR"

copy_file() {
  local src="$1"
  local dest="$DEST_DIR/$(basename "$src")"
  if [[ -f "$src" ]]; then
    cp -v "$src" "$dest"
  else
    echo "[warn] source not found: $src" >&2
  fi
}

if [[ "${1:-}" == "--all" ]]; then
  echo "[info] Copying all MEGA_*.csv files to $DEST_DIR"
  shopt -s nullglob
  for src in "$REPO_ROOT_DIR"/MEGA_*.csv; do
    copy_file "$src"
  done
  shopt -u nullglob
else
  echo "[info] Copying players and teams CSVs to $DEST_DIR"
  copy_file "$REPO_ROOT_DIR/MEGA_players.csv"
  copy_file "$REPO_ROOT_DIR/MEGA_teams.csv"
fi

echo "[done] Data sync complete → $DEST_DIR"
