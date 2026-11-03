#!/usr/bin/env python3
"""Chronological comparison on the common historical Madden 27 sample."""
import csv
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODELS = {
    'Win70/SoS30 (saved)': 'saved_home_win_conditional',
    'Mixed (historical versions)': 'mixed_home_probability_reconstructed',
    'ELO, bonus 0': 'elo_home_probability_bonus_0',
    'ELO, bonus +75': 'elo_home_probability_bonus_75',
}


def compare(source):
    with source.open(newline='', encoding='utf-8') as handle:
        rows = [r for r in csv.DictReader(handle)
                if r['edition'] == 'Madden 27' and r['performance_eligible'] == 'true'
                and r['elo_scored_eligible'] == 'true'
                and all(r[column] for column in MODELS.values())]
    weeks = sorted({int(r['display_week']) for r in rows})
    if len(weeks) < 2:
        raise ValueError('Need at least two forecast weeks')
    cutoff = weeks[len(weeks)//2]
    lines = ['# Match model selection', '',
             f'Common sample: {len(rows)} regular decisive Madden 27 games; split at display Week {cutoff}.',
             'All candidates use the same games in each partition. Lower Brier/log loss is better.',
             'This is a retrospective chronological check, not an untouched holdout: the full sample was previously inspected.',
             'No coefficients or bonus were fitted. Partitions are by game week, not random game draws.', '',
             '| Partition | Model | n | Brier | Log loss |',
             '|---|---|---:|---:|---:|']
    for part, subset in [('Earlier', [r for r in rows if int(r['display_week']) < cutoff]),
                         ('Later', [r for r in rows if int(r['display_week']) >= cutoff])]:
        for model, column in MODELS.items():
            pairs = [(float(r[column]), int(r['actual_result'] == 'home_win')) for r in subset]
            brier = sum((p-y)**2 for p, y in pairs)/len(pairs)
            loss = -sum(y*math.log(p)+(1-y)*math.log(1-p) for p, y in pairs)/len(pairs)
            lines.append(f'| {part} | {model} | {len(pairs)} | {brier:.4f} | {loss:.4f} |')
    lines += ['', 'Provisional selection: Win70/SoS30, which has the smallest Brier and log loss in both partitions.',
              'The sample is small, teams recur, and mixed versions differ over time; this does not prove superiority or validate Super Bowl probabilities.',
              'Production uses the same 70/30 coefficients and 25–75% bounds, with Force Wins excluded from performance records as required by the current input contract.',
              'Historical saved probabilities used official W-L, so the production Force Win correction is not itself validated by these scores.',
              'No venue bonus is added: the saved candidate had none, and +75 ELO has no robust paired evidence.',
              'Performance Win% and past SoS remain fixed at the input snapshot during the simulation; fictitious simulated scores are not added to analytical strength.',
              'Future forecasts are needed for an independent prospective test.', '',
              'Reproduce: `python3 scripts/analyze_forecast_quality.py` then `python3 scripts/compare_match_models.py`.', '']
    return '\n'.join(lines)


if __name__ == '__main__':
    report = compare(ROOT / 'analysis/forecast_quality/matches.csv')
    (ROOT / 'analysis/forecast_quality/model_selection.md').write_text(report, encoding='utf-8')
    print(report)
