"""One-off back-fill of the prediction ledger (engine/ledger.py) from git history of data.json.

python analyst/backfill_ledger.py --ledger-out LEDGER.json --results-out RESULTS.json [--since 2026-10-27] [--ref HEAD]

Replays every commit that touched data.json since SINCE up to REF: each commit's ODD (games G, props P, blend MB, picks PK)
and the model.json at the same commit go through engine.ledger.ledger_rows. Rows merge into a ledger keyed by row id,
{id: {'first': row, 'last': row}}: the first and the last pre-kickoff snapshot of each line (one snapshot gives first == last).
Snapshots are ordered by (snapshot_ts, built, commit_at, content): 'built' and 'commit_at' are fields this script adds to
every row, the ODD.at and the commit time (%cI) of the commit that built it; the row's own JSON breaks any last tie. Many builds carry one prop quote unchanged (same snapshot_ts), each with its own pj, P, pick flag and
model_fit_at; 'last' is the latest build of the latest quote and 'first' the earliest build of the earliest quote, so for
an unchanged quote 'first' means the earliest build that carried it, not the moment it was quoted. Then
every id is graded for the side its row holds (engine.ledger_grading) from the finals and weekly stats in data.json at
REF, giving results {id: {'res', 'fin' | 'val'}}.

Stamps: ODD.at is when the game lines were fetched; game rows are stamped and cut at kickoff with it. A prop row is stamped
(and cut at kickoff) with the fetch time of its own event's cache, odds/props/<eid>.json 'fetched' at that commit: ODD.pat
is only the newest of those, so it would date an older event's quotes too late. A prop with no readable cache file falls
back to ODD.pat, then to ODD.at (each such event is logged per commit and counted in the summary). A prop whose event had
kicked off by the commit's own ODD.at is dropped: sources.py keeps old caches, so a later build still carries it.

Pass --ref main (or origin/main): the default HEAD is wherever the checkout is, and in a worktree that can be a stale
branch point. --since is a UTC date, taken at 00:00 UTC; commits are filtered on their commit date.

Both outputs are written to the paths given (nothing inside the repo by default). If a file exists it is loaded and merged,
so run order and --since don't matter: a re-run adds no duplicate ids, keeps existing results, moves a first snapshot only
to a strictly smaller (snapshot_ts, built, commit_at, content) and a last one only to a strictly larger; the merged
ledger is the same whatever order the rows arrive in. Outputs written by earlier versions of this script stamped props with
ODD.pat and have no 'built' or 'commit_at' field: a run that finds such a ledger refuses (exit 1, nothing written); regenerate both
outputs from empty paths. A commit that
can't be read or priced is skipped with a one-line reason; the run never aborts on one. If data.json at REF has no finals
(ODD.FIN) or no weekly stats (LOG), the run warns on stderr, writes nothing and exits 1.
"""
import argparse, datetime, json, os, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from engine.ledger import ledger_rows  # noqa: E402
from engine.picks import started  # noqa: E402
from engine.ledger_grading import grade_rows  # noqa: E402


def _ts(s):
    """A snapshot_ts (ISO; no zone means UTC) as an aware datetime."""
    d = datetime.datetime.fromisoformat(s.replace('Z', '+00:00'))
    return d if d.tzinfo else d.replace(tzinfo=datetime.timezone.utc)


# ---- pure logic (no git)

_EPOCH = datetime.datetime.min.replace(tzinfo=datetime.timezone.utc)


def _key(row):
    """The order snapshots of one id go in: when the quote was taken, which build carried it, when that build was committed
    (a row without 'commit_at' sorts first), and the row's own JSON so that even a full tie resolves the same way every time."""
    c = row.get('commit_at')
    return (_ts(row['snapshot_ts']), _ts(row.get('built') or row['snapshot_ts']), _ts(c) if c else _EPOCH,
            json.dumps(row, sort_keys=True, separators=(',', ':')))


def live_props(odd):
    """ODD.P rows whose event hasn't kicked off by the commit's own ODD.at (a later build still carries a started event's old cache)."""
    now = _ts(odd['at'])
    return [p for p in odd['P'] if p.get('ko') and not started(p['ko'], now)]


def fallback_events(odd, fetched):
    """The events among ODD's live props with no cache fetch time in FETCHED (their props are stamped with ODD.pat, or ODD.at without one)."""
    return sorted({p['eid'] for p in live_props(odd) if not (fetched or {}).get(p['eid'])})


