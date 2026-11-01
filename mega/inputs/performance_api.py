"""Download and validate snapshot-bound NeonSportz evidence without a browser."""
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import csv
import hashlib
import json
from pathlib import Path
import shutil
import tempfile
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlsplit
from urllib.request import Request, urlopen

from mega.inputs.games import flag
from mega.inputs.evidence_bundle import evidence_source, pack_evidence
from mega.stats.performance import COUNTS, MAXIMA, TEAM_YARDS, build_performance

BASE = 'https://neonsportz.com'
API = BASE + '/api/leagues/MEGA/'
INPUTS = ('MEGA_games.csv', 'MEGA_teams.csv', *(f'MEGA_{name}.csv' for name in COUNTS),
          'docs/data/import_metadata.json')
CATEGORY_FIELDS = dict(passing='passAtt', rushing='rushAtt', receiving='recCatches',
                       defense='defTotalTackles', kicking='fGAtt', punting='puntAtt')
GAME_FIELDS = ('pk', 'homeScore', 'awayScore', 'weekIndex', 'gameId', 'stageIndex',
               'seasonIndex', 'status', 'simmed', 'home_fw', 'away_fw', 'is_superseded')
PLAYER_FIELDS = {'id', 'statId', 'game', 'seasonIndex', 'stageIndex', 'weekIndex',
                 'game_is_superseded', 'fantasy_points'}
PLAYER_FIELDS.update(field for mapping in COUNTS.values() for field in mapping.values())
PLAYER_FIELDS.update(field for mapping in MAXIMA.values() for field in mapping.values())
TEAM_FIELDS = {'id', 'statId', 'game', 'seasonIndex', 'stageIndex', 'weekIndex',
               'tODiff', *TEAM_YARDS}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False, allow_nan=False) + '\n', encoding='utf-8')


class APIClient:
    """Public read-only requests; no browser session or credentials are used."""

    def __init__(self, timeout=30, retries=3):
        self.timeout = timeout
        self.retries = retries

    def get(self, url):
        if not url.startswith(API) or urlsplit(url).netloc != 'neonsportz.com':
            raise ValueError('Unexpected API URL')
        request = Request(url, headers={'Accept': 'application/json', 'User-Agent': 'MEGA-performance-import/1'})
        for attempt in range(self.retries + 1):
            try:
                with urlopen(request, timeout=self.timeout) as response:
                    if not response.geturl().startswith(API):
                        raise ValueError('API redirected outside the league API')
                    if response.headers.get_content_type() != 'application/json':
                        raise ValueError('API did not return JSON')
                    return json.load(response)
            except HTTPError as exc:
                # Rate limits stop acquisition, rather than increasing traffic.
                if exc.code not in {500, 502, 503, 504} or attempt == self.retries:
                    raise
            except (URLError, TimeoutError):
                if attempt == self.retries:
                    raise
            time.sleep(min(2 ** attempt, 8))


def game_evidence(game, get, date):
    game_id = game['id']
    if not game_id.isdecimal():
        raise ValueError('Invalid exported game page ID')
    prefix = API + f'games/{game_id}/'
    identity = get(prefix)
    team_rows = get(prefix + 'stats/teams/')
    player_rows = get(prefix + 'stats/players/')
    if not isinstance(identity, dict) or not isinstance(team_rows, list) or not isinstance(player_rows, list):
        raise ValueError(f'Unexpected game API schema: {game_id}')
    captured = {key: identity[key] for key in GAME_FIELDS}
    if str(captured['pk']) != game_id:
        raise ValueError('API returned a different game')
    for key in ('homeScore', 'awayScore', 'weekIndex', 'gameId', 'stageIndex', 'seasonIndex', 'status'):
        if str(captured[key]) != game[key]:
            raise ValueError(f'API and export disagree on {key}: {game_id}; refresh the exports')
    for key in ('home_fw', 'away_fw', 'is_superseded'):
        if flag(captured[key]) != flag(game[key]):
            raise ValueError(f'API and export disagree on {key}: {game_id}')
    sides = {}
    expected = {game['homeTeam'], game['awayTeam']}
    if len(team_rows) != 2 or {row['team']['displayName'] for row in team_rows} != expected:
        raise ValueError(f'Unexpected team-game inventory: {game_id}')
    seen = set()
    for side in ('home', 'away'):
        name = game[side + 'Team']
        team = next(row for row in team_rows if row['team']['displayName'] == name)
        obj = dict(team=name, teamStats={key: team[key] for key in sorted(TEAM_FIELDS)},
                   categories={key: [] for key in CATEGORY_FIELDS}, players={})
        for row in player_rows:
            if row['team']['displayName'] not in expected:
                raise ValueError('Player stat has an unknown team')
            if row['team']['displayName'] != name:
                continue
            row_id = str(row['id'])
            if row_id in seen:
                raise ValueError('Duplicate API player row ID')
            seen.add(row_id)
            player = {key: row[key] for key in sorted(PLAYER_FIELDS) if row.get(key) is not None}
            player.update(playerId=str(row['player']['rosterId']), playerName=row['player']['fullName'],
                          position=row['player']['position'], team=name)
            obj['players'][row_id] = player
            for category, field in CATEGORY_FIELDS.items():
                # Zero attempts still represents an observed appearance; null does not.
                if field not in row:
                    raise ValueError(f'Missing API category field: {field}')
                if row[field] is not None:
                    obj['categories'][category].append(row_id)
        sides[side] = obj
    return dict(sourceUrl=BASE + f'/leagues/MEGA/games/{game_id}', retrievedDate=date,
                acquisition='api', apiUrls=[prefix, prefix + 'stats/teams/', prefix + 'stats/players/'],
                game=captured, sides=sides)


