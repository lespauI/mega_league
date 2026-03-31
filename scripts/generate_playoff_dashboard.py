#!/usr/bin/env python3
"""Pre-compute playoff dashboard JSON from CSV data sources."""

import csv
import json
import os
import sys
from collections import defaultdict
from datetime import datetime, timezone

SEASON_INDEX = 2

HOME_FIELD_ADVANTAGE = 0.02
WIN_STREAK_THRESHOLD = 3
WIN_STREAK_BONUS = 0.03
DIVISIONAL_REGRESSION = 0.15
ELO_WEIGHT = 0.50
WIN_PCT_WEIGHT = 0.25
SOS_WEIGHT = 0.15
SOV_WEIGHT = 0.10
DEFAULT_ELO = 1200.0

DEF_POSITIONS = frozenset([
    'CB', 'DT', 'FS', 'LEDGE', 'MIKE', 'REDGE', 'SAM', 'SS', 'WILL',
])

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def read_csv(filename):
    path = os.path.join(ROOT, filename)
    with open(path, 'r', encoding='utf-8') as f:
        return list(csv.DictReader(f))


def load_playoff_teams():
    teams = {}
    for row in read_csv('MEGA_teams.csv'):
        if int(row.get('seasonIndex', -1)) != SEASON_INDEX:
            continue
        seed = int(row.get('seed', 0) or 0)
        if seed < 1 or seed > 7:
            continue
        name = row['displayName'].strip()
        teams[name] = {
            'abbr': row['abbrName'].strip(),
            'displayName': name,
            'logoId': int(row['logoId']),
            'conference': row['conferenceName'].strip(),
            'division': row.get('divName', '').strip(),
            'seed': seed,
            'wins': int(row['totalWins']),
            'losses': int(row['totalLosses']),
            'playoffStatus': int(row.get('playoffStatus', 0)),
            'ovrRating': int(row['ovrRating']),
            'ptsFor': int(row['ptsFor']),
            'ptsAgainst': int(row['ptsAgainst']),
            'offPassYds': int(row['offPassYds']),
            'offRushYds': int(row['offRushYds']),
            'offTotalYds': int(row['offTotalYds']),
            'defPassYds': int(row['defPassYds']),
            'defRushYds': int(row['defRushYds']),
            'defTotalYds': int(row['defTotalYds']),
        }
        streak_val = row.get('winLossStreak', '0')
        try:
            streak = int(streak_val)
            if streak > 127:
                streak = streak - 256
        except (ValueError, TypeError):
            streak = 0
        teams[name]['winStreak'] = streak
    return teams


def load_elo():
    elo = {}
    for row in read_csv('mega_elo.csv'):
        team = row.get('Team', '').strip()
        elo_col = [c for c in row if c and c.startswith('Week')]
        val = row.get(elo_col[0], '') if elo_col else ''
        if team and val:
            try:
                elo[team] = float(val)
            except ValueError:
                pass
    return elo


def load_sos():
    sos = {}
    path = os.path.join(ROOT, 'output', 'ranked_sos_by_conference.csv')
    if not os.path.exists(path):
        return sos
    with open(path, 'r', encoding='utf-8') as f:
        for row in csv.DictReader(f):
            sos[row['team']] = float(row.get('past_ranked_sos_avg', 0.5))
    return sos


def load_rankings():
    rankings = {}
    max_week = {}
    for row in read_csv('MEGA_rankings.csv'):
        if int(row.get('seasonIndex', 0)) != SEASON_INDEX:
            continue
        team = row['team'].strip()
        week = int(row.get('weekIndex', 0))
        rank = int(row.get('rank', 16))
        if team not in max_week or week > max_week[team]:
            max_week[team] = week
            rankings[team] = rank
    return rankings


def load_all_teams_info():
    info = {}
    for row in read_csv('MEGA_teams.csv'):
        if int(row.get('seasonIndex', -1)) != SEASON_INDEX:
            continue
        name = row['displayName'].strip()
        streak_val = row.get('winLossStreak', '0')
        try:
            streak = int(streak_val)
            if streak > 127:
                streak = streak - 256
        except (ValueError, TypeError):
            streak = 0
        info[name] = {
            'division': row.get('divName', '').strip(),
            'conference': row.get('conferenceName', '').strip(),
            'win_streak': streak,
        }
    return info


