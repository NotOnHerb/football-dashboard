"""The field dictionary (schema/fields.py) and the JSON schema (schema/data.schema.json) must agree with the build.

Both tests replay build.py on the saved inputs (the same replay as tests/test_golden.py) and check the result.
The college block (CF) is empty in that replay (no CFBD fixtures), so its row lengths are also checked against the
last committed data.json when there is one.
"""
import json, os, subprocess, sys

import jsonschema
import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
from schema import fields  # noqa: E402

RUNNER = os.path.join(HERE, 'golden', 'runner.py')
SCHEMA_FILE = os.path.join(ROOT, 'schema', 'data.schema.json')


@pytest.fixture(scope='module')
def data(tmp_path_factory):
    work = tmp_path_factory.mktemp('replay')
    env = dict(os.environ, PYTHONHASHSEED='0', PYTHONUTF8='1')
    r = subprocess.run([sys.executable, RUNNER, 'replay', str(work)], env=env, capture_output=True, text=True)
    assert r.returncode == 0, r.stdout[-3000:] + r.stderr[-3000:]
    return json.load(open(work / 'data.json', encoding='utf-8'))


def rows_of(d, block):
    """Every row of a block in a data.json, or None when the block is absent (e.g. no college data)."""
    if block == 'P': return [r for rows in d['P'].values() for r in rows]
    if block == 'LOG': return [r for rows in d['LOG'].values() for r in rows]
    if block == 'DY.L': return list(d['DY']['L'].values()) if d.get('DY') and 'L' in d['DY'] else None   # L, E are absent when the Sleeper lookup failed
    if block in ('DY.P', 'DY.K'): return d['DY'][block[3:]] if d.get('DY') else None
    if block == 'ODD.FIN': return d['ODD']['FIN'] if d.get('ODD') else None
    if block == 'CF.P': return d['CF']['P'] if d.get('CF') else None
    if block in ('CF.CB.P', 'CF.CB.S'): return d['CF']['CB'][block[-1]] if d.get('CF') and d['CF'].get('CB') else None
    return d[block]   # X, OLP, T, G


def expected_len(d, block):
    n = len(fields.FIELDS[block])
    if block == 'T': n += len(d['TC'])                    # code, then one column per TC entry
    if block == 'CF.CB.P': n += len(d['CF']['CB']['S'])   # then one rank per board
    return n


def s(v): return isinstance(v, str)
def n(v): return isinstance(v, (int, float)) and not isinstance(v, bool)
def i(v): return isinstance(v, int) and not isinstance(v, bool)
def opt(f): return lambda v: v is None or f(v)
def gsis(v): return s(v) and v.startswith('00-')
def lst(k): return lambda v: isinstance(v, list) and len(v) == k
depth = opt(lambda v: lst(2)(v) and s(v[0]) and isinstance(v[1], bool))   # ["WR1", true]
injury = opt(lambda v: lst(3)(v) and s(v[0]) and s(v[1]) and i(v[2]))     # [status, injury, week]

# What each named position holds (a small sample, enough to catch a same-length swap of fields).
TYPES = {
    'P': {'name': s, 'team': s, 'games': i, 'vals': lambda v: isinstance(v, list), 'std_per_game': n, 'injury': injury, 'depth_label': depth,
          'form': lst(4), 'gsis_id': gsis},
    'X': {'name': s, 'team': s, 'pos': s, 'games': i, 'tackles': i, 'sacks': n, 'idp_pts': n, 'injury': injury,
          'depth_label': depth, 'form': lst(4), 'gsis_id': gsis},
    'LOG': {'week': i, 'opponent': s, 'ppr_pts': n, 'receptions': i},
    'OLP': {'name': s, 'team': s, 'pos': s, 'slot': s, 'penalties': i, 'penalty_yds': i, 'injury': injury},
    'DY.P': {'name': s, 'pos': s, 'team': s, 'value_1qb': i, 'value_2qb': i, 'injury': injury, 'depth_label': depth,
             'gsis_id': opt(gsis)},
    'DY.K': {'pick': s, 'value_1qb': i, 'value_2qb': i},
    'DY.L': {'name': s, 'pos': s, 'team': s, 'value_1qb': opt(i), 'games': i, 'injury': injury, 'depth_label': depth,
             'gsis_id': gsis},
    'CF.P': {'name': s, 'pos': s, 'team': s, 'conference': s, 'draft_eligible': opt(lambda v: isinstance(v, bool)),
             'dynasty_score': n, 'letter_grade': s, 'consensus_rank': opt(i), 'avg_rank': opt(n), 'boards': opt(i),
             'best_rank': opt(i), 'worst_rank': opt(i)},
    'CF.CB.P': {'rank': i, 'name': s, 'pos': s, 'school': s, 'avg_rank': n, 'boards': i, 'best_rank': i, 'worst_rank': i},
    'CF.CB.S': {'source': s, 'url': s, 'updated': s, 'length': i},
    'T': {'code': s},
    'G': {'away': s, 'home': s, 'label': s},
    'ODD.FIN': {'week': i, 'away': s, 'home': s, 'away_score': i, 'home_score': i},
}


