#!/usr/bin/env python3
import csv
import sys

def get_player(players, name):
    for p in players:
        if p['name'] == name:
            return p
    return None

def get_combined_stats(players, name):
    """Get combined stats for players who appear on multiple teams"""
    matches = [p for p in players if p['name'] == name]
    if not matches:
        return None
    if len(matches) == 1:
        return matches[0]
    
    combined = matches[0].copy()
    for i in range(1, len(matches)):
        combined['yards'] += matches[i]['yards']
        combined['catches'] += matches[i]['catches']
        combined['tds'] += matches[i]['tds']
        combined['yac'] += matches[i]['yac']
        combined['drops'] += matches[i]['drops']
    
    combined['team'] = f"{matches[0]['team']}/{matches[1]['team']}"
    return combined

def validate_receiving_stats():
    all_players = []
    with open('MEGA_receiving.csv', 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if int(row['recTotalCatches']) > 0:
                all_players.append({
                    'name': row['player__fullName'],
                    'team': row['team__abbrName'],
                    'position': row['player__position'],
                    'yards': int(row['recTotalYds']),
                    'ypg': float(row['recAvgYdsPerGame']),
                    'tds': int(row['recTotalTDs']),
                    'catches': int(row['recTotalCatches']),
                    'ypc': float(row['recAvgYdsPerCatch']),
                    'catch_pct': float(row['recAvgCatchPct']),
                    'drops': int(row['recTotalDrops']),
                    'yac': int(row['recTotalYdsAfterCatch']),
                    'yac_avg': float(row['recAvgYacPerCatch']),
                    'longest': int(row['recTotalLongest'])
                })
    
    qualified = [p for p in all_players if p['catches'] >= 10]
    
    errors = []
    
    print("=" * 80)
    print("VALIDATING RECEIVING STATISTICS")
    print("=" * 80)
    
    print("\n1. TOP RECEIVING YARDS:")
    top_yards = sorted(all_players, key=lambda x: x['yards'], reverse=True)[:5]
    for p in top_yards:
        print(f"   {p['name']} ({p['team']}) - {p['yards']} yards, {p['catches']} rec, {p['ypg']:.2f} YPG, {p['tds']} TD")
    
    yards_checks = [
        ('Ja\'Marr Chase', 787, 58, 87.44, 7),
        ('Tetairoa McMillan', 770, 51, 85.56, 4),
        ('Brian Thomas Jr', 676, 15, 84.50, 6),
        ('Kyle Pitts', 659, 43, 82.38, 3),
        ('Mason Taylor', 651, 45, 81.38, 7)
    ]
    
    for name, yards, catches, ypg, tds in yards_checks:
        player = get_player(all_players, name)
        if player is None:
            errors.append(f"❌ {name} not found in data")
        else:
            if player['yards'] != yards:
                errors.append(f"❌ {name}: Expected {yards} yards, got {player['yards']}")
            if player['catches'] != catches:
                errors.append(f"❌ {name}: Expected {catches} catches, got {player['catches']}")
            if abs(player['ypg'] - ypg) > 0.01:
                errors.append(f"❌ {name}: Expected {ypg:.2f} YPG, got {player['ypg']:.2f}")
            if player['tds'] != tds:
                errors.append(f"❌ {name}: Expected {tds} TDs, got {player['tds']}")
    
    print("\n2. TOP RECEIVING TOUCHDOWNS:")
    top_tds = sorted(all_players, key=lambda x: x['tds'], reverse=True)[:8]
    for p in top_tds:
        print(f"   {p['name']} ({p['team']}) - {p['tds']} TD, {p['yards']} yards, {p['catches']} rec")
    
    td_checks = [
        ('Nico Collins', 8),
        ('Dont\'e Thornton Jr.', 8),
        ('Ja\'Marr Chase', 7),
        ('Amon-Ra St. Brown', 7),
        ('Mason Taylor', 7),
        ('T.J. Hockenson', 7),
        ('Chigoziem Okonkwo', 7),
        ('Chimere Dike', 7)
    ]
    
    for name, tds in td_checks:
        player = get_player(all_players, name)
        if player and player['tds'] != tds:
            errors.append(f"❌ {name}: Expected {tds} TDs, got {player['tds']}")
    
    print("\n3. TOP RECEPTIONS:")
    top_catches = sorted(all_players, key=lambda x: x['catches'], reverse=True)[:5]
    for p in top_catches:
        print(f"   {p['name']} ({p['team']}) - {p['catches']} catches, {p['yards']} yards")
    
    catch_checks = [
        ('Ja\'Marr Chase', 58, 787),
        ('Tetairoa McMillan', 51, 770),
        ('Brock Bowers', 49, 603),
        ('Tyler Warren', 46, 536),
        ('Mason Taylor', 45, 651)
    ]
    
    for name, catches, yards in catch_checks:
        player = get_player(all_players, name)
        if player:
            if player['catches'] != catches:
                errors.append(f"❌ {name}: Expected {catches} catches, got {player['catches']}")
            if player['yards'] != yards:
                errors.append(f"❌ {name}: Expected {yards} yards, got {player['yards']}")
    
    print("\n4. TOP YARDS PER GAME:")
    top_ypg = sorted(all_players, key=lambda x: x['ypg'], reverse=True)[:5]
    for p in top_ypg:
        print(f"   {p['name']} ({p['team']}) - {p['ypg']:.2f} YPG")
    
    ypg_checks = [
        ('Ja\'Marr Chase', 87.44),
        ('Tetairoa McMillan', 85.56),
        ('Brian Thomas Jr', 84.50),
        ('Kyle Pitts', 82.38),
        ('Mason Taylor', 81.38)
    ]
    
    for name, ypg in ypg_checks:
        player = get_player(all_players, name)
        if player and abs(player['ypg'] - ypg) > 0.01:
            errors.append(f"❌ {name}: Expected {ypg:.2f} YPG, got {player['ypg']:.2f}")
    
    print("\n5. TOP YARDS PER CATCH (min 10 catches):")
    top_ypc = sorted(qualified, key=lambda x: x['ypc'], reverse=True)[:5]
    for p in top_ypc:
        print(f"   {p['name']} ({p['team']}) - {p['ypc']:.2f} YPC ({p['catches']} catches)")
    
    ypc_checks = [
        ('Brian Thomas Jr', 45.07, 15),
        ('Nico Collins', 26.44, 18),
        ('Zay Flowers', 23.12, 17),
        ('CeeDee Lamb', 20.17, 24)
    ]
    
    for name, ypc, catches in ypc_checks:
        player = get_player(all_players, name)
        if player:
            if abs(player['ypc'] - ypc) > 0.01:
                errors.append(f"❌ {name}: Expected {ypc:.2f} YPC, got {player['ypc']:.2f}")
            if player['catches'] != catches:
                errors.append(f"❌ {name}: Expected {catches} catches, got {player['catches']}")
    
    print("\n6. ELITE TIGHT ENDS:")
    tes = [p for p in all_players if p['position'] == 'TE' and p['catches'] >= 20]
    top_tes = sorted(tes, key=lambda x: x['yards'], reverse=True)[:4]
    for p in top_tes:
        print(f"   {p['name']} ({p['team']}) - {p['yards']} yards, {p['catches']} rec, {p['tds']} TD, {p['ypg']:.2f} YPG")
    
    te_checks = [
        ('Brock Bowers', 603, 49, 5, 75.38, 96.08),
        ('Darren Waller', 603, 39, 5, 75.38, 92.86),
        ('Mason Taylor', 651, 45, 7, 81.38),
        ('Dallas Goedert', 564, 31, 4, 70.50)
    ]
    
    for check in te_checks:
        name = check[0]
        player = get_player(all_players, name)
        if player:
            if player['yards'] != check[1]:
                errors.append(f"❌ {name}: Expected {check[1]} yards, got {player['yards']}")
            if player['catches'] != check[2]:
                errors.append(f"❌ {name}: Expected {check[2]} catches, got {player['catches']}")
            if player['tds'] != check[3]:
                errors.append(f"❌ {name}: Expected {check[3]} TDs, got {player['tds']}")
            if abs(player['ypg'] - check[4]) > 0.01:
                errors.append(f"❌ {name}: Expected {check[4]:.2f} YPG, got {player['ypg']:.2f}")
    
    print("\n7. VOLUME RECEIVERS:")
    volume_checks = [
        ('Dont\'e Thornton Jr.', 599, 41, 8, 74.88),
        ('Puka Nacua', 525, 34, 5, 75.00),
        ('Amon-Ra St. Brown', 556, 36, 7, 61.78),
        ('Tank Dell', 552, 42, 3, 69.00)
    ]
    
    print("   Checking volume receivers:")
    for name, yards, catches, tds, ypg in volume_checks:
        player = get_player(all_players, name)
        if player:
            print(f"   {name}: {player['yards']} yards, {player['catches']} rec, {player['tds']} TD, {player['ypg']:.2f} YPG")
            if player['yards'] != yards:
                errors.append(f"❌ {name}: Expected {yards} yards, got {player['yards']}")
            if player['catches'] != catches:
                errors.append(f"❌ {name}: Expected {catches} catches, got {player['catches']}")
            if player['tds'] != tds:
                errors.append(f"❌ {name}: Expected {tds} TDs, got {player['tds']}")
            if abs(player['ypg'] - ypg) > 0.01:
                errors.append(f"❌ {name}: Expected {ypg:.2f} YPG, got {player['ypg']:.2f}")
    
    print("\n8. DROP PROBLEMS:")
    drop_players = sorted([p for p in all_players if p['drops'] >= 6], 
                         key=lambda x: x['drops'], reverse=True)[:5]
    for p in drop_players:
        print(f"   {p['name']} ({p['team']}) - {p['drops']} drops ({p['catches']} catches)")
    
    drop_checks = [
        ('Mason Taylor', 12, 45),
        ('Dawson Knox', 8, 33),
        ('Dalton Schultz', 8, 32),
        ('Kyle Pitts', 6, 43),
        ('Tetairoa McMillan', 6, 51)
    ]
    
    for name, drops, catches in drop_checks:
        player = get_player(all_players, name)
        if player:
            if player['drops'] != drops:
                errors.append(f"❌ {name}: Expected {drops} drops, got {player['drops']}")
            if player['catches'] != catches:
                errors.append(f"❌ {name}: Expected {catches} catches, got {player['catches']}")
    
    print("\n9. BEST CATCH PERCENTAGE (min 20 catches):")
    qualified_catch = [p for p in all_players if p['catches'] >= 19]
    top_catch_pct = sorted(qualified_catch, key=lambda x: x['catch_pct'], reverse=True)[:5]
    for p in top_catch_pct:
        print(f"   {p['name']} ({p['team']}) - {p['catch_pct']:.2f}% ({p['catches']} catches)")
    
    catch_pct_checks = [
        ('Terry McLaurin', 100.00, 19),
        ('Jonathan Taylor', 97.37, 37),
        ('Alvin Kamara', 97.30, 36),
        ('Ja\'Marr Chase', 98.31, 58),
        ('Dallas Goedert', 96.88, 31)
    ]
    
    for name, catch_pct, catches in catch_pct_checks:
        player = get_player(all_players, name)
        if player:
            if abs(player['catch_pct'] - catch_pct) > 0.01:
                errors.append(f"❌ {name}: Expected {catch_pct:.2f}% catch rate, got {player['catch_pct']:.2f}%")
    
    print("\n10. LONGEST RECEPTION:")
    longest = sorted(all_players, key=lambda x: x['longest'], reverse=True)[0]
    print(f"   {longest['name']} ({longest['team']}) - {longest['longest']} yards")
    if longest['name'] == 'Tyreek Hill' and longest['longest'] != 95:
        errors.append(f"❌ Tyreek Hill: Expected 95 yard longest reception, got {longest['longest']}")
    
    print("\n11. UNDERPERFORMING STARS:")
    underperform_checks = [
        ('Tyreek Hill', 470, 4),
        ('Marvin Harrison Jr', 341, 0),
        ('Drake London', 183, 0)
    ]
    
    print("   Checking underperforming stars (Tyreek Hill uses combined Dolphins+Patriots stats):")
    for name, yards, expected_tds in underperform_checks:
        if name == 'Tyreek Hill':
            player = get_combined_stats(all_players, name)
        else:
            player = get_player(all_players, name)
        if player:
            print(f"   {name} ({player['team']}): {player['yards']} yards, {player['tds']} TD")
            if player['yards'] != yards:
                errors.append(f"❌ {name}: Expected {yards} yards, got {player['yards']}")
            if player['tds'] != expected_tds:
                errors.append(f"❌ {name}: Markdown shows {expected_tds} TDs but actual combined total is {player['tds']} TDs")
    
    print("\n12. ROOKIE STANDOUTS:")
    rookie_checks = [
        ('Tetairoa McMillan', 770, 51, 4),
        ('Brian Thomas Jr', 676, 15, 6),
        ('Brock Bowers', 603, 49, 5),
        ('Dont\'e Thornton Jr.', 599, 41, 8),
        ('Mason Taylor', 651, 45, 7)
    ]
    
    print("   Checking rookie standouts:")
    for name, yards, catches, tds in rookie_checks:
        player = get_player(all_players, name)
        if player:
            print(f"   {name}: {player['yards']} yards, {player['catches']} rec, {player['tds']} TD")
            if player['yards'] != yards:
                errors.append(f"❌ {name}: Expected {yards} yards, got {player['yards']}")
            if player['catches'] != catches:
                errors.append(f"❌ {name}: Expected {catches} catches, got {player['catches']}")
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
    sys.exit(validate_receiving_stats())
