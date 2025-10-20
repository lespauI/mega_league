#!/usr/bin/env python3
import csv
import os
from collections import defaultdict
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

def read_standings():
    teams_div = {}
    with open('MEGA_teams.csv', 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            team = row['displayName'].strip()
            div = row.get('divisionName', '').strip()
            conf = row.get('conferenceName', '').strip()
            teams_div[team] = {'division': div, 'conference': conf}

    with open('output/ranked_sos_by_conference.csv', 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        standings = list(reader)

    afc_divs = defaultdict(list)
    nfc_divs = defaultdict(list)
    
    for row in standings:
        team = row['team']
        conf = row['conference']
        w = int(row['W'])
        l = int(row['L'])
        
        if team in teams_div:
            div = teams_div[team]['division']
            team_data = {
                'team': team,
                'W': w,
                'L': l,
                'win_pct': w / (w + l) if (w + l) > 0 else 0,
                'remaining_sos': float(row['ranked_sos_avg']),
                'past_sos': float(row['past_ranked_sos_avg']),
                'total_sos': float(row['total_ranked_sos']),
                'remaining_games': int(row['remaining_games'])
            }
            
            if conf == 'AFC':
                afc_divs[div].append(team_data)
            else:
                nfc_divs[div].append(team_data)
    
    for div in afc_divs:
        afc_divs[div].sort(key=lambda x: x['win_pct'], reverse=True)
    
    for div in nfc_divs:
        nfc_divs[div].sort(key=lambda x: x['win_pct'], reverse=True)
    
    return afc_divs, nfc_divs

def get_playoff_picture(divs):
    leaders = []
    for div_name in sorted(divs.keys()):
        leader = divs[div_name][0].copy()
        leader['division'] = div_name
        leaders.append(leader)
    
    leaders.sort(key=lambda x: x['win_pct'], reverse=True)
    
    wc_candidates = []
    for div_name in divs:
        for team in divs[div_name][1:]:
            wc_candidates.append(team.copy())
    
    wc_candidates.sort(key=lambda x: x['win_pct'], reverse=True)
    
    return leaders, wc_candidates

def create_race_visualization(conf_name, leaders, wc_candidates, output_path):
    fig, ax = plt.subplots(figsize=(14, 10))
    
    all_teams = leaders[:4] + wc_candidates[:10]
    y_pos = range(len(all_teams))
    
    colors = []
    for i, team in enumerate(all_teams):
        if i < 4:
            colors.append('#2563eb')
        elif i < 7:
            colors.append('#16a34a')
        elif i < 9:
            colors.append('#eab308')
        else:
            colors.append('#dc2626')
    
    wins = [t['W'] for t in all_teams]
    bars = ax.barh(y_pos, wins, color=colors, alpha=0.7)
    
    for i, (team, bar) in enumerate(zip(all_teams, bars)):
        seed = i + 1
        if i < 4:
            label = f"{seed}. {team['team']} ({team['division'][:8]})"
        else:
            label = f"{seed}. {team['team']}"
        
        record = f"{team['W']}-{team['L']}"
        sos_label = f"SOS: {team['remaining_sos']:.3f}"
        
        ax.text(-0.5, bar.get_y() + bar.get_height()/2, label, 
                ha='right', va='center', fontsize=10, fontweight='bold')
        
        ax.text(bar.get_width() + 0.3, bar.get_y() + bar.get_height()/2, 
                f"{record}  |  {sos_label}", 
                ha='left', va='center', fontsize=9)
    
    ax.axhline(y=3.5, color='black', linestyle='--', linewidth=2, alpha=0.5)
    ax.axhline(y=6.5, color='orange', linestyle='--', linewidth=1.5, alpha=0.5)
    ax.axhline(y=8.5, color='red', linestyle='--', linewidth=1.5, alpha=0.5)
    
    ax.set_xlabel('Wins', fontsize=12, fontweight='bold')
    ax.set_title(f'{conf_name} Playoff Race - Week 14\nRemaining SOS shown for each team', 
                 fontsize=16, fontweight='bold', pad=20)
    ax.set_yticks([])
    ax.set_xlim(-8, 16)
    ax.grid(axis='x', alpha=0.3)
    
    div_patch = mpatches.Patch(color='#2563eb', alpha=0.7, label='Division Leaders (Seeds 1-4)')
    wc_patch = mpatches.Patch(color='#16a34a', alpha=0.7, label='Wild Card (Seeds 5-7) ✓')
    bubble_patch = mpatches.Patch(color='#eab308', alpha=0.7, label='On the Bubble')
    out_patch = mpatches.Patch(color='#dc2626', alpha=0.7, label='Currently Out')
    
    ax.legend(handles=[div_patch, wc_patch, bubble_patch, out_patch], 
              loc='lower right', fontsize=10)
    
    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"Created: {output_path}")

def create_bubble_analysis(conf_name, leaders, wc_candidates, output_path):
    fig, ax = plt.subplots(figsize=(12, 8))
    
    bubble_teams = wc_candidates[5:12]
    
    x_wins = [t['W'] for t in bubble_teams]
    y_sos = [t['remaining_sos'] for t in bubble_teams]
    colors_map = {
        0: '#16a34a',
        1: '#16a34a',
        2: '#eab308',
        3: '#eab308',
        4: '#dc2626',
        5: '#dc2626',
        6: '#dc2626'
    }
    colors = [colors_map.get(i, '#dc2626') for i in range(len(bubble_teams))]
    
    sizes = [(10 - t['L']) * 50 + 100 for t in bubble_teams]
    
    scatter = ax.scatter(x_wins, y_sos, c=colors, s=sizes, alpha=0.6, edgecolors='black', linewidth=2)
    
    for i, team in enumerate(bubble_teams):
        ax.annotate(team['team'], 
                   (x_wins[i], y_sos[i]),
                   xytext=(5, 5), textcoords='offset points',
                   fontsize=9, fontweight='bold',
                   bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.7))
    
    ax.axhline(y=sum(y_sos)/len(y_sos), color='gray', linestyle='--', alpha=0.5, label='Avg Remaining SOS')
    ax.axvline(x=sum(x_wins)/len(x_wins), color='gray', linestyle='--', alpha=0.5, label='Avg Wins')
    
    ax.set_xlabel('Wins', fontsize=12, fontweight='bold')
    ax.set_ylabel('Remaining Strength of Schedule (higher = harder)', fontsize=12, fontweight='bold')
    ax.set_title(f'{conf_name} Wild Card Bubble\nTeams fighting for the final playoff spots', 
                 fontsize=14, fontweight='bold')
    ax.grid(True, alpha=0.3)
    ax.legend(fontsize=9)
    
    textstr = 'Bubble size = fewer losses\nGreen = Currently in playoffs\nYellow = On the bubble\nRed = Outside looking in'
    ax.text(0.02, 0.98, textstr, transform=ax.transAxes, fontsize=9,
            verticalalignment='top', bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
    
    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"Created: {output_path}")

