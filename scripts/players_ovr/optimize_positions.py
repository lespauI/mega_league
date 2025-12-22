import csv
import os
import numpy as np
from sklearn.linear_model import Ridge
from sklearn.preprocessing import PolynomialFeatures
from collections import defaultdict

POSITION_ATTRIBUTES = {
    'QB': ['throwPowerRating', 'awareRating', 'throwAccShortRating', 'throwAccMidRating',
           'throwAccDeepRating', 'playActionRating', 'speedRating', 'agilityRating', 'throwAccRating'],
    'HB': ['speedRating', 'accelRating', 'bCVRating', 'carryRating', 'jukeMoveRating',
           'agilityRating', 'awareRating', 'breakTackleRating', 'catchRating', 'truckRating',
           'strengthRating', 'impactBlockRating', 'leadBlockRating', 'passBlockRating', 'runBlockRating'],
    'FB': ['leadBlockRating', 'impactBlockRating', 'runBlockRating', 'passBlockRating',
           'strengthRating', 'accelRating', 'carryRating', 'truckRating', 'awareRating'],
    'WR': ['speedRating', 'accelRating', 'catchRating', 'cITRating', 'routeRunShortRating',
           'routeRunMedRating', 'routeRunDeepRating', 'agilityRating', 'awareRating',
           'changeOfDirectionRating', 'jumpRating', 'releaseRating', 'specCatchRating',
           'runBlockRating', 'passBlockRating', 'breakTackleRating', 'strengthRating'],
    'TE': ['catchRating', 'cITRating', 'runBlockRating', 'passBlockRating', 'speedRating',
           'strengthRating', 'routeRunShortRating', 'routeRunMedRating', 'routeRunDeepRating',
           'breakTackleRating', 'awareRating', 'specCatchRating', 'accelRating', 'agilityRating',
           'releaseRating', 'jumpRating', 'changeOfDirectionRating'],
    'LT': ['passBlockRating', 'runBlockRating', 'strengthRating', 'awareRating', 'impactBlockRating',
           'passBlockPowerRating', 'passBlockFinesseRating', 'runBlockPowerRating', 'runBlockFinesseRating',
           'powerMovesRating', 'finesseMovesRating'],
    'RT': ['passBlockRating', 'runBlockRating', 'strengthRating', 'awareRating', 'impactBlockRating',
           'passBlockPowerRating', 'passBlockFinesseRating', 'runBlockPowerRating', 'runBlockFinesseRating',
           'powerMovesRating', 'finesseMovesRating'],
    'LG': ['runBlockRating', 'passBlockRating', 'strengthRating', 'powerMovesRating',
           'awareRating', 'finesseMovesRating', 'impactBlockRating',
           'passBlockPowerRating', 'passBlockFinesseRating', 'runBlockPowerRating', 'runBlockFinesseRating'],
    'RG': ['runBlockRating', 'passBlockRating', 'strengthRating', 'powerMovesRating',
           'awareRating', 'finesseMovesRating', 'impactBlockRating',
           'passBlockPowerRating', 'passBlockFinesseRating', 'runBlockPowerRating', 'runBlockFinesseRating'],
    'C': ['passBlockRating', 'runBlockRating', 'strengthRating', 'awareRating',
          'powerMovesRating', 'impactBlockRating', 'finesseMovesRating',
          'passBlockPowerRating', 'passBlockFinesseRating', 'runBlockPowerRating', 'runBlockFinesseRating'],
    'CB': ['speedRating', 'manCoverRating', 'zoneCoverRating', 'accelRating', 'agilityRating',
           'changeOfDirectionRating', 'awareRating', 'pressRating', 'playRecRating', 'tackleRating',
           'jumpRating', 'pursuitRating', 'hitPowerRating'],
    'FS': ['zoneCoverRating', 'speedRating', 'manCoverRating', 'pursuitRating', 'awareRating',
           'playRecRating', 'tackleRating', 'hitPowerRating', 'accelRating',
           'agilityRating', 'changeOfDirectionRating', 'pressRating', 'jumpRating'],
    'SS': ['zoneCoverRating', 'manCoverRating', 'tackleRating', 'playRecRating', 'pursuitRating',
           'awareRating', 'hitPowerRating', 'speedRating', 'accelRating',
           'agilityRating', 'changeOfDirectionRating', 'pressRating', 'jumpRating'],
    'DT': ['tackleRating', 'strengthRating', 'powerMovesRating', 'playRecRating', 'awareRating',
           'finesseMovesRating', 'blockShedRating', 'hitPowerRating', 'pursuitRating', 'accelRating'],
    'MIKE': ['tackleRating', 'playRecRating', 'pursuitRating', 'zoneCoverRating', 'blockShedRating',
             'awareRating', 'speedRating', 'strengthRating', 'hitPowerRating',
             'manCoverRating', 'accelRating', 'agilityRating'],
    'WILL': ['tackleRating', 'playRecRating', 'pursuitRating', 'zoneCoverRating', 'blockShedRating',
             'awareRating', 'speedRating', 'strengthRating', 'hitPowerRating',
             'manCoverRating', 'accelRating', 'agilityRating'],
    'SAM': ['tackleRating', 'playRecRating', 'pursuitRating', 'zoneCoverRating', 'blockShedRating',
            'awareRating', 'speedRating', 'strengthRating', 'hitPowerRating',
            'manCoverRating', 'accelRating', 'agilityRating'],
    'REDGE': ['tackleRating', 'speedRating', 'accelRating', 'finesseMovesRating', 'powerMovesRating',
              'blockShedRating', 'playRecRating', 'awareRating', 'strengthRating', 'pursuitRating',
              'hitPowerRating', 'agilityRating'],
    'LEDGE': ['tackleRating', 'speedRating', 'accelRating', 'finesseMovesRating', 'powerMovesRating',
              'blockShedRating', 'playRecRating', 'awareRating', 'strengthRating', 'pursuitRating',
              'hitPowerRating', 'agilityRating'],
    'K': ['kickPowerRating', 'kickAccRating', 'awareRating'],
    'P': ['kickPowerRating', 'kickAccRating', 'awareRating'],
    'LS': ['awareRating', 'strengthRating']
}

