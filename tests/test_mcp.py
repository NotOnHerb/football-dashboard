"""The MCP server, called through the SDK's in-memory client against the golden replay's data. Offline: no network,
FD_API_URL unset, add_idea writes under tmp_path."""
import asyncio, json, os, sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT); sys.path.insert(0, HERE)
import api_export  # noqa: E402
from mcp import Client  # noqa: E402
from mcp_server.data import Source  # noqa: E402
from mcp_server.server import create_server, find_players, score_name  # noqa: E402
from replay_util import replay_dir  # noqa: E402

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
    return create_server(Source(root=str(work)), ideas_path=str(tmp_path / 'ideas' / 'inbox.jsonl'))


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
    # per book without ODD.PKB: the current picks whose best price is at that book
    mine = call(server, 'get_picks', book=pk['bk'].lower())
    assert [p['id'] for p in mine['picks']] == [pk['id']] and 'no per-book picks' in mine['source']
    assert pk['bk'] != 'Pinnacle' and call(server, 'get_picks', book='Pinnacle')['picks'] == []


def test_get_picks_uses_picks_by_book_when_present(work, data, tmp_path):
    pk = data['ODD']['PK']
    other = dict(pk[0], pr=pk[0]['pr'] + 5, bk='DraftKings')
    d = tmp_path / 'root'; (d / 'api').mkdir(parents=True)
    api_export.export(dict(data, ODD=dict(data['ODD'], PKB={'DraftKings': [other], 'BetRivers': pk})), str(d / 'api' / 'v1'))
    s = create_server(Source(root=str(d)), ideas_path=str(tmp_path / 'i.jsonl'))
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
    import shutil
    shutil.copy(work / 'data.json', tmp_path / 'data.json')
    s = create_server(Source(root=str(tmp_path)), ideas_path=str(tmp_path / 'i.jsonl'))
    assert call(s, 'get_picks')['count'] == len(data['ODD']['PK'])
    # no model.json here: calibration falls back to the summary in index.json
    assert call(s, 'calibration', prop='Rec yds')['source'].startswith('index.json')
    empty = create_server(Source(root=str(tmp_path / 'nothing')), ideas_path=str(tmp_path / 'j.jsonl'))
    async def go():
        async with Client(empty) as client: return await client.call_tool('get_picks', {})
    assert asyncio.run(go()).is_error


def test_add_idea_writes_only_where_told(work, tmp_path):
    inbox = tmp_path / 'ideas' / 'inbox.jsonl'
    s = create_server(Source(root=str(work)), ideas_path=str(inbox))
    r = call(s, 'add_idea', text='  fade backup QBs on the road  ', tags=['model'])
    assert r['saved'] and inbox.exists()
    call(s, 'add_idea', text='second')
    lines = [json.loads(x) for x in inbox.read_text(encoding='utf-8').splitlines()]
    assert [x['text'] for x in lines] == ['fade backup QBs on the road', 'second'] and lines[0]['tags'] == ['model']
    assert call(s, 'add_idea', text='   ')['error']
    assert not os.path.exists(os.path.join(ROOT, 'ideas', 'inbox.jsonl'))   # the repo's own inbox was not touched