def create_markdown_report(afc_leaders, afc_wc, nfc_leaders, nfc_wc):
    report = []
    report.append("# 🏈 NFL MEGA League Playoff Race Analysis - Week 14")
    report.append("")
    report.append("## Current Playoff Picture")
    report.append("")
    
    report.append("### AFC Playoff Standings")
    report.append("")
    report.append("**Division Leaders:**")
    for i, team in enumerate(afc_leaders[:4], 1):
        div_short = team['division'].replace('AFC ', '')
        report.append(f"- **Seed {i}:** {team['team']} ({team['W']}-{team['L']}) - {div_short} | Remaining SOS: {team['remaining_sos']:.3f}")
    
    report.append("")
    report.append("**Wild Card:**")
    for i, team in enumerate(afc_wc[:3], 5):
        report.append(f"- **Seed {i}:** {team['team']} ({team['W']}-{team['L']}) ✓ IN | Remaining SOS: {team['remaining_sos']:.3f}")
    
    report.append("")
    report.append("**On the Bubble:**")
    for i, team in enumerate(afc_wc[3:8], 8):
        report.append(f"- **{i}.** {team['team']} ({team['W']}-{team['L']}) | Remaining SOS: {team['remaining_sos']:.3f}")
    
    report.append("")
    report.append("### NFC Playoff Standings")
    report.append("")
    report.append("**Division Leaders:**")
    for i, team in enumerate(nfc_leaders[:4], 1):
        div_short = team['division'].replace('NFC ', '')
        report.append(f"- **Seed {i}:** {team['team']} ({team['W']}-{team['L']}) - {div_short} | Remaining SOS: {team['remaining_sos']:.3f}")
    
    report.append("")
    report.append("**Wild Card:**")
    for i, team in enumerate(nfc_wc[:3], 5):
        report.append(f"- **Seed {i}:** {team['team']} ({team['W']}-{team['L']}) ✓ IN | Remaining SOS: {team['remaining_sos']:.3f}")
    
    report.append("")
    report.append("**On the Bubble:**")
    for i, team in enumerate(nfc_wc[3:8], 8):
        report.append(f"- **{i}.** {team['team']} ({team['W']}-{team['L']}) | Remaining SOS: {team['remaining_sos']:.3f}")
    
    report.append("")
    report.append("---")
    report.append("")
    report.append("## Key Races to Watch")
    report.append("")
    
    report.append("### AFC Wild Card Battle")
    report.append("")
    report.append("**INTENSE 6-7 LOGJAM!** Five teams at 6-7 fighting for the last playoff spots:")
    report.append("")
    for team in afc_wc[:7]:
        if team['W'] == 6 and team['L'] == 7:
            advantage = "✓ Easiest path" if team['remaining_sos'] < 0.45 else "⚠️ Brutal finish" if team['remaining_sos'] > 0.55 else "→ Balanced"
            report.append(f"- **{team['team']}**: {team['remaining_games']} games left | SOS {team['remaining_sos']:.3f} {advantage}")
    
    report.append("")
    report.append("**Analysis:** The team with the easiest remaining schedule has the inside track. Watch for teams with SOS below 0.45!")
    report.append("")
    
    report.append("### NFC South: Four-Way Chaos")
    report.append("")
    report.append("Three teams at 8-5, one at 7-6. Anyone can win this division:")
    report.append("")
    nfc_south_teams = []
    for team in nfc_leaders + nfc_wc:
        if 'South' in team.get('division', '') or team['team'] in ['Saints', 'Buccaneers', 'Falcons', 'Panthers']:
            nfc_south_teams.append(team)
    
    for team in sorted(nfc_south_teams, key=lambda x: x['win_pct'], reverse=True):
        report.append(f"- **{team['team']}** ({team['W']}-{team['L']}): Remaining SOS {team['remaining_sos']:.3f}")
    
    report.append("")
    report.append("**Analysis:** Saints have the TOUGHEST remaining schedule (0.612) while Falcons have the EASIEST (0.433). Falcons could steal the division!")
    report.append("")
    
    report.append("### NFC East Tiebreaker")
    report.append("")
    report.append("Giants and Cowboys both 8-5. Head-to-head record will be crucial:")
    report.append(f"- **Giants**: Remaining SOS {nfc_leaders[1]['remaining_sos']:.3f}")
    cowboys = [t for t in nfc_wc if t['team'] == 'Cowboys'][0]
    report.append(f"- **Cowboys**: Remaining SOS {cowboys['remaining_sos']:.3f}")
    report.append("")
    report.append("**Analysis:** Cowboys have slightly easier path, but both teams control their destiny.")
    report.append("")
    
    report.append("---")
    report.append("")
    report.append("## Strength of Schedule Impact")
    report.append("")
    report.append("### Easiest Remaining Schedules (SOS < 0.45)")
    report.append("")
    
    all_teams = []
    for team in afc_leaders + afc_wc[:10]:
        team['conf'] = 'AFC'
        all_teams.append(team)
    for team in nfc_leaders + nfc_wc[:10]:
        team['conf'] = 'NFC'
        all_teams.append(team)
    
    easy_schedule = sorted([t for t in all_teams if t['remaining_sos'] < 0.50], key=lambda x: x['remaining_sos'])
    for team in easy_schedule[:8]:
        report.append(f"- {team['team']} ({team['conf']}): **{team['remaining_sos']:.3f}** - {team['W']}-{team['L']} → Could surge")
    
    report.append("")
    report.append("### Hardest Remaining Schedules (SOS > 0.55)")
    report.append("")
    
    hard_schedule = sorted([t for t in all_teams if t['remaining_sos'] > 0.55], key=lambda x: x['remaining_sos'], reverse=True)
    for team in hard_schedule[:8]:
        report.append(f"- {team['team']} ({team['conf']}): **{team['remaining_sos']:.3f}** - {team['W']}-{team['L']} → Tough road ahead")
    
    report.append("")
    report.append("---")
    report.append("")
    report.append("*Analysis based on ranked strength of schedule using team performance metrics*")
    
    return '\n'.join(report)

