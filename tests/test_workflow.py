"""The build's outputs and the workflows that publish them.

build.py writes data.json and the same data split into data/<shard>.json (schema/shards.py), which the page loads.
refresh.yml commits only the ledgers and deploys the site (pages.py) through a Pages artifact; deploy.yml redeploys it,
offline, after a push that changes only the page's code. Generated files are never committed.
"""
import glob, json, os, re, shlex, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, ROOT)
import replay_util  # noqa: E402
from schema import shards  # noqa: E402

REFRESH = os.path.join(ROOT, '.github', 'workflows', 'refresh.yml')
DEPLOY = os.path.join(ROOT, '.github', 'workflows', 'deploy.yml')
# What the refresh commits: the ledgers, the state the next build starts from.
LEDGERS = {'model.json', 'cfb', 'odds'}
# What the build generates for the site: published through the Pages artifact, never committed.
GENERATED = {'index.html', 'data.json', 'data', 'api'}


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


def test_refresh_commits_the_ledgers_and_deploys_the_site():
    """The refresh commits exactly the ledgers, then gathers the site and deploys it; pages.py serves every
    generated file."""
    import pages
    scripts = script_blocks(REFRESH)
    saves = [s for s in scripts if re.search(r'\bgit commit\b', s)]
    assert len(saves) == 1, saves
    assert set(git_adds(saves[0])) == LEDGERS
    assert scripts.index('python pages.py _site') > scripts.index(saves[0])
    assert GENERATED <= set(pages.REQUIRED + pages.OPTIONAL)
    assert deploy_steps(REFRESH) == ['actions/upload-pages-artifact@v3', 'actions/deploy-pages@v4']


def test_generated_files_are_not_tracked():
    """git ignores the generated files and tracks none of them, so a local build can't commit one by accident."""
    ignore = set(open(os.path.join(ROOT, '.gitignore'), encoding='utf-8').read().split('\n'))
    assert {'/index.html', '/data.json', '/data/', '/api/'} <= ignore
    tracked = subprocess.run(['git', 'ls-files', '--'] + sorted(GENERATED), cwd=ROOT, capture_output=True, text=True, check=True)
    assert tracked.stdout == ''


def deploy_steps(path):
    """The Pages actions a workflow uses, in order."""
    return re.findall(r'uses:\s*(actions/(?:upload-pages-artifact|deploy-pages)@\S+)', open(path, encoding='utf-8').read())


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


def concurrency_group(path):
    return re.search(r'^concurrency:\s*\n\s+group:\s*(\S+)', open(path, encoding='utf-8').read(), re.M).group(1)


def test_deploy_redeploys_offline():
    """The deploy workflow rebuilds the site from the published data (no build, no secrets, nothing committed),
    triggers on the page's code, and queues behind (never alongside) the refresh."""
    text = open(DEPLOY, encoding='utf-8').read()
    assert script_blocks(DEPLOY) == ['python pages.py --live _site']
    assert 'secrets.' not in text and 'pip install' not in text and 'git ' not in text
    assert deploy_steps(DEPLOY) == ['actions/upload-pages-artifact@v3', 'actions/deploy-pages@v4']
    assert concurrency_group(DEPLOY) == concurrency_group(REFRESH) == 'refresh-data'
    paths = re.search(r'^\s+paths:\s*\n((?:\s+- .*\n)+)', text, re.M).group(1)
    paths = {p.strip()[2:].strip("'") for p in paths.strip().split('\n')}
    assert {'template.html', 'js/**', 'assets/**', 'pages.py', '.github/workflows/deploy.yml'} <= paths


def test_restamp_uses_the_built_date(tmp_path):
    """python restamp.py stamps index.html from template.html with the date data.json was built, and a fresh version."""
    (tmp_path / 'template.html').write_text('<script src="js/main.js?v=__VER__"></script> updated __DATE__', encoding='utf-8')
    (tmp_path / 'data.json').write_text(json.dumps({'META': {'built': 'Nov 02, 2026 at 12:00 UTC'}}), encoding='utf-8')
    subprocess.run([sys.executable, os.path.join(ROOT, 'restamp.py')], cwd=tmp_path, check=True, capture_output=True)
    page = (tmp_path / 'index.html').read_text(encoding='utf-8')
    assert re.fullmatch(r'<script src="js/main\.js\?v=\d{12}"></script> updated Nov 02, 2026 at 12:00 UTC', page), page
