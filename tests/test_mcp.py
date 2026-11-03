"""The MCP server, called through the SDK's in-memory client against the golden replay's data. Offline: no network,
FD_API_URL unset, add_idea writes under tmp_path."""
import asyncio, datetime, json, os, shutil, sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT); sys.path.insert(0, HERE)
import api_export  # noqa: E402
from mcp import Client  # noqa: E402
from mcp_server.data import Source  # noqa: E402
from mcp_server import server as server_module  # noqa: E402
from mcp_server.server import find_players, score_name  # noqa: E402
from replay_util import replay_dir  # noqa: E402

UTC = datetime.timezone.utc
NOW = datetime.datetime(2026, 11, 2, 12, tzinfo=UTC)   # the golden replay's frozen clock: before every kickoff in its data


def create_server(source, ideas_path, now=NOW):
    """The server with a fixed clock, so what counts as 'already kicked off' does not depend on the day the test runs."""
    return server_module.create_server(source, ideas_path=str(ideas_path), now=lambda: now)


TOOLS = {'get_week_games', 'get_picks', 'get_pick_log', 'get_player', 'get_props', 'explain_pick', 'get_team',
         'calibration', 'health', 'add_idea'}


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    monkeypatch.delenv('FD_API_URL', raising=False)


@pytest.fixture(scope='module')
def work(tmp_path_factory):
    """The replay folder with api/v1 exported into it, laid out like the repo root (data.json, model.json, api/v1/)."""
    d = replay_dir(tmp_path_factory)
    data = json.load(open(d / 'data.json', encoding='utf-8'))
    api_export.export(data, str(d / 'api' / 'v1'))
    return d


@pytest.fixture(scope='module')
def data(work):
    return json.load(open(work / 'data.json', encoding='utf-8'))


def without_pkb(data):
    """A copy of the data as an older build wrote it, with no ODD.PKB."""
    return dict(data, ODD={k: v for k, v in data['ODD'].items() if k != 'PKB'})


def call(server, name, **args):
    """One tool call through an in-memory client; returns the tool's structured result."""
    async def go():
        async with Client(server) as client:
            r = await client.call_tool(name, args)
            assert not r.is_error, r
            return r.structured_content
    return asyncio.run(go())


@pytest.fixture
def server(work, tmp_path):
    return create_server(Source(root=str(work)), tmp_path / 'ideas' / 'inbox.jsonl')


def test_mcp_tools_list(server):
    async def go():
        async with Client(server) as client: return (await client.list_tools()).tools
    tools = asyncio.run(go())
    assert {t.name for t in tools} == TOOLS
    assert all(t.description for t in tools)
    writers = [t.name for t in tools if not t.annotations.read_only_hint]
    assert writers == ['add_idea']


def test_get_picks_matches_data(server, data):
    r = call(server, 'get_picks')
    assert [p['id'] for p in r['picks']] == [p['id'] for p in data['ODD']['PK']] and r['count'] == len(data['ODD']['PK']) >= 1
    pk = data['ODD']['PK'][0]
    got = r['picks'][0]
    assert (got['player'], got['market'], got['side'], got['line'], got['price'], got['book']) == (pk['n'], pk['mk'], pk['sd'], pk['pt'], pk['pr'], pk['bk'])
    bad = call(server, 'get_picks', book='DraftKngs')   # a typo is an error that lists the books, not an empty list
    assert bad['error'] == 'no such book' and 'DraftKings' in bad['books']


def test_get_picks_per_book_matches_pkb(server, data):
    """The data has ODD.PKB (the build writes it for every book): each book's picks are exactly its PKB list."""
    assert set(data['ODD']['PKB']) == set(data['ODD']['books'])
    for bk, want in data['ODD']['PKB'].items():
        r = call(server, 'get_picks', book=bk.lower())
        assert r['book'] == bk and 'picks_by_book' in r['source'] and 'SUBSET' not in r['source']
        assert [p['id'] for p in r['picks']] == [p['id'] for p in want] and r['count'] == len(want)
        for got, pk in zip(r['picks'], want):
            assert (got['player'], got['side'], got['line'], got['price'], got['book']) == (pk['n'], pk['sd'], pk['pt'], pk['pr'], pk['bk'])
    assert any(data['ODD']['PKB'].values())