def snapshot_rows(odd, model, fetched=None, commit_at=''):
    """Ledger rows for one commit's ODD and its MODEL, each with 'built' = ODD.at and 'commit_at' = COMMIT_AT (the commit time). Game rows are stamped ODD.at; prop rows
    (of events not yet started at ODD.at) with FETCHED[eid], the fetch time of the prop's own event cache (else ODD.pat,
    else ODD.at), and cut at kickoff by that time. One ledger_rows call per distinct time, props only kept."""
    at = odd['at']; pat = odd.get('pat') or at; fetched = fetched or {}
    rows = ledger_rows(odd['G'], [], model, odd['MB'], odd['PK'], at)
    groups = {}
    for p in live_props(odd): groups.setdefault(fetched.get(p['eid']) or pat, []).append(p)
    for ts, ps in groups.items(): rows += [r for r in ledger_rows(odd['G'], ps, model, odd['MB'], odd['PK'], ts) if r['k'] == 'p']
    return [dict(r, built=at, commit_at=commit_at) for r in rows]


def replay(shas, load, log=print):
    """Rows from every commit in SHAS: LOAD(sha) returns (ODD dict, model dict, {eid: props cache fetch time}). Returns (rows,
    parsed shas, [(sha, reason)] for the commits skipped, events stamped with ODD.pat or ODD.at for want of a cache time, summed over
    commits). A commit that raises is skipped (LOG gets a one-line reason), never fatal."""
    rows = []; parsed = []; skipped = []; fallbacks = 0
    for sha in shas:
        try:
            odd, model, fetched, *more = load(sha)    # a fourth item, if any, is the commit time
            got = snapshot_rows(odd, model, fetched, *more); fb = fallback_events(odd, fetched)
        except Exception as ex:
            why = '%s: %s' % (type(ex).__name__, str(ex).splitlines()[0][:100] if str(ex) else '')
            skipped.append((sha, why)); log('skip %s  %s' % (sha[:7], why)); continue
        if fb: log('%s  %d event(s) with no readable props cache, stamped with ODD.pat or ODD.at: %s' % (sha[:7], len(fb), ', '.join(fb)))
        rows += got; parsed.append(sha); fallbacks += len(fb)
    return rows, parsed, skipped, fallbacks


def merge_rows(ledger, rows):
    """Merge ROWS into LEDGER ({id: {'first', 'last'}}) in place. A new id starts with first == last; an existing id's first
    moves only to a strictly smaller (snapshot_ts, built, commit_at, content) and its last only to a strictly larger one (a row
    without 'built' counts as built at its snapshot_ts). So first is the smallest key and last the largest of everything merged, whatever
    order the rows arrive in or the --since of an earlier run, and a repeat changes nothing. Returns (new ids, moved
    firsts and lasts)."""
    new = moved = 0
    for row in sorted(rows, key=_key):
        e = ledger.get(row['id']); k = _key(row)
        if e is None: ledger[row['id']] = {'first': row, 'last': row}; new += 1; continue
        if k < _key(e['first']): e['first'] = row; moved += 1
        if k > _key(e['last']): e['last'] = row; moved += 1
    return new, moved


def finals_from_fin(fin):
    """engine.grading's FINALS from ODD.FIN rows [week, away, home, away score, home score]."""
    out = {}
    for wk, a, h, asc, hsc in fin:
        out[(wk, a, h)] = (asc, hsc); out[(wk, h)] = out[(wk, a)] = (a, h, asc, hsc)
    return out


def grade_ledger(ledger, results, data):
    """Grade every ledger id not yet in RESULTS (updated in place) from DATA, the data.json at the end ref. Returns the
    number of newly graded ids."""
    logs = data['LOG']; logmax = max((r[0] for rs in logs.values() for r in rs), default=0)
    new = grade_rows([e['last'] for e in ledger.values()], finals_from_fin(data['ODD']['FIN']), logs, logmax, done=results)
    results.update(new)
    return len(new)


# ---- git access

def _git(repo, *args):
    p = subprocess.run(['git', '-C', repo, *args], capture_output=True)
    if p.returncode: raise RuntimeError((p.stderr.decode('utf-8', 'replace').strip() or 'git failed').splitlines()[-1])
    return p.stdout


def commits_touching(repo, since, ref):
    """Shas of the commits up to REF that changed data.json and were committed at or after SINCE (a date, taken at 00:00
    UTC; git's own --since reads a bare date at the current time of day), oldest first."""
    start = _ts(since); out = []
    for line in _git(repo, 'log', '--format=%H %cI', ref, '--', 'data.json').decode().splitlines():
        sha, when = line.split()
        if _ts(when) >= start: out.append(sha)
    return out[::-1]


