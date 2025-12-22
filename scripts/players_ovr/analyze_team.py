#!/usr/bin/env python3
import sys
import subprocess

def main():
    if len(sys.argv) < 2:
        print("Usage: python analyze_team.py <TeamName> [PositionGroup]")
        print("\nExamples:")
        print("  python analyze_team.py Cowboys")
        print("  python analyze_team.py Cowboys OL")
        print("  python analyze_team.py Cowboys LB")
        sys.exit(1)
    
    team = sys.argv[1]
    position_group = sys.argv[2] if len(sys.argv) > 2 else None
    
    filter_msg = f"{team}"
    if position_group:
        filter_msg += f" - {position_group.upper()}"
    
    print(f"\nAnalyzing position optimizations for: {filter_msg}", flush=True)
    print("="*80, flush=True)
    
    print("[1/3] Exporting position data from MEGA_players.csv...", flush=True)
    result = subprocess.run([sys.executable, "export_individual_positions.py"], 
                          capture_output=True, text=True)
    if result.returncode != 0:
        print(f"ERROR: {result.stderr}")
        sys.exit(1)
    
    print("[2/3] Calculating OVR formulas...", flush=True)
    result = subprocess.run([sys.executable, "calculate_advanced_formulas.py"], 
                          capture_output=True, text=True)
    if result.returncode != 0:
        print(f"ERROR: {result.stderr}")
        sys.exit(1)
    
    print(f"[3/3] Finding optimal positions for {filter_msg}...\n", flush=True)
    print("="*80 + "\n", flush=True)
    
    cmd = [sys.executable, "optimize_positions.py", team]
    if position_group:
        cmd.append(position_group)
    
    result = subprocess.run(cmd)
    
    sys.exit(result.returncode)

if __name__ == '__main__':
    main()