def test_explain_pick_finds_book_only_picks_and_book_versions(data, tmp_path):
    """A side can be official at one book's prices without being in ODD.PK; get_picks(book) returns it, so explain_pick must find it."""
    pk = data['ODD']['PK'][0]
    only = dict(pk, id=pk['id'].rsplit('|', 2)[0] + '|Rec yds|o', sd='o', pr=-105, bk='DraftKings')   # in DraftKings' list alone
    differs = dict(pk, pr=pk['pr'] + 7, bk='DraftKings')                                               # same id, DraftKings' own price
    pkb = {bk: list(v) for bk, v in data['ODD']['PKB'].items()}
    pkb['DraftKings'] = [only, differs]
    d = tmp_path / 'root'; (d / 'api').mkdir(parents=True)
    api_export.export(dict(data, ODD=dict(data['ODD'], PKB=pkb)), str(d / 'api' / 'v1'))
    s = create_server(Source(root=str(d)), tmp_path / 'i.jsonl')
    assert only['id'] not in [p['id'] for p in data['ODD']['PK'] + data['ODD']['LG']]   # really absent from PK and the log
    listed = [p['id'] for p in call(s, 'get_picks', book='draftkings')['picks']]
    assert only['id'] in listed
    r = call(s, 'explain_pick', pick_id=only['id'])             # found by searching every book's list, and says whose
    assert r['book_version'] == 'DraftKings' and "DraftKings's version" in r['reasons'][0] and r['pick']['price'] == -105
    r = call(s, 'explain_pick', pick_id=only['id'], book='DRAFTKINGS')
    assert r['book_version'] == 'DraftKings' and r['pick']['price'] == -105
    # an id that is also in PK: no book means the best-price pick, with a book it is that book's version
    best = call(s, 'explain_pick', pick_id=pk['id'])
    assert best['book_version'] is None and best['pick']['price'] == pk['pr']
    mine = call(s, 'explain_pick', pick_id=pk['id'], book='DraftKings')
    assert mine['book_version'] == 'DraftKings' and mine['pick']['price'] == differs['pr'] and 'can differ' in mine['reasons'][0]
    assert call(s, 'explain_pick', pick_id=pk['id'], book='Nope')['error'] == 'no such book'
    assert 'error' in call(s, 'explain_pick', pick_id='p|nope', book='DraftKings')


def test_get_picks_per_book_keeps_the_kickoff_filter(work, data, tmp_path):
    ko = datetime.datetime.fromisoformat(data['ODD']['G'][0]['t'].replace('Z', '+00:00'))
    s = create_server(Source(root=str(work)), tmp_path / 'i.jsonl', now=ko + datetime.timedelta(minutes=1))
    assert all(call(s, 'get_picks', book=bk)['picks'] == [] for bk in data['ODD']['PKB'])


def test_get_picks_without_pkb_falls_back_to_a_subset(data, tmp_path):
    """Older data (or a build without ODD.PKB): the current picks whose best price is at that book, said plainly."""
    d = tmp_path / 'root'; (d / 'api').mkdir(parents=True)
    api_export.export(without_pkb(data), str(d / 'api' / 'v1'))
    assert not (d / 'api' / 'v1' / 'picks_by_book.json').exists()
    s = create_server(Source(root=str(d)), tmp_path / 'i.jsonl')
    pk = data['ODD']['PK'][0]
    mine = call(s, 'get_picks', book=pk['bk'].lower())
    assert [p['id'] for p in mine['picks']] == [pk['id']] and 'no per-book picks' in mine['source'] and 'SUBSET' in mine['source']
    assert pk['bk'] != 'Pinnacle' and call(s, 'get_picks', book='Pinnacle')['picks'] == []
    assert call(s, 'get_picks', book='DraftKngs')['error'] == 'no such book'


