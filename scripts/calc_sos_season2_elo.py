#!/usr/bin/env python3
"""Thin wrapper — delegates to calc_sos_elo.py with --season-index 2.

Translates legacy --season2-start-row flag to --start-row for backwards compatibility.
"""

from __future__ import annotations

import sys
from typing import List

from calc_sos_elo import main


def _translate_argv(argv: List[str]) -> List[str]:
    result: List[str] = ["--season-index", "2"]
    i = 0
    while i < len(argv):
        if argv[i] == "--season2-start-row" and i + 1 < len(argv):
            result.extend(["--start-row", argv[i + 1]])
            i += 2
        else:
            result.append(argv[i])
            i += 1
    return result


if __name__ == "__main__":
    raise SystemExit(main(_translate_argv(sys.argv[1:])))