POSITION_CHANGES = {
    'SS': ['FS'],
    'FS': ['SS'],
    'LT': ['RT', 'LG', 'RG', 'C'],
    'RT': ['LT', 'LG', 'RG', 'C'],
    'LG': ['LT', 'RT', 'RG', 'C'],
    'RG': ['LT', 'RT', 'LG', 'C'],
    'C': ['LT', 'RT', 'LG', 'RG'],
    'SAM': ['MIKE', 'WILL', 'LEDGE', 'REDGE'],
    'MIKE': ['SAM', 'WILL', 'LEDGE', 'REDGE'],
    'WILL': ['SAM', 'MIKE', 'LEDGE', 'REDGE'],
    'LEDGE': ['REDGE', 'SAM', 'MIKE', 'WILL', 'DT'],
    'REDGE': ['LEDGE', 'SAM', 'MIKE', 'WILL', 'DT'],
    'DT': ['LEDGE', 'REDGE'],
    'TE': ['FB'],
    'FB': ['TE']
}

POSITION_GROUPS = {
    'OL': ['LT', 'RT', 'LG', 'RG', 'C'],
    'LB': ['MIKE', 'WILL', 'SAM'],
    'EDGE': ['LEDGE', 'REDGE'],
    'DL': ['DT', 'LEDGE', 'REDGE'],
    'S': ['SS', 'FS'],
    'OFFENSE': ['QB', 'HB', 'FB', 'WR', 'TE', 'LT', 'RT', 'LG', 'RG', 'C'],
    'DEFENSE': ['CB', 'FS', 'SS', 'DT', 'MIKE', 'WILL', 'SAM', 'LEDGE', 'REDGE'],
    'SPECIAL': ['K', 'P', 'LS']
}

trained_models = {}