def test_get_picks_uses_picks_by_book_when_present(work, data, tmp_path):
    pk = data['ODD']['PK']
    other = dict(pk[0], pr=pk[0]['pr'] + 5, bk='DraftKings')
    d = tmp_path / 'root'; (d / 'api').mkdir(parents=True)
    api_export.export(dict(data, ODD=dict(data['ODD'], PKB={'DraftKings': [other], 'BetRivers': pk})), str(d / 'api' / 'v1'))
    s = create_server(Source(root=str(d)), tmp_path / 'i.jsonl')
    r = call(s, 'get_picks', book='draftkings')
    assert r['book'] == 'DraftKings' and 'picks_by_book' in r['source'] and r['picks'][0]['price'] == other['pr']
    assert call(s, 'get_picks', book='Nope')['error'] == 'no such book'


def test_explain_pick_has_reasons(server, data):
    pk = data['ODD']['PK'][0]
    r = call(server, 'explain_pick', pick_id=pk['id'])
    assert r['id'] == pk['id'] and r['reasons'] and all(isinstance(x, str) and x for x in r['reasons'])
    text = ' '.join(r['reasons'])
    assert 'Lean' in text and 'Total score %s' % pk['s'] in text and str(pk['n']) in r['summary']
    assert r['scores']['needed_for_a_pick'] == data['ODD']['RU']['pick'] and r['scores']['lean'] == pk['ls']
    assert r['pick']['id'] == pk['id']
    assert 'error' in call(server, 'explain_pick', pick_id='p|nope')


def test_explain_pick_covers_logged_and_parlay_picks(server, data):
    graded = next(p for p in data['ODD']['LG'] if p['k'] == 'p' and p.get('res'))
    r = call(server, 'explain_pick', pick_id=graded['id'])
    assert any(x.startswith('Result: %s' % graded['res']) for x in r['reasons'])
    parlay = next(p for p in data['ODD']['LG'] if p['k'] == 'x')
    r = call(server, 'explain_pick', pick_id=parlay['id'])
    assert sum(1 for x in r['reasons'] if x.startswith('Leg:')) == len(parlay['legs'])


def test_get_player_by_name(server, data):
    r = call(server, 'get_player', query='jaxon smith njigba')
    assert r['player']['name'] == 'Jaxon Smith-Njigba' and r['player']['team'] == 'SEA'
    row = next(x for x in data['P']['WR'] if x[0] == 'Jaxon Smith-Njigba')
    assert r['player']['vals']['PPR/g'] == row[3][0] and r['player']['gsis_id'] == row[8] and r['player']['log']
    gid = r['player']['gsis_id']
    assert call(server, 'get_player', query=gid)['player']['gsis_id'] == gid
    assert call(server, 'get_player', query='Colston Lovelan')['player']['name'] == 'Colston Loveland'   # a typo still finds him
    loveland = call(server, 'get_player', query='loveland')
    assert [p['market'] for p in loveland['picks']] == [data['ODD']['PK'][0]['mk']]
    assert 'error' in call(server, 'get_player', query='zzzzqq')


def test_name_matching_rules():
    ps = [{'name': "Ja'Marr Chase", 'gsis_id': '00-1'}, {'name': 'Jaxon Smith-Njigba', 'gsis_id': '00-2'}, {'name': 'Amon-Ra St. Brown', 'gsis_id': '00-3'}]
    assert find_players(ps, 'jamarr chase')[0]['gsis_id'] == '00-1'
    assert find_players(ps, 'st brown')[0]['gsis_id'] == '00-3'
    assert find_players(ps, '00-2')[0]['name'] == 'Jaxon Smith-Njigba'
    assert score_name('chase', "Ja'Marr Chase") > 0 and score_name('xyz', 'Chase') == 0


