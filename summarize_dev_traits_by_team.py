import csv
from collections import defaultdict
from typing import Dict, Tuple
import sys


def parse_int(val: str) -> int:
    try:
        return int(val)
    except Exception:
        return None  # type: ignore


def summarize(input_path: str, output_path: str) -> Tuple[int, int]:
    """
    Read MEGA players CSV, aggregate dev trait counts by team, and write summary CSV.

    Mapping used (from devTrait numeric):
      0 -> normal
      1 -> star
      2 -> superstar
      3 -> xfactor

    Special handling for rookies (yearsPro == 0):
      If devTrait in {1,2,3} and yearsPro == 0, count as 'hiden' (not in star/superstar/xfactor).
    """
    counts: Dict[str, Dict[str, int]] = defaultdict(lambda: {
        'normal': 0,
        'hiden': 0,       # spelling per user request
        'star': 0,
        'superstar': 0,
        'xfactor': 0,
    })

    rows_read = 0
    teams_seen = set()

    with open(input_path, newline='', encoding='utf-8', errors='replace') as f:
        reader = csv.DictReader(f)
        # Validate required columns exist
        required = {'team', 'devTrait', 'yearsPro'}
        missing = [c for c in required if c not in reader.fieldnames]
        if missing:
            raise ValueError(f"Missing required columns: {', '.join(missing)}")

        for row in reader:
            rows_read += 1
            team = (row.get('team') or '').strip()
            if not team:
                # skip free agents / no-team
                continue
            teams_seen.add(team)

            dev = (row.get('devTrait') or '').strip()
            years_pro = parse_int((row.get('yearsPro') or '').strip())

            # Rookie hidden logic
            if dev in {'1', '2', '3'} and years_pro == 0:
                counts[team]['hiden'] += 1
                continue

            if dev == '0':
                counts[team]['normal'] += 1
            elif dev == '1':
                counts[team]['star'] += 1
            elif dev == '2':
                counts[team]['superstar'] += 1
            elif dev == '3':
                counts[team]['xfactor'] += 1
            else:
                # Unrecognized devTrait; ignore silently
                pass

    # Write output in requested column order
    fieldnames = ['team', 'normal', 'hiden', 'star', 'superstar', 'xfactor']
    with open(output_path, 'w', newline='', encoding='utf-8') as out:
        writer = csv.DictWriter(out, fieldnames=fieldnames)
        writer.writeheader()
        for team in sorted(counts.keys()):
            row = {'team': team}
            row.update(counts[team])
            writer.writerow(row)

    return rows_read, len(teams_seen)


def main(argv=None):
    argv = sys.argv if argv is None else argv
    input_path = 'MEGA_players.csv'
    output_path = 'dev_traits_by_team.csv'

    # Allow optional args: [input] [output]
    if len(argv) >= 2:
        input_path = argv[1]
    if len(argv) >= 3:
        output_path = argv[2]

    rows, teams = summarize(input_path, output_path)
    print(f"Processed {rows} rows across {teams} teams -> {output_path}")


if __name__ == '__main__':
    main()

