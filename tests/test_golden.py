"""The build must produce the same data.json from the same inputs.

Replays build.py on the saved inputs in tests/golden/fixtures and compares the result with
tests/golden/expected_data.json.gz. A change that is meant to change the output (a model tweak, a new field) is
accepted by re-blessing:  python tests/golden/runner.py bless <tmp dir>  and committing the new expected file.
"""
import gzip, json, math, os, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
RUNNER = os.path.join(HERE, 'golden', 'runner.py')
EXPECTED = os.path.join(HERE, 'golden', 'expected_data.json.gz')


def diffs(a, b, path='$'):
    """Yields (path, expected, got) for every difference; floats compare to 1e-9."""
    if isinstance(a, dict) and isinstance(b, dict):
        for k in sorted(set(a) | set(b), key=str):
            if k not in b: yield path + '.' + str(k), a[k], '<missing>'
            elif k not in a: yield path + '.' + str(k), '<missing>', b[k]
            else: yield from diffs(a[k], b[k], path + '.' + str(k))
    elif isinstance(a, list) and isinstance(b, list):
        if len(a) != len(b): yield path + '.length', len(a), len(b)
        for i, (x, y) in enumerate(zip(a, b)): yield from diffs(x, y, '%s[%d]' % (path, i))
    elif isinstance(a, float) or isinstance(b, float):
        if not (isinstance(a, (int, float)) and isinstance(b, (int, float)) and math.isclose(a, b, rel_tol=1e-9, abs_tol=1e-9)):
            yield path, a, b
    elif a != b:
        yield path, a, b


def test_build_matches_golden(tmp_path):
    env = dict(os.environ, PYTHONHASHSEED='0', PYTHONUTF8='1')
    r = subprocess.run([sys.executable, RUNNER, 'replay', str(tmp_path)], env=env, capture_output=True, text=True)
    assert r.returncode == 0, r.stdout[-3000:] + r.stderr[-3000:]
    got = json.load(open(tmp_path / 'data.json', encoding='utf-8'))
    exp = json.load(gzip.open(EXPECTED, 'rt', encoding='utf-8'))
    found = list(diffs(exp, got))
    assert not found, '%d differences from the golden data.json, first 25:\n%s' % (
        len(found), '\n'.join('%s: expected %r, got %r' % (p, str(e)[:80], str(g)[:80]) for p, e, g in found[:25]))
