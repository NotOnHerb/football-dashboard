"""analyst/snapshot.py must write the same Desk snapshot from the golden data.json.

Runs snapshot.py on tests/golden/expected_data.json.gz plus the saved odds/picks.json, with the clock frozen at the
golden time, and compares every snap/*.json file with tests/golden/expected_snapshot.json.gz (exact match).
A change that is meant to change the snapshot is accepted by re-blessing:
    python tests/test_snapshot.py bless
"""
import gzip, importlib.util, json, os, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
GOLDEN = os.path.join(HERE, 'golden')
EXPECTED = os.path.join(GOLDEN, 'expected_snapshot.json.gz')


def run_snapshot(work):
    """Writes the golden data.json and pick log into WORK, runs snapshot.main there, returns {file name: parsed json}."""
    from freezegun import freeze_time
    os.makedirs(os.path.join(work, 'odds'), exist_ok=True)
    with gzip.open(os.path.join(GOLDEN, 'expected_data.json.gz'), 'rb') as a, open(os.path.join(work, 'data.json'), 'wb') as b:
        b.write(a.read())
    with gzip.open(os.path.join(GOLDEN, 'fixtures', 'repo', 'odds', 'picks.json.gz'), 'rb') as a, \
            open(os.path.join(work, 'odds', 'picks.json'), 'wb') as b:
        b.write(a.read())
    now = json.load(open(os.path.join(GOLDEN, 'fixtures', 'meta.json')))['now']
    spec = importlib.util.spec_from_file_location('snapshot_under_test', os.path.join(ROOT, 'analyst', 'snapshot.py'))
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    here = os.getcwd()
    try:
        os.chdir(work)
        with freeze_time(now):
            mod.main(os.path.join(work, 'out'))
    finally:
        os.chdir(here)
    snap = os.path.join(work, 'out', 'snap')
    return {f: json.load(open(os.path.join(snap, f), encoding='utf-8')) for f in sorted(os.listdir(snap))}


def test_snapshot_matches_golden(tmp_path):
    got = run_snapshot(str(tmp_path))
    exp = json.load(gzip.open(EXPECTED, 'rt', encoding='utf-8'))
    assert sorted(got) == sorted(exp)
    bad = [f for f in exp if got[f] != exp[f]]
    assert not bad, 'snapshot files differ from the golden: %s' % bad


if __name__ == '__main__' and sys.argv[1:] == ['bless']:
    with tempfile.TemporaryDirectory() as tmp:
        out = run_snapshot(tmp)
    with open(EXPECTED, 'wb') as f:
        f.write(gzip.compress(json.dumps(out, sort_keys=True, separators=(',', ':')).encode('utf-8'), 9, mtime=0))
    print('saved', EXPECTED, sorted(out))
