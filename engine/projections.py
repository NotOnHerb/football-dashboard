"""Player projections: the recipe (season average + recent form + last season), the matchup factor, the chance of
going over a line from the fitted swing pattern, and the anytime-TD chance from usage.

model.json supplies the inputs: w and k0 for the recipe, q (quantiles of actual / projection) and cal for p_over,
td for td_chance. model_fit.py fits them.
Importing this module needs only the standard library (analyst/snapshot.py runs without numpy); td_chance uses numpy.
"""


def base_projection(hist, prior, w, k0):
    """Projection from this season's values HIST (oldest first): w * season average + (1 - w) * last 3 games, then mixed
    with last season's per-game PRIOR as if it were k0 extra games. No prior (None or NaN) or k0 = 0 skips the mix.
    A numpy array is averaged with numpy (as model_fit and the lab do); a list with sum/len (as the build does)."""
    if hasattr(hist, 'mean'):
        c = w * hist.mean() + (1 - w) * hist[-3:].mean()
    else:
        avg = sum(hist) / len(hist); l3 = sum(hist[-3:]) / len(hist[-3:]); c = w * avg + (1 - w) * l3
    if prior is not None and k0 and prior == prior:   # prior != prior only for NaN
        c = (len(hist) * c + k0 * prior) / (len(hist) + k0)
    return c


def matchup_factor(opp_allowed, league_avg):
    """Scales a projection by half of how far the opponent's allowed number is from the league average, kept to 0.8-1.25."""
    return min(1.25, max(.8, 1 + .5 * (opp_allowed / league_avg - 1)))


def p_over(q, cal, mu, line):
    """Chance of going over LINE when the projection is MU: the share of quantiles Q (actual / projection) above
    line / mu, plus the calibration nudge CAL, kept to 0.01-0.99. None without quantiles or a positive projection."""
    if not q or not mu or mu <= 0: return None
    x = line / mu; p_ = sum(1 for v in q if v > x) / len(q)
    return min(.99, max(.01, p_ + cal))


def td_chance(td_model, usage, pos):
    """Anytime-TD chance from usage (carries/g, targets/g, games) and position, with the logistic model TD_MODEL
    (model.json 'td'). None without a model, under 4 games or 5 touches a game, or for non RB/WR/TE."""
    import numpy as np   # here, not at the top, so the module imports without numpy
    u = usage
    if not td_model or not u or u[2] < 4 or u[0] + u[1] < 5 or pos not in ('RB', 'WR', 'TE'): return None
    t = td_model; x = [u[0], u[1], 1.0 if pos == 'RB' else 0.0, 1.0 if pos == 'TE' else 0.0]
    z = t['w'][0] + sum(t['w'][i + 1] * (x[i] - t['mu'][i]) / t['sd'][i] for i in range(4)); return 1 / (1 + np.exp(-z))
