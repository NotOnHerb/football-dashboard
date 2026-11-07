"""analyst/backfill_ledger.py: replays git history of data.json into first/last ledger snapshots and grades them."""
import copy, json, os, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT); sys.path.insert(0, os.path.join(HERE, 'test_engine'))
from analyst import backfill_ledger as bf  # noqa: E402
import test_ledger as tl  # noqa: E402  (fixture builders: game(), yds_prop(), td_prop(), MODEL)

REPEAT_TS = '2026-11-03T10:52'


def odd(at, b=None, pat=None, fin=()):
    prop = tl.yds_prop(b=b)
    return {'MB': .5, 'G': [tl.game()], 'P': [prop, tl.td_prop()], 'PK': [], 'FIN': [list(f) for f in fin], 'at': at, 'pat': pat or at}


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
    commit(repo, '2026-11-03T12:00:00Z', {'ODD': odd(REPEAT_TS, b=moved)})                       # X moves its price: a later snapshot
    commit(repo, '2026-11-03T13:00:00Z', {'ODD': odd(REPEAT_TS, b=moved)})                       # same odds re-committed
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


def test_repeated_snapshot_ts_adds_nothing():
    rows = bf.snapshot_rows(odd('2026-11-02T10:52'), tl.MODEL)
    led = {}
    assert bf.merge_rows(led, rows) == (len(rows), 0)
    again = copy.deepcopy(rows)
    for r in again: r['o'] = {'pr': 999, 'bk': 'Q'}                  # same snapshot_ts, different content
    before = copy.deepcopy(led)
    assert bf.merge_rows(led, again) == (0, 0) and led == before


def test_older_snapshot_never_replaces_first_or_last():
    old = bf.snapshot_rows(odd('2026-11-01T10:00'), tl.MODEL); new = bf.snapshot_rows(odd('2026-11-02T10:00'), tl.MODEL)
    led = {}
    bf.merge_rows(led, new); bf.merge_rows(led, old)
    assert all(e['first']['snapshot_ts'] == e['last']['snapshot_ts'] == '2026-11-02T10:00' for e in led.values())


def test_rows_stamp_props_with_pat_and_games_with_at():
    rows = bf.snapshot_rows(odd('2026-11-02T10:52', pat='2026-11-02T09:00'), tl.MODEL)
    assert {r['snapshot_ts'] for r in rows if r['k'] == 'g'} == {'2026-11-02T10:52'}
    assert {r['snapshot_ts'] for r in rows if r['k'] == 'p'} == {'2026-11-02T09:00'}


def test_replay_skips_a_bad_commit_without_aborting():
    good = odd('2026-11-02T10:52'); logged = []
    docs = {'a': (good, tl.MODEL), 'b': ({'MB': .5}, tl.MODEL), 'd': (good, tl.MODEL)}
    def load_(sha):
        if sha == 'e': raise ValueError('bad json')
        return docs[sha]
    rows, parsed, skipped = bf.replay(['a', 'b', 'e', 'd'], load_, logged.append)
    assert parsed == ['a', 'd'] and [s for s, _ in skipped] == ['b', 'e'] and len(logged) == 2 and 'bad json' in logged[1]
    assert len(rows) == 2 * len(bf.snapshot_rows(good, tl.MODEL))


def test_malformed_commit_in_a_real_repo_is_skipped(tmp_path):
    s = run(make_repo(tmp_path), tmp_path)
    assert s['commits'] == 5 and s['parsed'] == 4 and len(s['skipped']) == 1 and s['skipped'][0][1].startswith('KeyError')


def test_since_leaves_out_earlier_commits(tmp_path):
    repo = make_repo(tmp_path)
    assert bf.commits_touching(repo, '2026-10-01', 'HEAD').__len__() == 6 and bf.commits_touching(repo, '2026-10-27', 'HEAD').__len__() == 5


# ---- grading

def test_grading_uses_the_last_commits_final_and_log(tmp_path):
    s = run(make_repo(tmp_path), tmp_path)
    res = load(tmp_path, 'results.json')
    assert res['g|E1|spread|-3.5'] == {'res': 'L', 'fin': [17, 20]}      # home won by 3: no cover at -3.5
    assert res['g|E1|spread|-3']['res'] == 'P' and res['g|E1|ml|']['res'] == 'W' and res['g|E1|total|44.5']['res'] == 'L'   # 37 total
    assert res['p|E1|P2|Rec yds|60.5'] == {'res': 'W', 'val': 70} and res['p|E1|P2|Rec yds|59.5']['res'] == 'W'
    assert res['p|E1|P1|Anytime TD|'] == {'res': 'V'}                   # no weekly row for P1: didn't play
    assert s['graded'] == s['ids']


def test_nothing_graded_while_the_game_is_unfinished(tmp_path):
    repo = make_repo(tmp_path)
    s = bf.backfill(repo, '2026-10-27', 'HEAD~2', str(tmp_path / 'l.json'), str(tmp_path / 'r.json'), log=lambda s_: None)
    assert s['graded'] == 0 and s['ids'] > 0


# ---- idempotence

def test_second_run_changes_nothing(tmp_path):
    repo = make_repo(tmp_path)
    run(repo, tmp_path)
    first = [open(tmp_path / 'out' / n, 'rb').read() for n in ('ledger.json', 'results.json')]
    s = run(repo, tmp_path)
    assert [open(tmp_path / 'out' / n, 'rb').read() for n in ('ledger.json', 'results.json')] == first
    assert s['new_ids'] == 0 and s['moved_last'] == 0 and s['newly_graded'] == 0


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
    rows, parsed, skipped = bf.replay(bf.commits_touching(repo, '2026-10-27', 'HEAD'), bf.make_loader(repo), lambda s: None)
    by = {r['id']: r for r in rows if r['snapshot_ts'] == '2026-11-03T10:52'}
    assert len(parsed) == 2 and not skipped
    assert by['p|E1|P2|Rec yds|60.5']['pm'] is None and by['p|E1|P2|Rec yds|60.5']['pf'] == .5