def history_evidence(player_id, season, year, get, date):
    if not player_id.isdecimal():
        raise ValueError('Invalid exported player ID')
    endpoint = API + f'players/{player_id}/history/'
    url, visited, snapshots = endpoint, set(), {}
    while url:
        if url in visited or len(visited) >= 100 or urlsplit(url).path != urlsplit(endpoint).path:
            raise ValueError('Invalid history pagination')
        visited.add(url)
        data = get(url)
        if not isinstance(data, dict) or not isinstance(data.get('results'), list):
            raise ValueError('Unexpected player-history API schema')
        for row in data['results']:
            if int(row['seasonIndex']) != season or int(row['stageIndex']) != 1:
                continue
            week = int(row['weekIndex'])
            team = row['team']
            value = None if team is None else (team['displayName'], team['abbrName'])
            if week in snapshots and snapshots[week] != value:
                raise ValueError('Conflicting team-history snapshots')
            snapshots[week] = value
        url = urljoin(endpoint, data['next']) if data.get('next') else None
        if url and not url.startswith(endpoint):
            raise ValueError('History pagination left the player endpoint')
    if not snapshots:
        raise ValueError(f'No active-season team history for {player_id}')
    rows = []
    for week, team in sorted(snapshots.items()):
        name = team[0] if team else 'FA'
        rows.append(dict(cells=[str(year), 'Regular Season', f'Week {week + 1}', name],
                         links=[dict(text=name, href='/leagues/MEGA/teams/' + team[1])] if team else []))
    return dict(sourceUrl=BASE + f'/leagues/MEGA/players/{player_id}/history', retrievedDate=date,
                acquisition='api', apiUrls=sorted(visited),
                tables=[dict(headers=['SEASON', 'STAGE', 'WEEK', 'TEAM'], rows=rows)])


def seal_evidence(root):
    """Bind local evidence; numerical validation remains a separate mandatory gate."""
    source = root / 'data/performance_evidence'
    metadata = json.loads((root / 'docs/data/import_metadata.json').read_text())
    season = int(metadata['seasonIndex'])
    with (root / 'MEGA_games.csv').open() as stream:
        games = [g for g in csv.DictReader(stream) if g['seasonIndex'] == str(season)
                 and g['stageIndex'] == '1' and g['status'] in {'2', '3', '4'} and not flag(g['is_superseded'])]
    if not games:
        raise ValueError('No completed active-season games; refusing empty evidence')
    for game in games:
        if not (source / 'games' / (game['id'] + '.json')).is_file():
            raise ValueError(f"Missing captured game {game['id']}")
    manifest = dict(schemaVersion=1, csvSeasonIndex=season, calendarYear=int(metadata['calendarYear']),
                    snapshotId=metadata['snapshotId'], inputHashes={name: digest(root / name) for name in INPUTS},
                    evidenceHashes={p.relative_to(source).as_posix(): digest(p) for folder in ('games', 'histories')
                                    for p in sorted((source / folder).glob('*.json'))})
    write_json(source / 'manifest.json', manifest)
    return len(games)


def cached_manifest(source, season, year):
    """Only reuse hash-bound API evidence from the same franchise cycle."""
    try:
        manifest = json.loads((source / 'manifest.json').read_text())
        if (manifest['schemaVersion'] == 1 and manifest['csvSeasonIndex'] == season
                and manifest['calendarYear'] == year and isinstance(manifest['evidenceHashes'], dict)):
            return manifest
    except (OSError, ValueError, KeyError, TypeError):
        pass
    return {}


def cached_evidence(source, manifest, relative):
    expected = manifest.get('evidenceHashes', {}).get(relative)
    path = source / relative
    try:
        if expected and digest(path) == expected:
            data = json.loads(path.read_text())
            if data.get('acquisition') == 'api':
                return data
    except (OSError, ValueError, TypeError, AttributeError):
        pass
    return None


def matches_export(capture, game):
    try:
        if str(capture['game']['pk']) != game['id']:
            return False
        for key in GAME_FIELDS:
            if key == 'pk':
                continue
            if key in ('home_fw', 'away_fw', 'is_superseded', 'simmed'):
                if flag(capture['game'][key]) != flag(game.get(key, 'False')):
                    return False
            elif str(capture['game'][key]) != game[key]:
                return False
        return all(capture['sides'][side]['team'] == game[side + 'Team'] for side in ('home', 'away'))
    except (KeyError, TypeError, ValueError):
        return False


