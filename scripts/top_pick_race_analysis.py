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
        afc_divs[div].sort(key=lambda x: x['win_pct'])
    
    for div in nfc_divs:
        nfc_divs[div].sort(key=lambda x: x['win_pct'])
    
    return afc_divs, nfc_divs

def get_draft_race(afc_divs, nfc_divs):
    all_teams = []
    
    for div_name in afc_divs:
        for team in afc_divs[div_name]:
            team_copy = team.copy()
            team_copy['conf'] = 'AFC'
            all_teams.append(team_copy)
    
    for div_name in nfc_divs:
        for team in nfc_divs[div_name]:
            team_copy = team.copy()
            team_copy['conf'] = 'NFC'
            all_teams.append(team_copy)
    
    all_teams.sort(key=lambda x: (x['win_pct'], -x['remaining_sos']))
    
    return all_teams[:16]

def create_draft_race_visualization(bottom_teams, output_path):
    fig, ax = plt.subplots(figsize=(14, 10))
    
    y_pos = range(len(bottom_teams))
    
    colors = []
    for i in range(len(bottom_teams)):
        if i < 3:
            colors.append('#dc2626')
        elif i < 10:
            colors.append('#f59e0b')
        else:
            colors.append('#84cc16')
    
    losses = [t['L'] for t in bottom_teams]
    bars = ax.barh(y_pos, losses, color=colors, alpha=0.7)
    
    for i, (team, bar) in enumerate(zip(bottom_teams, bars)):
        pick = i + 1
        label = f"{pick}. {team['team']} ({team['conf']})"
        
        record = f"{team['W']}-{team['L']}"
        sos_label = f"SOS: {team['remaining_sos']:.3f}"
        
        ax.text(-0.5, bar.get_y() + bar.get_height()/2, label, 
                ha='right', va='center', fontsize=10, fontweight='bold')
        
        ax.text(bar.get_width() + 0.3, bar.get_y() + bar.get_height()/2, 
                f"{record}  |  {sos_label}", 
                ha='left', va='center', fontsize=9)
    
    ax.axhline(y=2.5, color='red', linestyle='--', linewidth=2, alpha=0.5)
    ax.axhline(y=9.5, color='orange', linestyle='--', linewidth=1.5, alpha=0.5)
    
    ax.set_xlabel('Losses', fontsize=12, fontweight='bold')
    ax.set_title('MEGA League Draft Pick Race - Week 14\nRemaining SOS shown for each team', 
                 fontsize=16, fontweight='bold', pad=20)
    ax.set_yticks([])
    ax.set_xlim(-8, 16)
    ax.grid(axis='x', alpha=0.3)
    
    top3_patch = mpatches.Patch(color='#dc2626', alpha=0.7, label='Top 3 Picks (QB Territory)')
    top10_patch = mpatches.Patch(color='#f59e0b', alpha=0.7, label='Top 10 (Premium Talent)')
    rest_patch = mpatches.Patch(color='#84cc16', alpha=0.7, label='Picks 11-16 (Solid Value)')
    
    ax.legend(handles=[top3_patch, top10_patch, rest_patch], 
              loc='lower right', fontsize=10)
    
    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"Created: {output_path}")

def create_tank_analysis(bottom_teams, output_path):
    fig, ax = plt.subplots(figsize=(12, 8))
    
    tank_teams = bottom_teams[:10]
    
    x_losses = [t['L'] for t in tank_teams]
    y_sos = [t['remaining_sos'] for t in tank_teams]
    colors_map = {
        0: '#dc2626',
        1: '#dc2626',
        2: '#dc2626',
        3: '#f59e0b',
        4: '#f59e0b',
        5: '#f59e0b',
        6: '#f59e0b',
        7: '#84cc16',
        8: '#84cc16',
        9: '#84cc16'
    }
    colors = [colors_map[i] for i in range(len(tank_teams))]
    
    sizes = [(t['W'] + 3) * 50 + 100 for t in tank_teams]
    
    scatter = ax.scatter(x_losses, y_sos, c=colors, s=sizes, alpha=0.6, edgecolors='black', linewidth=2)
    
    for i, team in enumerate(tank_teams):
        ax.annotate(team['team'], 
                   (x_losses[i], y_sos[i]),
                   xytext=(5, 5), textcoords='offset points',
                   fontsize=9, fontweight='bold',
                   bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.7))
    
    ax.axhline(y=sum(y_sos)/len(y_sos), color='gray', linestyle='--', alpha=0.5, label='Avg Remaining SOS')
    ax.axvline(x=sum(x_losses)/len(x_losses), color='gray', linestyle='--', alpha=0.5, label='Avg Losses')
    
    ax.set_xlabel('Losses', fontsize=12, fontweight='bold')
    ax.set_ylabel('Remaining Strength of Schedule (higher = more likely to lose)', fontsize=12, fontweight='bold')
    ax.set_title('Draft Pick Race: Tank Battle\nTeams competing for top draft positions', 
                 fontsize=14, fontweight='bold')
    ax.grid(True, alpha=0.3)
    ax.legend(fontsize=9)
    
    textstr = 'Bubble size = more wins (worse draft pick)\nRed = Top 3 picks\nOrange = Top 10\nGreen = Picks 11-16'
    ax.text(0.02, 0.98, textstr, transform=ax.transAxes, fontsize=9,
            verticalalignment='top', bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
    
    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"Created: {output_path}")

