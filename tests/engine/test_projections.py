"""Player projections (recipe, matchup, chance of over, TD chance) and the team ratings models."""
import math
import numpy as np
import pandas as pd

from engine import projections, team_model


def test_base_projection_mixes_season_and_last_three():
    h = [10, 20, 30, 40]
    assert projections.base_projection(h, None, .5, 4) == .5 * 25 + .5 * 30


def test_base_projection_adds_last_season_prior():
    h = [10, 20, 30, 40]
    c = .5 * 25 + .5 * 30
    assert projections.base_projection(h, 50, .5, 4) == (4 * c + 4 * 50) / 8


def test_base_projection_skips_missing_prior_and_zero_weight():
    h = [10, 20, 30, 40]
    c = .5 * 25 + .5 * 30
    assert projections.base_projection(h, np.nan, .5, 4) == c
    assert projections.base_projection(h, 50, .5, 0) == c


def test_base_projection_numpy_matches_numpy_mean():
    h = np.array([3.0, 7.0, 1.0, 9.0, 4.0])
    assert projections.base_projection(h, None, .85, 4) == .85 * h.mean() + .15 * h[-3:].mean()


def test_matchup_factor_is_clamped():
    assert projections.matchup_factor(10, 10) == 1.0
    assert projections.matchup_factor(12, 10) == 1 + .5 * (12 / 10 - 1)
    assert projections.matchup_factor(100, 10) == 1.25
    assert projections.matchup_factor(0, 10) == .8


def test_p_over_counts_quantiles_and_nudges():
    q = [i / 100 for i in range(101)]   # actual/projection spread evenly 0..1
    # line at half the projection: 50 of 101 quantiles are above .5
    assert projections.p_over(q, 0, 100, 50) == 50 / 101
    assert projections.p_over(q, .1, 100, 50) == 50 / 101 + .1
    assert projections.p_over(q, 0, 100, 1000) == .01
    assert projections.p_over(q, 5, 100, 50) == .99
    assert projections.p_over(q, 0, 0, 50) is None
    assert projections.p_over(q, 0, None, 50) is None
    assert projections.p_over(None, 0, 100, 50) is None


TD = {'w': [-1.0, .5, .3, .2, -.1], 'mu': [10, 4, .3, .1], 'sd': [5, 2, .5, .3]}


def test_td_chance_from_usage():
    x = [12.0, 3.0, 1.0, 0.0]
    z = TD['w'][0] + sum(TD['w'][i + 1] * (x[i] - TD['mu'][i]) / TD['sd'][i] for i in range(4))
    assert projections.td_chance(TD, (12.0, 3.0, 8), 'RB') == 1 / (1 + math.exp(-z))


def test_td_chance_needs_model_usage_and_skill_position():
    assert projections.td_chance(None, (12.0, 3.0, 8), 'RB') is None
    assert projections.td_chance(TD, None, 'RB') is None
    assert projections.td_chance(TD, (12.0, 3.0, 3), 'RB') is None   # fewer than 4 games
    assert projections.td_chance(TD, (2.0, 2.0, 8), 'RB') is None    # under 5 touches a game
    assert projections.td_chance(TD, (12.0, 3.0, 8), 'QB') is None


def _games():
    rows = []
    teams = ['A', 'B', 'C', 'D']
    strength = {'A': 7, 'B': 3, 'C': -2, 'D': -8}
    for i, h in enumerate(teams):
        for a in teams:
            if h == a: continue
            hs = 24 + strength[h] / 2 + 1.5; as_ = 24 + strength[a] / 2 - 1.5
            rows.append({'home_team': h, 'away_team': a, 'home_score': hs, 'away_score': as_})
    return pd.DataFrame(rows), set(teams)


def test_fit_nfl_ranks_teams_and_projects():
    g, teams = _games()
    R, hfa, off, deff, mu = team_model.fit_nfl(g, teams)
    assert sorted(R, key=lambda t: -R[t]) == ['A', 'B', 'C', 'D']
    assert hfa > 0
    m, t = team_model.project((R, hfa, off, deff, mu), 'A', 'D')
    assert m == R['A'] - R['D'] + hfa
    assert t == 2 * mu + off['A'] + off['D'] - deff['A'] - deff['D']


def test_fit_nfl_prior_shifts_ratings():
    g, teams = _games()
    R0 = team_model.fit_nfl(g, teams)[0]
    R1 = team_model.fit_nfl(g, teams, prior={t: 1.0 for t in teams})[0]
    assert all(R1[t] != R0[t] for t in teams)


def test_fit_ridge_margins():
    games = [{'homeTeam': 'X', 'awayTeam': 'Y', 'homePoints': 30, 'awayPoints': 10, 'neutralSite': False},
             {'homeTeam': 'Y', 'awayTeam': 'Z', 'homePoints': 21, 'awayPoints': 20, 'neutralSite': True},
             {'homeTeam': 'Z', 'awayTeam': 'X', 'homePoints': 7, 'awayPoints': 28, 'neutralSite': False}]
    R, hfa = team_model.fit_ridge_margins(games, {'W': 2.0}, 5.0)
    assert set(R) == {'W', 'X', 'Y', 'Z'}
    assert R['X'] > R['Y'] > R['Z']
    assert math.isclose(R['W'], 2.0, abs_tol=1e-9)   # a team with no games keeps its prior


def test_model_fit_and_lab_use_the_same_recipe(tmp_path, monkeypatch):
    import json, os, sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    import model_fit
    from analyst import lab
    h, prior = np.array([3.0, 7.0, 1.0, 9.0, 4.0]), 6.5
    c = model_fit.W * h.mean() + (1 - model_fit.W) * h[-3:].mean()
    expected = (len(h) * c + model_fit.K0 * prior) / (len(h) + model_fit.K0)
    assert projections.base_projection(h, prior, model_fit.W, model_fit.K0) == expected
    json.dump({'w': model_fit.W, 'k0': model_fit.K0}, open(tmp_path / 'model.json', 'w'))
    monkeypatch.chdir(tmp_path)
    assert lab.current_recipe(h, prior) == expected
    assert lab.current_recipe(h, np.nan) == c
