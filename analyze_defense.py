#!/usr/bin/env python3
import csv
from collections import defaultdict

def load_defense_data(csv_file):
    players = []
    with open(csv_file, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            player = {
                'name': row['player__fullName'],
                'team': row['team__abbrName'],
                'position': row['player__position'],
                'games': float(row['gamesPlayed']) if row['gamesPlayed'] else 0,
                'fantasy_points': float(row['fantasy_points']) if row['fantasy_points'] else 0,
                'tackles': float(row['defTotalTackles']) if row['defTotalTackles'] else 0,
                'sacks': float(row['defTotalSacks']) if row['defTotalSacks'] else 0,
                'ints': float(row['defTotalInts']) if row['defTotalInts'] else 0,
                'int_yards': float(row['defTotalIntReturnYds']) if row['defTotalIntReturnYds'] else 0,
                'forced_fumbles': float(row['defTotalForcedFum']) if row['defTotalForcedFum'] else 0,
                'fumble_rec': float(row['defTotalFumRec']) if row['defTotalFumRec'] else 0,
                'deflections': float(row['defTotalDeflections']) if row['defTotalDeflections'] else 0,
                'tds': float(row['defTotalTDs']) if row['defTotalTDs'] else 0,
                'safeties': float(row['defTotalSafeties']) if row['defTotalSafeties'] else 0,
                'years_pro': int(row['player__yearsPro']) if row['player__yearsPro'] else 0
            }
            players.append(player)
    return players

def analyze_defense(players):
    results = {}
    
    # Forced Fumbles Leaders
    ff_leaders = sorted(players, key=lambda x: (-x['forced_fumbles'], -x['tackles']))[:5]
    results['forced_fumbles'] = ff_leaders
    
    # Interceptions Leaders
    int_leaders = sorted(players, key=lambda x: (-x['ints'], -x['int_yards']))[:7]
    results['interceptions'] = int_leaders
    
    # Pick-Six Kings (by INT return yards)
    pick_six = sorted([p for p in players if p['int_yards'] > 0], 
                     key=lambda x: -x['int_yards'])[:5]
    results['pick_six'] = pick_six
    
    # Sacks Leaders
    sack_leaders = sorted(players, key=lambda x: (-x['sacks'], -x['tackles']))[:7]
    results['sacks'] = sack_leaders
    
    # Deflections Leaders
    def_leaders = sorted(players, key=lambda x: (-x['deflections'], -x['tackles']))[:5]
    results['deflections'] = def_leaders
    
    # Tackles Leaders
    tackle_leaders = sorted(players, key=lambda x: (-x['tackles'], -x['ints']))[:6]
    results['tackles'] = tackle_leaders
    
    # Fantasy Points Leaders
    fp_leaders = sorted(players, key=lambda x: -x['fantasy_points'])[:10]
    results['fantasy_points'] = fp_leaders
    
    # Per Game Stats
    qualified = [p for p in players if p['games'] >= 6]
    results['tackles_per_game'] = sorted(qualified, 
                                        key=lambda x: -x['tackles']/x['games'])[:5]
    results['sacks_per_game'] = sorted([p for p in players if p['games'] >= 5], 
                                       key=lambda x: -x['sacks']/x['games'])[:5]
    results['ints_per_game'] = sorted([p for p in players if p['games'] >= 5], 
                                      key=lambda x: -x['ints']/x['games'])[:5]
    
    # Team defense stats
    team_stats = defaultdict(lambda: {'tackles': 0, 'sacks': 0, 'ints': 0, 'players': []})
    for p in players:
        team_stats[p['team']]['tackles'] += p['tackles']
        team_stats[p['team']]['sacks'] += p['sacks']
        team_stats[p['team']]['ints'] += p['ints']
        team_stats[p['team']]['players'].append(p)
    
    results['team_stats'] = team_stats
    
    # Rookies (yearsPro == 0)
    rookies = [p for p in players if p['years_pro'] == 0]
    rookie_sacks = sorted(rookies, key=lambda x: -x['sacks'])[:3]
    rookie_ints = sorted(rookies, key=lambda x: -x['ints'])[:3]
    results['rookie_sacks'] = rookie_sacks
    results['rookie_ints'] = rookie_ints
    
    return results

def write_markdown(results, filename, lang='en'):
    with open(filename, 'w') as f:
        if lang == 'en':
            f.write("# 🛡️ MEGA Neonsportz - Defensive Statistics Analysis\n\n")
            f.write("## 🏆 League Leaders\n\n")
            
            # Forced Fumbles
            f.write("### Forced Fumble Leaders\n")
            for i, p in enumerate(results['forced_fumbles'], 1):
                extra = []
                if p['tackles'] > 0:
                    extra.append(f"{int(p['tackles'])} tackles")
                if p['ints'] > 0:
                    extra.append(f"{int(p['ints'])} INT")
                extra_str = ", " + ", ".join(extra) if extra else ""
                f.write(f"{i}. **{p['name']}** ({p['team']}) - {int(p['forced_fumbles'])} forced fumbles{extra_str}\n")
            f.write("\n")
            
            # Interceptions
            f.write("### Interception Leaders\n")
            for i, p in enumerate(results['interceptions'], 1):
                extra = []
                if p['int_yards'] > 0:
                    extra.append(f"{int(p['int_yards'])} return yards")
                if p['tds'] > 0:
                    extra.append(f"{int(p['tds'])} TD")
                extra_str = ", " + ", ".join(extra) if extra else ""
                f.write(f"{i}. **{p['name']}** ({p['team']}) - {int(p['ints'])} INTs{extra_str}\n")
            f.write("\n")
            
            # Pick-Six Kings
            f.write("### Pick-Six Kings\n")
            for i, p in enumerate(results['pick_six'], 1):
                td_str = f", {int(p['tds'])} TD" if p['tds'] > 0 else ""
                f.write(f"{i}. **{p['name']}** ({p['team']}) - {int(p['ints'])} INTs, {int(p['int_yards'])} return yards{td_str}\n")
            f.write("\n")
            
            # Sacks
            f.write("### Sack Leaders\n")
            for i, p in enumerate(results['sacks'], 1):
                f.write(f"{i}. **{p['name']}** ({p['team']}) - {p['sacks']} sacks, {int(p['tackles'])} tackles\n")
            f.write("\n")
            
            # Deflections
            f.write("### Deflection Leaders\n")
            for i, p in enumerate(results['deflections'], 1):
                int_str = f", {int(p['ints'])} INTs" if p['ints'] > 0 else ""
                f.write(f"{i}. **{p['name']}** ({p['team']}) - {int(p['deflections'])} deflections, {int(p['tackles'])} tackles{int_str}\n")
            f.write("\n")
            
            # Tackles
            f.write("### Total Tackles\n")
            for i, p in enumerate(results['tackles'], 1):
                extra = []
                if p['ints'] > 0:
                    extra.append(f"{int(p['ints'])} INTs")
                if p['sacks'] > 0:
                    extra.append(f"{p['sacks']} sacks")
                if p['tds'] > 0:
                    extra.append(f"{int(p['tds'])} TDs")
                extra_str = ", " + ", ".join(extra) if extra else ""
                f.write(f"{i}. **{p['name']}** ({p['team']}) - {int(p['tackles'])} tackles{extra_str}\n")
            f.write("\n")
            
        else:  # Russian
            f.write("# 🛡️ MEGA Neonsportz - Анализ Защитной Статистики\n\n")
            f.write("## 🏆 Лидеры Лиги\n\n")
            
            # Forced Fumbles
            f.write("### Лидеры по Forced Fumbles\n")
            for i, p in enumerate(results['forced_fumbles'], 1):
                extra = []
                if p['tackles'] > 0:
                    extra.append(f"{int(p['tackles'])} tackles")
                if p['ints'] > 0:
                    extra.append(f"{int(p['ints'])} INT")
                extra_str = ", " + ", ".join(extra) if extra else ""
                f.write(f"{i}. **{p['name']}** ({p['team']}) - {int(p['forced_fumbles'])} forced fumbles{extra_str}\n")
            f.write("\n")
            
            # Interceptions
            f.write("### Лидеры по Interceptions\n")
            for i, p in enumerate(results['interceptions'], 1):
                extra = []
                if p['int_yards'] > 0:
                    extra.append(f"{int(p['int_yards'])} return yards")
                if p['tds'] > 0:
                    extra.append(f"{int(p['tds'])} TD")
                extra_str = ", " + ", ".join(extra) if extra else ""
                f.write(f"{i}. **{p['name']}** ({p['team']}) - {int(p['ints'])} INTs{extra_str}\n")
            f.write("\n")
            
            # Pick-Six Kings
            f.write("### Короли Pick-Six\n")
            for i, p in enumerate(results['pick_six'], 1):
                td_str = f", {int(p['tds'])} TD" if p['tds'] > 0 else ""
                f.write(f"{i}. **{p['name']}** ({p['team']}) - {int(p['ints'])} INTs, {int(p['int_yards'])} return yards{td_str}\n")
            f.write("\n")
            
            # Sacks
            f.write("### Лидеры по Sacks\n")
            for i, p in enumerate(results['sacks'], 1):
                f.write(f"{i}. **{p['name']}** ({p['team']}) - {p['sacks']} sacks, {int(p['tackles'])} tackles\n")
            f.write("\n")
            
            # Deflections
            f.write("### Лидеры по Deflections\n")
            for i, p in enumerate(results['deflections'], 1):
                int_str = f", {int(p['ints'])} INTs" if p['ints'] > 0 else ""
                f.write(f"{i}. **{p['name']}** ({p['team']}) - {int(p['deflections'])} deflections, {int(p['tackles'])} tackles{int_str}\n")
            f.write("\n")
            
            # Tackles
            f.write("### Лидеры по Tackles\n")
            for i, p in enumerate(results['tackles'], 1):
                extra = []
                if p['ints'] > 0:
                    extra.append(f"{int(p['ints'])} INTs")
                if p['sacks'] > 0:
                    extra.append(f"{p['sacks']} sacks")
                if p['tds'] > 0:
                    extra.append(f"{int(p['tds'])} TDs")
                extra_str = ", " + ", ".join(extra) if extra else ""
                f.write(f"{i}. **{p['name']}** ({p['team']}) - {int(p['tackles'])} tackles{extra_str}\n")
            f.write("\n")

if __name__ == '__main__':
    print("Loading defense data...")
    players = load_defense_data('MEGA_defense.csv')
    
    print(f"Loaded {len(players)} defensive players")
    
    print("Analyzing statistics...")
    results = analyze_defense(players)
    
    print("Writing markdown files...")
    write_markdown(results, 'defense_analysis.md', 'en')
    write_markdown(results, 'defense_analysis_ru.md', 'ru')
    
    print("✅ Analysis complete!")
    print("\nTop 5 in each category:")
    print("\n=== FORCED FUMBLES ===")
    for p in results['forced_fumbles']:
        print(f"{p['name']} ({p['team']}) - {int(p['forced_fumbles'])} FF")
    
    print("\n=== INTERCEPTIONS ===")
    for p in results['interceptions'][:5]:
        print(f"{p['name']} ({p['team']}) - {int(p['ints'])} INTs, {int(p['int_yards'])} yards")
    
    print("\n=== SACKS ===")
    for p in results['sacks'][:5]:
        print(f"{p['name']} ({p['team']}) - {p['sacks']} sacks")
    
    print("\n=== TACKLES ===")
    for p in results['tackles'][:5]:
        print(f"{p['name']} ({p['team']}) - {int(p['tackles'])} tackles")