def test_get_props_and_team_and_games(server, data):
    r = call(server, 'get_props')
    assert r['matching'] == len(data['ODD']['P'])
    g = data['ODD']['G'][0]
    both = call(server, 'get_props', game='%s@%s' % (g['a'], g['h']))
    assert both['matching'] == len(data['ODD']['P']) and call(server, 'get_props', game=g['id'])['matching'] == both['matching']
    assert call(server, 'get_props', game='KC')['matching'] == 0
    one = call(server, 'get_props', player='loveland')
    assert {p['player'] for p in one['props']} == {'Colston Loveland'}
    assert len(call(server, 'get_props', limit=3)['props']) == 3
    w = call(server, 'get_week_games')
    assert w['week'] == g['wk'] and w['games'][0]['picks'] == [data['ODD']['PK'][0]['id']]
    t = call(server, 'get_team', code='chi')
    assert t['team']['code'] == 'CHI' and t['games'][0]['home'] == 'SEA' and len(t['picks']) == 1
    assert call(server, 'get_team', code='Bears')['team']['code'] == 'CHI'
    assert 'error' in call(server, 'get_team', code='XXX')


def test_get_pick_log_filters_and_record(server, data):
    lg = data['ODD']['LG']
    r = call(server, 'get_pick_log', kind='prop', result='L', limit=2)
    want = [p for p in lg if p['k'] == 'p' and p.get('res') == 'L']
    assert r['matching'] == len(want) and len(r['picks']) <= 2 and r['record']['l'] == len(want) and r['record']['w'] == 0
    assert [p['id'] for p in r['picks']] == [p['id'] for p in want][:2]
    assert call(server, 'get_pick_log', kind='parlay')['matching'] == sum(1 for p in lg if p['k'] == 'x')
    pend = call(server, 'get_pick_log', result='pending')
    assert pend['matching'] == sum(1 for p in lg if p.get('res') is None)
    assert call(server, 'get_pick_log', week=999)['matching'] == 0
    assert 'error' in call(server, 'get_pick_log', kind='nonsense')


def test_calibration_health_and_missing_college_data(server, data):
    c = call(server, 'calibration', prop='rec yds', projection=50, line=44.5)
    assert c['prop'] == 'Rec yds' and c['source'] == 'model.json' and c['calibration_shift'] == data['ODD']['MC']['Rec yds']
    assert 0.01 <= c['model_chance_over'] <= 0.99 and c['sample_size'] > 0
    assert 'usage model' in call(server, 'calibration', prop='Anytime TD')['note']
    assert 'available' in call(server, 'calibration', prop='Sacks')
    h = call(server, 'health')
    assert h['ok'] is True and h['sections'] == data['META']['health'] and h['week'] == data['ODD']['G'][0]['wk']
    assert data['CF'] is None   # tools that read college data work without it
    assert call(server, 'get_pick_log', kind='college')['matching'] == len(data['CFB']['LG'])


def test_source_builds_from_data_json_when_there_is_no_api_folder(work, tmp_path, data):
    shutil.copy(work / 'data.json', tmp_path / 'data.json')
    s = create_server(Source(root=str(tmp_path)), tmp_path / 'i.jsonl')
    assert call(s, 'get_picks')['count'] == len(data['ODD']['PK'])
    # no model.json here: calibration falls back to the summary in index.json
    assert call(s, 'calibration', prop='Rec yds')['source'].startswith('index.json')
    empty = create_server(Source(root=str(tmp_path / 'nothing')), tmp_path / 'j.jsonl')
    async def go():
        async with Client(empty) as client: return await client.call_tool('get_picks', {})
    assert asyncio.run(go()).is_error