def load_season_games():
    games = []
    for row in read_csv('MEGA_games.csv'):
        if int(row.get('seasonIndex', -1)) != SEASON_INDEX:
            continue
        if int(row.get('stageIndex', 0)) != 1:
            continue
        status = int(row['status']) if row['status'] else 1
        games.append({
            'home': row['homeTeam'].strip(),
            'away': row['awayTeam'].strip(),
            'home_score': int(row['homeScore']) if row['homeScore'] else 0,
            'away_score': int(row['awayScore']) if row['awayScore'] else 0,
            'completed': status in [2, 3, 4],
        })
    return games


def compute_team_stats(all_info, games):
    stats = {}
    for team in all_info:
        stats[team] = {
            'W': 0, 'L': 0, 'T': 0,
            'defeated_opponents': [],
        }

    for g in games:
        if not g['completed']:
            continue
        h, a = g['home'], g['away']
        if h not in stats or a not in stats:
            continue
        hs, as_ = g['home_score'], g['away_score']
        if hs > as_:
            stats[h]['W'] += 1
            stats[a]['L'] += 1
            stats[h]['defeated_opponents'].append(a)
        elif as_ > hs:
            stats[a]['W'] += 1
            stats[h]['L'] += 1
            stats[a]['defeated_opponents'].append(h)
        else:
            stats[h]['T'] += 1
            stats[a]['T'] += 1

    for team in stats:
        total = stats[team]['W'] + stats[team]['L'] + stats[team]['T']
        stats[team]['win_pct'] = (
            (stats[team]['W'] + 0.5 * stats[team]['T']) / total if total > 0 else 0
        )
    return stats


def calculate_sov_rating(defeated, rankings):
    if not defeated:
        return 0.5
    ranks = [rankings.get(opp, 16) for opp in defeated]
    avg = sum(ranks) / len(ranks)
    return 1.0 - (avg - 1) / 31


def get_streak_modifier(streak):
    if streak >= WIN_STREAK_THRESHOLD:
        return WIN_STREAK_BONUS
    if streak <= -WIN_STREAK_THRESHOLD:
        return -WIN_STREAK_BONUS
    return 0.0


def compute_win_prob(home, away, teams, elo_map, sos_map, rankings, all_info, team_stats):
    home_elo = elo_map.get(home, DEFAULT_ELO)
    away_elo = elo_map.get(away, DEFAULT_ELO)
    home_elo_norm = max(0, min(1, (home_elo - 1000) / 400))
    away_elo_norm = max(0, min(1, (away_elo - 1000) / 400))

    home_win_pct = team_stats.get(home, {}).get('win_pct', 0.5)
    away_win_pct = team_stats.get(away, {}).get('win_pct', 0.5)

    home_sos = sos_map.get(home, 0.5)
    away_sos = sos_map.get(away, 0.5)

    home_defeated = team_stats.get(home, {}).get('defeated_opponents', [])
    away_defeated = team_stats.get(away, {}).get('defeated_opponents', [])
    home_sov = calculate_sov_rating(home_defeated, rankings)
    away_sov = calculate_sov_rating(away_defeated, rankings)

    home_rating = (
        home_elo_norm * ELO_WEIGHT
        + home_win_pct * WIN_PCT_WEIGHT
        + home_sos * SOS_WEIGHT
        + home_sov * SOV_WEIGHT
    )
    away_rating = (
        away_elo_norm * ELO_WEIGHT
        + away_win_pct * WIN_PCT_WEIGHT
        + away_sos * SOS_WEIGHT
        + away_sov * SOV_WEIGHT
    )

    if home_rating + away_rating > 0:
        prob = home_rating / (home_rating + away_rating)
    else:
        prob = 0.5

    prob += HOME_FIELD_ADVANTAGE

    home_streak = all_info.get(home, {}).get('win_streak', 0)
    away_streak = all_info.get(away, {}).get('win_streak', 0)
    prob += get_streak_modifier(home_streak)
    prob -= get_streak_modifier(away_streak)

    home_div = all_info.get(home, {}).get('division', '')
    away_div = all_info.get(away, {}).get('division', '')
    if home_div == away_div and home_div:
        prob = prob + (0.5 - prob) * DIVISIONAL_REGRESSION

    return round(max(0.25, min(0.75, prob)), 4)


