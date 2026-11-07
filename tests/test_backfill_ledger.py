"""analyst/backfill_ledger.py: replays git history of data.json into first/last ledger snapshots and grades them."""
import copy, json, os, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT); sys.path.insert(0, os.path.join(HERE, 'test_engine'))
from analyst import backfill_ledger as bf  # noqa: E402
import test_ledger as tl  # noqa: E402  (fixture builders: game(), yds_prop(), td_prop(), MODEL)

REPEAT_TS = '2026-11-03T10:52'


def odd(at, b=None, pat=None, fin=(), pk=()):
    prop = tl.yds_prop(b=b)
    return {'MB': .5, 'G': [tl.game()], 'P': [prop, tl.td_prop()], 'PK': list(pk), 'FIN': [list(f) for f in fin], 'at': at, 'pat': pat or at}


def commit(repo, date, data, model=tl.MODEL, msg='Refresh data'):
    with open(os.path.join(repo, 'data.json'), 'w') as f: json.dump(dict(data, META={'built': date}), f)
    with open(os.path.join(repo, 'model.json'), 'w') as f: json.dump(model, f)
    env = dict(os.environ, GIT_AUTHOR_DATE=date, GIT_COMMITTER_DATE=date)
    subprocess.run(['git', '-C', repo, 'add', 'data.json', 'model.json'], check=True)
    subprocess.run(['git', '-C', repo, '-c', 'user.name=t', '-c', 'user.email=t@t', '-c', 'commit.gpgsign=false', 'commit', '-q', '-m', msg], check=True, env=env)


def make_repo(tmp_path):
    repo = str(tmp_path / 'repo'); os.makedirs(repo)
    subprocess.run(['git', 'init', '-q', repo], check=True)
    moved = {'X': [60.5, -125, 60.5, 105], 'Y': [59.5, -120, 59.5, 100], 'Z': [60.5, -105, 60.5, -115], 'Pinnacle': [60.5, -108, 60.5, -112]}
    commit(repo, '2026-10-20T12:00:00Z', {'ODD': odd('2026-10-20T10:00')})                       # before --since
    commit(repo, '2026-11-02T12:00:00Z', {'ODD': odd('2026-11-02T10:52')})                       # first snapshot
    other = {'LOG': {'Q': [[1, 'ZZ', 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]]}}                            # a finished game that isn't E1
    commit(repo, '2026-11-03T12:00:00Z', dict({'ODD': odd(REPEAT_TS, b=moved, fin=[(1, 'ZZ', 'YY', 1, 2)])}, **other))   # X moves its price: a later snapshot
    commit(repo, '2026-11-03T13:00:00Z', dict({'ODD': odd(REPEAT_TS, b=moved, fin=[(1, 'ZZ', 'YY', 1, 2)])}, **other))   # same odds re-committed
    commit(repo, '2026-11-04T12:00:00Z', {'ODD': {'MB': .5, 'G': [tl.game()]}})                  # malformed: no P, PK, at
    log = {'P2': [[9, 'AW', 0, 0, 70, 0, 0, 0, 0, 70, 0, 0]]}                                    # week 9: 70 rec yds
    commit(repo, '2026-11-09T12:00:00Z', {'ODD': odd('2026-11-09T10:00', fin=[(9, 'AW', 'HM', 17, 20)]), 'LOG': log})   # after kickoff: no new rows
    return repo


def run(repo, tmp_path, **kw):
    kw = dict(since='2026-10-27', ref='HEAD', **kw)
    return bf.backfill(repo, kw['since'], kw['ref'], str(tmp_path / 'out' / 'ledger.json'), str(tmp_path / 'out' / 'results.json'), log=lambda s: None)


def load(tmp_path, name): return json.load(open(tmp_path / 'out' / name))


# ---- replay and merge

