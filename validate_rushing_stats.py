#!/usr/bin/env python3
import csv
import sys

def get_player(players, name):
    for p in players:
        if p['name'] == name:
            return p
    return None

def validate_rushing_stats():
    all_players = []
    with open('MEGA_rushing.csv', 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if int(row['rushTotalAtt']) > 0:
                all_players.append({
                    'name': row['player__fullName'],
                    'team': row['team__abbrName'],
                    'position': row['player__position'],
                    'yards': int(row['rushTotalYds']),
                    'ypg': float(row['rushAvgYdsPerGame']),
                    'tds': int(row['rushTotalTDs']),
                    'ypc': float(row['rushAvgYdsPerAtt']),
                    'attempts': int(row['rushTotalAtt']),
                    'broken_tackles': int(row['rushTotalBrokenTackles']),
                    'yac': int(row['rushTotalYdsAfterContact']),
                    'yac_avg': float(row['rushAvgYdsAfterContact']),
                    'longest': int(row['rushTotalLongest']),
                    'runs_20plus': int(row['rushTotal20PlusYds']),
                    'fumbles': int(row['rushTotalFum'])
                })
    
    rbs = [p for p in all_players if p['position'] == 'HB' and p['attempts'] >= 40]
    
    errors = []
    
    print("=" * 80)
    print("VALIDATING RUSHING STATISTICS")
    print("=" * 80)
    
    print("\n1. TOP RUSHING YARDS:")
    top_yards = sorted(rbs, key=lambda x: x['yards'], reverse=True)[:5]
    for p in top_yards:
        print(f"   {p['name']} ({p['team']}) - {p['yards']} yards, {p['ypg']:.2f} YPG, {p['ypc']:.2f} YPC")
    
    yards_checks = [
        ('RJ Harvey', 854, 94.89, 7.69),
        ('TreVeyon Henderson', 811, 101.38, 6.01),
        ('Javonte Williams', 720, 90.00, 5.07),
        ('Saquon Barkley', 727, 90.88, 5.59),
        ('Chase Brown', 696, 77.33, 5.04)
    ]
    
    for name, yards, ypg, ypc in yards_checks:
        player = get_player(all_players, name)
        if player is None:
            errors.append(f"❌ {name} not found in data")
        else:
            if player['yards'] != yards:
                errors.append(f"❌ {name}: Expected {yards} yards, got {player['yards']}")
            if abs(player['ypg'] - ypg) > 0.01:
                errors.append(f"❌ {name}: Expected {ypg:.2f} YPG, got {player['ypg']:.2f}")
            if abs(player['ypc'] - ypc) > 0.01:
                errors.append(f"❌ {name}: Expected {ypc:.2f} YPC, got {player['ypc']:.2f}")
    
    print("\n2. TOP RUSHING TOUCHDOWNS:")
    top_tds = sorted(rbs, key=lambda x: x['tds'], reverse=True)[:5]
    for p in top_tds:
        print(f"   {p['name']} ({p['team']}) - {p['tds']} TD")
    
    td_checks = [
        ('TreVeyon Henderson', 11),
        ('Javonte Williams', 11),
        ('Bucky Irving', 11),
        ('Tony Pollard', 11),
        ('Derrick Henry', 10)
    ]
    
    for name, tds in td_checks:
        player = get_player(all_players, name)
        if player and player['tds'] != tds:
            errors.append(f"❌ {name}: Expected {tds} TDs, got {player['tds']}")
    
    print("\n3. TOP YARDS PER CARRY (min 40 attempts):")
    qualified_rbs = [p for p in rbs if p['attempts'] >= 40]
    top_ypc = sorted(qualified_rbs, key=lambda x: x['ypc'], reverse=True)[:5]
    for p in top_ypc:
        print(f"   {p['name']} ({p['team']}) - {p['ypc']:.2f} YPC ({p['attempts']} attempts)")
    
    ypc_checks = [
        ('RJ Harvey', 7.69),
        ('Chuba Hubbard', 6.01),
        ('TreVeyon Henderson', 6.01),
        ('Kenneth Walker III', 5.94),
        ('Christian McCaffrey', 5.93)
    ]
    
    for name, ypc in ypc_checks:
        player = get_player(all_players, name)
        if player and abs(player['ypc'] - ypc) > 0.01:
            errors.append(f"❌ {name}: Expected {ypc:.2f} YPC, got {player['ypc']:.2f}")
    
    print("\n4. TOP YARDS PER GAME:")
    top_ypg = sorted(rbs, key=lambda x: x['ypg'], reverse=True)[:5]
    for p in top_ypg:
        print(f"   {p['name']} ({p['team']}) - {p['ypg']:.2f} YPG")
    
    ypg_checks = [
        ('TreVeyon Henderson', 101.38),
        ('RJ Harvey', 94.89),
        ('Saquon Barkley', 90.88),
        ('Javonte Williams', 90.00),
        ('Isiah Pacheco', 86.86)
    ]
    
    for name, ypg in ypg_checks:
        player = get_player(all_players, name)
        if player and abs(player['ypg'] - ypg) > 0.01:
            errors.append(f"❌ {name}: Expected {ypg:.2f} YPG, got {player['ypg']:.2f}")
    
    print("\n5. TOP BROKEN TACKLES:")
    top_bt = sorted(rbs, key=lambda x: x['broken_tackles'], reverse=True)[:5]
    for p in top_bt:
        print(f"   {p['name']} ({p['team']}) - {p['broken_tackles']} broken tackles")
    
    bt_checks = [
        ('RJ Harvey', 27),
        ('Quinshon Judkins', 25),
        ('Tony Pollard', 25),
        ('Bijan Robinson', 24),
        ('Saquon Barkley', 23)
    ]
    
    for name, bt in bt_checks:
        player = get_player(all_players, name)
        if player and player['broken_tackles'] != bt:
            errors.append(f"❌ {name}: Expected {bt} broken tackles, got {player['broken_tackles']}")
    
    print("\n6. TOP YARDS AFTER CONTACT (YAC):")
    top_yac = sorted(rbs, key=lambda x: x['yac'], reverse=True)[:5]
    for p in top_yac:
        print(f"   {p['name']} ({p['team']}) - {p['yac']} YAC, avg {p['yac_avg']:.2f}")
    
    yac_checks = [
        ('Javonte Williams', 262, 32.75),
        ('TreVeyon Henderson', 249, 31.13),
        ('Derrick Henry', 245, 30.63),
        ('Isiah Pacheco', 205, 29.29),
        ('Saquon Barkley', 211, 26.38)
    ]
    
    for name, yac, yac_avg in yac_checks:
        player = get_player(all_players, name)
        if player:
            if player['yac'] != yac:
                errors.append(f"❌ {name}: Expected {yac} YAC, got {player['yac']}")
            if abs(player['yac_avg'] - yac_avg) > 0.01:
                errors.append(f"❌ {name}: Expected {yac_avg:.2f} avg YAC, got {player['yac_avg']:.2f}")
    
    print("\n7. DUAL-THREAT QBS:")
    qbs = [p for p in all_players if p['position'] == 'QB' and p['attempts'] >= 20]
    top_qb_rushers = sorted(qbs, key=lambda x: x['yards'], reverse=True)[:3]
    for p in top_qb_rushers:
        print(f"   {p['name']} ({p['team']}) - {p['yards']} yards, {p['ypc']:.2f} YPC, {p['tds']} TD")
    
    qb_checks = [
        ('Lamar Jackson', 438, 9.73, 4),
        ('Jalen Hurts', 303, 8.42, 6),
        ('Jayden Daniels', 102, 3.09, 5)
    ]
    
    for name, yards, ypc, tds in qb_checks:
        player = get_player(all_players, name)
        if player:
            if player['yards'] != yards:
                errors.append(f"❌ {name}: Expected {yards} yards, got {player['yards']}")
            if abs(player['ypc'] - ypc) > 0.01:
                errors.append(f"❌ {name}: Expected {ypc:.2f} YPC, got {player['ypc']:.2f}")
            if player['tds'] != tds:
                errors.append(f"❌ {name}: Expected {tds} TDs, got {player['tds']}")
    
    print("\n8. LONGEST RUN:")
    longest = sorted(all_players, key=lambda x: x['longest'], reverse=True)[0]
    print(f"   {longest['name']} ({longest['team']}) - {longest['longest']} yards")
    if longest['name'] == 'RJ Harvey' and longest['longest'] != 88:
        errors.append(f"❌ RJ Harvey: Expected 88 yard longest run, got {longest['longest']}")
    
    print("\n9. MOST 20+ YARD RUNS:")
    top_20plus = sorted(all_players, key=lambda x: x['runs_20plus'], reverse=True)[:3]
    for p in top_20plus:
        print(f"   {p['name']} ({p['team']}) - {p['runs_20plus']} runs of 20+ yards")
    
    print("\n10. MOST ATTEMPTS:")
    top_att = sorted(rbs, key=lambda x: x['attempts'], reverse=True)[:5]
    for p in top_att:
        print(f"   {p['name']} ({p['team']}) - {p['attempts']} attempts")
    
    att_checks = [
        ('Javonte Williams', 142),
        ('Chase Brown', 138),
        ('Tony Pollard', 135),
        ('TreVeyon Henderson', 135),
        ('Saquon Barkley', 130)
    ]
    
    for name, attempts in att_checks:
        player = get_player(all_players, name)
        if player and player['attempts'] != attempts:
            errors.append(f"❌ {name}: Expected {attempts} attempts, got {player['attempts']}")
    
    print("\n11. FUMBLE PROBLEMS:")
    fumble_players = sorted([p for p in all_players if p['fumbles'] >= 2], 
                          key=lambda x: x['fumbles'], reverse=True)[:5]
    for p in fumble_players:
        print(f"   {p['name']} ({p['team']}, {p['position']}) - {p['fumbles']} fumbles")
    
    fumble_checks = [
        ('Anthony Richardson Sr', 4),
        ('Bryce Young', 4),
        ('Jordan Love', 4)
    ]
    
    for name, fumbles in fumble_checks:
        player = get_player(all_players, name)
        if player and player['fumbles'] != fumbles:
            errors.append(f"❌ {name}: Expected {fumbles} fumbles, got {player['fumbles']}")
    
    print("\n12. INEFFICIENT VOLUME BACKS:")
    inefficient = [
        ('Bijan Robinson', 438, 3.95, 111),
        ('Josh Jacobs', 376, 3.92, 96),
        ('James Conner', 304, 4.68, 65)
    ]
    
    print("   Checking inefficient volume backs:")
    for name, yards, ypc, attempts in inefficient:
        player = get_player(all_players, name)
        if player:
            print(f"   {name}: {player['yards']} yards, {player['ypc']:.2f} YPC ({player['attempts']} attempts)")
            if player['yards'] != yards:
                errors.append(f"❌ {name}: Expected {yards} yards, got {player['yards']}")
            if abs(player['ypc'] - ypc) > 0.01:
                errors.append(f"❌ {name}: Expected {ypc:.2f} YPC, got {player['ypc']:.2f}")
            if player['attempts'] != attempts:
                errors.append(f"❌ {name}: Expected {attempts} attempts, got {player['attempts']}")
    
    print("\n13. ROOKIE STANDOUTS:")
    rookie_checks = [
        ('RJ Harvey', 854, 7.69, 8),
        ('TreVeyon Henderson', 811, 6.01, 11),
        ('Kaleb Johnson', 591, 5.91, 6),
        ('Quinshon Judkins', 543, 4.72, 4),
        ('Dylan Sampson', 521, 5.43, 8)
    ]
    
    print("   Checking rookie standouts:")
    for name, yards, ypc, tds in rookie_checks:
        player = get_player(all_players, name)
        if player:
            print(f"   {name}: {player['yards']} yards, {player['ypc']:.2f} YPC, {player['tds']} TD")
            if player['yards'] != yards:
                errors.append(f"❌ {name}: Expected {yards} yards, got {player['yards']}")
            if abs(player['ypc'] - ypc) > 0.01:
                errors.append(f"❌ {name}: Expected {ypc:.2f} YPC, got {player['ypc']:.2f}")
            if player['tds'] != tds:
                errors.append(f"❌ {name}: Expected {tds} TDs, got {player['tds']}")
    
    print("\n" + "=" * 80)
    if errors:
        print(f"VALIDATION FAILED - {len(errors)} ERROR(S) FOUND:")
        print("=" * 80)
        for error in errors:
            print(error)
        return 1
    else:
        print("✅ ALL VALIDATIONS PASSED!")
        print("=" * 80)
        return 0

if __name__ == '__main__':
    sys.exit(validate_rushing_stats())
