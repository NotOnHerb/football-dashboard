"""Team ratings from game scores, by ridge regression.

fit_nfl rates margins (a point rating per team plus home field) and scoring (offense and defense per team, a league
scoring level and home field), so it projects both a margin and a total. fit_ridge_margins is the margins-only fit the
college board uses.
"""
import numpy as np


def fit_nfl(games, teams, prior=None, lam=8.0):
    """Fits NFL ratings from GAMES (rows with home_team, away_team, home_score, away_score; other teams are skipped).
    PRIOR (team -> points) is subtracted before the fit and added back, so ratings shrink toward it instead of 0.
    Returns (ratings, home field, offense, defense, league points per team per game)."""
    tl = sorted(teams); ix = {t: i for i, t in enumerate(tl)}; n = len(tl); Xm = []; ym = []; Xp = []; yp = []
    for r in games.itertuples():
        if r.home_team not in ix or r.away_team not in ix: continue
        h, a = ix[r.home_team], ix[r.away_team]
        x = np.zeros(n + 1); x[h] = 1; x[a] = -1; x[n] = 1; Xm.append(x); ym.append(r.home_score - r.away_score - ((prior[r.home_team] - prior[r.away_team]) if prior else 0))
        for sc, o, dd, hm in ((r.home_score, h, a, 1), (r.away_score, a, h, -1)):
            x = np.zeros(2 * n + 2); x[o] = 1; x[n + dd] = -1; x[2 * n] = 1; x[2 * n + 1] = hm / 2; Xp.append(x); yp.append(sc)
    rid = lambda X, y, pen: np.linalg.solve(np.array(X).T @ np.array(X) + np.diag(pen), np.array(X).T @ np.array(y))
    bm = rid(Xm, ym, np.r_[np.full(n, lam), .01]); bp_ = rid(Xp, yp, np.r_[np.full(2 * n, lam), .01, .01])
    R = {t: bm[ix[t]] + (prior[t] if prior else 0) for t in tl}
    return R, bm[n], {t: bp_[ix[t]] for t in tl}, {t: bp_[n + ix[t]] for t in tl}, bp_[2 * n]


def project(fit, home, away):
    """Projected (home margin, total) from a fit_nfl result."""
    R, hfa, O, D_, mu = fit
    m = R[home] - R[away] + hfa; t = 2 * mu + O[home] + O[away] - D_[home] - D_[away]; return m, t


def fit_ridge_margins(games, prior, lam):
    """Margin ratings from GAMES (dicts with homeTeam, awayTeam, homePoints, awayPoints, neutralSite), shrunk toward
    PRIOR (team -> points). Returns (ratings for every team in the games or the prior, home field)."""
    teams = sorted({g['homeTeam'] for g in games} | {g['awayTeam'] for g in games} | set(prior)); ix = {t: i for i, t in enumerate(teams)}; n = len(teams); X = []; y = []
    for g in games:
        x = np.zeros(n + 1); x[ix[g['homeTeam']]] = 1; x[ix[g['awayTeam']]] = -1; x[n] = 0 if g['neutralSite'] else 1
        X.append(x); y.append(g['homePoints'] - g['awayPoints'] - (prior.get(g['homeTeam'], 0) - prior.get(g['awayTeam'], 0)))
    X = np.array(X); y = np.array(y); bb = np.linalg.solve(X.T @ X + np.diag(np.r_[np.full(n, lam), .01]), X.T @ y)
    return {t: bb[ix[t]] + prior.get(t, 0) for t in teams}, bb[n]
