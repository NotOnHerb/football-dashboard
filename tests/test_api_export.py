"""api_export.py turns data.json into named-field files under api/v1/. Input is the golden replay's data.json."""
import json, os, subprocess, sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT); sys.path.insert(0, HERE)
import api_export  # noqa: E402
from replay_util import replay_data  # noqa: E402

FILES = ['index', 'players', 'teams', 'games', 'picks', 'props', 'pick_log', 'dynasty', 'college', 'health']


@pytest.fixture(scope='module')
def data(tmp_path_factory):
    return replay_data(tmp_path_factory)


@pytest.fixture(scope='module')
def out(data, tmp_path_factory):
    d = tmp_path_factory.mktemp('api') / 'v1'
    written = api_export.export(data, str(d))
    return d, written


def load(out_dir, name):
    with open(out_dir / (name + '.json'), encoding='utf-8') as f: return json.load(f)


def test_export_writes_every_file(out):
    d, written = out
    for name in FILES + ['data.schema']: assert (d / (name + '.json')).exists(), name
    assert sorted(os.path.basename(p) for p in written) == sorted(n + '.json' for n in FILES + ['data.schema'])
    assert (d / 'data.schema.json').read_bytes() == open(os.path.join(ROOT, 'schema', 'data.schema.json'), 'rb').read()


def test_export_rows_are_named(out, data):
    d, _ = out
    pl = load(d, 'players')
    assert pl[0]['gsis_id'] and pl[0]['team']
    assert all(p['gsis_id'] and p['team'] for p in pl)
    wr = next(p for p in pl if p['kind'] == 'offense' and p['pos'] == 'WR')
    assert list(wr['vals']) == [c[0] for c in data['PC']['WR']]   # stats are labelled, not positional
    assert wr['depth_label'] is None or set(wr['depth_label']) == {'label', 'starter'}
    t = load(d, 'teams')
    assert len(t) == 32 and set(t[0]['stats']) == {c[0] for c in data['TC']}
    # game logs ride along with the player
    logged = next(p for p in pl if p['log'])
    assert set(logged['log'][0]) == set(api_export.rows_named('LOG', [data['LOG'][logged['gsis_id']][0]])[0])


def unname(p, keys):
    """The inverse of api_export.name_pick, for the test: back to data.json's short keys."""
    back = {v: k for k, v in keys.items()}
    out = {back.get(k, k): v for k, v in p.items() if k != 'sport'}
    if isinstance(out.get('first'), dict): out['first'] = {{v: k for k, v in api_export.FIRST_KEYS.items()}.get(k, k): v for k, v in out['first'].items()}
    if isinstance(out.get('legs'), list): out['legs'] = [unname(l, keys) for l in out['legs']]
    return out


def test_export_is_lossless_for_picks(out, data):
    d, _ = out
    assert len(set(api_export.PICK_KEYS.values())) == len(api_export.PICK_KEYS)   # no two short keys share a name
    picks = load(d, 'picks')
    assert picks and [unname(p, api_export.PICK_KEYS) for p in picks] == data['ODD']['PK']
    log = load(d, 'pick_log')
    nfl = [p for p in log if p['sport'] == 'nfl']
    assert [unname(p, api_export.PICK_KEYS) for p in nfl] == data['ODD']['LG']
    assert any(p['type'] == 'x' and p['legs'] for p in nfl)   # parlay legs are renamed too
    college = [unname(p, api_export.COLLEGE_PICK_KEYS) for p in log if p['sport'] == 'college']
    assert college and college == data['CFB']['LG']


def test_college_picks_are_lossless_too(data, tmp_path):
    """The replay has no current college picks, so add one shaped like build.py's."""
    cp = dict(data['CFB']['LG'][0], res=None); cp.pop('fin', None); cp.pop('u', None)
    full = dict(data, CFB=dict(data['CFB'], PK=[cp]))
    api_export.export(full, str(tmp_path))
    picks = load(tmp_path, 'picks')
    assert [p['sport'] for p in picks] == ['nfl', 'college']
    assert unname(picks[1], api_export.COLLEGE_PICK_KEYS) == cp
    assert {'game_id', 'others_line', 'book_lines'} <= set(picks[1])
    assert len(set(api_export.COLLEGE_PICK_KEYS.values())) == len(api_export.COLLEGE_PICK_KEYS)
    assert len(set(api_export.FIRST_KEYS.values())) == len(api_export.FIRST_KEYS)


