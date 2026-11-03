"""Runs build.py on saved inputs with the clock frozen, so two runs of the same code give the same data.json.

    python tests/golden/runner.py record WORKDIR   download every source the build reads and save it, plus the repo's
                                                   current state files (odds/, model.json, ...), then build
    python tests/golden/runner.py replay WORKDIR   build from the saved files only (no network)
    python tests/golden/runner.py bless  WORKDIR   replay, then save its data.json as the expected output

WORKDIR gets a copy of the code and the saved state; the build writes data.json there, never in the repo.
Run with PYTHONHASHSEED=0 and PYTHONUTF8=1 (tests/test_golden.py does).
"""
import glob, gzip, io, json, os, re, runpy, shutil, sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
FIX = os.path.join(ROOT, 'tests', 'golden', 'fixtures')
EXPECTED = os.path.join(ROOT, 'tests', 'golden', 'expected_data.json.gz')
CODE = ['build.py', 'sources.py', 'template.html', 'engine']   # files and packages the build imports
# repo files the build reads (and the daily refresh keeps changing), frozen at record time
STATE = ['model.json', 'boards/*.csv', 'odds/*.json', 'odds/props/*.json', 'cfb/fetch_log.txt',
         'cfb/games_{s}.json', 'cfb/games_{p}.json', 'cfb/lines_{s}.json']


def key(url):
    return re.sub(r'[^A-Za-z0-9._-]+', '_', url.split('://', 1)[-1]) + '.gz'


# Big downloads trimmed at record time to the columns (and rows) the build reads; values are kept verbatim.
# url fragment -> (columns to keep or None, keep only the rows with the newest value of this column or None)
TRIM = {'depth_charts/': (['dt', 'team', 'player_name', 'gsis_id', 'pos_grp', 'pos_abb', 'pos_rank'], 'dt'),
        'players/players.csv': (['gsis_id', 'pfr_id', 'display_name', 'birth_date', 'college_name', 'draft_year', 'draft_round',
                                 'draft_pick', 'headshot', 'espn_id', 'height', 'weight'], None),
        'db_playerids.csv': (['fantasypros_id', 'gsis_id', 'sleeper_id', 'espn_id', 'name', 'position', 'team', 'age'], None),
        'weekly_rosters/': (['week', 'gsis_id', 'team', 'status', 'status_description_abbr'], None)}


def trim(url, raw):
    import csv
    rule = next((v for k, v in TRIM.items() if k in url), None)
    if not rule: return raw
    cols, newest = rule
    rows = list(csv.reader(io.StringIO(raw.decode('utf-8'))))
    head = rows[0]; ix = [head.index(c) for c in (cols or head)]
    body = rows[1:]
    if newest:
        j = head.index(newest); top = max(r[j] for r in body); body = [r for r in body if r[j] == top]
    out = io.StringIO(); w = csv.writer(out, lineterminator='\n')
    w.writerow([head[i] for i in ix]); w.writerows([[r[i] for i in ix] for r in body])
    return out.getvalue().encode('utf-8')


def main(mode, work):
    meta_f = os.path.join(FIX, 'meta.json')
    if mode == 'record':
        import datetime
        # GOLDEN_NOW picks the frozen clock (e.g. before a game's kickoff, so there are picks to compare)
        meta = {'season': int(os.environ.get('SEASON', 2026)),
                'now': os.environ.get('GOLDEN_NOW') or datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat()}
        shutil.rmtree(FIX, ignore_errors=True); os.makedirs(os.path.join(FIX, 'net')); os.makedirs(os.path.join(FIX, 'repo'))
        json.dump(meta, open(meta_f, 'w'), indent=1)
    meta = json.load(open(meta_f))
    shutil.rmtree(work, ignore_errors=True); os.makedirs(work)
    for f in CODE:
        if os.path.isdir(os.path.join(ROOT, f)):
            shutil.copytree(os.path.join(ROOT, f), os.path.join(work, f), ignore=shutil.ignore_patterns('__pycache__'))
        else: shutil.copy(os.path.join(ROOT, f), os.path.join(work, f))
    if mode == 'record':
        for pat in STATE:
            for src in glob.glob(os.path.join(ROOT, pat.format(s=meta['season'], p=meta['season'] - 1))):
                rel = os.path.relpath(src, ROOT)
                os.makedirs(os.path.dirname(os.path.join(FIX, 'repo', rel)), exist_ok=True)
                with open(src, 'rb') as a, open(os.path.join(FIX, 'repo', rel + '.gz'), 'wb') as b: b.write(gzip.compress(a.read(), 9, mtime=0))
    for src in glob.glob(os.path.join(FIX, 'repo', '**', '*.gz'), recursive=True):
        rel = os.path.relpath(src, os.path.join(FIX, 'repo'))[:-3]
        os.makedirs(os.path.dirname(os.path.join(work, rel)) or work, exist_ok=True)
        with gzip.open(src, 'rb') as a, open(os.path.join(work, rel), 'wb') as b: b.write(a.read())

    os.environ.update(SEASON=str(meta['season']), ODDS_OFFLINE='1')
    for k in ('CFBD_KEY', 'ODDS_API_KEY', 'CSV_PATH', 'DP_DIR'): os.environ.pop(k, None)
    os.chdir(work); sys.path.insert(0, work)
    import sources
    real_get = sources._get

    def fake_get(url, headers=None):
        f = os.path.join(FIX, 'net', key(url))
        if mode == 'record' and not os.path.exists(f):
            with open(f, 'wb') as out: out.write(gzip.compress(trim(url, real_get(url, headers).getvalue()), 9, mtime=0))
        if not os.path.exists(f):
            raise RuntimeError('no saved copy of %s (re-record the fixtures)' % url)
        return io.BytesIO(gzip.open(f).read())
    sources._get = fake_get

    from freezegun import freeze_time
    with freeze_time(meta['now']):
        runpy.run_path(os.path.join(work, 'build.py'), run_name='__main__')
    if mode == 'bless':
        with open(os.path.join(work, 'data.json'), 'rb') as a, open(EXPECTED, 'wb') as b: b.write(gzip.compress(a.read(), 9, mtime=0))
        print('saved', EXPECTED)


if __name__ == '__main__':
    main(sys.argv[1], os.path.abspath(sys.argv[2]))
