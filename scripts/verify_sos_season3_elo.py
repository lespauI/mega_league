#!/usr/bin/env python3
"""Thin wrapper — delegates to verify_sos_elo.py with --season-index 3."""

from __future__ import annotations

import sys

from verify_sos_elo import main

if __name__ == "__main__":
    raise SystemExit(main(["--season-index", "3"] + sys.argv[1:]))