def check_types(block, rows):
    for r in rows:
        row = fields.named(block, r)
        for name, ok in TYPES[block].items():
            assert ok(row[name]), '%s.%s has the wrong kind of value: %r (row %r)' % (block, name, row[name], r)


def check_lengths(d):
    seen = {}
    for block in fields.FIELDS:
        rows = rows_of(d, block)
        if rows is None: continue
        want = expected_len(d, block)
        bad = [r for r in rows if len(r) != want]
        assert not bad, '%s: %d of %d rows are not %d long, e.g. %r' % (block, len(bad), len(rows), want, bad[0])
        check_types(block, rows)
        seen[block] = len(rows)
    for pos, rows in d['P'].items():
        for r in rows:
            assert len(r[3]) == len(d['PC'][pos]), 'P.%s vals has %d values, PC has %d labels' % (pos, len(r[3]), len(d['PC'][pos]))
    return seen


def test_row_lengths_match_fields(data):
    seen = check_lengths(data)
    for block in ('P', 'X', 'LOG', 'OLP', 'DY.P', 'DY.K', 'DY.L', 'T', 'G', 'ODD.FIN'):
        assert seen.get(block), 'the replay has no %s rows to check' % block


def test_row_lengths_match_committed_data():
    path = os.path.join(ROOT, 'data.json')
    if not os.path.exists(path): pytest.skip('no committed data.json')
    seen = check_lengths(json.load(open(path, encoding='utf-8')))   # blocks that are null or absent that day are not checked
    missing = [b for b in fields.FIELDS if b not in seen]
    if missing: pytest.skip('checked what is there; the committed data.json has no rows for %s' % ', '.join(missing))


def test_data_validates_against_schema(data):
    jsonschema.validate(data, json.load(open(SCHEMA_FILE, encoding='utf-8')))


def test_schema_key_matches_fields(data):
    sch = data['SCHEMA']
    for block, names in fields.FIELDS.items(): assert sch[block] == names
    assert sch['P.vals'] == {pos: [c[0] for c in cols] for pos, cols in data['PC'].items()}
    assert sch['T.cols'] == [c[0] for c in data['TC']]


def test_named_roundtrip(data):
    row = data['P']['WR'][0]
    assert fields.named('P', row)['gsis_id'] == row[8]
    assert fields.named('P', row)['vals'] == row[3]
    # a college row shaped like the build's: stats and bio, computed scores, then the consensus match
    cf_row = ['Trey Owens', 'QB', 'Arkansas State', 'Sun Belt', 3, 4, 299, 2024, 57.0, 0.24, 71.0, True,
              233.0, 68.2, 1940.0, 11.0, 6.0, 8.3, 61.0, 210.0, 4.0, 3.4, None, None, None, None, None, 19.0, 77, 220,
              64.9, 'B', 154.6, 154.6, 8, 12, 14.5, 4, 9, 21]
    assert len(cf_row) == 40
    cf = fields.named('CF.P', cf_row)
    assert (cf['dynasty_score'], cf['letter_grade'], cf['consensus_rank'], cf['avg_rank'], cf['boards'],
            cf['best_rank'], cf['worst_rank']) == (64.9, 'B', 12, 14.5, 4, 9, 21)
    check_types('CF.P', [cf_row])
    named = fields.rows_named('X', data['X'][:3])
    assert [n['gsis_id'] for n in named] == [r[20] for r in data['X'][:3]]


def test_cf_fields_follow_the_documented_layout():
    f = fields.FIELDS['CF.P']
    assert len(f) == 40
    assert (f[26], f[27], f[30], f[31], f[35], f[36], f[37], f[38], f[39]) == (
        'rec_yds_share', 'rush_yds_share', 'dynasty_score', 'letter_grade',
        'consensus_rank', 'avg_rank', 'boards', 'best_rank', 'worst_rank')