def make_loader(repo):
    """A LOAD(sha) for replay: (data.json's ODD, model.json, {eid: odds/props/<eid>.json 'fetched'}, commit time %cI) as of that commit. Before
    model.json existed (first committed 2026-10-29) the build ran without a model, so a commit with no model.json gets
    model None, as the refresh did. A props cache file that can't be read is left out (its props fall back to ODD.pat, then ODD.at)."""
    def load(sha):
        odd = json.loads(_git(repo, 'show', sha + ':data.json'))['ODD']
        has = subprocess.run(['git', '-C', repo, 'cat-file', '-e', sha + ':model.json'], capture_output=True).returncode == 0
        fetched = {}
        for path in _git(repo, 'ls-tree', '--name-only', sha, 'odds/props/').decode().split():
            try: fetched[os.path.basename(path)[:-5]] = json.loads(_git(repo, 'show', sha + ':' + path))['fetched']
            except Exception: pass
        when = _git(repo, 'show', '-s', '--format=%cI', sha).decode().strip()
        return odd, json.loads(_git(repo, 'show', sha + ':model.json')) if has else None, fetched, when
    return load


def _read(path):
    try:
        with open(path, encoding='utf-8') as f: return json.load(f)
    except FileNotFoundError: return {}


def _write(path, obj):
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f: json.dump(obj, f, separators=(',', ':'), sort_keys=True)


class NothingToGrade(Exception):
    """data.json at the end ref has no finals or no weekly stats (its odds section probably failed)."""


class StaleOutput(Exception):
    """An existing ledger file was written by an earlier version of this script (rows without 'built')."""


def backfill(repo, since, ref, ledger_out, results_out, log=print):
    """Replay, merge and grade; writes both files. Returns a summary dict. Before writing anything, raises NothingToGrade
    when data.json at REF has no ODD.FIN or no LOG, and StaleOutput when an existing ledger lacks 'built' or 'commit_at'."""
    data = json.loads(_git(repo, 'show', ref + ':data.json'))
    fin = (data.get('ODD') or {}).get('FIN'); stats = data.get('LOG')
    if not fin or not stats:
        raise NothingToGrade('data.json at %s has no %s: nothing to grade with; pass a --ref whose build finished' % (
            ref, ' or '.join(k for k, v in (('finals (ODD.FIN)', fin), ('weekly stats (LOG)', stats)) if not v)))
    ledger = _read(ledger_out); results = _read(results_out)
    if any(not isinstance(e, dict) or not all(isinstance(e.get(part), dict) and e[part].get('built') and e[part].get('commit_at')
                                              for part in ('first', 'last')) for e in ledger.values()):
        raise StaleOutput('%s was written by an earlier version of this script (rows without "built" or "commit_at", props stamped with ODD.pat): '
                          'nothing written; regenerate %s and %s from empty paths' % (ledger_out, ledger_out, results_out))
    shas = commits_touching(repo, since, ref)
    rows, parsed, skipped, fallbacks = replay(shas, make_loader(repo), log)
    new, moved = merge_rows(ledger, rows)
    graded = grade_ledger(ledger, results, data)
    _write(ledger_out, ledger); _write(results_out, results)
    return {'commits': len(shas), 'parsed': len(parsed), 'skipped': skipped, 'new_ids': new, 'moved': moved,
            'ids': len(ledger), 'fallbacks': fallbacks, 'newly_graded': graded, 'graded': len(results)}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--ledger-out', required=True); ap.add_argument('--results-out', required=True)
    ap.add_argument('--since', default='2026-10-27', help='UTC date; commits committed before 00:00 UTC that day are left out')
    ap.add_argument('--ref', default='HEAD', help='the commit to replay up to and grade from; pass main (or origin/main): in a worktree HEAD can be a stale branch point')
    ap.add_argument('--repo', default=ROOT)
    a = ap.parse_args(argv)
    try: s = backfill(a.repo, a.since, a.ref, a.ledger_out, a.results_out)
    except (NothingToGrade, StaleOutput) as ex: print('error:', ex, file=sys.stderr); sys.exit(1)
    print('commits %d: parsed %d, skipped %d | ids %d (+%d new, %d first/last moved) | graded %d (+%d) | events stamped with pat/at: %d' % (
        s['commits'], s['parsed'], len(s['skipped']), s['ids'], s['new_ids'], s['moved'], s['graded'], s['newly_graded'], s['fallbacks']))
    return s


if __name__ == '__main__': main()