def test_first_and_last_snapshots_kept_per_id(tmp_path):
    s = run(make_repo(tmp_path), tmp_path)
    led = load(tmp_path, 'ledger.json')
    e = led['p|E1|P2|Rec yds|60.5']
    assert e['first']['snapshot_ts'] == '2026-11-02T10:52' and e['last']['snapshot_ts'] == REPEAT_TS
    assert e['first']['o'] == e['last']['o'] == {'pr': -105, 'bk': 'Z'}
    assert e['first']['u'] == {'pr': -110, 'bk': 'X'} and e['last']['u'] == {'pr': 105, 'bk': 'X'}   # X's under price moved
    assert e['first'] != e['last']
    assert s['ids'] == len(led) == 7 and s['commits'] == 5   # 4 game lines, 2 yds lines, 1 anytime TD


def test_one_snapshot_gives_first_equal_last_and_ids_are_unique(tmp_path):
    run(make_repo(tmp_path), tmp_path)
    led = load(tmp_path, 'ledger.json')
    assert all(e['first']['id'] == e['last']['id'] == k for k, e in led.items())
    assert led['p|E1|P1|Anytime TD|']['first']['snapshot_ts'] == '2026-11-02T10:52'


def test_a_repeated_snapshot_adds_nothing():
    rows = bf.snapshot_rows(odd('2026-11-02T10:52'), tl.MODEL, None, '2026-11-02T11:00:00+00:00')
    led = {}
    assert bf.merge_rows(led, rows) == (len(rows), 0)
    before = copy.deepcopy(led)
    assert bf.merge_rows(led, copy.deepcopy(rows)) == (0, 0) and led == before   # a refresh re-committing identical odds
    other = copy.deepcopy(rows)
    for r in other: r['o'] = {'pr': 999, 'bk': 'Q'}                              # same stamps, different content: decided by content,
    assert _merged(rows, other) == _merged(other, rows)                          # the same whichever arrives first


def test_older_snapshot_moves_first_only_and_run_order_does_not_matter():
    old = bf.snapshot_rows(odd('2026-11-01T10:00'), tl.MODEL); new = bf.snapshot_rows(odd('2026-11-02T10:00'), tl.MODEL)
    led = {}
    bf.merge_rows(led, new)
    assert bf.merge_rows(led, old) == (0, len(old))   # a replay that starts earlier only moves firsts
    assert all(e['first']['snapshot_ts'] == '2026-11-01T10:00' and e['last']['snapshot_ts'] == '2026-11-02T10:00' for e in led.values())
    again = {}; bf.merge_rows(again, old); bf.merge_rows(again, new)
    assert again == led and bf.merge_rows(led, old + new) == (0, 0)


def test_rows_stamp_props_with_pat_when_no_event_cache_time_is_known_and_games_with_at():
    rows = bf.snapshot_rows(odd('2026-11-02T10:52', pat='2026-11-02T09:00'), tl.MODEL)
    assert {r['snapshot_ts'] for r in rows if r['k'] == 'g'} == {'2026-11-02T10:52'}
    assert {r['snapshot_ts'] for r in rows if r['k'] == 'p'} == {'2026-11-02T09:00'}


def test_each_prop_is_stamped_with_its_own_events_cache_time():
    o = odd('2026-11-02T10:52', pat='2026-11-02T10:40')              # pat is the newest cache across events
    o['G'] = [tl.game(), dict(tl.game(), id='E2')]
    o['P'] = [tl.yds_prop(), dict(tl.yds_prop(gid='P9'), eid='E2')]
    rows = bf.snapshot_rows(o, tl.MODEL, {'E1': '2026-11-02T10:40', 'E2': '2026-11-01T08:00'})
    ts = {r['eid']: r['snapshot_ts'] for r in rows if r['k'] == 'p'}
    assert ts == {'E1': '2026-11-02T10:40', 'E2': '2026-11-01T08:00'}
    assert len([r for r in rows if r['k'] == 'p']) == 4 and len([r for r in rows if r['k'] == 'g']) == 8   # no duplicates from the grouping
    odd_no_cache = bf.snapshot_rows(o, tl.MODEL, {'E1': '2026-11-02T10:40'})   # E2 has no cache file: pat
    assert {r['eid']: r['snapshot_ts'] for r in odd_no_cache if r['k'] == 'p'}['E2'] == '2026-11-02T10:40'