def create_markdown_report(bottom_teams):
    report = []
    report.append("# 📉 NFL MEGA League Draft Pick Race - Week 14")
    report.append("")
    report.append("## Current Draft Order (by record)")
    report.append("")
    
    report.append("### Top 3 Picks - QB Territory")
    report.append("")
    for i, team in enumerate(bottom_teams[:3], 1):
        sos_impact = "🟢 Easy (might win games!)" if team['remaining_sos'] < 0.45 else "🔴 Brutal (tank secure)" if team['remaining_sos'] > 0.55 else "🟡 Balanced"
        report.append(f"- **Pick {i}:** {team['team']} ({team['conf']}) - {team['W']}-{team['L']} | Remaining SOS: {team['remaining_sos']:.3f} {sos_impact}")
    
    report.append("")
    report.append("### Top 10 Picks - Premium Talent")
    report.append("")
    for i, team in enumerate(bottom_teams[3:10], 4):
        sos_impact = "🟢 Easy (risk of winning)" if team['remaining_sos'] < 0.45 else "🔴 Brutal (stay bottom)" if team['remaining_sos'] > 0.55 else "🟡 Balanced"
        report.append(f"- **Pick {i}:** {team['team']} ({team['conf']}) - {team['W']}-{team['L']} | Remaining SOS: {team['remaining_sos']:.3f} {sos_impact}")
    
    report.append("")
    report.append("### Picks 11-16 - Still Solid Value")
    report.append("")
    for i, team in enumerate(bottom_teams[10:16], 11):
        sos_impact = "🟢 Easy" if team['remaining_sos'] < 0.45 else "🔴 Brutal" if team['remaining_sos'] > 0.55 else "🟡 Balanced"
        report.append(f"- **Pick {i}:** {team['team']} ({team['conf']}) - {team['W']}-{team['L']} | Remaining SOS: {team['remaining_sos']:.3f} {sos_impact}")
    
    report.append("")
    report.append("---")
    report.append("")
    report.append("## Key Tank Battles to Watch")
    report.append("")
    
    report.append("### The #1 Pick Race")
    report.append("")
    top3 = bottom_teams[:3]
    report.append(f"**{len(top3)} teams fighting for the top spot:**")
    report.append("")
    for team in top3:
        expected_wins = team['W'] + (team['remaining_games'] * (1.0 - team['remaining_sos']))
        report.append(f"- **{team['team']}** ({team['W']}-{team['L']}): Projected final record ~{expected_wins:.1f}-{team['L'] + (team['remaining_games'] * team['remaining_sos']):.1f}")
    report.append("")
    
    report.append("### SOS Impact on Draft Position")
    report.append("")
    report.append("**Teams with EASY remaining schedule (danger of winning):**")
    report.append("")
    easy_sos = sorted([t for t in bottom_teams if t['remaining_sos'] < 0.45], key=lambda x: x['remaining_sos'])
    for team in easy_sos[:5]:
        report.append(f"- **{team['team']}**: SOS {team['remaining_sos']:.3f} - Currently {team['W']}-{team['L']} → Risk of sliding down draft board!")
    
    report.append("")
    report.append("**Teams with BRUTAL remaining schedule (tank secure):**")
    report.append("")
    hard_sos = sorted([t for t in bottom_teams if t['remaining_sos'] > 0.55], key=lambda x: x['remaining_sos'], reverse=True)
    for team in hard_sos[:5]:
        report.append(f"- **{team['team']}**: SOS {team['remaining_sos']:.3f} - Currently {team['W']}-{team['L']} → Draft position locked in!")
    
    report.append("")
    report.append("---")
    report.append("")
    report.append("*Lower SOS = Higher chance of winning games = Worse draft pick*")
    report.append("*Higher SOS = Higher chance of losing = Better draft pick*")
    
    return '\n'.join(report)

def main():
    os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    afc_divs, nfc_divs = read_standings()
    bottom_teams = get_draft_race(afc_divs, nfc_divs)
    
    os.makedirs('output/draft_race', exist_ok=True)
    
    create_draft_race_visualization(bottom_teams, 'output/draft_race/draft_pick_race.png')
    create_tank_analysis(bottom_teams, 'output/draft_race/tank_battle.png')
    
    markdown_report = create_markdown_report(bottom_teams)
    with open('output/draft_race/draft_race_report.md', 'w', encoding='utf-8') as f:
        f.write(markdown_report)
    
    print("\n" + "="*80)
    print("DRAFT PICK RACE ANALYSIS COMPLETE!")
    print("="*80)
    print("\nGenerated files:")
    print("  - output/draft_race/draft_pick_race.png")
    print("  - output/draft_race/tank_battle.png")
    print("  - output/draft_race/draft_race_report.md")
    print("\nKey findings:")
    print("  Top 3: Battle for #1 overall pick is tight!")
    print("  Watch teams with low SOS - they might win games and lose draft position")
    print("  Teams with brutal remaining schedules have their tank secured!")

if __name__ == "__main__":
    main()