def test_add_idea_writes_only_where_told(work, tmp_path):
    before = repo_inbox()
    inbox = tmp_path / 'ideas' / 'inbox.jsonl'
    s = create_server(Source(root=str(work)), inbox)
    r = call(s, 'add_idea', text='  fade backup QBs on the road  ', tags=['model'])
    assert r['saved'] and inbox.exists()
    call(s, 'add_idea', text='second')
    lines = [json.loads(x) for x in inbox.read_text(encoding='utf-8').splitlines()]
    assert [x['text'] for x in lines] == ['fade backup QBs on the road', 'second'] and lines[0]['tags'] == ['model']
    assert call(s, 'add_idea', text='   ')['error']
    assert repo_inbox() == before   # the repo's own inbox was not touched (it may exist: the owner's real ideas)


def repo_inbox():
    """(size, mtime) of the repo's own ideas/inbox.jsonl, or None if it does not exist."""
    p = os.path.join(ROOT, 'ideas', 'inbox.jsonl')
    return (os.path.getsize(p), os.path.getmtime(p)) if os.path.exists(p) else None


# ---------------------------------------------------------------- already-kicked-off games are not current

def test_started_games_picks_and_props_are_not_current(work, data, tmp_path):
    ko = data['ODD']['G'][0]['t']
    kickoff = datetime.datetime.fromisoformat(ko.replace('Z', '+00:00'))
    s = create_server(Source(root=str(work)), tmp_path / 'i.jsonl', now=kickoff + datetime.timedelta(minutes=1))
    assert call(s, 'get_picks')['picks'] == [] and call(s, 'get_picks', book='BetRivers')['picks'] == []
    w = call(s, 'get_week_games')
    assert w['games'] == [] and w['remaining'] == []
    assert call(s, 'get_props')['matching'] == 0
    t = call(s, 'get_team', code='CHI')
    assert t['games'] == [] and t['picks'] == []
    assert call(s, 'get_player', query='loveland')['picks'] == []
    # history is kept: the log and explanations still work
    assert call(s, 'get_pick_log')['matching'] == len(data['ODD']['LG']) + len(data['CFB']['LG'])
    assert call(s, 'explain_pick', pick_id=data['ODD']['PK'][0]['id'])['reasons']
    s = create_server(Source(root=str(work)), tmp_path / 'i.jsonl', now=kickoff - datetime.timedelta(minutes=1))
    assert call(s, 'get_picks')['count'] == 1 and len(call(s, 'get_week_games')['games']) == 1


# ---------------------------------------------------------------- explanations quote the rules, not copies of them

def server_with(data, tmp_path, odd_pk=(), cfb_pk=(), cfb_lg=()):
    """A server over a folder whose api/v1 has extra picks added to the replay's data."""
    d = tmp_path / 'root'; (d / 'api').mkdir(parents=True)
    full = dict(data, ODD=dict(data['ODD'], PK=list(odd_pk) + data['ODD']['PK']),
                CFB=dict(data['CFB'], PK=list(cfb_pk), LG=list(cfb_lg) + data['CFB']['LG']))
    api_export.export(full, str(d / 'api' / 'v1'))
    return create_server(Source(root=str(d)), tmp_path / 'i.jsonl')


def college_pick(data, **kw):
    base = dict(data['CFB']['LG'][0], res=None); base.pop('fin', None); base.pop('u', None)
    return dict(base, **kw)


def test_explain_college_pick_uses_the_college_rules(data, tmp_path):
    from engine import rules as R
    cp = college_pick(data, s=1, gap=1.2)
    graded = dict(college_pick(data, id='c|1|hs'), res='W', fin=[10, 20], u=0.87)
    s = server_with(data, tmp_path, cfb_pk=[cp], cfb_lg=[graded])
    r = call(s, 'explain_pick', pick_id=cp['id'])
    text = ' '.join(r['reasons'])
    assert r['scores']['needed_for_a_pick'] == R.COLLEGE_MIN_SCORE == 1 and r['scores']['total'] == 1
    assert 'at least %d books' % R.COLLEGE_MIN_BOOKS in text and 'Pinnacle' in text and '%+d' % R.COLLEGE_MIN_PRICE in text
    assert 'Total score' not in text    # the NFL "needed 2" line does not apply to college
    assert call(s, 'explain_pick', pick_id=graded['id'])['reasons'][-1].startswith('Result: W')   # a graded pick ends with its result


