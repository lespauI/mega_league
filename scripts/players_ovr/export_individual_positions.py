import csv
import os
from collections import defaultdict

POSITION_CHANGES = {
    'SS': ['FS'],
    'FS': ['SS'],
    'LT': ['RT', 'G', 'C'],
    'RT': ['LT', 'G', 'C'],
    'LG': ['LT', 'RT', 'RG', 'C'],
    'RG': ['LT', 'RT', 'LG', 'C'],
    'G': ['LT', 'RT', 'C'],
    'C': ['LT', 'RT', 'G'],
    'SAM': ['MIKE', 'WILL', 'LEDGE', 'REDGE'],
    'MIKE': ['SAM', 'WILL', 'LEDGE', 'REDGE'],
    'WILL': ['SAM', 'MIKE', 'LEDGE', 'REDGE'],
    'LEDGE': ['REDGE', 'SAM', 'MIKE', 'WILL', 'DT'],
    'REDGE': ['LEDGE', 'SAM', 'MIKE', 'WILL', 'DT'],
    'DT': ['LEDGE', 'REDGE'],
    'TE': ['FB'],
    'FB': ['TE']
}

POSITION_CORE_ATTRIBUTES = {
    'QB': [
        'position', 'fullName', 'team', 'playerBestOvr',
        'throwPowerRating', 'awareRating', 'throwAccShortRating', 'throwAccMidRating',
        'throwAccDeepRating', 'playActionRating', 'speedRating', 'agilityRating', 'throwAccRating'
    ],
    'HB': [
        'position', 'fullName', 'team', 'playerBestOvr',
        'speedRating', 'accelRating', 'bCVRating', 'carryRating', 'jukeMoveRating',
        'agilityRating', 'awareRating', 'breakTackleRating', 'catchRating', 'truckRating',
        'strengthRating', 'impactBlockRating', 'leadBlockRating', 'passBlockRating', 'runBlockRating'
    ],
    'FB': [
        'position', 'fullName', 'team', 'playerBestOvr',
        'leadBlockRating', 'impactBlockRating', 'runBlockRating', 'passBlockRating',
        'strengthRating', 'accelRating', 'carryRating', 'truckRating', 'awareRating'
    ],
    'WR': [
        'position', 'fullName', 'team', 'playerBestOvr',
        'speedRating', 'accelRating', 'catchRating', 'cITRating', 'routeRunShortRating',
        'routeRunMedRating', 'routeRunDeepRating', 'agilityRating', 'awareRating',
        'changeOfDirectionRating', 'jumpRating', 'releaseRating', 'specCatchRating',
        'runBlockRating', 'passBlockRating', 'breakTackleRating', 'strengthRating'
    ],
    'TE': [
        'position', 'fullName', 'team', 'playerBestOvr',
        'catchRating', 'cITRating', 'runBlockRating', 'passBlockRating', 'speedRating',
        'strengthRating', 'routeRunShortRating', 'routeRunMedRating', 'routeRunDeepRating',
        'breakTackleRating', 'awareRating', 'specCatchRating', 'accelRating', 'agilityRating',
        'releaseRating', 'jumpRating', 'changeOfDirectionRating'
    ],
    'LT': [
        'position', 'fullName', 'team', 'playerBestOvr',
        'passBlockRating', 'runBlockRating', 'strengthRating', 'awareRating', 'impactBlockRating',
        'passBlockPowerRating', 'passBlockFinesseRating', 'runBlockPowerRating', 'runBlockFinesseRating',
        'powerMovesRating', 'finesseMovesRating'
    ],
    'RT': [
        'position', 'fullName', 'team', 'playerBestOvr',
        'passBlockRating', 'runBlockRating', 'strengthRating', 'awareRating', 'impactBlockRating',
        'passBlockPowerRating', 'passBlockFinesseRating', 'runBlockPowerRating', 'runBlockFinesseRating',
        'powerMovesRating', 'finesseMovesRating'
    ],
    'LG': [
        'position', 'fullName', 'team', 'playerBestOvr',
        'runBlockRating', 'passBlockRating', 'strengthRating', 'powerMovesRating',
        'awareRating', 'finesseMovesRating', 'impactBlockRating',
        'passBlockPowerRating', 'passBlockFinesseRating', 'runBlockPowerRating', 'runBlockFinesseRating'
    ],
    'RG': [
        'position', 'fullName', 'team', 'playerBestOvr',
        'runBlockRating', 'passBlockRating', 'strengthRating', 'powerMovesRating',
        'awareRating', 'finesseMovesRating', 'impactBlockRating',
        'passBlockPowerRating', 'passBlockFinesseRating', 'runBlockPowerRating', 'runBlockFinesseRating'
    ],
    'G': [
        'position', 'fullName', 'team', 'playerBestOvr',
        'runBlockRating', 'passBlockRating', 'strengthRating', 'powerMovesRating',
        'awareRating', 'finesseMovesRating', 'impactBlockRating',
        'passBlockPowerRating', 'passBlockFinesseRating', 'runBlockPowerRating', 'runBlockFinesseRating'
    ],
    'C': [
        'position', 'fullName', 'team', 'playerBestOvr',
        'passBlockRating', 'runBlockRating', 'strengthRating', 'awareRating',
        'powerMovesRating', 'impactBlockRating', 'finesseMovesRating',
        'passBlockPowerRating', 'passBlockFinesseRating', 'runBlockPowerRating', 'runBlockFinesseRating'
    ],
    'CB': [
        'position', 'fullName', 'team', 'playerBestOvr',
        'speedRating', 'manCoverRating', 'zoneCoverRating', 'accelRating', 'agilityRating',
        'changeOfDirectionRating', 'awareRating', 'pressRating', 'playRecRating', 'tackleRating',
        'jumpRating', 'pursuitRating', 'hitPowerRating'
    ],
    'FS': [
        'position', 'fullName', 'team', 'playerBestOvr',
        'zoneCoverRating', 'speedRating', 'manCoverRating', 'pursuitRating', 'awareRating',
        'playRecRating', 'tackleRating', 'hitPowerRating', 'accelRating',
        'agilityRating', 'changeOfDirectionRating', 'pressRating', 'jumpRating'
    ],
    'SS': [
        'position', 'fullName', 'team', 'playerBestOvr',
        'zoneCoverRating', 'manCoverRating', 'tackleRating', 'playRecRating', 'pursuitRating',
        'awareRating', 'hitPowerRating', 'speedRating', 'accelRating',
        'agilityRating', 'changeOfDirectionRating', 'pressRating', 'jumpRating'
    ],
    'DT': [
        'position', 'fullName', 'team', 'playerBestOvr',
        'tackleRating', 'strengthRating', 'powerMovesRating', 'playRecRating', 'awareRating',
        'finesseMovesRating', 'blockShedRating', 'hitPowerRating', 'pursuitRating', 'accelRating'
    ],
    'MIKE': [
        'position', 'fullName', 'team', 'playerBestOvr',
        'tackleRating', 'playRecRating', 'pursuitRating', 'zoneCoverRating', 'blockShedRating',
        'awareRating', 'speedRating', 'strengthRating', 'hitPowerRating',
        'manCoverRating', 'accelRating', 'agilityRating'
    ],
    'WILL': [
        'position', 'fullName', 'team', 'playerBestOvr',
        'tackleRating', 'playRecRating', 'pursuitRating', 'zoneCoverRating', 'blockShedRating',
        'awareRating', 'speedRating', 'strengthRating', 'hitPowerRating',
        'manCoverRating', 'accelRating', 'agilityRating'
    ],
    'SAM': [
        'position', 'fullName', 'team', 'playerBestOvr',
        'tackleRating', 'playRecRating', 'pursuitRating', 'zoneCoverRating', 'blockShedRating',
        'awareRating', 'speedRating', 'strengthRating', 'hitPowerRating',
        'manCoverRating', 'accelRating', 'agilityRating'
    ],
    'REDGE': [
        'position', 'fullName', 'team', 'playerBestOvr',
        'tackleRating', 'speedRating', 'accelRating', 'finesseMovesRating', 'powerMovesRating',
        'blockShedRating', 'playRecRating', 'awareRating', 'strengthRating', 'pursuitRating',
        'hitPowerRating', 'agilityRating'
    ],
    'LEDGE': [
        'position', 'fullName', 'team', 'playerBestOvr',
        'tackleRating', 'speedRating', 'accelRating', 'finesseMovesRating', 'powerMovesRating',
        'blockShedRating', 'playRecRating', 'awareRating', 'strengthRating', 'pursuitRating',
        'hitPowerRating', 'agilityRating'
    ],
    'K': [
        'position', 'fullName', 'team', 'playerBestOvr',
        'kickPowerRating', 'kickAccRating', 'awareRating'
    ],
    'P': [
        'position', 'fullName', 'team', 'playerBestOvr',
        'kickPowerRating', 'kickAccRating', 'awareRating'
    ],
    'LS': [
        'position', 'fullName', 'team', 'playerBestOvr',
        'awareRating', 'strengthRating'
    ]
}

