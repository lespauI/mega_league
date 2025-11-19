#!/usr/bin/env python3
"""
Deterministic tiny draft CSV generator.

Creates `output/tiny_players.csv` with a small, reproducible set of rookies
covering all dev tiers (3,2,1,0), multiple teams, positions, and first 4 rounds.

CSV schema:
  rookieYear,fullName,team,position,playerBestOvr,devTrait,draftRound,draftPick,college

Usage:
  python3 scripts/fixtures/generate_tiny_draft.py

No external dependencies.
"""
from __future__ import annotations

import csv
import os
from typing import List, Dict


OUT_PATH = os.path.join("output", "tiny_players.csv")
FIELDNAMES = [
    "rookieYear",
    "fullName",
    "team",
    "position",
    "playerBestOvr",
    "devTrait",
    "draftRound",
    "draftPick",
    "college",
]


def rows() -> List[Dict[str, str]]:
    # Fixed, hand-crafted dataset for reproducibility
    # Year aligns with examples elsewhere in the repo
    year = "2026"
    data = [
        # Round 1
        {"rookieYear": year, "fullName": "Jaxon Reed", "team": "Bears", "position": "QB", "playerBestOvr": "79", "devTrait": "3", "draftRound": "1", "draftPick": "3", "college": "Ohio State"},
        {"rookieYear": year, "fullName": "Mason Carter", "team": "Patriots", "position": "WR", "playerBestOvr": "76", "devTrait": "2", "draftRound": "1", "draftPick": "12", "college": "Alabama"},
        {"rookieYear": year, "fullName": "Tyrell Brooks", "team": "Rams", "position": "CB", "playerBestOvr": "74", "devTrait": "1", "draftRound": "1", "draftPick": "24", "college": "LSU"},
        {"rookieYear": year, "fullName": "Evan Watts", "team": "Seahawks", "position": "LT", "playerBestOvr": "72", "devTrait": "0", "draftRound": "1", "draftPick": "29", "college": "Oregon"},

        # Round 2
        {"rookieYear": year, "fullName": "Caleb Knox", "team": "49ers", "position": "DE", "playerBestOvr": "73", "devTrait": "2", "draftRound": "2", "draftPick": "6", "college": "Georgia"},
        {"rookieYear": year, "fullName": "Ramon Ortega", "team": "Giants", "position": "HB", "playerBestOvr": "71", "devTrait": "0", "draftRound": "2", "draftPick": "15", "college": "Texas"},
        {"rookieYear": year, "fullName": "Logan Pierce", "team": "Eagles", "position": "TE", "playerBestOvr": "72", "devTrait": "1", "draftRound": "2", "draftPick": "27", "college": "Iowa"},

        # Round 3
        {"rookieYear": year, "fullName": "Dominic Hale", "team": "Cowboys", "position": "MLB", "playerBestOvr": "70", "devTrait": "0", "draftRound": "3", "draftPick": "5", "college": "Penn State"},
        {"rookieYear": year, "fullName": "Nate Jennings", "team": "Chiefs", "position": "FS", "playerBestOvr": "73", "devTrait": "2", "draftRound": "3", "draftPick": "18", "college": "Clemson"},
        {"rookieYear": year, "fullName": "Micah Douglas", "team": "Packers", "position": "RT", "playerBestOvr": "71", "devTrait": "1", "draftRound": "3", "draftPick": "31", "college": "Wisconsin"},

        # Round 4
        {"rookieYear": year, "fullName": "Quincy Burke", "team": "Bills", "position": "K", "playerBestOvr": "67", "devTrait": "0", "draftRound": "4", "draftPick": "4", "college": "Florida State"},
        {"rookieYear": year, "fullName": "Aiden Romero", "team": "Ravens", "position": "WR", "playerBestOvr": "75", "devTrait": "3", "draftRound": "4", "draftPick": "22", "college": "USC"},
    ]

    # Stable sort by round, then pick, ensuring deterministic output order
    data.sort(key=lambda r: (int(r["draftRound"]), int(r["draftPick"])))
    return data


def main() -> None:
    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    data = rows()

    with open(OUT_PATH, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=FIELDNAMES)
        writer.writeheader()
        for r in data:
            # Ensure only expected fields are written (no extras)
            writer.writerow({k: r.get(k, "") for k in FIELDNAMES})

    print(f"Wrote {len(data)} rows to {OUT_PATH}")


if __name__ == "__main__":
    main()

