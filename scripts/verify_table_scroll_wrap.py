#!/usr/bin/env python3
"""
Verify that wide tables in the given HTML are wrapped in a horizontal scroll container.

Checks:
- Presence of `.table-wrap` CSS with `overflow-x: auto` (mobile-friendly scroll)
- Presence of `.table-wrap > table` rule with `min-width: 100%` (ensures table expands)
- Every `<table>` element appears inside a `<div class="table-wrap"> ... </div>` wrapper

Usage:
  python3 scripts/verify_table_scroll_wrap.py --html docs/draft_class_2026.html
"""
from __future__ import annotations

import argparse
import re
import sys


def main() -> int:
    ap = argparse.ArgumentParser(description="Verify horizontal scroll wrappers for tables in HTML")
    ap.add_argument("--html", required=True, help="Path to the HTML file to check")
    args = ap.parse_args()

    try:
        with open(args.html, "r", encoding="utf-8") as fh:
            html_text = fh.read()
    except FileNotFoundError:
        print(f"wrap-verify: file not found: {args.html}", file=sys.stderr)
        return 2

    errors: list[str] = []

    # CSS presence checks
    if not re.search(r"\.table-wrap\s*\{[^}]*overflow-x\s*:\s*auto", html_text, re.IGNORECASE | re.DOTALL):
        errors.append(".table-wrap CSS missing overflow-x:auto")
    if not re.search(r"\.table-wrap\s*>\s*table\s*\{[^}]*min-width\s*:\s*100%", html_text, re.IGNORECASE | re.DOTALL):
        errors.append(".table-wrap > table CSS missing min-width:100%")

    # Wrapper-around-table check
    total_tables = len(re.findall(r"<table\b", html_text, re.IGNORECASE))
    wrapped_tables = len(re.findall(r"<div\s+class=\"table-wrap\"[^>]*>\s*<table\b", html_text, re.IGNORECASE))
    if total_tables == 0:
        errors.append("no <table> elements found to verify wrappers")
    elif wrapped_tables < total_tables:
        errors.append(f"only {wrapped_tables} of {total_tables} tables are inside .table-wrap")

    if errors:
        print("wrap-verify: FAILED:", file=sys.stderr)
        for e in errors:
            print(f"  - {e}", file=sys.stderr)
        return 1

    print(f"wrap-verify: OK — {wrapped_tables}/{total_tables} tables wrapped; CSS present")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

