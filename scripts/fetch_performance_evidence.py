#!/usr/bin/env python3
"""Refresh and reconcile performance evidence from the public NeonSportz API."""
import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from mega.inputs.performance_api import collect


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--workers', type=int, choices=range(1, 5), default=3)
    parser.add_argument('--full-refresh', action='store_true',
                        help='Refetch every completed game and required history; default reuses validated cache')
    args = parser.parse_args()
    try:
        result = collect(args.root, full_refresh=args.full_refresh,
                         progress=lambda message: print(message, flush=True))
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(f'API refresh failed; previous evidence retained: {exc}', file=sys.stderr)
        return 1
    print(f"Validated API evidence installed: {result['completedGames']} games, "
          f"{result['excludedGames']} Force Wins, {len(result['tradeCorrections'])} trade corrections. "
          'Run scripts/run_all.py to rebuild the site.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