def test_export_handles_missing_college_data(out, data):
    d, _ = out
    assert data['CF'] is None   # the replay has no prospect data
    c = load(d, 'college')
    assert c['prospects'] is None and c['big_board'] is None and c['big_board_sources'] is None   # null, not empty
    assert len(c['games']) == len(data['CFB']['G'])
    book = next(iter(c['games'][0]['books'].values()))
    assert set(book) <= set(api_export.COLLEGE_BOOK_FIELDS) and 'home_spread' in book


def test_export_removes_files_this_build_did_not_write(data, tmp_path):
    with_pkb = dict(data, ODD=dict(data['ODD'], PKB={'BetRivers': []}))
    api_export.export(with_pkb, str(tmp_path))
    assert (tmp_path / 'picks_by_book.json').exists()
    (tmp_path / 'notes.txt').write_text('keep'); (tmp_path / 'other.json').write_text('{}')
    api_export.export(data, str(tmp_path))   # the next build has no PKB
    assert not (tmp_path / 'picks_by_book.json').exists() and (tmp_path / 'picks.json').exists()
    assert (tmp_path / 'notes.txt').exists() and (tmp_path / 'other.json').exists()   # only the API's own files are ever removed
    assert set(api_export.API_FILES) >= {os.path.basename(p)[:-5] for p in api_export.export(with_pkb, str(tmp_path / 'x'))}


def test_export_refuses_a_folder_that_holds_data_json(data, tmp_path):
    """`python api_export.py data.json .` must not delete or overwrite anything in the repo root."""
    (tmp_path / 'data.json').write_text('{"keep": true}'); (tmp_path / 'model.json').write_text('{"keep": true}')
    with pytest.raises(ValueError, match='holds a data.json'): api_export.export(data, str(tmp_path))
    assert json.load(open(tmp_path / 'data.json')) == {'keep': True} and json.load(open(tmp_path / 'model.json')) == {'keep': True}
    assert sorted(os.listdir(tmp_path)) == ['data.json', 'model.json']
    src = tmp_path / 'in.json'; src.write_text(json.dumps(data), encoding='utf-8')
    r = subprocess.run([sys.executable, os.path.join(ROOT, 'api_export.py'), str(src), str(tmp_path)], capture_output=True, text=True,
                       env=dict(os.environ, PYTHONUTF8='1'))
    assert r.returncode != 0 and json.load(open(tmp_path / 'model.json')) == {'keep': True}


def test_export_games_props_and_health(out, data):
    d, _ = out
    g = load(d, 'games')
    assert g['week'] == data['ODD']['G'][0]['wk'] and len(g['lines']) == len(data['ODD']['G'])
    line = g['lines'][0]
    assert line['away'] == data['ODD']['G'][0]['a'] and 'moneyline' in next(iter(line['books'].values()))
    assert line['label']   # joined from G
    pr = load(d, 'props')
    assert len(pr) == len(data['ODD']['P']) and {'player', 'gsis_id', 'market', 'books'} <= set(pr[0])
    h = load(d, 'health')
    assert h['sections'] == data['META']['health'] and h['ok'] is True
    ix = load(d, 'index')
    assert ix['season'] == data['META']['season'] and ix['rules'] == data['ODD']['RU'] and ix['counts']['picks'] == 1


def test_picks_by_book_only_when_the_build_wrote_it(data, tmp_path):
    assert not os.path.exists(tmp_path / 'a' / 'picks_by_book.json')
    api_export.export(data, str(tmp_path / 'a'))
    assert not os.path.exists(tmp_path / 'a' / 'picks_by_book.json')
    with_pkb = dict(data, ODD=dict(data['ODD'], PKB={'BetRivers': data['ODD']['PK'], 'DraftKings': []}))
    api_export.export(with_pkb, str(tmp_path / 'b'))
    pbb = json.load(open(tmp_path / 'b' / 'picks_by_book.json', encoding='utf-8'))
    assert [p['id'] for p in pbb['BetRivers']] == [p['id'] for p in data['ODD']['PK']] and pbb['DraftKings'] == []


def test_runs_as_a_script_with_only_the_standard_library(data, tmp_path):
    """The daily refresh runs `python api_export.py` with only requirements.txt installed."""
    src = tmp_path / 'data.json'; src.write_text(json.dumps(data), encoding='utf-8')
    r = subprocess.run([sys.executable, '-I', os.path.join(ROOT, 'api_export.py'), str(src), str(tmp_path / 'api' / 'v1')],
                       capture_output=True, text=True, env=dict(os.environ, PYTHONUTF8='1'))
    assert r.returncode == 0, r.stdout + r.stderr
    assert (tmp_path / 'api' / 'v1' / 'players.json').exists()
    mods = open(os.path.join(ROOT, 'api_export.py'), encoding='utf-8').read()
    assert 'import mcp' not in mods and 'pandas' not in mods
