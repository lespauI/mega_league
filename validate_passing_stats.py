#!/usr/bin/env python3
import csv
import sys

def get_player(players, name):
    for p in players:
        if p['name'] == name:
            return p
    return None

def validate_passing_stats():
    players = []
    with open('MEGA_passing.csv', 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row['player__position'] == 'QB' and float(row['passTotalAtt']) >= 150:
                players.append({
                    'name': row['player__fullName'],
                    'team': row['team__abbrName'],
                    'yards': int(row['passTotalYds']),
                    'ypg': float(row['passAvgYdsPerGame']),
                    'tds': int(row['passTotalTDs']),
                    'ints': int(row['passTotalInts']),
                    'rating': float(row['passerAvgRating']),
                    'comp_pct': float(row['passAvgCompPct']),
                    'ypa': float(row['passAvgYdsPerAtt']),
                    'sacks': int(row['passTotalSacks']),
                    'attempts': int(row['passTotalAtt']),
                    'completions': int(row['passTotalComp']),
                    'longest': int(row['passTotalLongest'])
                })
    
    errors = []
    
    print("=" * 80)
    print("VALIDATING PASSING STATISTICS")
    print("=" * 80)
    
    print("\n1. TOP PASSING YARDS:")
    top_yards = sorted(players, key=lambda x: x['yards'], reverse=True)[:5]
    for p in top_yards:
        print(f"   {p['name']} ({p['team']}) - {p['yards']} yards, {p['ypg']:.2f} YPG")
    
    expected = [
        ('Justin Fields', 2519, 314.88),
        ('Cam Ward', 2273, 252.56),
        ('Joe Burrow', 2249, 249.89),
        ('Jayden Daniels', 2207, 245.22),
        ('C.J. Stroud', 2029, 253.63)
    ]
    
    for name, yards, ypg in expected:
        player = get_player(players, name)
        if player is None:
            errors.append(f"❌ {name} not found in data")
        else:
            if player['yards'] != yards:
                errors.append(f"❌ {name}: Expected {yards} yards, got {player['yards']}")
            if abs(player['ypg'] - ypg) > 0.01:
                errors.append(f"❌ {name}: Expected {ypg:.2f} YPG, got {player['ypg']:.2f}")
    
    print("\n2. TOP PASSING TOUCHDOWNS:")
    top_tds = sorted(players, key=lambda x: x['tds'], reverse=True)[:8]
    for p in top_tds:
        print(f"   {p['name']} ({p['team']}) - {p['tds']} TD")
    
    td_checks = [
        ('Justin Fields', 26),
        ('Joe Burrow', 18),
        ('Cam Ward', 18),
        ('C.J. Stroud', 18),
        ('Sam Darnold', 18),
        ('Jared Goff', 18),
        ('Joe Milton III', 18),
        ('Bryce Young', 18)
    ]
    
    for name, tds in td_checks:
        player = get_player(players, name)
        if player and player['tds'] != tds:
            errors.append(f"❌ {name}: Expected {tds} TDs, got {player['tds']}")
    
    print("\n3. TOP PASSER RATING:")
    top_rating = sorted(players, key=lambda x: x['rating'], reverse=True)[:5]
    for p in top_rating:
        print(f"   {p['name']} ({p['team']}) - {p['rating']:.2f}")
    
    rating_checks = [
        ('Joe Milton III', 113.30),
        ('Matthew Stafford', 107.76),
        ('Sam Darnold', 107.75),
        ('Caleb Williams', 107.15),
        ('Jared Goff', 105.56)
    ]
    
    for name, rating in rating_checks:
        player = get_player(players, name)
        if player and abs(player['rating'] - rating) > 0.01:
            errors.append(f"❌ {name}: Expected {rating:.2f} rating, got {player['rating']:.2f}")
    
    print("\n4. TOP COMPLETION PERCENTAGE:")
    top_comp = sorted(players, key=lambda x: x['comp_pct'], reverse=True)[:5]
    for p in top_comp:
        print(f"   {p['name']} ({p['team']}) - {p['comp_pct']:.2f}%")
    
    comp_checks = [
        ('Joe Milton III', 72.20),
        ('Caleb Williams', 71.57),
        ('Matthew Stafford', 69.95),
        ('Jared Goff', 69.57),
        ('Sam Darnold', 68.40)
    ]
    
    for name, comp_pct in comp_checks:
        player = get_player(players, name)
        if player and abs(player['comp_pct'] - comp_pct) > 0.01:
            errors.append(f"❌ {name}: Expected {comp_pct:.2f}% completion, got {player['comp_pct']:.2f}%")
    
    print("\n5. TOP YARDS PER ATTEMPT:")
    top_ypa = sorted(players, key=lambda x: x['ypa'], reverse=True)[:5]
    for p in top_ypa:
        print(f"   {p['name']} ({p['team']}) - {p['ypa']:.2f} YPA")
    
    ypa_checks = [
        ('Dak Prescott', 10.46),
        ('Trevor Lawrence', 9.86),
        ('Cam Ward', 9.51),
        ('Lamar Jackson', 9.45),
        ('Bo Nix', 9.07)
    ]
    
    for name, ypa in ypa_checks:
        player = get_player(players, name)
        if player and abs(player['ypa'] - ypa) > 0.01:
            errors.append(f"❌ {name}: Expected {ypa:.2f} YPA, got {player['ypa']:.2f}")
    
    print("\n6. MOST INTERCEPTIONS:")
    top_ints = sorted(players, key=lambda x: x['ints'], reverse=True)[:5]
    for p in top_ints:
        print(f"   {p['name']} ({p['team']}) - {p['ints']} INT")
    
    int_checks = [
        ('Tua Tagovailoa', 24),
        ('Kyler Murray', 24),
        ('Bryce Young', 22),
        ('Anthony Richardson Sr', 21),
        ('Justin Fields', 21)
    ]
    
    for name, ints in int_checks:
        player = get_player(players, name)
        if player and player['ints'] != ints:
            errors.append(f"❌ {name}: Expected {ints} INTs, got {player['ints']}")
    
    print("\n7. MOST SACKS:")
    top_sacks = sorted(players, key=lambda x: x['sacks'], reverse=True)[:6]
    for p in top_sacks:
        print(f"   {p['name']} ({p['team']}) - {p['sacks']} sacks")
    
    sack_checks = [
        ('Kyler Murray', 42),
        ('Bryce Young', 22),
        ('Caleb Williams', 20),
        ('Jalen Hurts', 20),
        ('Drake Maye', 19),
        ('Jared Goff', 19)
    ]
    
    for name, sacks in sack_checks:
        player = get_player(players, name)
        if player and player['sacks'] != sacks:
            errors.append(f"❌ {name}: Expected {sacks} sacks, got {player['sacks']}")
    
    print("\n8. PROBLEMATIC QBS:")
    problem_qbs = [
        ('Kyler Murray', {'comp_pct': 43.28, 'rating': 35.53, 'ints': 24, 'tds': 4}),
        ('Josh Allen', {'comp_pct': 53.67, 'rating': 68.03, 'ints': 19}),
        ('Anthony Richardson Sr', {'rating': 69.69, 'ints': 21}),
        ('Aaron Rodgers', {'rating': 70.98, 'ints': 9})
    ]
    
    for name, stats in problem_qbs:
        player = get_player(players, name)
        if player:
            print(f"   {name}:")
            if 'comp_pct' in stats:
                print(f"      Completion: {player['comp_pct']:.2f}% (expected {stats['comp_pct']:.2f}%)")
                if abs(player['comp_pct'] - stats['comp_pct']) > 0.01:
                    errors.append(f"❌ {name}: Expected {stats['comp_pct']:.2f}% completion, got {player['comp_pct']:.2f}%")
            if 'rating' in stats:
                print(f"      Rating: {player['rating']:.2f} (expected {stats['rating']:.2f})")
                if abs(player['rating'] - stats['rating']) > 0.01:
                    errors.append(f"❌ {name}: Expected {stats['rating']:.2f} rating, got {player['rating']:.2f}")
            if 'ints' in stats:
                print(f"      INTs: {player['ints']} (expected {stats['ints']})")
                if player['ints'] != stats['ints']:
                    errors.append(f"❌ {name}: Expected {stats['ints']} INTs, got {player['ints']}")
            if 'tds' in stats:
                print(f"      TDs: {player['tds']} (expected {stats['tds']})")
                if player['tds'] != stats['tds']:
                    errors.append(f"❌ {name}: Expected {stats['tds']} TDs, got {player['tds']}")
    
    print("\n9. LONGEST PASS:")
    all_players = []
    with open('MEGA_passing.csv', 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if int(row['passTotalLongest']) > 0:
                all_players.append({
                    'name': row['player__fullName'],
                    'team': row['team__abbrName'],
                    'longest': int(row['passTotalLongest'])
                })
    longest = sorted(all_players, key=lambda x: x['longest'], reverse=True)[0]
    print(f"   {longest['name']} ({longest['team']}) - {longest['longest']} yards")
    if longest['name'] == 'Drake Maye' and longest['longest'] != 95:
        errors.append(f"❌ Drake Maye: Expected 95 yard longest pass, got {longest['longest']}")
    
    print("\n10. MOST ATTEMPTS:")
    top_att = sorted(players, key=lambda x: x['attempts'], reverse=True)[0]
    print(f"   {top_att['name']} ({top_att['team']}) - {top_att['attempts']} attempts")
    
    print("\n11. MOST COMPLETIONS:")
    top_comp_total = sorted(players, key=lambda x: x['completions'], reverse=True)[0]
    print(f"   {top_comp_total['name']} ({top_comp_total['team']}) - {top_comp_total['completions']} completions")
    if top_comp_total['name'] == 'Justin Fields' and top_comp_total['completions'] != 184:
        errors.append(f"❌ Justin Fields: Expected 184 completions, got {top_comp_total['completions']}")
    
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
    sys.exit(validate_passing_stats())
