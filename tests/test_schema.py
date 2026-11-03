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
    if block == 'DY.L': return list(d['DY']['L'].values()) if d.get('DY') else None
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


def check_lengths(d):
    seen = {}
    for block in fields.FIELDS:
        rows = rows_of(d, block)
        if rows is None: continue
        want = expected_len(d, block)
        bad = [r for r in rows if len(r) != want]
        assert not bad, '%s: %d of %d rows are not %d long, e.g. %r' % (block, len(bad), len(rows), want, bad[0])
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
    seen = check_lengths(json.load(open(path, encoding='utf-8')))
    assert seen.get('CF.P'), 'the committed data.json has no college rows'


def test_data_validates_against_schema(data):
    jsonschema.validate(data, json.load(open(SCHEMA_FILE, encoding='utf-8')))


def test_schema_key_matches_fields(data):
    s = data['SCHEMA']
    for block, names in fields.FIELDS.items(): assert s[block] == names
    assert s['P.vals'] == {pos: [c[0] for c in cols] for pos, cols in data['PC'].items()}
    assert s['T.cols'] == [c[0] for c in data['TC']]


def test_named_roundtrip(data):
    row = data['P']['WR'][0]
    assert fields.named('P', row)['gsis_id'] == row[8]
    assert fields.named('P', row)['vals'] == row[3]
    cf_row = list(range(40))
    assert fields.named('CF.P', cf_row)['dynasty_score'] == cf_row[30]
    assert fields.named('CF.P', cf_row)['name_key'] == cf_row[39]
    named = fields.rows_named('X', data['X'][:3])
    assert [n['gsis_id'] for n in named] == [r[20] for r in data['X'][:3]]


def test_cf_fields_follow_the_documented_layout():
    f = fields.FIELDS['CF.P']
    assert len(f) == 40
    assert (f[26], f[27], f[30], f[31], f[35], f[39]) == (
        'rec_yds_share', 'rush_yds_share', 'dynasty_score', 'letter_grade', 'consensus_rank', 'name_key')
