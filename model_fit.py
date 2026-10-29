"""Fits the projection model from nflverse weekly stats and writes model.json.

What it learns (all from games already played, nothing from the future):
  - q:      for each prop type, how real games swing around our projection (101 quantiles of actual / projection).
            The page turns this into "chance he goes over this line".
  - td:     anytime-TD chance from usage (carries and targets per game, plus position), a small logistic model.
  - priors: each player's per-game numbers from last season, mixed in early in the season.
Recipe that was backtested on 2025-2026 games: 85% season average + 15% last 3 games, plus 4 games' worth of last season.
Runs from the refresh workflow; skips itself if model.json is less than 6 days old (set FORCE=1 to refit).
"""
import os, json, datetime, numpy as np, pandas as pd
import sources

SEASON = sources.SEASON
W, K0, BLEND = .85, 4, .5          # recipe weights and how much we trust our model vs the market's fair chance
OUT = 'model.json'
MK = {'Pass yds': 'passing_yards', 'Rush yds': 'rushing_yards', 'Rec yds': 'receiving_yards',
      'Receptions': 'receptions', 'Pass TDs': 'passing_tds', 'Anytime TD': 'anytd'}


def fresh():
    try:
        m = json.load(open(OUT))
        age = datetime.datetime.now(datetime.timezone.utc) - datetime.datetime.fromisoformat(m['fit_at'])
        return m.get('season') == SEASON and age.days < 6
    except Exception:
        return False


def weekly(y):
    df = pd.read_csv(sources._get(sources.NFLVERSE + 'stats_player/stats_player_week_%d.csv' % y), low_memory=False)
    df = df[df.season_type == 'REG'].copy()
    for c in ['passing_yards', 'rushing_yards', 'receiving_yards', 'receptions', 'passing_tds', 'rushing_tds', 'receiving_tds',
              'attempts', 'carries', 'targets', 'fantasy_points_ppr', 'fantasy_points']:
        df[c] = df[c].fillna(0)
    df['anytd'] = ((df.rushing_tds + df.receiving_tds) >= 1).astype(float)
    return df


def relevant(pos, att, car, tgt, k):
    if k in ('Pass yds', 'Pass TDs'): return pos == 'QB' and att >= 20
    if k == 'Rush yds': return car >= 7
    if k in ('Rec yds', 'Receptions'): return pos in ('WR', 'TE', 'RB') and tgt >= 3.5
    return pos in ('RB', 'WR', 'TE') and (car + tgt) >= 5


def base(h, prior):
    c = W * h.mean() + (1 - W) * h[-3:].mean()
    if prior is not None and not np.isnan(prior):
        c = (len(h) * c + K0 * prior) / (len(h) + K0)
    return c


def fitlog(X, y, l2=1.0, it=3000, lr=.5):
    mu, sd = X.mean(0), X.std(0) + 1e-9
    Z = np.c_[np.ones(len(X)), (X - mu) / sd]; w = np.zeros(Z.shape[1])
    for _ in range(it):
        p = 1 / (1 + np.exp(-Z @ w)); w -= lr * (Z.T @ (p - y) / len(y) + l2 * np.r_[0, w[1:]] / len(y))
    return {'mu': mu.round(5).tolist(), 'sd': sd.round(5).tolist(), 'w': w.round(5).tolist()}


def main():
    if fresh() and not os.environ.get('FORCE'):
        print('model.json is fresh, not refitting'); return
    D = {y: weekly(y) for y in (SEASON - 2, SEASON - 1, SEASON)}
    ratio = {k: [] for k in MK if k != 'Anytime TD'}; tdX, tdy = [], []
    for y in (SEASON - 1, SEASON):
        cur, prev = D[y], D[y - 1]
        pg = prev.groupby('player_id'); pn = pg.size()
        pm = pg[list(MK.values())].mean()
        for pid, g in cur.sort_values('week').groupby('player_id'):
            pos = g.position.iloc[-1]
            if pos not in ('QB', 'RB', 'WR', 'TE'): continue
            pri = pm.loc[pid] if pid in pm.index and pn[pid] >= 4 else None
            att, car, tgt = g.attempts.values, g.carries.values, g.targets.values
            for i in range(3, len(g)):
                a_, c_, t_ = att[:i].mean(), car[:i].mean(), tgt[:i].mean()
                for k, col in MK.items():
                    if not relevant(pos, a_, c_, t_, k): continue
                    v = g[col].values
                    if k == 'Anytime TD':
                        if i >= 4: tdX.append([c_, t_, pos == 'RB', pos == 'TE']); tdy.append(v[i])
                        continue
                    mu = base(v[:i], None if pri is None else pri[col])
                    if mu > 0: ratio[k].append(v[i] / mu)
    q = {k: np.quantile(np.array(r), np.linspace(0, 1, 101)).round(4).tolist() for k, r in ratio.items()}
    td = fitlog(np.array(tdX, float), np.array(tdy, float))
    # last season per-game numbers for every player with 4+ games (used as the early-season prior)
    last = D[SEASON - 1]; g = last.groupby('player_id'); n = g.size()
    agg = g[list(MK.values()) + ['fantasy_points_ppr', 'fantasy_points']].mean()
    pri = {pid: [round(float(x), 3) for x in agg.loc[pid].values] + [int(n[pid])] for pid in agg.index if n[pid] >= 4}
    out = {'season': SEASON, 'fit_at': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'w': W, 'k0': K0, 'blend': BLEND,
           'q': q, 'td': td, 'prior_cols': list(MK.keys()) + ['PPR', 'Std', 'games'], 'priors': pri,
           'n': {k: len(r) for k, r in ratio.items()} | {'Anytime TD': len(tdy)}}
    json.dump(out, open(OUT, 'w'), separators=(',', ':'))
    print('model fit:', out['n'], '| priors', len(pri), '| median swing', {k: v[50] for k, v in q.items()})


if __name__ == '__main__':
    main()
