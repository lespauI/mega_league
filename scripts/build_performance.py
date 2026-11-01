#!/usr/bin/env python3
"""Build validated Force-Win-free performance inputs without changing raw exports."""
import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from mega.stats.performance import build_performance

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--season-index", type=int, default=0)
    args = parser.parse_args()
    result = build_performance(args.root, args.season_index)
    print(f"Performance evidence: {result['completedGames']} completed, {result['excludedGames']} excluded; "
          f"{len(result['tradeCorrections'])} duplicate corrections, {len(result['unavailableFields'])} unavailable fields")
