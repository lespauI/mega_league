# Match model selection

Common sample: 44 regular decisive Madden 27 games; split at display Week 15.
All candidates use the same games in each partition. Lower Brier/log loss is better.
This is a retrospective chronological check, not an untouched holdout: the full sample was previously inspected.
No coefficients or bonus were fitted. Partitions are by game week, not random game draws.

| Partition | Model | n | Brier | Log loss |
|---|---|---:|---:|---:|
| Earlier | Win70/SoS30 (saved) | 27 | 0.2101 | 0.6091 |
| Earlier | Mixed (historical versions) | 27 | 0.2173 | 0.6243 |
| Earlier | ELO, bonus 0 | 27 | 0.2267 | 0.6461 |
| Earlier | ELO, bonus +75 | 27 | 0.2111 | 0.6120 |
| Later | Win70/SoS30 (saved) | 17 | 0.1895 | 0.5673 |
| Later | Mixed (historical versions) | 17 | 0.2147 | 0.6193 |
| Later | ELO, bonus 0 | 17 | 0.2282 | 0.6491 |
| Later | ELO, bonus +75 | 17 | 0.2706 | 0.7346 |

Provisional selection: Win70/SoS30, which has the smallest Brier and log loss in both partitions.
The sample is small, teams recur, and mixed versions differ over time; this does not prove superiority or validate Super Bowl probabilities.
Production uses the same 70/30 coefficients and 25–75% bounds, with Force Wins excluded from performance records as required by the current input contract.
Historical saved probabilities used official W-L, so the production Force Win correction is not itself validated by these scores.
No venue bonus is added: the saved candidate had none, and +75 ELO has no robust paired evidence.
Performance Win% and past SoS remain fixed at the input snapshot during the simulation; fictitious simulated scores are not added to analytical strength.
Future forecasts are needed for an independent prospective test.

Reproduce: `python3 scripts/analyze_forecast_quality.py` then `python3 scripts/compare_match_models.py`.

User-selected postseason setting: +75 ELO equivalent, multiplying home victory odds by 10**(75/400), with 25–75% bounds. This is a sensitivity-based preference, not a fitted or independently validated parameter. The displayed Super Bowl metric counts conference titles (100% per conference), not league championships.