def test_a_prop_whose_own_cache_was_fetched_after_kickoff_is_left_out():
    o = odd('2026-11-02T10:52'); o['P'] = [tl.yds_prop()]
    assert not [r for r in bf.snapshot_rows(o, tl.MODEL, {'E1': '2026-11-08T19:00'}) if r['k'] == 'p']   # kickoff 2026-11-08T18:00Z


def test_a_build_after_kickoff_drops_props_whose_cache_was_fetched_before_it():
    o = odd('2026-11-08T18:30')                                          # built after the 18:00Z kickoff, still carrying the old cache
    assert not bf.snapshot_rows(o, tl.MODEL, {'E1': '2026-11-07T10:00'})   # games and props both gone
    assert bf.fallback_events(o, {}) == []                               # started events aren't counted as fallbacks


def test_builds_sharing_a_prop_snapshot_ts_order_by_build_time():
    pk = tl.rows_for([tl.game()], [tl.yds_prop(), tl.td_prop(), tl.td_prop('P3', pj=.7)])[1]
    cache = {'E1': '2026-11-02T09:00'}                                   # one quote, carried through two builds
    def built(at, pk):
        o = odd(at, pk=pk); o['P'].append(tl.td_prop('P3', pj=.7)); return bf.snapshot_rows(o, tl.MODEL, cache)
    early = built('2026-11-02T10:52', pk)
    late = built('2026-11-03T10:52', [])                                 # same quote, no pick flags this build
    assert {r['built'] for r in early if r['k'] == 'p'} == {'2026-11-02T10:52'} and {r['snapshot_ts'] for r in late if r['k'] == 'p'} == {'2026-11-02T09:00'}
    flagged = [r['id'] for r in early if r['k'] == 'p' and r['pick']]
    assert flagged                                                       # the builds differ in a pick flag
    for order in (early + late, late + early):
        led = {}; bf.merge_rows(led, order)
        for i in flagged:
            assert led[i]['first']['built'] == '2026-11-02T10:52' and led[i]['first']['pick'] is True
            assert led[i]['last']['built'] == '2026-11-03T10:52' and led[i]['last']['pick'] is False
        assert led == _merged(early, late)
        assert bf.merge_rows(led, early + late) == (0, 0)
    # a later quote still beats a later build of an older quote
    newer_quote = bf.snapshot_rows(odd('2026-11-02T11:00'), tl.MODEL, {'E1': '2026-11-02T10:30'})
    led = {}; bf.merge_rows(led, late + newer_quote)
    assert led['p|E1|P2|Rec yds|60.5']['last']['snapshot_ts'] == '2026-11-02T10:30'


def test_tied_snapshot_and_build_order_by_commit_time_then_content():
    cache = {'E1': '2026-11-02T09:00'}
    def at(commit_at, fit):                                              # one build time, committed twice with different content
        return bf.snapshot_rows(odd('2026-11-02T10:52'), dict(tl.MODEL, fit_at=fit), cache, commit_at)
    a = at('2026-11-02T11:00:00+00:00', 'fit-A'); b = at('2026-11-02T11:05:00+00:00', 'fit-B')
    for order in (a + b, b + a):
        led = _merged(order)
        assert all(e['first']['model_fit_at'] == 'fit-A' and e['last']['model_fit_at'] == 'fit-B' for e in led.values())
    assert _merged(a, b) == _merged(b, a) and bf.merge_rows(_merged(a, b), b + a) == (0, 0)
    c = at('2026-11-02T11:00:00+00:00', 'fit-C')                         # tied on commit time too: the content decides, the same either way
    assert _merged(a, c) == _merged(c, a)
    legacy = [{k: v for k, v in r.items() if k != 'commit_at'} for r in a]   # no commit_at sorts before any commit time
    led = _merged(b, legacy)
    assert all(e['first'].get('commit_at') is None and e['last']['commit_at'] == '2026-11-02T11:05:00+00:00' for e in led.values())


