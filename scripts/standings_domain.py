"""Pure standings calculations shared by playoff reports and the Week 18 tool."""

from collections import defaultdict


def calculate_team_stats(teams_info, games, *, include_game_results=False, include_touchdowns=False):
    """Calculate completed-game standings using the existing league rules.

    The optional fields support the Week 18 simulator's common-opponent
    tiebreaker explanations. Core callers keep the original result shape.
    """
    stats = {}

    for team in teams_info:
        stats[team] = {
            'W': 0, 'L': 0, 'T': 0,
            'conference_W': 0, 'conference_L': 0, 'conference_T': 0,
            'division_W': 0, 'division_L': 0, 'division_T': 0,
            'points_for': 0, 'points_against': 0,
            'conference_points_for': 0, 'conference_points_against': 0,
            'head_to_head': defaultdict(lambda: {'W': 0, 'L': 0, 'T': 0}),
            'opponents': [],
            'defeated_opponents': [],
        }
        if include_game_results:
            stats[team]['game_results'] = []
        if include_touchdowns:
            stats[team]['touchdowns'] = 0

    for game in games:
        if not game['completed']:
            continue

        home = game['home']
        away = game['away']
        home_score = game['home_score']
        away_score = game['away_score']

        if home not in stats or away not in stats:
            continue

        if include_game_results:
            stats[home]['game_results'].append({'opponent': away, 'pf': home_score, 'pa': away_score})
            stats[away]['game_results'].append({'opponent': home, 'pf': away_score, 'pa': home_score})

        stats[home]['opponents'].append(away)
        stats[away]['opponents'].append(home)

        stats[home]['points_for'] += home_score
        stats[home]['points_against'] += away_score
        stats[away]['points_for'] += away_score
        stats[away]['points_against'] += home_score

        if include_touchdowns:
            stats[home]['touchdowns'] += home_score // 7
            stats[away]['touchdowns'] += away_score // 7

        home_conf = teams_info[home]['conference']
        away_conf = teams_info[away]['conference']
        home_div = teams_info[home]['division']
        away_div = teams_info[away]['division']

        if home_score > away_score:
            stats[home]['W'] += 1
            stats[away]['L'] += 1
            stats[home]['defeated_opponents'].append(away)
            stats[home]['head_to_head'][away]['W'] += 1
            stats[away]['head_to_head'][home]['L'] += 1

            if home_conf == away_conf:
                stats[home]['conference_W'] += 1
                stats[away]['conference_L'] += 1
                stats[home]['conference_points_for'] += home_score
                stats[home]['conference_points_against'] += away_score
                stats[away]['conference_points_for'] += away_score
                stats[away]['conference_points_against'] += home_score

            if home_div == away_div:
                stats[home]['division_W'] += 1
                stats[away]['division_L'] += 1

        elif away_score > home_score:
            stats[away]['W'] += 1
            stats[home]['L'] += 1
            stats[away]['defeated_opponents'].append(home)
            stats[away]['head_to_head'][home]['W'] += 1
            stats[home]['head_to_head'][away]['L'] += 1

            if home_conf == away_conf:
                stats[away]['conference_W'] += 1
                stats[home]['conference_L'] += 1
                stats[home]['conference_points_for'] += home_score
                stats[home]['conference_points_against'] += away_score
                stats[away]['conference_points_for'] += away_score
                stats[away]['conference_points_against'] += home_score

            if home_div == away_div:
                stats[away]['division_W'] += 1
                stats[home]['division_L'] += 1
        else:
            stats[home]['T'] += 1
            stats[away]['T'] += 1
            stats[home]['head_to_head'][away]['T'] += 1
            stats[away]['head_to_head'][home]['T'] += 1

            if home_conf == away_conf:
                stats[home]['conference_T'] += 1
                stats[away]['conference_T'] += 1

    for team in stats:
        total = stats[team]['W'] + stats[team]['L'] + stats[team]['T']
        stats[team]['win_pct'] = (stats[team]['W'] + 0.5 * stats[team]['T']) / total if total > 0 else 0

        conf_total = stats[team]['conference_W'] + stats[team]['conference_L'] + stats[team]['conference_T']
        stats[team]['conference_pct'] = (stats[team]['conference_W'] + 0.5 * stats[team]['conference_T']) / conf_total if conf_total > 0 else 0

        div_total = stats[team]['division_W'] + stats[team]['division_L'] + stats[team]['division_T']
        stats[team]['division_pct'] = (stats[team]['division_W'] + 0.5 * stats[team]['division_T']) / div_total if div_total > 0 else 0

        defeated_records = []
        for opponent in stats[team]['defeated_opponents']:
            opponent_total = stats[opponent]['W'] + stats[opponent]['L'] + stats[opponent]['T']
            opponent_pct = (stats[opponent]['W'] + 0.5 * stats[opponent]['T']) / opponent_total if opponent_total > 0 else 0
            defeated_records.append(opponent_pct)
        stats[team]['strength_of_victory'] = sum(defeated_records) / len(defeated_records) if defeated_records else 0

        opponent_records = []
        for opponent in stats[team]['opponents']:
            opponent_total = stats[opponent]['W'] + stats[opponent]['L'] + stats[opponent]['T']
            opponent_pct = (stats[opponent]['W'] + 0.5 * stats[opponent]['T']) / opponent_total if opponent_total > 0 else 0
            opponent_records.append(opponent_pct)
        stats[team]['strength_of_schedule'] = sum(opponent_records) / len(opponent_records) if opponent_records else 0

    return stats
