#!/usr/bin/env python3
import csv
from collections import defaultdict

csv_file = 'MEGA_defense.csv'

team_data = defaultdict(lambda: {
    'team_name': '',
    'total_ints': 0,
    'players_with_ints': 0,
    'players': []
})

with open(csv_file, 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    for row in reader:
        team_abbr = row['team__abbrName']
        team_name = row['team__displayName']
        player_name = row['player__fullName']
        position = row['player__position']
        ints = int(row['defTotalInts']) if row['defTotalInts'] else 0
        int_yards = int(row['defTotalIntReturnYds']) if row['defTotalIntReturnYds'] else 0
        int_tds = int(row['defTotalTDs']) if row['defTotalTDs'] else 0
        
        team_data[team_abbr]['team_name'] = team_name
        team_data[team_abbr]['total_ints'] += ints
        
        if ints > 0:
            team_data[team_abbr]['players_with_ints'] += 1
            team_data[team_abbr]['players'].append({
                'name': player_name,
                'position': position,
                'ints': ints,
                'yards': int_yards,
                'tds': int_tds
            })

print("=" * 100)
print("АНАЛИЗ ПЕРЕХВАТОВ ПО КОМАНДАМ - MEGA NEONSPORTZ LEAGUE")
print("=" * 100)
print()

print("=" * 100)
print("РЕЙТИНГ ПО РАЗНООБРАЗИЮ (количество игроков с перехватами)")
print("=" * 100)
sorted_by_diversity = sorted(team_data.items(), 
                             key=lambda x: (x[1]['players_with_ints'], x[1]['total_ints']), 
                             reverse=True)

for rank, (team_abbr, data) in enumerate(sorted_by_diversity, 1):
    if data['players_with_ints'] > 0:
        print(f"{rank:2d}. {data['team_name']:20s} ({team_abbr:3s}) - "
              f"{data['players_with_ints']:2d} игроков, {data['total_ints']:3d} INT всего")

print()
print("=" * 100)
print("РЕЙТИНГ ПО ОБЩЕМУ КОЛИЧЕСТВУ ПЕРЕХВАТОВ")
print("=" * 100)

sorted_by_total = sorted(team_data.items(), 
                        key=lambda x: (x[1]['total_ints'], x[1]['players_with_ints']), 
                        reverse=True)

for rank, (team_abbr, data) in enumerate(sorted_by_total, 1):
    if data['total_ints'] > 0:
        avg = data['total_ints'] / data['players_with_ints'] if data['players_with_ints'] > 0 else 0
        print(f"{rank:2d}. {data['team_name']:20s} ({team_abbr:3s}) - "
              f"{data['total_ints']:3d} INT, {data['players_with_ints']:2d} игроков (сред. {avg:.1f} на игрока)")

print()
print("=" * 100)
print("ДЕТАЛЬНАЯ СТАТИСТИКА ПО КОМАНДАМ (топ-10 по разнообразию)")
print("=" * 100)

for rank, (team_abbr, data) in enumerate(sorted_by_diversity[:10], 1):
    print()
    print(f"{rank}. {data['team_name'].upper()} ({team_abbr}) - {data['players_with_ints']} игроков, {data['total_ints']} INT")
    print("-" * 100)
    
    sorted_players = sorted(data['players'], key=lambda x: (x['ints'], x['yards']), reverse=True)
    
    for p in sorted_players:
        td_str = f", {p['tds']} TD" if p['tds'] > 0 else ""
        print(f"  • {p['name']:30s} {p['position']:6s} - {p['ints']:2d} INT, {p['yards']:4d} ярдов{td_str}")

print()
print("=" * 100)
print("СТАТИСТИКА ПО ПОЗИЦИЯМ (топ-3 команды)")
print("=" * 100)

for rank, (team_abbr, data) in enumerate(sorted_by_diversity[:3], 1):
    positions = defaultdict(int)
    for p in data['players']:
        positions[p['position']] += 1
    
    print(f"\n{rank}. {data['team_name']} ({team_abbr}):")
    sorted_positions = sorted(positions.items(), key=lambda x: x[1], reverse=True)
    pos_str = ", ".join([f"{pos}: {count}" for pos, count in sorted_positions])
    print(f"   Позиции: {pos_str}")

print()
