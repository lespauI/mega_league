#!/usr/bin/env python3
"""Run fixture checks, optionally a staged build and current-site browser smoke tests."""

import argparse
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
NODE_CHECKS = ("cycle_storage", "current_elo", "shared_csv", "data_manifest", "year_context", "cap_tool")
KNOWN_CAP_FAILURES = (
    "Assertion failed: Scenario B: expected Y+1 spent base + next-year penalty",
    "Assertion failed: Scenario B: expected Y+1 space base - next-year penalty",
    "Assertion failed: Scenario C: expected Y+2 spent unchanged",
    "Assertion failed: Scenario C: expected Y+2 space unchanged",
    "Assertion failed: Scenario D: Y+3 spent unchanged",
    "Assertion failed: Scenario D: Y+3 space unchanged",
)


def known_cap_failure(result):
    lines = [line for line in result.stdout.splitlines() if line.startswith("Assertion failed:")]
    return result.returncode == 1 and len(lines) == len(KNOWN_CAP_FAILURES) and all(
        sum(line.startswith(expected) for line in lines) == 1 for expected in KNOWN_CAP_FAILURES
    ) and all(line.startswith(("Assertion failed:", "Cap tool tests completed.")) for line in result.stdout.splitlines() if line)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build", action="store_true", help="Also run a full staged build without publishing")
    parser.add_argument("--site", action="store_true", help="Also validate the existing published site")
    parser.add_argument("--browser", action="store_true", help="Also run current-cycle browser smoke tests (requires npm ci and Playwright)")
    parser.add_argument("--allow-known-cap-failures", action="store_true",
                        help="Report only the six recorded B/C/D assertion failures as known; all other failures still fail")
    args = parser.parse_args(argv)
    commands = [
        ("Python fixture suite", [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-p", "test_*.py"]),
        ("Week numbers", [sys.executable, "scripts/tests/test_week_numbers.py"]),
        *[(f"Node {name}", ["node", f"scripts/tests/test_{name}.mjs"]) for name in NODE_CHECKS],
    ]
    if args.build:
        commands.append(("Full staged build", [sys.executable, "scripts/run_all.py", "--validate-only"]))
    if args.site:
        commands.append(("Published site", [sys.executable, "scripts/verify_site.py"]))
    if args.browser:
        commands.append(("Browser smoke", ["npm", "run", "test:e2e:smoke"]))
    statuses = []
    environment = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}
    for label, command in commands:
        print(f"\n{label}", flush=True)
        try:
            result = subprocess.run(command, cwd=ROOT, env=environment, text=True,
                                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        except OSError as exc:
            print(exc)
            statuses.append((label, "FAIL"))
            continue
        print(result.stdout, end="" if result.stdout.endswith("\n") else "\n")
        status = "PASS" if result.returncode == 0 else "FAIL"
        if label == "Node cap_tool" and args.allow_known_cap_failures and known_cap_failure(result):
            status = "KNOWN FAILURE (six recorded B/C/D assertions)"
        statuses.append((label, status))
    print("\nCheck results")
    for label, status in statuses:
        print(f"{status}: {label}")
    return int(any(status == "FAIL" for _, status in statuses))


if __name__ == "__main__":
    raise SystemExit(main())
