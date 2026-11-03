"""A sportsbook quote without a line cannot be priced, so the build must leave it out instead of failing.

The Odds API can post a spread or total outcome with a price and no `point`. Scored on its own (ODD.PKB prices each book
alone) such a quote used to raise TypeError inside build.py's odds block, which left ODD empty and the whole Betting tab
down. This replays the golden build with the saved odds edited that way and checks ODD is still built, with
PK and PKB, and that the books involved have no spread (or total) quote.
"""
import copy, gzip, json, os, shutil, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
GOLDEN = os.path.join(HERE, 'golden')
sys.path.insert(0, GOLDEN)
import runner  # noqa: E402

DRIVER = "import sys; sys.path.insert(0, %r); import runner; runner.FIX = %r; runner.main('replay', %r)"


def replay_with_edited_odds(tmp_path, edit):
    """Replays the golden build with odds/lines.json passed through edit(lines). Returns the built data.json."""
    fix = tmp_path / 'fixtures'
    shutil.copytree(runner.FIX, fix)
    f = fix / 'repo' / 'odds' / 'lines.json.gz'
    lines = json.load(gzip.open(f, 'rt', encoding='utf-8'))
    edit(lines)
    with gzip.open(f, 'wt', encoding='utf-8') as out: json.dump(lines, out)
    env = dict(os.environ, PYTHONHASHSEED='0', PYTHONUTF8='1')
    work = tmp_path / 'work'
    r = subprocess.run([sys.executable, '-c', DRIVER % (GOLDEN, str(fix), str(work))], env=env, capture_output=True, text=True)
    assert r.returncode == 0, r.stdout[-3000:] + r.stderr[-3000:]
    return json.load(open(work / 'data.json', encoding='utf-8'))


def drop_points(lines):
    for ev in lines['data']:
        for B in ev['bookmakers']:
            for M in B['markets']:
                if B['key'] == 'fanduel' and M['key'] == 'spreads':
                    for o in M['outcomes']: o.pop('point', None)
                if B['key'] == 'betrivers' and M['key'] == 'totals':
                    for o in M['outcomes']:
                        if o['name'] == 'Over': o.pop('point', None)


def test_quotes_without_a_line_are_left_out(tmp_path):
    d = replay_with_edited_odds(tmp_path, drop_points)
    O = d['ODD']
    assert O is not None, 'odds block failed'
    g = O['G'][0]['b']
    assert 's' not in g['FanDuel'] and 'm' in g['FanDuel'] and 'o' in g['FanDuel']
    assert 'o' not in g['BetRivers'] and 's' in g['BetRivers']
    assert 's' in g['DraftKings'] and 'o' in g['DraftKings']
    assert O['PK'] and list(O['PKB']) == O['books']
    for pk in [O['PK']] + list(O['PKB'].values()):
        assert all(x['k'] != 'g' or x['pt'] is not None or x['mk'] == 'ml' for x in pk)