def train_model_for_position(position_file):
    with open(position_file, 'r') as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    
    if not rows:
        return None
    
    position = os.path.basename(position_file).replace('.csv', '')
    attribute_names = POSITION_ATTRIBUTES.get(position, [])
    
    X_data = []
    y_data = []
    
    for row in rows:
        try:
            ovr = float(row['playerBestOvr'])
            if ovr < 40:
                continue
            
            attributes = []
            skip_row = False
            for attr in attribute_names:
                val = row.get(attr, '0')
                if val == '' or val is None:
                    val = 0
                try:
                    attributes.append(float(val))
                except ValueError:
                    skip_row = True
                    break
            
            if not skip_row and len(attributes) == len(attribute_names):
                X_data.append(attributes)
                y_data.append(ovr)
        except (ValueError, KeyError):
            continue
    
    if len(X_data) < 10:
        return None
    
    X = np.array(X_data)
    y = np.array(y_data)
    
    best_r2 = 0
    best_model = None
    best_poly = None
    
    configs = [
        {'poly_degree': 1, 'alpha': 0.5},
        {'poly_degree': 1, 'alpha': 1.0},
        {'poly_degree': 1, 'alpha': 5.0},
        {'poly_degree': 1, 'alpha': 10.0},
        {'poly_degree': 1, 'alpha': 50.0},
        {'poly_degree': 2, 'alpha': 1.0},
        {'poly_degree': 2, 'alpha': 5.0},
        {'poly_degree': 2, 'alpha': 10.0},
        {'poly_degree': 2, 'alpha': 50.0},
        {'poly_degree': 2, 'alpha': 100.0},
    ]
    
    for config in configs:
        try:
            if config['poly_degree'] == 1:
                model = Ridge(alpha=config['alpha'])
                model.fit(X, y)
                r2 = model.score(X, y)
                poly = None
            else:
                poly = PolynomialFeatures(degree=config['poly_degree'], include_bias=False)
                X_poly = poly.fit_transform(X)
                model = Ridge(alpha=config['alpha'])
                model.fit(X_poly, y)
                r2 = model.score(X_poly, y)
            
            if r2 > best_r2 or (r2 > best_r2 - 0.002 and config['poly_degree'] < (2 if best_poly else 1)):
                best_r2 = r2
                best_model = model
                best_poly = poly
        except Exception:
            continue
    
    return {
        'model': best_model,
        'poly': best_poly,
        'attribute_names': attribute_names
    }

def load_all_models():
    positions_dir = '../../output/positions'
    
    for position in POSITION_ATTRIBUTES.keys():
        position_file = os.path.join(positions_dir, f'{position}.csv')
        if os.path.exists(position_file):
            model_info = train_model_for_position(position_file)
            if model_info:
                trained_models[position] = model_info
                print(f"Loaded model for {position}")

def calculate_ovr_for_position(player_data, target_position):
    if target_position not in trained_models:
        return None
    
    model_info = trained_models[target_position]
    attribute_names = model_info['attribute_names']
    
    attributes = []
    for attr in attribute_names:
        val = player_data.get(attr, '0')
        if val == '' or val is None:
            val = 0
        try:
            attributes.append(float(val))
        except ValueError:
            return None
    
    if len(attributes) != len(attribute_names):
        return None
    
    X = np.array([attributes])
    if model_info['poly'] is not None:
        X_poly = model_info['poly'].transform(X)
        predicted_ovr = model_info['model'].predict(X_poly)[0]
    else:
        predicted_ovr = model_info['model'].predict(X)[0]
    
    predicted_ovr = max(40, min(99, predicted_ovr))
    
    return round(predicted_ovr)