def test_explain_anytime_td_uses_the_td_rule(data, tmp_path):
    from engine import rules as R
    td = next(p for p in data['ODD']['P'] if p['mk'] == 'Anytime TD')
    bk, x = next(iter(td['b'].items()))
    pick = {'id': 'p|%s|%s|Anytime TD|y' % (td['eid'], td['gid']), 'k': 'p', 'eid': td['eid'], 'wk': 8, 't': td['ko'], 'n': td['n'], 'gid': td['gid'],
            'tm': td['t'], 'opp': td['opp'], 'mk': 'Anytime TD', 'sd': 'y', 'pt': None, 'pr': x[1], 'bk': bk, 's': 2, 'v': None, 'ls': 2, 'vs': 0,
            'pj': td['pj'], 'pc': 0.6, 'srt': 1.0}
    r = call(server_with(data, tmp_path, odd_pk=[pick]), 'explain_pick', pick_id=pick['id'])
    text = ' '.join(r['reasons'])
    assert 'value score is not used for anytime TDs' in text and 'fair price is not used' not in text and '+%d or shorter' % data['ODD']['RU']['tdmax'] in text
    assert 'at least %d games' % R.LEAN_MIN_GAMES in text
    assert 'value' not in r['scores'] and 'Value scores are' not in text and 'needs a line of at least' not in text


def test_explain_numbers_come_from_engine_rules(server, data, monkeypatch):
    from engine import rules as R
    pk = data['ODD']['PK'][0]
    text = ' '.join(call(server, 'explain_pick', pick_id=pk['id'])['reasons'])
    assert 'Lean tiers are 1 at 4 points, 2 at 7 and 3 at 10' in text and 'at least 4 games' in text and 'at most 2 toward' in text
    monkeypatch.setattr(R, 'LEAN_TIERS', (.05, .08, .11))
    monkeypatch.setattr(R, 'LEAN_MIN_GAMES', 6)
    monkeypatch.setattr(R, 'LEAN_MAX_SCORE', 3)
    text = ' '.join(call(server, 'explain_pick', pick_id=pk['id'])['reasons'])
    assert 'Lean tiers are 1 at 5 points, 2 at 8 and 3 at 11' in text and 'at least 6 games' in text and 'at most 3 toward' in text


def test_college_scores_come_from_engine_rules(data, tmp_path, monkeypatch):
    from engine import rules as R
    cp = college_pick(data)
    s = server_with(data, tmp_path, cfb_pk=[cp])
    assert 'score 2 from a gap of 1.5 points, else 1.' in ' '.join(call(s, 'explain_pick', pick_id=cp['id'])['reasons'])
    monkeypatch.setattr(R, 'COLLEGE_STRONG_SCORE', 5)
    assert 'score 5 from a gap of 1.5 points' in ' '.join(call(s, 'explain_pick', pick_id=cp['id'])['reasons'])
    build = open(os.path.join(ROOT, 'build.py'), encoding='utf-8').read()
    assert "'s':COLLEGE_STRONG_SCORE if abs(d)>=COLLEGE_GAP_STRONG else COLLEGE_MIN_SCORE" in build


def test_week_games_without_odds_lines_still_lists_the_schedule(data, tmp_path):
    """When the odds section failed (ODD.G empty) the schedule rows from G are still the week's games."""
    d = tmp_path / 'root'; (d / 'api').mkdir(parents=True)
    api_export.export(dict(data, ODD=dict(data['ODD'], G=[], PK=[], P=[])), str(d / 'api' / 'v1'))
    w = call(create_server(Source(root=str(d)), tmp_path / 'i.jsonl'), 'get_week_games')
    assert w['games'] == [] and [(r['away'], r['home']) for r in w['remaining']] == [tuple(data['G'][0][:2])]