def load_playoff_games():
    results = []
    for row in read_csv('MEGA_games.csv'):
        if int(row.get('seasonIndex', -1)) != SEASON_INDEX:
            continue
        if int(row.get('stageIndex', 0)) != 0:
            continue
        status = int(row['status']) if row['status'] else 1
        completed = status in [2, 3, 4]
        results.append({
            'home': row['homeTeam'].strip(),
            'away': row['awayTeam'].strip(),
            'homeScore': int(row['homeScore']) if row['homeScore'] and completed else None,
            'awayScore': int(row['awayScore']) if row['awayScore'] and completed else None,
            'weekIndex': int(row.get('weekIndex', 0)),
            'completed': completed,
        })
    return results


def match_playoff_game(playoff_games, team_a, team_b):
    for g in playoff_games:
        teams_in_game = {g['home'], g['away']}
        if team_a in teams_in_game and team_b in teams_in_game:
            if g['completed']:
                return g
    return None


def build_bracket(teams, elo_map, sos_map, rankings, all_info, team_stats, playoff_games):
    bracket = {}
    for conf in ['AFC', 'NFC']:
        conf_teams = {
            t['seed']: name for name, t in teams.items() if t['conference'] == conf
        }

        wc_matchups = [
            (2, 7, f'{conf.lower()}_wc_1'),
            (3, 6, f'{conf.lower()}_wc_2'),
            (4, 5, f'{conf.lower()}_wc_3'),
        ]

        wildcard = []
        for home_seed, away_seed, mid in wc_matchups:
            home = conf_teams.get(home_seed)
            away = conf_teams.get(away_seed)
            if not home or not away:
                continue

            prob = compute_win_prob(
                home, away, teams, elo_map, sos_map, rankings, all_info, team_stats
            )

            game = match_playoff_game(playoff_games, home, away)
            status = 'completed' if game and game['completed'] else 'scheduled'
            home_score = None
            away_score = None
            winner = None
            if game and game['completed']:
                if game['home'] == home:
                    home_score = game['homeScore']
                    away_score = game['awayScore']
                else:
                    home_score = game['awayScore']
                    away_score = game['homeScore']
                if home_score is not None and away_score is not None:
                    winner = home if home_score > away_score else away

            wildcard.append({
                'matchupId': mid,
                'homeSeed': home_seed,
                'home': home,
                'awaySeed': away_seed,
                'away': away,
                'homeScore': home_score,
                'awayScore': away_score,
                'homeWinPct': prob,
                'status': status,
                'winner': winner,
            })

        bye_team = conf_teams.get(1)

        divisional = [
            {
                'matchupId': f'{conf.lower()}_div_1',
                'home': None,
                'away': None,
                'homeScore': None,
                'awayScore': None,
                'homeWinPct': None,
                'status': 'pending',
                'winner': None,
                'feedsFrom': [f'{conf.lower()}_wc_1'],
                'byeTeam': bye_team,
            },
            {
                'matchupId': f'{conf.lower()}_div_2',
                'home': None,
                'away': None,
                'homeScore': None,
                'awayScore': None,
                'homeWinPct': None,
                'status': 'pending',
                'winner': None,
                'feedsFrom': [f'{conf.lower()}_wc_2', f'{conf.lower()}_wc_3'],
            },
        ]

        championship = {
            'matchupId': f'{conf.lower()}_champ',
            'home': None,
            'away': None,
            'homeScore': None,
            'awayScore': None,
            'homeWinPct': None,
            'status': 'pending',
            'winner': None,
        }

        bracket[conf] = {
            'wildcard': wildcard,
            'divisional': divisional,
            'championship': championship,
            'byeTeam': bye_team,
        }

    super_bowl = {
        'matchupId': 'super_bowl',
        'home': None,
        'away': None,
        'homeScore': None,
        'awayScore': None,
        'homeWinPct': None,
        'status': 'pending',
        'winner': None,
    }

    return bracket, super_bowl