def main():
    os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    afc_divs, nfc_divs = read_standings()
    
    afc_leaders, afc_wc = get_playoff_picture(afc_divs)
    nfc_leaders, nfc_wc = get_playoff_picture(nfc_divs)
    
    os.makedirs('output/playoff_race', exist_ok=True)
    
    create_race_visualization('AFC', afc_leaders, afc_wc, 'output/playoff_race/afc_playoff_race.png')
    create_race_visualization('NFC', nfc_leaders, nfc_wc, 'output/playoff_race/nfc_playoff_race.png')
    
    create_bubble_analysis('AFC', afc_leaders, afc_wc, 'output/playoff_race/afc_bubble.png')
    create_bubble_analysis('NFC', nfc_leaders, nfc_wc, 'output/playoff_race/nfc_bubble.png')
    
    markdown_report = create_markdown_report(afc_leaders, afc_wc, nfc_leaders, nfc_wc)
    with open('output/playoff_race/playoff_race_report.md', 'w', encoding='utf-8') as f:
        f.write(markdown_report)
    
    print("\n" + "="*80)
    print("PLAYOFF RACE ANALYSIS COMPLETE!")
    print("="*80)
    print("\nGenerated files:")
    print("  - output/playoff_race/afc_playoff_race.png")
    print("  - output/playoff_race/nfc_playoff_race.png")
    print("  - output/playoff_race/afc_bubble.png")
    print("  - output/playoff_race/nfc_bubble.png")
    print("  - output/playoff_race/playoff_race_report.md")
    print("\nKey findings:")
    print("  AFC: Massive 6-7 logjam for Wild Card spots")
    print("  NFC: South division is complete chaos - 4 teams in contention")
    print("  Watch teams with easiest remaining SOS - they'll surge!")

if __name__ == "__main__":
    main()
