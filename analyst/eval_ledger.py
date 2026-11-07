"""Scores graded prediction-ledger rows (engine/ledger.py): is the model calibrated, and how much weight has it earned
against the market?

    import analyst.eval_ledger as ev                # run from the repo root
    ev.report(rows)                                 # everything below, as one dict
    ev.scores(rows)                                 # Brier and log loss: blend, model and market, and paired differences
    ev.reliability(rows, 'P')                       # forecast buckets: average chance said vs share that happened
    ev.weight(rows)                                 # the model's fitted weight, with a game-clustered interval

    python analyst/eval_ledger.py graded.jsonl ...  # the same report from JSON Lines files of graded rows

A graded row is a ledger row plus its outcome for the side the row holds (the over, yes, or home side): 'y' (1 or 0)
or 'res' ('W' or 'L'; a push 'P' or void 'V' is left out). Rows need 'eid' (the game, for clustering), 'pm' (model),
'pf' (market fair) and, for the blend's scores, 'P'. Filter rows before passing them (by market, book count, week);
this module takes every row it is given. Rows from one game share game script and weather, so every interval
resamples whole games, never single rows.

The weight is Benter's second stage: a logistic regression of the outcome on logit(market) and the gap
logit(model) - logit(market). The gap's coefficient c is the weight the model has earned on the log-odds scale
(0: the market already knows everything the model does; the dashboard's 0.5 linear blend is close to c = 0.5).
Standard library plus numpy, the way analyst/lab.py is.
"""
import json, math, sys

import numpy as np

EPS = 1e-4   # chances are kept inside [EPS, 1 - EPS] for log loss and log-odds


def outcome(row):
    """1 when the row's side happened, 0 when it didn't, None for a push, a void or no result yet."""
    if row.get('y') is not None: return int(row['y'])
    return {'W': 1, 'L': 0}.get(row.get('res'))


def usable(rows):
    """Rows with an outcome, a model chance and a market chance."""
    return [r for r in rows if outcome(r) is not None and r.get('pm') is not None and r.get('pf') is not None]


def _clip(p): return np.clip(np.asarray(p, dtype=float), EPS, 1 - EPS)


def _logit(p): p = _clip(p); return np.log(p / (1 - p))


def _brier(p, y): return (np.asarray(p, dtype=float) - y) ** 2


def _logloss(p, y): p = _clip(p); return -(y * np.log(p) + (1 - y) * np.log(1 - p))


def _games(rows):
    """(game index per row, number of games), games numbered in order of first appearance."""
    ix = {}; g = np.array([ix.setdefault(r['eid'], len(ix)) for r in rows]); return g, len(ix)


def _resamples(g, n_games, boot, rng):
    """BOOT lists of row indices, each from a resample of whole games with replacement."""
    members = [[] for _ in range(n_games)]
    for i, k in enumerate(g): members[k].append(i)
    members = [np.array(m) for m in members]
    for _ in range(boot):
        yield np.concatenate([members[k] for k in rng.integers(0, n_games, n_games)])


def _interval(xs, level=.95):
    a = (1 - level) / 2; return float(np.quantile(xs, a)), float(np.quantile(xs, 1 - a))


def scores(rows, boot=1000, seed=0):
    """Brier score and log loss (lower is better) of the blend (P), the model (pm) and the market (pf) on the same
    rows (usable rows with P), plus the paired differences blend - market and model - market, each with a 95%
    game-clustered bootstrap interval. A negative difference means the forecast beat the market."""
    R = [r for r in usable(rows) if r.get('P') is not None]
    y = np.array([outcome(r) for r in R], dtype=float); g, n_games = _games(R)
    F = {'blend': [r['P'] for r in R], 'model': [r['pm'] for r in R], 'market': [r['pf'] for r in R]}
    out = {'n': len(R), 'games': n_games}
    if not R: return out
    idx = list(_resamples(g, n_games, boot, np.random.default_rng(seed)))
    for name, f in (('brier', _brier), ('log_loss', _logloss)):
        per = {k: f(v, y) for k, v in F.items()}; s = {k: float(v.mean()) for k, v in per.items()}
        for k in ('blend', 'model'):
            d = per[k] - per['market']; lo, hi = _interval([d[i].mean() for i in idx])
            s['%s_minus_market' % k] = {'mean': float(d.mean()), 'lo': lo, 'hi': hi}
        out[name] = s
    return out


def reliability(rows, key='P', bins=10):
    """Forecast KEY ('P', 'pm' or 'pf') in BINS equal buckets of [0, 1] (a chance of 1 goes in the top one): per
    non-empty bucket the rows, the average chance said, the share that happened, and the binomial standard error a
    calibrated forecaster would show there."""
    R = [r for r in usable(rows) if r.get(key) is not None]
    p = np.array([r[key] for r in R], dtype=float); y = np.array([outcome(r) for r in R], dtype=float)
    k = np.minimum((p * bins).astype(int), bins - 1); out = []
    for b in range(bins):
        m = k == b
        if not m.any(): continue
        said = float(p[m].mean())
        out.append({'bin': '%.2f-%.2f' % (b / bins, (b + 1) / bins),
                    'n': int(m.sum()), 'said': said, 'went': float(y[m].mean()), 'se': math.sqrt(said * (1 - said) / m.sum())})
    return out


def _fit(X, y, iters=50):
    """Logistic regression coefficients by Newton's method (iteratively reweighted least squares)."""
    beta = np.zeros(X.shape[1])
    for _ in range(iters):
        p = 1 / (1 + np.exp(-(X @ beta))); w = p * (1 - p)
        step = np.linalg.solve(X.T @ (X * w[:, None]), X.T @ (y - p)); beta += step
        if np.abs(step).max() < 1e-10: break
    return beta


def weight(rows, boot=1000, seed=0):
    """The model's weight: fits y ~ a + b * logit(pf) + c * (logit(pm) - logit(pf)) on usable rows. Returns a, b
    (1 when the market is calibrated), c (the model's weight) and a 95% game-clustered bootstrap interval for c."""
    R = usable(rows); g, n_games = _games(R)
    if len(R) < 3: return {'n': len(R), 'games': n_games, 'a': None, 'b': None, 'c': None, 'lo': None, 'hi': None}
    y = np.array([outcome(r) for r in R], dtype=float)
    lm = _logit([r['pf'] for r in R]); gap = _logit([r['pm'] for r in R]) - lm
    X = np.column_stack([np.ones(len(R)), lm, gap])
    a, b, c = _fit(X, y)
    cs = [_fit(X[i], y[i])[2] for i in _resamples(g, n_games, boot, np.random.default_rng(seed))]
    lo, hi = _interval(cs)
    return {'n': len(R), 'games': n_games, 'a': float(a), 'b': float(b), 'c': float(c), 'lo': lo, 'hi': hi}


def report(rows, boot=1000, seed=0, bins=10):
    """scores, a reliability table for each forecast, and the weight, for the Researcher's report."""
    return {'scores': scores(rows, boot, seed),
            'reliability': {name: reliability(rows, key, bins) for name, key in (('blend', 'P'), ('model', 'pm'), ('market', 'pf'))},
            'weight': weight(rows, boot, seed)}


def read_jsonl(paths):
    rows = []
    for path in paths:
        with open(path, encoding='utf-8') as f: rows += [json.loads(line) for line in f if line.strip()]
    return rows


if __name__ == '__main__':
    if len(sys.argv) < 2: sys.exit('usage: python analyst/eval_ledger.py graded.jsonl [more.jsonl ...]')
    print(json.dumps(report(read_jsonl(sys.argv[1:])), indent=1))
