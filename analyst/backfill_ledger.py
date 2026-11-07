"""One-off back-fill of the prediction ledger (engine/ledger.py) from git history of data.json.

python analyst/backfill_ledger.py --ledger-out LEDGER.json --results-out RESULTS.json [--since 2026-10-27] [--ref HEAD]

Replays every commit that touched data.json since SINCE up to REF: each commit's ODD (games G, props P, blend MB, picks PK)
and the model.json at the same commit go through engine.ledger.ledger_rows. Rows merge into a ledger keyed by row id,
{id: {'first': row, 'last': row}}: the first and the last pre-kickoff snapshot of each line (one snapshot gives first == last;
a snapshot_ts already seen for an id adds nothing, so a refresh that re-committed identical odds changes nothing). Then
every id is graded for the side its row holds (engine.ledger_grading) from the finals and weekly stats in data.json at
REF, giving results {id: {'res', 'fin' | 'val'}}.

Stamps: ODD.at is when the game lines were fetched and ODD.pat when the props were (the newest props cache); game rows
are stamped and cut at kickoff with 'at', prop rows with 'pat' (falling back to 'at'), so each is dated by its own quotes.

Both outputs are written to the paths given (nothing inside the repo by default). If a file exists it is loaded and merged:
a re-run adds no duplicate ids, keeps existing results, never replaces a first snapshot and moves a last one only to a
later snapshot. A commit that can't be read or priced is skipped with a one-line reason; the run never aborts on one.
"""
import argparse, datetime, json, os, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from engine.ledger import ledger_rows  # noqa: E402
from engine.ledger_grading import grade_rows  # noqa: E402


def _ts(s):
    """A snapshot_ts (ISO; no zone means UTC) as an aware datetime."""
    d = datetime.datetime.fromisoformat(s.replace('Z', '+00:00'))
    return d if d.tzinfo else d.replace(tzinfo=datetime.timezone.utc)


# ---- pure logic (no git)

def snapshot_rows(odd, model):
    """Ledger rows for one commit's ODD and its MODEL: game rows stamped ODD.at, prop rows stamped ODD.pat (else at)."""
    at = odd['at']; pat = odd.get('pat') or at
    rows = ledger_rows(odd['G'], [], model, odd['MB'], odd['PK'], at)
    if odd['P']: rows += [r for r in ledger_rows(odd['G'], odd['P'], model, odd['MB'], odd['PK'], pat) if r['k'] == 'p']
    return rows


def replay(shas, load, log=print):
    """Rows from every commit in SHAS: LOAD(sha) returns (ODD dict, model dict). Returns (rows, parsed shas, [(sha, reason)])
    for the commits skipped; a commit that raises is skipped (LOG gets a one-line reason), never fatal."""
    rows = []; parsed = []; skipped = []
    for sha in shas:
        try:
            odd, model = load(sha)
            got = snapshot_rows(odd, model)
        except Exception as ex:
            why = '%s: %s' % (type(ex).__name__, str(ex).splitlines()[0][:100] if str(ex) else '')
            skipped.append((sha, why)); log('skip %s  %s' % (sha[:7], why)); continue
        rows += got; parsed.append(sha)
    return rows, parsed, skipped


def merge_rows(ledger, rows):
    """Merge ROWS into LEDGER ({id: {'first', 'last'}}) in place, oldest snapshot first. A new id starts with first == last;
    an existing id's last moves only to a strictly later snapshot_ts, and its first never changes. Returns (new ids, moved lasts)."""
    new = moved = 0
    for row in sorted(rows, key=lambda r: _ts(r['snapshot_ts'])):
        e = ledger.get(row['id'])
        if e is None: ledger[row['id']] = {'first': row, 'last': row}; new += 1
        elif _ts(row['snapshot_ts']) > _ts(e['last']['snapshot_ts']): e['last'] = row; moved += 1
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
    logs = data.get('LOG') or {}
    logmax = max((r[0] for rs in logs.values() for r in rs), default=0)
    new = grade_rows([e['last'] for e in ledger.values()], finals_from_fin((data.get('ODD') or {}).get('FIN') or []), logs, logmax, done=results)
    results.update(new)
    return len(new)


# ---- git access

def _git(repo, *args):
    p = subprocess.run(['git', '-C', repo, *args], capture_output=True)
    if p.returncode: raise RuntimeError((p.stderr.decode('utf-8', 'replace').strip() or 'git failed').splitlines()[-1])
    return p.stdout


def commits_touching(repo, since, ref):
    """Shas of the commits up to REF since the date SINCE that changed data.json, oldest first."""
    return _git(repo, 'log', '--reverse', '--since=' + since, '--format=%H', ref, '--', 'data.json').decode().split()


def make_loader(repo):
    """A LOAD(sha) for replay: (data.json's ODD, model.json) as of that commit. Before model.json existed (first committed
    2026-10-29) the build ran without a model, so a commit with no model.json gets model None, as the refresh did."""
    def load(sha):
        odd = json.loads(_git(repo, 'show', sha + ':data.json'))['ODD']
        has = subprocess.run(['git', '-C', repo, 'cat-file', '-e', sha + ':model.json'], capture_output=True).returncode == 0
        return odd, json.loads(_git(repo, 'show', sha + ':model.json')) if has else None
    return load


def _read(path):
    try:
        with open(path, encoding='utf-8') as f: return json.load(f)
    except FileNotFoundError: return {}


def _write(path, obj):
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f: json.dump(obj, f, separators=(',', ':'), sort_keys=True)


def backfill(repo, since, ref, ledger_out, results_out, log=print):
    """Replay, merge and grade; writes both files. Returns a summary dict."""
    ledger = _read(ledger_out); results = _read(results_out)
    shas = commits_touching(repo, since, ref)
    rows, parsed, skipped = replay(shas, make_loader(repo), log)
    new, moved = merge_rows(ledger, rows)
    data = json.loads(_git(repo, 'show', ref + ':data.json'))
    graded = grade_ledger(ledger, results, data)
    _write(ledger_out, ledger); _write(results_out, results)
    return {'commits': len(shas), 'parsed': len(parsed), 'skipped': skipped, 'new_ids': new, 'moved_last': moved,
            'ids': len(ledger), 'newly_graded': graded, 'graded': len(results)}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--ledger-out', required=True); ap.add_argument('--results-out', required=True)
    ap.add_argument('--since', default='2026-10-27'); ap.add_argument('--ref', default='HEAD')
    ap.add_argument('--repo', default=ROOT)
    a = ap.parse_args(argv)
    s = backfill(a.repo, a.since, a.ref, a.ledger_out, a.results_out)
    print('commits %d: parsed %d, skipped %d | ids %d (+%d new, %d last moved) | graded %d (+%d)' % (
        s['commits'], s['parsed'], len(s['skipped']), s['ids'], s['new_ids'], s['moved_last'], s['graded'], s['newly_graded']))
    return s


if __name__ == '__main__': main()
