#!/usr/bin/env python3
"""Validate the complete static publication without changing it."""

import argparse
from pathlib import Path
import sys

if not __package__:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from mega.site import validate_site


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1],
                        help="Assembled publication root (default: repository root)")
    args = parser.parse_args(argv)
    errors = validate_site(args.root)
    for error in errors:
        print(f"ERROR: {error}", file=sys.stderr)
    if errors:
        print(f"Site validation failed: {len(errors)} error(s).", file=sys.stderr)
        return 1
    print("Site validation passed: active pages, local assets, and snapshot data are complete.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
