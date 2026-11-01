"""Production performance eligibility, evidence and attribution contracts."""
import csv
import json
from pathlib import Path
import tempfile
import unittest

from mega.inputs.performance import analytics_path
from mega.inputs.games import flag, is_force_win
from mega.stats.performance import (
    COUNTS, MAXIMA, aggregate, build_performance, digest, load_evidence,
    resolve_stat_identities, write_rows,
)


class PerformanceTests(unittest.TestCase):
    def test_strict_eligibility_checks_both_flags_without_changing_status(self):
        for home, away in [('True', 'False'), ('False', 'True')]:
            row = dict(home_fw=home, away_fw=away, status='3')
            self.assertTrue(is_force_win(row))
            self.assertEqual(row['status'], '3')
        self.assertFalse(is_force_win(dict(home_fw='false', away_fw='0')))
        with self.assertRaises(ValueError):
            is_force_win(dict(home_fw='true', away_fw='missing'))
        with self.assertRaises(ValueError):
            flag('')

    def fixture(self, root):
        source = root / 'data/performance_evidence'
        (source / 'games').mkdir(parents=True)
        (root / 'spec').mkdir()
        (root / 'spec/performance_policy.json').write_text('{"schemaVersion":1}')
        teams = [dict(displayName=name, abbrName=abbr, cityName=name, calendarYear=2026,
                      seasonIndex=0, totalWins=1 if name == 'Alpha' else 0,
                      totalLosses=0 if name == 'Alpha' else 1, totalTies=1,
                      **{f: 0 for f in ('offPassYds', 'offRushYds', 'offTotalYds', 'defPassYds', 'defRushYds', 'defTotalYds')})
                 for name, abbr in [('Alpha', 'A'), ('Beta', 'B')]]
        write_rows(root / 'MEGA_teams.csv', teams)
        games, naive = [], {d: {} for d in COUNTS}
        for index in range(2):
            game = dict(id=str(index + 1), gameId=str(index + 10), homeTeam='Alpha', awayTeam='Beta',
                        homeScore='17' if index == 0 else '0', awayScore='10' if index == 0 else '0',
                        seasonIndex='0', stageIndex='1', weekIndex=str(index), status='3',
                        home_fw='True' if index == 0 else 'False', away_fw='False', is_superseded='False')
            games.append(game)
            capture = dict(sourceUrl='https://neonsportz.com/leagues/MEGA/games/' + game['id'],
                           game={**{k: int(game[k]) for k in ('homeScore', 'awayScore', 'seasonIndex', 'stageIndex', 'weekIndex', 'status', 'gameId')},
                                 'pk': index + 1, 'home_fw': index == 0, 'away_fw': False, 'is_superseded': False}, sides={})
            for side, name in [('home', 'Alpha'), ('away', 'Beta')]:
                side_index = 0 if side == 'home' else 1
                obj = dict(team=name, teamStats=dict(game=index + 1, weekIndex=index, tODiff=0,
                    **{f: 0 for f in ('offPassYds', 'offRushYds', 'offTotalYds', 'defPassYds', 'defRushYds', 'defTotalYds')}),
                           categories={}, players={})
                for category_index, dataset in enumerate(COUNTS):
                    player_id = str(100 + side_index * 10 + category_index)
                    row_id = str(1000 + index * 100 + side_index * 10 + category_index)
                    row = {source_field: 0 for source_field in [*COUNTS[dataset].values(), *MAXIMA.get(dataset, {}).values()]}
                    row.update(id=int(row_id), playerId=player_id, playerName='Player ' + player_id,
                               team=name, statId=int(row_id), game=index + 1, seasonIndex=0,
                               stageIndex=1, weekIndex=index, fantasy_points=0, game_is_superseded=False)
                    if dataset == 'passing':
                        row.update(passAtt=4, passComp=2, passYds=40, passLongest=30 if index == 0 else 20)
                    obj['players'][row_id] = row
                    obj['categories'][dataset] = [row_id]
                    naive[dataset].setdefault((name, player_id), []).append(row)
                capture['sides'][side] = obj
            (source / 'games' / (game['id'] + '.json')).write_text(json.dumps(capture))
        write_rows(root / 'MEGA_games.csv', games)
        for dataset, keyed in naive.items():
            raw = [dict(team__displayName=name, team__abbrName='A' if name == 'Alpha' else 'B',
                        player__rosterId=pid, player__fullName='Player ' + pid,
                        **aggregate(dataset, rows)) for (name, pid), rows in keyed.items()]
            write_rows(root / f'MEGA_{dataset}.csv', raw)
        manifest = dict(schemaVersion=1, csvSeasonIndex=0, calendarYear=2026,
                        inputHashes={p.name: digest(p) for p in root.glob('MEGA_*.csv')},
                        evidenceHashes={p.relative_to(source).as_posix(): digest(p) for p in source.rglob('*.json')})
        (source / 'manifest.json').write_text(json.dumps(manifest))
        return source

    def test_full_rebuild_excludes_both_sides_and_preserves_official_bytes(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.fixture(root)
            before = {p.name: p.read_bytes() for p in root.glob('MEGA_*.csv')}
            manifest = build_performance(root)
            self.assertTrue(manifest['complete'])
            self.assertEqual((manifest['completedGames'], manifest['excludedGames']), (2, 1))
            for name, content in before.items():
                self.assertEqual((root / name).read_bytes(), content)
            with (root / 'output/performance/teams.csv').open() as stream:
                teams = list(csv.DictReader(stream))
            self.assertTrue(all(r['performanceGames'] == '1' and r['excludedGames'] == '1' for r in teams))
            self.assertTrue(all(r['totalWins'] == '0' and r['totalTies'] == '1' and r['ptsFor'] == '0' for r in teams))
            path = analytics_path(root / 'MEGA_passing.csv')
            with path.open() as stream:
                players = list(csv.DictReader(stream))
            self.assertTrue(all(r['gamesPlayed'] == '1' and r['passTotalYds'] == '40.0' and r['passTotalLongest'] == '20.0' for r in players))
            with (root / 'output/performance/games.csv').open() as stream:
                games = list(csv.DictReader(stream))
            self.assertEqual([g['id'] for g in games], ['2'])

    def test_missing_changed_and_wrong_cycle_evidence_fail(self):
        for damage in ('missing', 'changed', 'cycle'):
            with self.subTest(damage=damage), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                source = self.fixture(root)
                if damage == 'missing':
                    (source / 'games/1.json').unlink()
                elif damage == 'changed':
                    (source / 'games/1.json').write_text('{}')
                else:
                    d = json.loads((source / 'manifest.json').read_text())
                    d['csvSeasonIndex'] = 1
                    (source / 'manifest.json').write_text(json.dumps(d))
                with self.assertRaises((ValueError, FileNotFoundError)):
                    build_performance(root)
                self.assertFalse((root / 'output/performance/manifest.json').exists())

    def test_resealed_inconsistent_season_totals_are_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = self.fixture(root)
            path = root / 'MEGA_passing.csv'
            with path.open() as stream:
                rows = list(csv.DictReader(stream))
            rows[0]['passTotalYds'] = '999'
            write_rows(path, rows)
            manifest = json.loads((source / 'manifest.json').read_text())
            manifest['inputHashes'][path.name] = digest(path)
            (source / 'manifest.json').write_text(json.dumps(manifest))
            with self.assertRaisesRegex(ValueError, 'Season totals do not reconcile'):
                build_performance(root)
            self.assertFalse((root / 'output/performance/manifest.json').exists())

    def test_routing_rejects_stale_raw_and_changed_adjusted_files(self):
        for damage in ('raw', 'adjusted', 'policy'):
            with self.subTest(damage=damage), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                self.fixture(root)
                build_performance(root)
                if damage == 'raw':
                    p = root / 'MEGA_teams.csv'
                elif damage == 'policy':
                    p = root / 'spec/performance_policy.json'
                else:
                    p = root / '.cache/performance/inputs/MEGA_passing.csv'
                p.write_text(p.read_text() + '\n')
                with self.assertRaises(ValueError):
                    analytics_path(root / 'MEGA_passing.csv')

    def test_duplicate_stat_identity_requires_history_and_preserves_original_team(self):
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary)
            (source / 'histories').mkdir()
            history = dict(sourceUrl='https://neonsportz.com/leagues/MEGA/players/42/history', tables=[{
                'headers': ['SEASON', 'STAGE', 'WEEK', 'TEAM'], 'rows': [
                    {'cells': ['2026', 'Regular Season', 'Week 3', 'Alpha'], 'links': [{'href': '/leagues/MEGA/teams/A'}]},
                    {'cells': ['2026', 'Regular Season', 'Week 8', 'Beta'], 'links': [{'href': '/leagues/MEGA/teams/B'}]}]}])
            (source / 'histories/42.json').write_text(json.dumps(history))
            teams = {'Alpha': {'abbrName': 'A'}, 'Beta': {'abbrName': 'B'}}
            rows = {'1': dict(playerId='42', statId=99, weekIndex=0, team='Alpha', rushYds=46),
                    '2': dict(playerId='42', statId=99, weekIndex=0, team='Beta', rushYds=46)}
            manifest = dict(calendarYear=2026, evidenceHashes={'histories/42.json': digest(source / 'histories/42.json')})
            discarded, corrections = resolve_stat_identities(rows, source, teams, manifest)
            self.assertEqual(discarded, {'2'})
            self.assertEqual(corrections[0]['retainedTeam'], 'Alpha')
            with self.assertRaises(ValueError):
                resolve_stat_identities(rows, source, teams, dict(calendarYear=2026, evidenceHashes={}))
            rows['2']['rushYds'] = 47
            with self.assertRaises(ValueError):
                resolve_stat_identities(rows, source, teams, manifest)


if __name__ == '__main__':
    unittest.main()
