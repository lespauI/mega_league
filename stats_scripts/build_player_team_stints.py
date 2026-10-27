from __future__ import annotations

from pathlib import Path
import sys

if not __package__:
    _PROJECT_ROOT = str(Path(__file__).resolve().parents[1])
    if _PROJECT_ROOT not in sys.path:
        sys.path.insert(0, _PROJECT_ROOT)

import csv
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, Tuple

from mega.inputs.csv import load_csv
from mega.inputs.identity import normalize_team_display, safe_float
from mega.stats.stints import (
    PASSING_FIELDS,
    RUSHING_FIELDS,
    StintKey,
    TeamMap,
    build_player_team_stints,
    build_team_map,
    ensure_stint_row,
    get_stint_key,
    reconcile_offense_with_team_totals,
)

if __name__ == "__main__":
    BASE_PATH = Path(__file__).parent.parent
    print(f"Working directory: {BASE_PATH}\n")
    build_player_team_stints(BASE_PATH)
    print("\n✓ Done! Use player_team_stints.csv for trade-aware player/team views.")
