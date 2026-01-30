#!/usr/bin/env python3
"""
Export only 2027 rookies from MEGA_players.csv to a separate CSV file.

Usage:
    python3 scripts/export_2027_rookies.py
    python3 scripts/export_2027_rookies.py --year 2027 --input MEGA_players.csv --output output/rookies_2027.csv
"""
import argparse
import csv
import sys
from pathlib import Path


def export_rookies(input_path: str, output_path: str, year: int):
    """Filter players by rookie year and export to CSV."""
    
    try:
        # Read all players
        with open(input_path, 'r', encoding='utf-8-sig', newline='') as f:
            reader = csv.DictReader(f)
            fieldnames = reader.fieldnames
            
            if not fieldnames:
                print(f"Error: No columns found in {input_path}", file=sys.stderr)
                sys.exit(1)
            
            if 'rookieYear' not in fieldnames:
                print(f"Error: 'rookieYear' column not found in {input_path}", file=sys.stderr)
                sys.exit(1)
            
            # Filter rookies
            rookies = []
            for row in reader:
                try:
                    rookie_year = row.get('rookieYear', '').strip()
                    if rookie_year and int(rookie_year) == year:
                        rookies.append(row)
                except (ValueError, TypeError):
                    # Skip rows with invalid rookieYear
                    continue
        
        # Write rookies to output
        output_dir = Path(output_path).parent
        if output_dir and not output_dir.exists():
            output_dir.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rookies)
        
        print(f"✓ Exported {len(rookies)} rookies from year {year}")
        print(f"  Input:  {input_path}")
        print(f"  Output: {output_path}")
        
    except FileNotFoundError:
        print(f"Error: File not found: {input_path}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description='Export rookies from a specific draft year to CSV'
    )
    parser.add_argument(
        '--year',
        type=int,
        default=2027,
        help='Rookie year to filter (default: 2027)'
    )
    parser.add_argument(
        '--input',
        default='MEGA_players.csv',
        help='Input players CSV file (default: MEGA_players.csv)'
    )
    parser.add_argument(
        '--output',
        default='output/rookies_2027.csv',
        help='Output CSV file (default: output/rookies_2027.csv)'
    )
    
    args = parser.parse_args()
    export_rookies(args.input, args.output, args.year)


if __name__ == '__main__':
    main()
