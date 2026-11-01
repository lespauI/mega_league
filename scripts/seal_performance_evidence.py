#!/usr/bin/env python3
"""Validate and rebind existing performance evidence offline.

Use fetch_performance_evidence.py when new or changed games require API data.
"""
import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from mega.inputs.performance_api import collect


def seal(root):
    def offline(url):
        raise ValueError('Cached evidence is insufficient; run scripts/fetch_performance_evidence.py')
    return collect(root, get=offline)['completedGames']


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    try:
        print(f'Validated and bound evidence for {seal(args.root)} completed games.')
    except (OSError, ValueError, KeyError, TypeError) as exc:
        parser.exit(1, f'Offline evidence validation failed: {exc}\n')
