"""Shared decisive-game probability for regular season and postseason.

Use performance records (excluding Force Wins) and past analytical SoS.
There is no fitted venue bonus: home/away determines orientation only.
"""

MODEL_VERSION = 'performance-win70-sos30-v1'


def team_strength(team, teams_info, stats):
    performance = teams_info[team].get('performance_stats', stats[team])
    return 0.7 * performance['win_pct'] + 0.3 * teams_info[team]['past_sos']


def win_probability(home, away, teams_info, stats, *, neutral=False):
    """P(home wins | decisive result); neutral matches use the same model."""
    home_rating = team_strength(home, teams_info, stats)
    away_rating = team_strength(away, teams_info, stats)
    total = home_rating + away_rating
    probability = home_rating / total if total > 0 else 0.5
    return max(0.25, min(0.75, probability))


POSTSEASON_HOME_ELO_EQUIVALENT = 75


def postseason_win_probability(home, away, teams_info, stats, *, neutral=False):
    """Apply the approved +75 ELO equivalent to the base model's odds."""
    p = win_probability(home, away, teams_info, stats)
    if neutral:
        return p
    odds = p / (1 - p) * 10 ** (POSTSEASON_HOME_ELO_EQUIVALENT / 400)
    return max(0.25, min(0.75, odds / (1 + odds)))