def load_top_players(playoff_team_names):
    ovr_map = {}
    for row in read_csv('MEGA_players.csv'):
        team = row.get('team', '').strip()
        name = row.get('fullName', '').strip()
        pos = row.get('position', '').strip()
        ovr = int(row.get('playerBestOvr', 0) or 0)
        key = (team, name)
        if key not in ovr_map or ovr > ovr_map[key][1]:
            ovr_map[key] = (pos, ovr)

    def get_ovr(team_display, player_name):
        entry = ovr_map.get((team_display, player_name))
        return entry[1] if entry else 0

    best = {t: {} for t in playoff_team_names}

    for row in read_csv('MEGA_passing.csv'):
        team = row['team__displayName'].strip()
        if team not in playoff_team_names:
            continue
        if row.get('player__position', '').strip() != 'QB':
            continue
        yards = int(row.get('passTotalYds', 0) or 0)
        cur = best[team].get('QB')
        if not cur or yards > cur['yards']:
            name = row['player__fullName'].strip()
            best[team]['QB'] = {
                'name': name,
                'yards': yards,
                'tds': int(row.get('passTotalTDs', 0) or 0),
                'ints': int(row.get('passTotalInts', 0) or 0),
                'rating': float(row.get('passerAvgRating', 0) or 0),
                'ovr': get_ovr(team, name),
            }

    for row in read_csv('MEGA_rushing.csv'):
        team = row['team__displayName'].strip()
        if team not in playoff_team_names:
            continue
        pos = row.get('player__position', '').strip()
        if pos not in ('HB', 'FB'):
            continue
        yards = int(row.get('rushTotalYds', 0) or 0)
        cur = best[team].get('RB')
        if not cur or yards > cur['yards']:
            name = row['player__fullName'].strip()
            best[team]['RB'] = {
                'name': name,
                'yards': yards,
                'tds': int(row.get('rushTotalTDs', 0) or 0),
                'avgYpc': float(row.get('rushAvgYdsPerAtt', 0) or 0),
                'ovr': get_ovr(team, name),
            }

    for row in read_csv('MEGA_receiving.csv'):
        team = row['team__displayName'].strip()
        if team not in playoff_team_names:
            continue
        pos = row.get('player__position', '').strip()
        if pos != 'WR':
            continue
        yards = int(row.get('recTotalYds', 0) or 0)
        cur = best[team].get('WR')
        if not cur or yards > cur['yards']:
            name = row['player__fullName'].strip()
            best[team]['WR'] = {
                'name': name,
                'yards': yards,
                'tds': int(row.get('recTotalTDs', 0) or 0),
                'catches': int(row.get('recTotalCatches', 0) or 0),
                'ovr': get_ovr(team, name),
            }

    DB_POS = {'CB', 'FS', 'SS'}
    LB_POS = {'MIKE', 'SAM', 'WILL'}
    DL_POS = {'DT', 'LEDGE', 'REDGE'}

    for row in read_csv('MEGA_defense.csv'):
        team = row['team__displayName'].strip()
        if team not in playoff_team_names:
            continue
        pos = row.get('player__position', '').strip()
        tackles = float(row.get('defTotalTackles', 0) or 0)
        sacks = float(row.get('defTotalSacks', 0) or 0)
        ints_ = int(row.get('defTotalInts', 0) or 0)
        score = tackles + sacks * 2 + ints_ * 3
        cur = best[team].get('DEF')
        if not cur or score > cur.get('_score', 0):
            name = row['player__fullName'].strip()
            best[team]['DEF'] = {
                'name': name,
                'sacks': sacks,
                'ints': ints_,
                'tackles': tackles,
                'ovr': get_ovr(team, name),
                '_score': score,
            }

        if pos in DB_POS:
            db_score = ints_ * 4 + tackles + float(row.get('defTotalDeflections', 0) or 0) * 2
            cur_db = best[team].get('DB')
            if not cur_db or db_score > cur_db.get('_score', 0):
                name = row['player__fullName'].strip()
                best[team]['DB'] = {
                    'name': name,
                    'sacks': sacks,
                    'ints': ints_,
                    'tackles': tackles,
                    'ovr': get_ovr(team, name),
                    '_score': db_score,
                }

        if pos in LB_POS:
            lb_score = tackles * 1.5 + sacks * 3 + ints_ * 3
            cur_lb = best[team].get('LB')
            if not cur_lb or lb_score > cur_lb.get('_score', 0):
                name = row['player__fullName'].strip()
                best[team]['LB'] = {
                    'name': name,
                    'sacks': sacks,
                    'ints': ints_,
                    'tackles': tackles,
                    'ovr': get_ovr(team, name),
                    '_score': lb_score,
                }

        if pos in DL_POS:
            dl_score = sacks * 4 + tackles + float(row.get('defTotalForcedFum', 0) or 0) * 3
            cur_dl = best[team].get('DL')
            if not cur_dl or dl_score > cur_dl.get('_score', 0):
                name = row['player__fullName'].strip()
                best[team]['DL'] = {
                    'name': name,
                    'sacks': sacks,
                    'ints': ints_,
                    'tackles': tackles,
                    'ovr': get_ovr(team, name),
                    '_score': dl_score,
                }

    for team in best:
        for k in ['DEF', 'DB', 'LB', 'DL']:
            if k in best[team] and '_score' in best[team][k]:
                del best[team][k]['_score']

    return best


