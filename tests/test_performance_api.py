"""API acquisition, source minimization, pagination and transactional validation."""
import copy
import csv
from email.message import Message
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import MagicMock, patch
from urllib.error import HTTPError, URLError

from mega.inputs.performance_api import (
    API, APIClient, CATEGORY_FIELDS, TEAM_FIELDS,
    collect, game_evidence, history_evidence,
)
import test_performance
from mega.inputs.evidence_bundle import evidence_source


class PerformanceAPITests(unittest.TestCase):
    def fixture(self, root):
        source = test_performance.PerformanceTests().fixture(root)
        (root / 'docs/data').mkdir(parents=True)
        (root / 'docs/data/import_metadata.json').write_text(json.dumps(
            dict(seasonIndex=0, calendarYear=2026, snapshotId='fixture')))
        responses = {}
        for path in (source / 'games').glob('*.json'):
            evidence = json.loads(path.read_text())
            game = evidence['game']
            game.setdefault('simmed', False)
            prefix = API + 'games/' + path.stem + '/'
            responses[prefix] = game
            players, teams = [], []
            for side in evidence['sides'].values():
                name = side['team']
                team = dict(displayName=name, abbrName=name[0], sensitiveProfile='do not retain')
                teams.append({**{key: 0 for key in TEAM_FIELDS}, **side['teamStats'], 'team': team})
                for row in side['players'].values():
                    p = {**{key: None for key in CATEGORY_FIELDS.values()}, **row}
                    p['team'] = team
                    p['player'] = dict(rosterId=int(row['playerId']), fullName=row['playerName'],
                                       position='QB', sensitiveProfile='do not retain')
                    players.append(p)
            responses[prefix + 'stats/players/'] = players
            responses[prefix + 'stats/teams/'] = teams
        return source, lambda url: copy.deepcopy(responses[url]), responses

    def test_refresh_validates_before_install_and_build_remains_offline(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source, get, _ = self.fixture(root)
            result = collect(root, get=get, workers=2, progress=lambda _: None)
            self.assertEqual((result['completedGames'], result['excludedGames']), (2, 1))
            data = json.loads((evidence_source(root) / 'games/1.json').read_text())
            self.assertEqual(data['acquisition'], 'api')
            self.assertNotIn('sensitiveProfile', json.dumps(data))
            self.assertNotIn('do not retain', json.dumps(data))
            self.assertEqual(data['sides']['home']['categories']['kicking'], ['1004'])
            self.assertFalse(list((root / 'data').glob('.performance-api-*')))
            # Validation scratch outputs must not replace the published site/cache.
            self.assertFalse((root / 'output').exists())

    def test_unchanged_snapshot_uses_no_network_and_full_refresh_bypasses_cache(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source, get, _ = self.fixture(root)
            collect(root, get=get, progress=lambda _: None)
            before = {p.relative_to(source): p.read_bytes() for p in source.rglob('*.json')}
            no_network = MagicMock(side_effect=AssertionError('Unexpected API request'))
            result = collect(root, get=no_network, progress=lambda _: None)
            self.assertEqual(result['acquisitionSummary']['gamesCached'], 2)
            no_network.assert_not_called()
            self.assertEqual(before, {p.relative_to(source): p.read_bytes() for p in source.rglob('*.json')})
            request = MagicMock(side_effect=get)
            result = collect(root, get=request, full_refresh=True, progress=lambda _: None)
            self.assertEqual(result['acquisitionSummary']['gamesFetched'], 2)
            self.assertEqual(request.call_count, 6)

    def test_changed_game_and_damaged_cache_refetch_only_the_affected_game(self):
        for change in ('flag', 'corrupt', 'missing'):
            with self.subTest(change=change), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                source, get, responses = self.fixture(root)
                collect(root, get=get, progress=lambda _: None)
                if change == 'flag':
                    path = root / 'MEGA_games.csv'
                    with path.open() as stream:
                        rows = list(csv.DictReader(stream))
                    rows[0]['home_fw'] = 'False'
                    test_performance.write_rows(path, rows)
                    responses[API + 'games/1/']['home_fw'] = False
                elif change == 'corrupt':
                    with (evidence_source(root) / 'games/1.json').open('a') as stream:
                        stream.write('corrupted')
                else:
                    (evidence_source(root) / 'games/1.json').unlink()
                request = MagicMock(side_effect=get)
                result = collect(root, get=request, progress=lambda _: None)
                expected = 1 if change == 'flag' else 0
                self.assertEqual(result['acquisitionSummary']['gamesFetched'], expected)
                self.assertEqual(result['acquisitionSummary']['gamesCached'], 2 - expected)
                self.assertEqual(request.call_count, 3 * expected)
                self.assertTrue(all('/games/1/' in call.args[0] for call in request.call_args_list))

    def test_hidden_box_score_changes_fail_reconciliation_with_full_refresh_advice(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source, get, _ = self.fixture(root)
            collect(root, get=get, progress=lambda _: None)
            before = (source / 'manifest.json').read_bytes()
            path = root / 'MEGA_passing.csv'
            with path.open() as stream:
                rows = list(csv.DictReader(stream))
            rows[0]['passTotalYds'] = '81'
            test_performance.write_rows(path, rows)
            with self.assertRaisesRegex(ValueError, '--full-refresh'):
                collect(root, get=MagicMock(side_effect=AssertionError('Unexpected API request')),
                        progress=lambda _: None)
            self.assertEqual((source / 'manifest.json').read_bytes(), before)

    def test_new_completed_game_fetches_only_new_game(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            _, get, responses = self.fixture(root)
            collect(root, get=get, progress=lambda _: None)
            prefix = API + 'games/'
            responses[prefix + '3/'] = {**responses[prefix + '2/'], 'pk': 3, 'gameId': 12, 'weekIndex': 2}
            for suffix in ('stats/teams/', 'stats/players/'):
                rows = copy.deepcopy(responses[prefix + '2/' + suffix])
                for row in rows:
                    row.update(game=3, weekIndex=2, id=row['id'] + 10000, statId=row['statId'] + 10000)
                responses[prefix + '3/' + suffix] = rows
            path = root / 'MEGA_games.csv'
            with path.open() as stream:
                games = list(csv.DictReader(stream))
            games.append({**games[1], 'id': '3', 'gameId': '12', 'weekIndex': '2'})
            test_performance.write_rows(path, games)
            for category, field in CATEGORY_FIELDS.items():
                path = root / f'MEGA_{category}.csv'
                with path.open() as stream:
                    raw = list(csv.DictReader(stream))
                for row in raw:
                    appearances = [p for game in ('1', '2', '3')
                                   for p in responses[prefix + game + '/stats/players/']
                                   if p.get(field) is not None
                                   and str(p['player']['rosterId']) == row['player__rosterId']
                                   and p['team']['displayName'] == row['team__displayName']]
                    row.update(test_performance.aggregate(category, appearances))
                test_performance.write_rows(path, raw)
            request = MagicMock(side_effect=get)
            result = collect(root, get=request, progress=lambda _: None)
            self.assertEqual(result['completedGames'], 3)
            self.assertEqual(result['acquisitionSummary']['gamesFetched'], 1)
            self.assertEqual(result['acquisitionSummary']['gamesCached'], 2)
            self.assertEqual(request.call_count, 3)
            self.assertTrue(all('/games/3/' in call.args[0] for call in request.call_args_list))

    def test_failure_preserves_previous_evidence_and_removes_staging(self):
        for failure in ('network', 'identity', 'totals', 'input_changed'):
            with self.subTest(failure=failure), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                source, get, responses = self.fixture(root)
                before = {p.relative_to(source): p.read_bytes() for p in source.rglob('*.json')}
                def broken(url):
                    if failure == 'network':
                        raise URLError('offline')
                    return get(url)
                if failure == 'identity':
                    responses[API + 'games/1/']['home_fw'] = False
                if failure == 'totals':
                    responses[API + 'games/1/stats/players/'][0]['passYds'] += 1
                def progress(_):
                    if failure == 'input_changed':
                        with (root / 'MEGA_passing.csv').open('a') as stream:
                            stream.write('\n')
                with self.assertRaises((ValueError, URLError)):
                    collect(root, get=broken, workers=1, progress=progress)
                self.assertEqual(before, {p.relative_to(source): p.read_bytes() for p in source.rglob('*.json')})
                self.assertFalse(list((root / 'data').glob('.performance-api-*')))

    def test_history_paginates_and_preserves_trade_and_free_agency(self):
        endpoint = API + 'players/42/history/'
        def row(week, team):
            return dict(seasonIndex=0, stageIndex=1, weekIndex=week,
                        team=dict(displayName=team, abbrName=team[0]) if team else None)
        responses = {endpoint: dict(results=[row(7, 'Beta'), row(4, None)], next=endpoint + '?page=2'),
                     endpoint + '?page=2': dict(results=[row(2, 'Alpha')], next=None)}
        data = history_evidence('42', 0, 2026, responses.__getitem__, '2026-11-01')
        self.assertEqual([r['cells'][2:] for r in data['tables'][0]['rows']],
                         [['Week 3', 'Alpha'], ['Week 5', 'FA'], ['Week 8', 'Beta']])
        self.assertEqual(data['tables'][0]['rows'][1]['links'], [])
        for next_url in ('https://example.com/leak', endpoint):
            responses[endpoint]['next'] = next_url
            with self.assertRaises(ValueError):
                history_evidence('42', 0, 2026, responses.__getitem__, '2026-11-01')

    def test_installation_error_restores_previous_directory(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source, get, _ = self.fixture(root)
            before = {p.relative_to(source): p.read_bytes() for p in source.rglob('*.json')}
            rename = Path.rename
            def fail_install(path, target):
                if path.name == 'performance_evidence' and path != source:
                    raise OSError('simulated replacement failure')
                return rename(path, target)
            with patch.object(Path, 'rename', fail_install):
                with self.assertRaisesRegex(OSError, 'replacement failure'):
                    collect(root, get=get, workers=1, progress=lambda _: None)
            self.assertEqual(before, {p.relative_to(source): p.read_bytes() for p in source.rglob('*.json')})
            self.assertFalse(list((root / 'data').glob('.performance-api-*')))

    def test_client_retries_transient_errors_but_stops_on_access_and_rate_limit(self):
        for status in (401, 403, 429):
            error = HTTPError(API, status, 'denied', {}, None)
            with patch('mega.inputs.performance_api.urlopen', side_effect=error) as request:
                with self.assertRaises(HTTPError):
                    APIClient().get(API + 'games/1/')
                self.assertEqual(request.call_count, 1)
        error = HTTPError(API, 503, 'temporary', {}, None)
        with patch('mega.inputs.performance_api.urlopen', side_effect=error) as request, \
                patch('mega.inputs.performance_api.time.sleep'):
            with self.assertRaises(HTTPError):
                APIClient(retries=2).get(API + 'games/1/')
            self.assertEqual(request.call_count, 3)
        with self.assertRaises(ValueError):
            APIClient().get('https://example.com/')

    def test_transport_sends_no_credentials_and_rejects_html(self):
        response = MagicMock()
        response.__enter__.return_value = response
        response.geturl.return_value = API + 'games/1/'
        response.headers = Message()
        response.headers['Content-Type'] = 'application/json'
        response.read.return_value = b'{"pk":1}'
        with patch('mega.inputs.performance_api.urlopen', return_value=response) as request:
            self.assertEqual(APIClient().get(API + 'games/1/'), {'pk': 1})
            headers = dict(request.call_args.args[0].header_items())
            self.assertNotIn('Cookie', headers)
            self.assertNotIn('Authorization', headers)
        response.headers.replace_header('Content-Type', 'text/html')
        with patch('mega.inputs.performance_api.urlopen', return_value=response):
            with self.assertRaisesRegex(ValueError, 'did not return JSON'):
                APIClient().get(API + 'games/1/')


if __name__ == '__main__':
    unittest.main()
