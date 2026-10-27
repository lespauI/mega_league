# Getting started with MEGA League analytics

The current cycle is Madden 27, season 1 (`seasonIndex=0`), with results through Week 12 plus completed Week 13 games and approved Week 8 ELO ratings. Madden 26 history stays under `archive/madden-26/`.

## Setup

Install Python 3 and download or clone this repository. Open a terminal in its root folder. Core analytics use the Python standard library; Node.js is needed for JavaScript checks, and Playwright is needed only for browser tests.

## Import league data

Follow the complete [export and update workflow](README.md#export-and-update-workflow). Request **Basic Info** and **Stats** from the NeonSportz export page, download both emailed ZIP attachments, and obtain the matching ELO CSV plus the separately maintained user map. Do not manually assemble a partial set of three CSVs or copy archived exports into the active root.

Validate before activation:

```bash
python3 scripts/validate_import.py \
  --basic-info-zip /path/to/basic-info.zip \
  --stats-zip /path/to/stats.zip \
  --elo-csv /path/to/mega_elo.csv \
  --users-csv /path/to/MEGA_users.csv \
  --season-index 0 --elo-source-week 8
```

Review the reported season/week. Run the same command with `--activate` to install the fully validated snapshot. Use the actual metadata when the cycle changes.

## Build and view

The first build for a new import must be the full pipeline:

```bash
python3 scripts/run_all.py --season-index 0
python3 scripts/verify_site.py
python3 -m http.server 8000
```

Open [the local landing page](http://localhost:8000/index.html). Serve the repository root, because browser datasets include root CSVs and files under `output/`. The build validates a complete temporary site before publishing locally. On failure, read the first error; do not substitute historical data or create empty outputs.

After a completed full build, the same snapshot supports smaller refreshes:

```bash
python3 scripts/run_all_stats.py
python3 scripts/run_all_playoff_analysis.py --season-index 0
```

Use `--validate-only` on a runner to check a staged build without updating published files. A changed input snapshot requires another full build.

## Check changes

```bash
python3 scripts/check.py
```

The existing cap-tool test has six known B/C/D projection assertions. The default command reports them as failures. `--allow-known-cap-failures` accepts only that exact known set, while continuing to fail on other errors. This does not change cap calculations.

For browser smoke checks after building:

```bash
npm ci
npx playwright install chromium
npm run test:e2e:smoke
```

See the [main README](README.md) for the publication/Git workflow and the [script guide](scripts/README.md) for individual commands. Cap and depth-chart scenarios are saved in your browser, scoped to the active cycle. Export a backup through the in-page controls before deliberate migration; do not clear storage during refreshes.
