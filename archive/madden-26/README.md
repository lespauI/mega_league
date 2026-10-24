# Madden 26 archive

Archived on **2026-10-24** before the transition to **Madden 27**. This directory is historical; its data must never be used as an automatic fallback for the active cycle.

## Contents and provenance

`manifest.json` records the source Git commit, original path, archive path, byte length, SHA-256 checksum, and whether each item was moved or copied. The snapshot contains **458 files**: **386 moved** out of active paths and **72 copied** as dependencies/references. Files retain their original bytes, including CSV line endings (`archive/.gitattributes` disables normalization).

- Root `MEGA_*.csv`, `mega_elo.csv`, and filtered exports: old league inputs.
- `output/`: old aggregates, schedules, projections, roster exports, training data, and generated reports. Formula coefficients, the trained guard model, and `attributes.md` were also copied for provenance; their active originals remain unchanged.
- `docs/`: the previous site's data, rendered reports, narratives, images, and copies of reusable HTML/JS/CSS dependencies.
- `index.html`: the previous site index, preserved unchanged.
- `scripts/fixtures/`: Madden 26 draft narrative and section introductions, distinct from retained synthetic testing fixtures.
- `mockups/`: the old NFC playoff infographic.
- `.zenflow/tasks/`: committed task history. Pre-existing untracked task folders were left in the working tree.
- `wild_card_season_1.md` and `plan.md`: historical analysis and completed draft-planning notes.
- `reference/`: previous README, AGENTS, CLAUDE, and beginner-guide documents. They describe the former cycle, not current operating instructions.

The archive is a data/site snapshot, not a separate checkout of every calculation script. Calculation source remains in the active project; the exact historical source is identified by `source_commit` in the manifest and recoverable from Git. Ignored local editor/chat settings, browser storage, and remote prediction-service votes are not part of this snapshot.

## Browse or restore

Read [the historical index](index.html) or [the previous project guide](reference/README.md). To browse with the old root-relative URLs, serve this directory from the repository root:

```bash
python3 -m http.server 8001 --directory archive/madden-26
```

Open `http://localhost:8001/index.html` using a separate browser profile if interacting with saved cap/depth scenarios. Historical pages retain their original code and external CDN/service dependencies; availability and writes to external services are not controlled by this snapshot. The archive's playoff prediction UI still contains the old remote configuration.

For analysis, copy the snapshot into a **separate working directory** and use the source revision recorded in the manifest. Restore files by their recorded `source` paths there. Do not overwrite Madden 27 exports in the active root. Do not regenerate reports inside this archive.

## Verify integrity

Run this read-only check from the repository root:

```bash
python3 - <<'PY'
from pathlib import Path
import hashlib
import json

root = Path('archive/madden-26')
manifest = json.loads((root / 'manifest.json').read_text())
for item in manifest['entries']:
    content = (root / item['path']).read_bytes()
    assert len(content) == item['bytes'], item['path']
    assert hashlib.sha256(content).hexdigest() == item['sha256'], item['path']
print(f"Verified {len(manifest['entries'])} archived files")
PY
```

The manifest covers the archived payload, not this newly written guide or the manifest itself. Keep both with the snapshot in Git.