def test_a_ledger_from_an_earlier_version_is_refused_and_nothing_is_written(tmp_path):
    repo = make_repo(tmp_path); led = tmp_path / 'old_ledger.json'; res = tmp_path / 'old_results.json'
    row = {k: v for k, v in bf.snapshot_rows(odd('2026-11-02T10:52'), tl.MODEL)[0].items() if k not in ('built', 'commit_at')}
    led.write_text(json.dumps({row['id']: {'first': row, 'last': row}})); res.write_text('{}')
    before = (led.read_bytes(), res.read_bytes())
    try: bf.backfill(repo, '2026-10-27', 'HEAD', str(led), str(res), log=lambda s_: None); raise AssertionError('should have refused')
    except bf.StaleOutput as ex: assert str(led) in str(ex) and str(res) in str(ex)
    assert (led.read_bytes(), res.read_bytes()) == before
    p = subprocess.run([sys.executable, os.path.join(ROOT, 'analyst', 'backfill_ledger.py'), '--repo', repo, '--since', '2026-10-27',
                        '--ledger-out', str(led), '--results-out', str(res)], capture_output=True, text=True)
    assert p.returncode == 1 and p.stdout == '' and 'regenerate' in p.stderr and str(led) in p.stderr and str(res) in p.stderr
    assert (led.read_bytes(), res.read_bytes()) == before


def _merged(*parts):
    led = {}
    for part in parts: bf.merge_rows(led, part)
    return led


def test_loader_reads_each_events_fetch_time_from_the_commit(tmp_path):
    repo = str(tmp_path / 'repo'); os.makedirs(os.path.join(repo, 'odds', 'props')); subprocess.run(['git', 'init', '-q', repo], check=True)
    json.dump({'fetched': '2026-11-01T08:00:00+00:00', 'data': {}}, open(os.path.join(repo, 'odds', 'props', 'E1.json'), 'w'))
    open(os.path.join(repo, 'odds', 'props', 'E2.json'), 'w').write('not json')
    subprocess.run(['git', '-C', repo, 'add', 'odds'], check=True)
    commit(repo, '2026-11-02T12:00:00Z', {'ODD': odd('2026-11-02T10:52')})
    _, _, fetched, when = bf.make_loader(repo)(subprocess.run(['git', '-C', repo, 'rev-parse', 'HEAD'], capture_output=True, text=True).stdout.strip())
    assert fetched == {'E1': '2026-11-01T08:00:00+00:00'} and when.startswith('2026-11-02T12:00:00')   # the unreadable file is left out
    rows, parsed, _, fallbacks = bf.replay(bf.commits_touching(repo, '2026-10-27', 'HEAD'), bf.make_loader(repo), lambda s: None)
    assert {r['snapshot_ts'] for r in rows if r['k'] == 'p'} == {'2026-11-01T08:00:00+00:00'} and fallbacks == 0
    assert {r['commit_at'][:19] for r in rows} == {'2026-11-02T12:00:00'}   # every row says which commit built it


def test_replay_skips_a_bad_commit_without_aborting():
    good = odd('2026-11-02T10:52'); logged = []; cache = {'E1': '2026-11-02T09:00'}
    docs = {'a': (good, tl.MODEL, cache), 'b': ({'MB': .5}, tl.MODEL, cache), 'd': (good, tl.MODEL, cache)}
    def load_(sha):
        if sha == 'e': raise ValueError('bad json')
        return docs[sha]
    rows, parsed, skipped, fallbacks = bf.replay(['a', 'b', 'e', 'd'], load_, logged.append)
    assert parsed == ['a', 'd'] and [s for s, _ in skipped] == ['b', 'e'] and len(logged) == 2 and 'bad json' in logged[1]
    assert len(rows) == 2 * len(bf.snapshot_rows(good, tl.MODEL, cache)) and fallbacks == 0


