"""The build's outputs and the daily refresh that commits them.

build.py writes data.json and the same data split into data/<shard>.json (schema/shards.py), which the page loads.
refresh.yml must commit every output, or the site serves a stale or missing file.
"""
import glob, json, os, re, shlex, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, ROOT)
import replay_util  # noqa: E402
from schema import shards  # noqa: E402

REFRESH = os.path.join(ROOT, '.github', 'workflows', 'refresh.yml')
# What the refresh must commit: the page, its data (whole and split), the API files and the state files it keeps.
OUTPUTS = {'index.html', 'data.json', 'data', 'api', 'model.json', 'cfb', 'odds'}


def test_shards_union_equals_data_json(tmp_path_factory):
    """The golden build's data/ holds every top-level key of its data.json exactly once, with the same value, and
    data/index.json lists what each file holds. Every file carries the same build stamp, a hash of data.json. The
    files are what shards.files makes from data.json, byte for byte, so the copies the page tests serve (re-split
    after editing data.json) match what the build ships."""
    work = replay_util.replay_dir(tmp_path_factory)
    whole = json.load(open(work / 'data.json', encoding='utf-8'))
    index = json.load(open(work / 'data' / 'index.json', encoding='utf-8'))
    build = shards.build_id(whole)
    assert index == {'build': build, 'shards': shards.SHARDS}
    assert sorted(os.path.basename(p) for p in glob.glob(str(work / 'data' / '*.json'))) == sorted(['index.json'] + ['%s.json' % s for s in index['shards']])
    seen = {}
    for name, keys in index['shards'].items():
        f = json.load(open(work / 'data' / ('%s.json' % name), encoding='utf-8'))
        assert list(f) == ['build', 'data'] and f['build'] == build, name
        assert list(f['data']) == keys, name
        for k, v in f['data'].items():
            assert k not in seen, '%s is in both %s and %s' % (k, seen[k], name)
            seen[k] = name
            assert v == whole[k], k
    assert set(seen) == set(whole)
    for f, text in shards.files(whole).items():
        assert open(work / 'data' / f, 'rb').read() == text.encode('utf-8'), f


def test_build_id_follows_the_data():
    data = {k: None for ks in shards.SHARDS.values() for k in ks}
    assert shards.build_id(data) == shards.build_id(dict(data)) != shards.build_id(dict(data, META={'built': 'x'}))


def test_split_rejects_unmapped_keys():
    """A new top-level key in data.json must be given a shard, and a shard key must exist, or the build fails."""
    data = {k: None for ks in shards.SHARDS.values() for k in ks}
    shards.split(data)
    for bad in (dict(data, NEW=1), {k: v for k, v in data.items() if k != 'ODD'}):
        try: shards.split(bad)
        except ValueError: continue
        raise AssertionError('split accepted keys %s' % sorted(bad))


def script_blocks(path):
    """The shell scripts in a workflow's `run:` keys (block scalars and one-liners), in file order."""
    lines, out, i = open(path, encoding='utf-8').read().split('\n'), [], 0
    while i < len(lines):
        m = re.match(r'^(\s*)(?:- )?run:\s*(.*?)\s*$', lines[i])
        i += 1
        if not m: continue
        if m.group(2) not in ('|', '|-', '>', '>-'):
            out.append(m.group(2)); continue
        ind, body = len(m.group(1)), []
        while i < len(lines) and (not lines[i].strip() or len(lines[i]) - len(lines[i].lstrip()) > ind):
            body.append(lines[i].strip()); i += 1
        out.append('\n'.join(body))
    return out


def git_adds(script):
    """Every path a shell script passes to `git add` before its `git commit`, including inside `if ...; then`."""
    paths = []
    for line in script.split('\n'):
        if re.search(r'\bgit commit\b', line): break
        for seg in re.split(r';|&&|\|\||\bthen\b', line):
            w = shlex.split(seg, comments=True)
            if w[:2] == ['git', 'add']: paths += [p for p in w[2:] if not p.startswith('-')]
    return paths


def test_git_adds_parser():
    s = 'git add index.html data.json data\nif [ -d api ]; then git add api; fi\ngit diff --staged --quiet || git commit -m x\ngit add late'
    assert git_adds(s) == ['index.html', 'data.json', 'data', 'api']


def test_refresh_commits_all_outputs():
    saves = [s for s in script_blocks(REFRESH) if re.search(r'\bgit commit\b', s)]
    assert len(saves) == 1, saves
    added = set(git_adds(saves[0]))
    assert OUTPUTS <= added, 'refresh.yml does not commit %s' % sorted(OUTPUTS - added)


def test_data_keys_name_shard_keys():
    """Every dataKeys entry in js/ names a top-level key some shard holds (the page loads shards by these names)."""
    known = {k for ks in shards.SHARDS.values() for k in ks}
    found = []
    for path in glob.glob(os.path.join(ROOT, 'js', '**', '*.js'), recursive=True):
        for lst in re.findall(r'dataKeys:\[([^\]]*)\]', open(path, encoding='utf-8').read()):
            found += [(os.path.basename(path), k) for k in re.findall(r"'([^']*)'", lst)]
    assert found
    unknown = [x for x in found if x[1] not in known]
    assert not unknown, unknown