def load_head_to_head(matchup_pairs):
    pair_keys = set()
    for a, b in matchup_pairs:
        key = '_vs_'.join(sorted([a, b]))
        pair_keys.add((key, frozenset([a, b])))

    h2h = {k: [] for k, _ in pair_keys}
    teams_for_key = {k: s for k, s in pair_keys}

    for row in read_csv('MEGA_games.csv'):
        if int(row.get('stageIndex', 0)) != 1:
            continue
        status = int(row['status']) if row['status'] else 1
        if status not in [2, 3, 4]:
            continue
        home = row['homeTeam'].strip()
        away = row['awayTeam'].strip()
        pair = frozenset([home, away])

        for key, team_set in teams_for_key.items():
            if pair == team_set:
                home_score = int(row['homeScore']) if row['homeScore'] else 0
                away_score = int(row['awayScore']) if row['awayScore'] else 0
                winner = home if home_score > away_score else (
                    away if away_score > home_score else 'Tie'
                )
                h2h[key].append({
                    'season': int(row.get('seasonIndex', 0)),
                    'week': int(row.get('weekIndex', 0)),
                    'home': home,
                    'away': away,
                    'homeScore': home_score,
                    'awayScore': away_score,
                    'winner': winner,
                })
                break

    for key in h2h:
        h2h[key].sort(key=lambda g: (g['season'], g['week']))

    return h2h


def main():
    os.chdir(ROOT)

    teams = load_playoff_teams()
    assert len(teams) == 14, f'Expected 14 playoff teams, got {len(teams)}'

    elo_map = load_elo()
    sos_map = load_sos()
    rankings = load_rankings()
    all_info = load_all_teams_info()
    season_games = load_season_games()
    team_stats = compute_team_stats(all_info, season_games)
    playoff_games = load_playoff_games()

    for name in teams:
        teams[name]['elo'] = round(elo_map.get(name, DEFAULT_ELO), 1)

    top_players = load_top_players(set(teams.keys()))
    for name in teams:
        teams[name]['topPlayers'] = top_players.get(name, {})

    bracket, super_bowl = build_bracket(
        teams, elo_map, sos_map, rankings, all_info, team_stats, playoff_games
    )

    wc_count = sum(
        len(bracket[c]['wildcard']) for c in bracket
    )
    assert wc_count == 6, f'Expected 6 WC matchups, got {wc_count}'

    matchup_pairs = []
    for conf in bracket:
        for m in bracket[conf]['wildcard']:
            matchup_pairs.append((m['home'], m['away']))

    h2h = load_head_to_head(matchup_pairs)

    output = {
        'generated_at': datetime.now(timezone.utc).isoformat(),
        'season_index': SEASON_INDEX,
        'teams': teams,
        'bracket': bracket,
        'super_bowl': super_bowl,
        'head_to_head': h2h,
    }

    out_dir = os.path.join(ROOT, 'docs', 'data')
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, 'playoff_dashboard.json')
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(f'Wrote {out_path}')
    print(f'  Teams: {len(teams)}')
    print(f'  WC matchups: {wc_count}')
    print(f'  H2H pairs: {len(h2h)}')
    for key, games in h2h.items():
        print(f'    {key}: {len(games)} games')

    return 0


if __name__ == '__main__':
    sys.exit(main())