def test_events_without_a_cache_time_are_logged_and_counted():
    logged = []; o = odd('2026-11-02T10:52')
    docs = {'a': (o, tl.MODEL, {}), 'b': (o, tl.MODEL, {'E1': '2026-11-02T09:00'}), 'c': (o, tl.MODEL, None)}
    rows, parsed, skipped, fallbacks = bf.replay(['a', 'b', 'c'], docs.get, logged.append)
    assert parsed == ['a', 'b', 'c'] and fallbacks == 2 and len(logged) == 2     # a and c each fall back for E1; b does not
    assert all('E1' in m and 'ODD.pat or ODD.at' in m for m in logged)


def test_malformed_commit_in_a_real_repo_is_skipped(tmp_path):
    s = run(make_repo(tmp_path), tmp_path)
    assert s['commits'] == 5 and s['parsed'] == 4 and len(s['skipped']) == 1 and s['skipped'][0][1].startswith('KeyError')


def test_since_leaves_out_earlier_commits(tmp_path):
    repo = make_repo(tmp_path)
    assert bf.commits_touching(repo, '2026-10-01', 'HEAD').__len__() == 6 and bf.commits_touching(repo, '2026-10-27', 'HEAD').__len__() == 5


def test_since_is_midnight_utc_whatever_the_time_of_day_now(tmp_path):
    repo = str(tmp_path / 'repo'); os.makedirs(repo); subprocess.run(['git', 'init', '-q', repo], check=True)
    commit(repo, '2026-10-26T23:59:00+00:00', {'ODD': odd('2026-10-26T10:00')})
    commit(repo, '2026-10-27T00:30:00+00:00', {'ODD': odd('2026-10-27T00:10')})     # early on the start date: in
    commit(repo, '2026-10-27T06:00:00+02:00', {'ODD': odd('2026-10-27T04:00')})     # 04:00 UTC with a +02:00 offset: in
    commit(repo, '2026-10-26T23:00:00-02:00', {'ODD': odd('2026-10-27T01:00')})     # 01:00 UTC on the 27th, written -02:00: in
    assert len(bf.commits_touching(repo, '2026-10-27', 'HEAD')) == 3
    assert len(bf.commits_touching(repo, '2026-10-26', 'HEAD')) == 4


# ---- grading

def test_grading_uses_the_last_commits_final_and_log(tmp_path):
    s = run(make_repo(tmp_path), tmp_path)
    res = load(tmp_path, 'results.json')
    assert res['g|E1|spread|-3.5'] == {'res': 'L', 'fin': [17, 20]}      # home won by 3: no cover at -3.5
    assert res['g|E1|spread|-3']['res'] == 'P' and res['g|E1|ml|']['res'] == 'W' and res['g|E1|total|44.5']['res'] == 'L'   # 37 total
    assert res['p|E1|P2|Rec yds|60.5'] == {'res': 'W', 'val': 70} and res['p|E1|P2|Rec yds|59.5']['res'] == 'W'
    assert res['p|E1|P1|Anytime TD|'] == {'res': 'V'}                   # no weekly row for P1: didn't play
    assert s['graded'] == s['ids']


def test_nothing_graded_while_the_game_is_unfinished(tmp_path):   # HEAD~2: finals and stats exist, but only for another game
    repo = make_repo(tmp_path)
    s = bf.backfill(repo, '2026-10-27', 'HEAD~2', str(tmp_path / 'l.json'), str(tmp_path / 'r.json'), log=lambda s_: None)
    assert s['graded'] == 0 and s['ids'] > 0


