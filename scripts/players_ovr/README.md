# Madden Player OVR Analysis

Calculate and analyze Madden player OVR formulas from MEGA league data with **99%+ accuracy**.

## Quick Start

```bash
# Setup virtual environment
cd scripts/players_ovr
source ../../myenv/bin/activate
pip install -r requirements.txt

# One-liner: Analyze a team (runs full pipeline)
python analyze_team.py Cowboys          # All positions
python analyze_team.py Cowboys OL       # Offensive line only
python analyze_team.py Cowboys LB       # Linebackers only
python analyze_team.py Eagles S         # Safeties only
```

## Manual Pipeline (Optional)

```bash
# 1. Export position data
python export_individual_positions.py

# 2. Calculate formulas
python calculate_advanced_formulas.py

# 3. Find optimal positions
python optimize_positions.py Cowboys
```

## Scripts

- **analyze_team.py** - ⭐ **One-liner** - Runs full pipeline for a specific team (export → calculate → optimize)
- **export_individual_positions.py** - Exports position CSV files with expanded attributes
- **calculate_advanced_formulas.py** - Derives OVR formulas using polynomial ridge regression (R² > 0.99)
- **optimize_positions.py** - Analyzes players and suggests optimal position changes

## Results

### 🎯 Accuracy Achieved
- **21/22 positions**: R² > 0.99 (99%+ accuracy)
- **20/22 positions**: R² > 0.995 (99.5%+ accuracy)  
- **2 positions**: R² = 1.0 (100% perfect - SAM, FB)
- **Average**: R² = 0.973 across all positions

### Top Performers (R² Score)
1. SAM (66 players): **1.000000** - Perfect
2. FB (29 players): **1.000000** - Perfect
3. TE (175 players): **0.999511**
4. WILL (110 players): **0.999432**
5. FS (133 players): **0.999419**

### Output Files
- `../../output/positions/*.csv` - Individual position CSV files (22 positions, used for training)
- `../../output/individual_position_formulas.txt` - Complete formulas with coefficients and R² scores

## Position Optimization

The **optimize_positions.py** script evaluates players at alternative positions and shows **all OVR predictions** (positive, negative, and no change).

### Allowed Position Changes
- **SS ↔ FS** (Safety positions are interchangeable)
- **OL positions** (LT, RT, LG, RG, C can move to any other OL position)
- **Linebackers ↔ Edge** (SAM, MIKE, WILL ↔ LEDGE, REDGE)
- **Edge ↔ DT** (LEDGE, REDGE ↔ DT)
- **TE ↔ FB** (Tight ends and fullbacks can interchange)

### Position Groups
Filter analysis by position group:
- **OL** - Offensive Line (LT, RT, LG, RG, C)
- **LB** - Linebackers (MIKE, WILL, SAM)
- **EDGE** - Edge Rushers (LEDGE, REDGE)
- **DL** - Defensive Line (DT, LEDGE, REDGE)
- **S** - Safeties (SS, FS)
- **OFFENSE** - All offensive positions
- **DEFENSE** - All defensive positions
- **SPECIAL** - Special teams (K, P, LS)

### Usage Examples
```bash
# All teams, all positions
python optimize_positions.py

# Specific team, all positions
python optimize_positions.py Cowboys

# Specific team and position group
python optimize_positions.py Cowboys OL       # Offensive line only
python optimize_positions.py Cowboys LB       # Linebackers only
python optimize_positions.py Cowboys S        # Safeties only
python optimize_positions.py Eagles EDGE      # Edge rushers only

# Help
python optimize_positions.py --help
```

## Position List

**Offense**: QB, HB, FB, WR, TE, LT, RT, LG, RG, C  
**Defense**: CB, FS, SS, DT, MIKE, WILL, SAM, LEDGE, REDGE  
**Special Teams**: K, P, LS

## Requirements

- Python 3.x
- MEGA_players.csv in project root  
- scikit-learn >= 1.8.0, numpy >= 2.4.0