def test_the_engine_reads_the_same_constants():
    """The rule numbers are named once, and the pick code uses the names (a change there changes picks and explanations together)."""
    from engine import rules as R
    assert R.LEAN_TIERS == (.04, .07, .10) and R.LEAN_MIN_GAMES == 4 and R.LEAN_MAX_SCORE == 2
    assert [R.lean_tier(e) for e in (.039, .04, .07, .10)] == [0, 1, 2, 3]
    assert (R.COLLEGE_MIN_BOOKS, R.COLLEGE_GAP_MIN, R.COLLEGE_GAP_MAX, R.COLLEGE_GAP_STRONG, R.COLLEGE_MIN_PRICE) == (3, 1, 3, 1.5, -118)
    src = open(os.path.join(ROOT, 'engine', 'picks.py'), encoding='utf-8').read()
    assert 'LEAN_MIN_GAMES' in src and 'LEAN_MAX_SCORE' in src and 'n >= 4' not in src


# ---------------------------------------------------------------- the data source stays current

def test_source_rereads_a_changed_file_and_prefers_newer_data_json(tmp_path, data):
    root = tmp_path / 'r'; (root / 'api').mkdir(parents=True)
    api_export.export(data, str(root / 'api' / 'v1'))
    src = Source(root=str(root))
    assert len(src.get('picks')) == 1
    p = root / 'api' / 'v1' / 'picks.json'
    p.write_text('[]', encoding='utf-8'); os.utime(p, (1, 2))   # rewritten on disk: a long-running server sees it
    assert src.get('picks') == []
    newer = json.loads(json.dumps(data)); newer['META']['built'] = 'Dec 31, 2026 at 23:59 UTC'   # data.json built after the api files
    (root / 'data.json').write_text(json.dumps(newer), encoding='utf-8')
    assert len(src.get('picks')) == 1 and src.get('index')['built'] == 'Dec 31, 2026 at 23:59 UTC'
    (root / 'data.json').write_text(json.dumps(data), encoding='utf-8')   # same build time as the api files: the api files are used
    assert src.get('picks') == []


def test_remote_source_caches_for_a_while_and_not_failures(monkeypatch):
    import io, urllib.error
    from mcp_server import data as data_module
    calls = []; answers = [OSError('dns'), {'a': 1}, {'a': 2}]

    class Resp(io.BytesIO):
        def __enter__(self): return self
        def __exit__(self, *a): return False

    def fake_urlopen(url, timeout=0):
        calls.append(url)
        if url.endswith('/gone.json'): raise urllib.error.HTTPError(url, 404, 'nf', {}, None)
        a = answers.pop(0)
        if isinstance(a, Exception): raise a
        return Resp(json.dumps(a).encode())
    monkeypatch.setattr(data_module.urllib.request, 'urlopen', fake_urlopen)
    t = [0.0]
    src = Source(base_url='https://example.test/api/v1/', ttl=300, clock=lambda: t[0])
    with pytest.raises(RuntimeError, match='could not reach'): src.get('x')   # a network failure is an error, never cached as "no file"
    assert src.get('x') == {'a': 1} and src.get('x') == {'a': 1} and len(calls) == 2   # then cached
    t[0] = 301
    assert src.get('x') == {'a': 2}                                                     # and fetched again after the TTL
    assert src.get('gone') is None and src.get('gone') is None and calls.count('https://example.test/api/v1/gone.json') == 1   # a real 404 is cached


def test_tools_say_whether_they_reach_the_network(work, tmp_path):
    async def hints(srv):
        async with Client(srv) as client: return {t.name: t.annotations.open_world_hint for t in (await client.list_tools()).tools}
    local = asyncio.run(hints(create_server(Source(root=str(work)), tmp_path / 'i.jsonl')))
    remote = asyncio.run(hints(create_server(Source(base_url='https://example.test/api/v1'), tmp_path / 'i.jsonl')))
    assert not any(local.values())
    assert remote['get_picks'] is True and remote['add_idea'] is False