def test_empty_finals_or_stats_at_the_ref_warn_and_write_nothing(tmp_path, capsys):
    for i, data in enumerate(({'ODD': odd('2026-11-02T10:52'), 'LOG': {'P2': [[9]]}},                      # no finals
                              {'ODD': odd('2026-11-02T10:52', fin=[(9, 'AW', 'HM', 17, 20)])},             # no stats
                              {'ODD': None, 'LOG': {'P2': [[9]]}})):                                       # odds section failed
        repo = str(tmp_path / ('r%d' % i)); os.makedirs(repo); subprocess.run(['git', 'init', '-q', repo], check=True)
        commit(repo, '2026-11-02T12:00:00Z', data)
        led, res = str(tmp_path / ('l%d.json' % i)), str(tmp_path / ('r%d.json' % i))
        try: bf.backfill(repo, '2026-10-27', 'HEAD', led, res, log=lambda s: None); raise AssertionError('should have refused')
        except bf.NothingToGrade as ex: assert 'FIN' in str(ex) or 'LOG' in str(ex)
        assert not os.path.exists(led) and not os.path.exists(res)
    repo = str(tmp_path / 'r0')
    p = subprocess.run([sys.executable, os.path.join(ROOT, 'analyst', 'backfill_ledger.py'), '--repo', repo, '--ledger-out', str(tmp_path / 'x.json'),
                        '--results-out', str(tmp_path / 'y.json')], capture_output=True, text=True)
    assert p.returncode == 1 and p.stdout == '' and 'nothing to grade' in p.stderr and not os.path.exists(tmp_path / 'x.json')


# ---- idempotence

def test_second_run_changes_nothing(tmp_path):
    repo = make_repo(tmp_path)
    run(repo, tmp_path)
    first = [open(tmp_path / 'out' / n, 'rb').read() for n in ('ledger.json', 'results.json')]
    s = run(repo, tmp_path)
    assert [open(tmp_path / 'out' / n, 'rb').read() for n in ('ledger.json', 'results.json')] == first
    assert s['new_ids'] == 0 and s['moved'] == 0 and s['newly_graded'] == 0


def test_existing_results_are_kept(tmp_path):
    repo = make_repo(tmp_path); os.makedirs(tmp_path / 'out')
    json.dump({'g|E1|ml|': {'res': 'L', 'fin': [0, 0]}}, open(tmp_path / 'out' / 'results.json', 'w'))
    run(repo, tmp_path)
    assert load(tmp_path, 'results.json')['g|E1|ml|'] == {'res': 'L', 'fin': [0, 0]}


def test_commit_without_model_json_is_priced_without_a_model(tmp_path):
    repo = str(tmp_path / 'repo'); os.makedirs(repo); subprocess.run(['git', 'init', '-q', repo], check=True)
    commit(repo, '2026-11-02T12:00:00Z', {'ODD': odd('2026-11-02T10:52')})
    os.remove(os.path.join(repo, 'model.json'))
    subprocess.run(['git', '-C', repo, 'rm', '-q', '--cached', 'model.json'], check=True)
    env = dict(os.environ, GIT_AUTHOR_DATE='2026-11-03T12:00:00Z', GIT_COMMITTER_DATE='2026-11-03T12:00:00Z')
    with open(os.path.join(repo, 'data.json'), 'w') as f: json.dump({'ODD': odd('2026-11-03T10:52'), 'META': 2}, f)
    subprocess.run(['git', '-C', repo, 'add', 'data.json'], check=True)
    subprocess.run(['git', '-C', repo, '-c', 'user.name=t', '-c', 'user.email=t@t', '-c', 'commit.gpgsign=false', 'commit', '-q', '-m', 'x'], check=True, env=env)
    rows, parsed, skipped, _ = bf.replay(bf.commits_touching(repo, '2026-10-27', 'HEAD'), bf.make_loader(repo), lambda s: None)
    by = {r['id']: r for r in rows if r['snapshot_ts'] == '2026-11-03T10:52'}
    assert len(parsed) == 2 and not skipped
    assert by['p|E1|P2|Rec yds|60.5']['pm'] is None and by['p|E1|P2|Rec yds|60.5']['pf'] == .5
