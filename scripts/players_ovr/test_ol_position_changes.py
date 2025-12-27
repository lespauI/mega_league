#!/usr/bin/env python3

import sys
from optimize_positions import POSITION_CHANGES

def test_ol_position_changes():
    ol_positions = ['LT', 'LG', 'C', 'RG', 'RT']
    
    for current_pos in ol_positions:
        assert current_pos in POSITION_CHANGES, f"{current_pos} missing from POSITION_CHANGES"
        
        allowed_moves = POSITION_CHANGES[current_pos]
        
        for target_pos in ol_positions:
            if target_pos != current_pos:
                assert target_pos in allowed_moves, \
                    f"FAIL: {current_pos} cannot move to {target_pos}. Allowed: {allowed_moves}"
        
        print(f"✓ {current_pos} can move to all OL positions: {allowed_moves}")
    
    print(f"\n✓ All {len(ol_positions)} OL positions can move to all other OL positions")
    return True

if __name__ == '__main__':
    try:
        test_ol_position_changes()
        sys.exit(0)
    except AssertionError as e:
        print(f"\n✗ TEST FAILED: {e}")
        sys.exit(1)