def analyze_position_changes(team_filter=None, position_group_filter=None, show_all_changes=False):
    players_file = '../../MEGA_players.csv'
    recommendations = []
    
    position_filter_set = None
    if position_group_filter:
        position_group_upper = position_group_filter.upper()
        if position_group_upper in POSITION_GROUPS:
            position_filter_set = set(POSITION_GROUPS[position_group_upper])
        else:
            position_filter_set = {position_group_filter}
    
    with open(players_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        
        for row in reader:
            position = row.get('position', '')
            team = row.get('team', '')
            full_name = row.get('fullName', '')
            
            if team_filter and team != team_filter:
                continue
            
            if position_filter_set and position not in position_filter_set:
                continue
            
            if position not in POSITION_CHANGES:
                continue
            
            try:
                current_ovr = int(float(row.get('playerBestOvr', 0)))
            except (ValueError, TypeError):
                continue
            
            if current_ovr < 40:
                continue
            
            alternative_positions = POSITION_CHANGES[position]
            
            for alt_pos in alternative_positions:
                predicted_ovr = calculate_ovr_for_position(row, alt_pos)
                
                if predicted_ovr is not None:
                    ovr_change = predicted_ovr - current_ovr
                    
                    if abs(ovr_change) > 15:
                        continue
                    
                    if not show_all_changes and ovr_change <= 0:
                        continue
                    
                    recommendations.append({
                        'team': team,
                        'name': full_name,
                        'current_position': position,
                        'current_ovr': current_ovr,
                        'suggested_position': alt_pos,
                        'predicted_ovr': predicted_ovr,
                        'ovr_change': ovr_change
                    })
    
    return recommendations

def main():
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] in ['-h', '--help']:
        print("\nUsage: python optimize_positions.py [TEAM] [POSITION_GROUP]")
        print("\nExamples:")
        print("  python optimize_positions.py                    # All teams, all positions")
        print("  python optimize_positions.py Cowboys             # Cowboys only, all positions")
        print("  python optimize_positions.py Cowboys OL          # Cowboys offensive line only")
        print("  python optimize_positions.py Cowboys LB          # Cowboys linebackers only")
        print("\nAvailable Position Groups:")
        for group, positions in sorted(POSITION_GROUPS.items()):
            print(f"  {group:<10} {', '.join(positions)}")
        print()
        return
    
    print("Loading position models...")
    load_all_models()
    print(f"\nLoaded {len(trained_models)} position models\n")
    
    team_filter = None
    position_group_filter = None
    
    if len(sys.argv) > 1:
        team_filter = sys.argv[1]
    
    if len(sys.argv) > 2:
        position_group_filter = sys.argv[2]
    
    if team_filter:
        filter_msg = f"Team: {team_filter}"
        if position_group_filter:
            filter_msg += f", Position Group: {position_group_filter.upper()}"
        print(f"Filtering for {filter_msg}\n")
    
    print("Analyzing position changes...")
    show_all_changes = position_group_filter is not None
    recommendations = analyze_position_changes(team_filter, position_group_filter, show_all_changes)
    
    recommendations.sort(key=lambda x: (x['team'], x['name']))
    
    if not recommendations:
        print("No position change recommendations found.")
        return
    
    print(f"\n{'='*100}")
    print(f"POSITION OPTIMIZATION ANALYSIS")
    print(f"{'='*100}\n")
    
    current_team = None
    for rec in recommendations:
        if rec['team'] != current_team:
            if current_team is not None:
                print()
            current_team = rec['team']
            print(f"\n{'='*100}")
            print(f"TEAM: {current_team}")
            print(f"{'='*100}")
            print(f"{'Player':<25} {'Current':<15} {'Suggested':<15} {'OVR Change':>15}")
            print(f"{'-'*100}")
        
        ovr_change = rec['ovr_change']
        
        if ovr_change > 0:
            change_str = f"\033[92m{ovr_change:+d} OVR\033[0m"
        elif ovr_change < 0:
            change_str = f"\033[91m{ovr_change:+d} OVR\033[0m"
        else:
            change_str = "No change"
        
        print(f"{rec['name']:<25} {rec['current_position']} ({rec['current_ovr']})".ljust(40) +
              f" {rec['suggested_position']} ({rec['predicted_ovr']})".ljust(30) +
              f" {change_str}".rjust(30))
    
    print(f"\n{'='*100}")
    print(f"Total Recommendations: {len(recommendations)}")
    print(f"{'='*100}\n")

if __name__ == '__main__':
    main()
