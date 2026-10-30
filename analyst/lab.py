"""Backtest helpers for the analyst. Everything is built from nflverse weekly stats (free) and the recipe in model.json.

    import analyst.lab as lab                       # run from the repo root
    R = lab.rows([2025, 2026])                      # one row per player-game, history only from earlier games
    lab.mae(R, 'Rec yds')                           # average miss of the current recipe
    lab.calibration(R, 'Receptions')                # predicted vs actual "over" share at lines 0.8x-1.2x projection
    lab.mae(R, 'Rec yds', recipe=lambda h, prior: 0.7*h.mean()+0.3*h[-3:].mean())   # try another recipe

A row: pid, pos, season, week, team, opp, att/car/tgt (per-game usage before this game), and per prop type
'<prop>|hist' (earlier values this season), '<prop>|act' (this game), '<prop>|prior' (last season per game).
"""
import json, numpy as np, pandas as pd, os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import sources, model_fit

MK = model_fit.MK
_cache = {}

def weekly(y):
    if y not in _cache: _cache[y] = model_fit.weekly(y)
    return _cache[y]

def rows(seasons, min_prior_games=3):
    out = []
    for s in seasons:
        cur, prev = weekly(s), weekly(s - 1)
        pg = prev.groupby('player_id'); pn = pg.size(); pm = pg[list(MK.values())].mean()
        for pid, g in cur.sort_values('week').groupby('player_id'):
            pos = g.position.iloc[-1]
            if pos not in ('QB', 'RB', 'WR', 'TE'): continue
            att, car, tgt = g.attempts.values, g.carries.values, g.targets.values
            for i in range(min_prior_games, len(g)):
                r = {'pid': pid, 'pos': pos, 'season': s, 'week': int(g.week.values[i]), 'team': g.team.values[i],
                     'opp': g.opponent_team.values[i], 'att': att[:i].mean(), 'car': car[:i].mean(), 'tgt': tgt[:i].mean()}
                for k, col in MK.items():
                    v = g[col].values; r[k + '|hist'] = v[:i]; r[k + '|act'] = v[i]
                    r[k + '|prior'] = pm.loc[pid, col] if pid in pm.index and pn[pid] >= 4 else np.nan
                out.append(r)
    return out

def relevant(r, k): return model_fit.relevant(r['pos'], r['att'], r['car'], r['tgt'], k)

def current_recipe(h, prior):
    m = json.load(open('model.json')); w, k0 = m['w'], m['k0']
    c = w * h.mean() + (1 - w) * h[-3:].mean()
    if prior is not None and not np.isnan(prior): c = (len(h) * c + k0 * prior) / (len(h) + k0)
    return c

def mae(R, k, recipe=current_recipe):
    xs = [(recipe(r[k + '|hist'], r[k + '|prior']), r[k + '|act']) for r in R if relevant(r, k)]
    return {'n': len(xs), 'avg_miss': float(np.mean([abs(a - b) for a, b in xs])) if xs else None}

def calibration(R, k, recipe=current_recipe, quantiles=None, cal=None):
    m = json.load(open('model.json'))
    q = np.array(quantiles or m['q'][k]); c = m.get('cal', {}).get(k, 0) if cal is None else cal
    P, Y = [], []
    for r in R:
        if not relevant(r, k): continue
        mu = recipe(r[k + '|hist'], r[k + '|prior'])
        if mu <= 0: continue
        for f in (0.8, 0.9, 1.0, 1.1, 1.2):
            L = np.floor(mu * f) + .5; P.append(min(.99, max(.01, np.mean(q > L / mu) + c))); Y.append(r[k + '|act'] > L)
    P, Y = np.array(P), np.array(Y)
    bins = [(0, .35), (.35, .45), (.45, .55), (.55, .65), (.65, 1.01)]
    return {'n': len(Y), 'said_over': float(P.mean()) if len(P) else None, 'went_over': float(Y.mean()) if len(Y) else None,
            'bins': [{'pred': f'{lo:.2f}-{hi:.2f}', 'n': int(((P >= lo) & (P < hi)).sum()),
                      'actual': float(Y[(P >= lo) & (P < hi)].mean()) if ((P >= lo) & (P < hi)).sum() else None} for lo, hi in bins]}
