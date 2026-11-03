#!/usr/bin/env python3
"""Sensitivity experiment; does not change production probabilities or pages.

Run from repository root: python3 -m scripts.compare_postseason_home_bonus --simulations 50000
"""
import argparse
import csv
import random
from collections import Counter
from pathlib import Path

from mega.standings.match_probability import win_probability
from mega.standings.postseason import simulate_conference_champions
try:
    from . import calc_playoff_probabilities as playoff
except ImportError:
    import calc_playoff_probabilities as playoff


def compare(simulations=20000, seed=0):
    teams, games, sos = playoff.load_data(season_index=0)
    stats = playoff.calculate_team_stats(teams, games)
    rankings = playoff.load_rankings_data(season_index=0)
    base = {(a, b): win_probability(a, b, teams, stats) for a in teams for b in teams if a != b}
    cases = ('none', 'plus_3pp', 'plus_5pp', 'elo75_odds')
    wins = {case: Counter() for case in cases}
    bye = Counter()
    bracket_seed_rng = random.Random(seed + 1)
    random.seed(seed)
    for _ in range(simulations):
        remaining = playoff.simulate_remaining_games(teams, stats, sos, games, rankings)
        fields, _, byes = playoff.determine_playoff_teams(teams, stats, remaining)
        for conference in byes:
            bye.update(byes[conference])
        bracket_seed = bracket_seed_rng.getrandbits(64)
        for case in cases:
            def probability(home, away, *, neutral=False):
                p = base[home, away]
                if neutral or case == 'none':
                    return p
                if case == 'elo75_odds':
                    # +75 ELO corresponds to multiplying victory odds
                    # by 10**(75/400); this does not add ELO to 70/30 strength.
                    odds = p / (1-p) * 10 ** (75/400)
                    p = odds / (1+odds)
                else:
                    p += {'plus_3pp': 0.03, 'plus_5pp': 0.05}[case]
                return min(0.75, max(0.25, p))
            # Same field and same 12 random draws for every case.
            champions = simulate_conference_champions(fields, probability, random.Random(bracket_seed))
            wins[case].update(champions.values())
    rows = []
    for team in sorted(teams, key=lambda t: -wins['none'][t]):
        row = {'team': team, 'conference': teams[team]['conference'], 'bye_pct': bye[team]*100/simulations}
        row.update({case: wins[case][team]*100/simulations for case in cases})
        rows.append(row)
    for case in cases:
        for conference in ('AFC', 'NFC'):
            assert abs(sum(row[case] for row in rows if row['conference'] == conference)-100) < 1e-8
    return rows


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--simulations', type=int, default=20000)
    parser.add_argument('--seed', type=int, default=0)
    args = parser.parse_args()
    if args.simulations <= 0:
        parser.error('simulations must be positive')
    rows = compare(args.simulations, args.seed)
    output = Path('analysis/forecast_quality/postseason_home_bonus.csv')
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open('w', newline='', encoding='utf-8') as handle:
        writer = csv.DictWriter(handle, fieldnames=rows[0])
        writer.writeheader()
        writer.writerows({key: (f'{value:.3f}' if isinstance(value, float) else value)
                          for key, value in row.items()} for row in rows)
    print(f'{args.simulations} paired fields, seed={args.seed}; Super Bowl appearances (100%/conference); regular season unchanged')
    for row in rows:
        print(row['team'], ' '.join(f'{case}={row[case]:.2f}%' for case in row if case not in ('team', 'conference')))
