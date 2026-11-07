"""A college pick from a book whose feed has no spread price carries no price (it used to show -110).

CollegeFootballData's lines have a spread but no spread price; only the Odds API books carry one. build.py used to fill
the gap with -110, so the page showed a price nobody posted. Now such a pick keeps pr = None (the page draws a dash), still
passes the price rule (there is nothing to check; the backtest assumed about -110) and, once graded, is paid at -110 so the
record and units do not move. This replays the golden build with one upcoming game given four CollegeFootballData books,
one of them 1.5 points off the rest, plus a past pick with no price in the saved pick log.
"""
import gzip, json, os, shutil, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
GOLDEN = os.path.join(HERE, 'golden')
sys.path.insert(0, GOLDEN)
import runner  # noqa: E402

DRIVER = "import sys; sys.path.insert(0, %r); import runner; runner.FIX = %r; runner.main('replay', %r)"
BOOKS = [('DraftKings', 14.0), ('ESPN Bet', 12.5), ('Bovada', 12.5), ('Caesars Sportsbook (Colorado)', 12.5)]


def jload(path): return json.load(gzip.open(path, 'rt', encoding='utf-8'))


def jsave(path, obj):
    with gzip.open(path, 'wt', encoding='utf-8') as out: json.dump(obj, out)


def replay(tmp_path):
    """Replays the golden build with the college inputs edited. Returns (data.json, the ids of the two games used)."""
    fix = tmp_path / 'fixtures'
    shutil.copytree(runner.FIX, fix)
    cfb, odds = fix / 'repo' / 'cfb', fix / 'repo' / 'odds'
    now = json.load(open(fix / 'meta.json'))['now']
    games = jload(cfb / 'games_2026.json.gz')
    fbs = [g for g in games if g['homeClassification'] == 'fbs' and g['awayClassification'] == 'fbs']
    upcoming = min((g for g in fbs if not g['completed'] and g['startDate'] > now), key=lambda g: (g['startDate'], g['id']))
    done = next(g for g in fbs if g['completed'] and g['homePoints'] is not None)
    lines = [x for x in jload(cfb / 'lines_2026.json.gz') if x['id'] != upcoming['id']]
    lines.append({'id': upcoming['id'], 'week': upcoming['week'], 'homeTeam': upcoming['homeTeam'], 'awayTeam': upcoming['awayTeam'],
                  'homeScore': None, 'awayScore': None,
                  'lines': [{'provider': p, 'spread': s, 'spreadOpen': s, 'overUnder': 50.5, 'overUnderOpen': 50.5,
                             'homeMoneyline': -300, 'awayMoneyline': 240} for p, s in BOOKS]})
    jsave(cfb / 'lines_2026.json.gz', lines)
    log = jload(odds / 'cfb_picks.json.gz')
    log['c|%s|hs' % done['id']] = {'id': 'c|%s|hs' % done['id'], 'k': 'c', 'gid': done['id'], 'wk': done['week'], 't': done['startDate'],
                                   'a': done['awayTeam'], 'h': done['homeTeam'], 'sd': 'hs', 'pt': 1000, 'pr': None, 'bk': 'DraftKings',
                                   'gap': 1.5, 'others': 0, 's': 2, 'lines': {}, 'res': None}
    jsave(odds / 'cfb_picks.json.gz', log)
    env = dict(os.environ, PYTHONHASHSEED='0', PYTHONUTF8='1')
    work = tmp_path / 'work'
    r = subprocess.run([sys.executable, '-c', DRIVER % (GOLDEN, str(fix), str(work))], env=env, capture_output=True, text=True)
    assert r.returncode == 0, r.stdout[-3000:] + r.stderr[-3000:]
    return json.load(open(work / 'data.json', encoding='utf-8')), upcoming['id'], done['id']


def test_unpriced_college_pick_has_no_price(tmp_path):
    data, up_id, done_id = replay(tmp_path)
    pk = [p for p in data['CFB']['PK'] if p['gid'] == up_id]
    assert len(pk) == 1, 'the 1.5-point-off book should be a pick: %s' % data['CFB']['PK']
    assert pk[0]['bk'] == 'DraftKings' and pk[0]['sd'] == 'hs' and pk[0]['s'] == 2
    assert pk[0]['pr'] is None
    logged = data['CFB']['LG']
    assert [r['pr'] for r in logged if r['gid'] == up_id] == [None]


def test_unpriced_college_pick_grades_at_minus_110(tmp_path):
    data, up_id, done_id = replay(tmp_path)
    r = [r for r in data['CFB']['LG'] if r['gid'] == done_id]
    assert len(r) == 1 and r[0]['pr'] is None and r[0]['res'] == 'W'
    assert r[0]['u'] == 0.909   # a win at -110