def get_all_attributes_for_position(position):
    meta_fields = ['position', 'fullName', 'team', 'playerBestOvr']
    
    core_attrs = [attr for attr in POSITION_CORE_ATTRIBUTES.get(position, []) 
                  if attr not in meta_fields]
    
    all_attrs = set(core_attrs)
    
    alternative_positions = POSITION_CHANGES.get(position, [])
    for alt_pos in alternative_positions:
        alt_attrs = [attr for attr in POSITION_CORE_ATTRIBUTES.get(alt_pos, []) 
                     if attr not in meta_fields]
        all_attrs.update(alt_attrs)
    
    return meta_fields + sorted(list(all_attrs))

def main():
    output_dir = '../../output/positions'
    os.makedirs(output_dir, exist_ok=True)
    
    position_players = defaultdict(list)
    guard_players = []
    
    with open('../../MEGA_players.csv', 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        
        for row in reader:
            position = row.get('position', '')
            
            if not position or position not in POSITION_CORE_ATTRIBUTES:
                continue
            
            attributes = get_all_attributes_for_position(position)
            player_data = {attr: row.get(attr, '') for attr in attributes}
            
            # Combine LG and RG into unified Guard position
            if position in ['LG', 'RG']:
                player_data['position'] = 'G'
                guard_players.append(player_data)
            else:
                position_players[position].append(player_data)
    
    # Add unified Guard position
    if guard_players:
        position_players['G'] = guard_players
    
    for position, players in sorted(position_players.items()):
        if not players:
            continue
        
        output_file = os.path.join(output_dir, f'{position}.csv')
        
        all_fields = set()
        for player in players:
            all_fields.update(player.keys())
        
        fieldnames = sorted(list(all_fields))
        if 'position' in fieldnames:
            fieldnames.remove('position')
            fieldnames.insert(0, 'position')
        if 'fullName' in fieldnames:
            fieldnames.remove('fullName')
            fieldnames.insert(1, 'fullName')
        if 'team' in fieldnames:
            fieldnames.remove('team')
            fieldnames.insert(2, 'team')
        if 'playerBestOvr' in fieldnames:
            fieldnames.remove('playerBestOvr')
            fieldnames.insert(3, 'playerBestOvr')
        
        normalized_players = []
        for player in players:
            normalized = {field: player.get(field, '') for field in fieldnames}
            normalized_players.append(normalized)
        
        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(normalized_players)
        
        print(f'Created {output_file} with {len(players)} players')

if __name__ == '__main__':
    main()
