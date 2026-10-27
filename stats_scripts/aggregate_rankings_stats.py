from __future__ import annotations

from pathlib import Path
import sys

if not __package__:
    _PROJECT_ROOT = str(Path(__file__).resolve().parents[1])
    if _PROJECT_ROOT not in sys.path:
        sys.path.insert(0, _PROJECT_ROOT)

from collections import defaultdict
from pathlib import Path
import csv

from mega.inputs.csv import load_csv
from mega.inputs.identity import normalize_team_display, safe_float
from mega.stats.rankings import aggregate_rankings_stats, safe_int

if __name__ == "__main__":
    base_path = Path(__file__).parent.parent
    print(f"Working directory: {base_path}\n")
    stats = aggregate_rankings_stats(base_path)
    print("\n✓ Done! Use team_rankings_stats.csv for visualizations.")