def player_inventory(captures):
    """Changes to a duplicated player's game rows invalidate their cached history."""
    players = defaultdict(set)
    for capture in captures:
        for side in capture['sides'].values():
            for row in side['players'].values():
                players[row['playerId']].add((str(row['id']), str(row['statId']), str(row['game']),
                                               str(row['weekIndex']), row['team']))
    return players


def collect(root, get=None, workers=3, progress=print, full_refresh=False):
    """Fetch changed games by default; validate the entire snapshot before installation."""
    root = Path(root).resolve()
    if workers not in range(1, 5):
        raise ValueError('Use 1–4 API workers')
    get = get or APIClient().get
    hashes = {name: digest(root / name) for name in (*INPUTS, 'spec/performance_policy.json')}
    metadata = json.loads((root / 'docs/data/import_metadata.json').read_text())
    season, year = int(metadata['seasonIndex']), int(metadata['calendarYear'])
    with (root / 'MEGA_games.csv').open() as stream:
        games = [g for g in csv.DictReader(stream) if g['seasonIndex'] == str(season)
                 and g['stageIndex'] == '1' and g['status'] in {'2', '3', '4'} and not flag(g['is_superseded'])]
    if not games or len({g['id'] for g in games}) != len(games):
        raise ValueError('Empty or duplicate completed-game inventory')
    date = datetime.now(timezone.utc).date().isoformat()
    previous = root / 'data/performance_evidence'
    if not full_refresh and (previous / 'manifest.json').is_file():
        previous = evidence_source(root)
    cache = {} if full_refresh else cached_manifest(previous, season, year)
    reusable, pending = {}, []
    old_captures = []
    for game in games:
        capture = cached_evidence(previous, cache, f"games/{game['id']}.json")
        if capture:
            old_captures.append(capture)
        if capture and matches_export(capture, game):
            reusable[game['id']] = capture
        else:
            pending.append(game)
    old_players = player_inventory(old_captures)
    progress(f"API plan: {len(pending)} games to fetch, {len(reusable)} cached" +
             (' (full refresh)' if full_refresh else ' (incremental)'))
    # Same filesystem as the destination, allowing rename publication and rollback.
    (root / 'data').mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.performance-api-', dir=root / 'data') as temporary:
        stage = Path(temporary)
        for name in hashes:
            destination = stage / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(root / name, destination)
        source = stage / 'data/performance_evidence'
        identities = defaultdict(list)
        captures_by_id = dict(reusable)
        with ThreadPoolExecutor(max_workers=workers) as pool:
            # Submit only one bounded batch: an error must not leave hundreds of
            # queued requests running after acquisition has already failed.
            for offset in range(0, len(pending), workers):
                batch = pending[offset:offset + workers]
                captures = pool.map(lambda g: game_evidence(g, get, date), batch)
                for index, (game, capture) in enumerate(zip(batch, captures), offset + 1):
                    captures_by_id[game['id']] = capture
                    if index % 20 == 0 or index == len(pending):
                        progress(f'API games: {index}/{len(pending)}')
        for game in games:
            capture = captures_by_id[game['id']]
            if game['id'] in reusable:
                destination = source / 'games' / (game['id'] + '.json')
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(previous / 'games' / destination.name, destination)
            else:
                write_json(source / 'games' / (game['id'] + '.json'), capture)
            for side in capture['sides'].values():
                for row in side['players'].values():
                    identities[(row['playerId'], row['statId'])].append(row['id'])
        players = sorted({player for (player, _), rows in identities.items() if len(rows) > 1})
        current_players = player_inventory(captures_by_id.values())
        histories_fetched = 0
        for player in players:
            relative = f'histories/{player}.json'
            history = cached_evidence(previous, cache, relative)
            if history and old_players.get(player) == current_players[player]:
                (source / 'histories').mkdir(exist_ok=True)
                shutil.copyfile(previous / relative, source / relative)
            else:
                write_json(source / relative, history_evidence(player, season, year, get, date))
                histories_fetched += 1
        progress(f'API histories: {histories_fetched} fetched, {len(players) - histories_fetched} cached; '
                 'reconciling all season totals')
        seal_evidence(stage)
        try:
            result = build_performance(stage, season)
        except (ValueError, KeyError, TypeError) as exc:
            raise ValueError(f'{exc}. Evidence was not installed; if old box scores changed without '
                             'a change in the game CSV, retry with --full-refresh.') from exc
        if any(digest(root / name) != expected for name, expected in hashes.items()):
            raise ValueError('Inputs changed during API acquisition; evidence was not installed')
        pack_evidence(source)
        result['evidenceManifestHash'] = digest(source / 'manifest.json')
        destination, backup = root / 'data/performance_evidence', stage / 'previous-evidence'
        if destination.exists():
            destination.rename(backup)
        try:
            source.rename(destination)
        except BaseException:
            if backup.exists():
                backup.rename(destination)
            raise
    result['acquisitionSummary'] = dict(gamesFetched=len(pending), gamesCached=len(reusable),
                                       historiesFetched=histories_fetched,
                                       historiesCached=len(players) - histories_fetched)
    return result
