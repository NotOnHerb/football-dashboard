"""Scoring the prediction ledger: proper scores, reliability, and the model's fitted weight against the market."""
import math, os, sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))   # repo root
from analyst import eval_ledger as ev  # noqa: E402


def logit(p): return math.log(p / (1 - p))


def sigmoid(z): return 1 / (1 + math.exp(-z))


def simulate(weight=.15, games=400, per_game=40, seed=7, game_sd=.3):
    """Graded ledger rows where the truth is the market's log-odds plus WEIGHT times the model-minus-market gap, plus a
    shared shock per game (so rows in a game are related)."""
    rng = np.random.default_rng(seed); rows = []
    for g in range(games):
        shock = rng.normal(0, game_sd)
        for _ in range(per_game):
            m = rng.normal(0, .6); d = rng.normal(0, .4)
            pf, pm = sigmoid(m), sigmoid(m + d)
            y = int(rng.random() < sigmoid(m + weight * d + shock))
            rows.append({'eid': 'G%d' % g, 'pf': pf, 'pm': pm, 'P': .5 * pm + .5 * pf, 'y': y})
    return rows


def test_recovers_a_known_weight_inside_its_interval():
    w = ev.weight(simulate(), boot=200, seed=1)
    assert w['lo'] < .15 < w['hi']
    assert abs(w['c'] - .15) < .1
    assert w['hi'] < .5   # and rules out the dashboard's 0.5
    assert w['n'] == 16000 and w['games'] == 400


def test_recovers_zero_weight_when_the_market_knows_everything():
    w = ev.weight(simulate(weight=0, seed=3), boot=200, seed=2)
    assert w['lo'] < 0 < w['hi']


def test_interval_resamples_whole_games():
    # every row repeated three times within its game: same games, same fit, so a game bootstrap gives the same interval
    # (a row bootstrap would shrink it by about the square root of 3)
    base = simulate(games=60, per_game=20, seed=5)
    tripled = [r for r in base for _ in range(3)]
    a, b = ev.weight(base, boot=100, seed=4), ev.weight(tripled, boot=100, seed=4)
    assert math.isclose(a['c'], b['c'], abs_tol=1e-6)
    assert math.isclose(a['lo'], b['lo'], abs_tol=1e-6) and math.isclose(a['hi'], b['hi'], abs_tol=1e-6)


def test_outcome_from_y_or_result_code():
    assert ev.outcome({'y': 1}) == 1 and ev.outcome({'y': 0}) == 0
    assert ev.outcome({'res': 'W'}) == 1 and ev.outcome({'res': 'L'}) == 0
    assert ev.outcome({'res': 'P'}) is None and ev.outcome({'res': 'V'}) is None and ev.outcome({'res': None}) is None


def test_usable_rows_need_an_outcome_and_both_chances():
    rows = [{'eid': 'A', 'pm': .6, 'pf': .5, 'P': .55, 'y': 1}, {'eid': 'A', 'pm': None, 'pf': .5, 'P': None, 'y': 1},
            {'eid': 'A', 'pm': .6, 'pf': .5, 'P': .55, 'res': 'P'}, {'eid': 'A', 'pm': .6, 'pf': None, 'P': None, 'res': 'W'}]
    assert len(ev.usable(rows)) == 1


def test_paired_scores_on_a_small_example():
    rows = [{'eid': 'A', 'pm': .8, 'pf': .6, 'P': .7, 'y': 1}, {'eid': 'B', 'pm': .3, 'pf': .5, 'P': .4, 'y': 0}]
    s = ev.scores(rows, boot=50, seed=0, min_games=1)
    assert s['n'] == 2 and s['games'] == 2
    assert math.isclose(s['brier']['market'], ((.6 - 1) ** 2 + .5 ** 2) / 2)
    assert math.isclose(s['brier']['blend'], ((.7 - 1) ** 2 + .4 ** 2) / 2)
    assert math.isclose(s['brier']['model'], ((.8 - 1) ** 2 + .3 ** 2) / 2)
    assert math.isclose(s['log_loss']['market'], -(math.log(.6) + math.log(.5)) / 2)
    assert math.isclose(s['brier']['blend_minus_market']['mean'], s['brier']['blend'] - s['brier']['market'])
    assert math.isclose(s['log_loss']['model_minus_market']['mean'], s['log_loss']['model'] - s['log_loss']['market'])
    d = s['brier']['blend_minus_market']; assert d['lo'] <= d['mean'] <= d['hi']


def test_reliability_table():
    rows = [{'eid': 'A', 'pf': .05, 'pm': .1, 'P': .12, 'y': 0}, {'eid': 'A', 'pf': .5, 'pm': .5, 'P': .15, 'y': 1},
            {'eid': 'B', 'pf': .5, 'pm': .5, 'P': .55, 'y': 1}, {'eid': 'B', 'pf': .5, 'pm': .5, 'P': .58, 'y': 0},
            {'eid': 'B', 'pf': .99, 'pm': .5, 'P': 1.0, 'y': 1}]
    t = ev.reliability(rows, 'P', bins=10)
    assert [b['bin'] for b in t] == ['0.10-0.20', '0.50-0.60', '0.90-1.00']   # empty buckets left out; 1.0 is in the top one
    assert [b['n'] for b in t] == [2, 2, 1]
    assert math.isclose(t[0]['said'], .135) and t[0]['went'] == .5
    assert math.isclose(t[1]['said'], .565) and t[1]['went'] == .5


def test_report_on_simulated_ledger():
    r = ev.report(simulate(games=80, per_game=20, seed=9), boot=50, seed=0)
    assert set(r) == {'scores', 'reliability', 'weight'}
    assert set(r['reliability']) == {'blend', 'model', 'market'}
    assert r['scores']['n'] == r['weight']['n'] == 1600


def test_too_few_games_gives_no_interval():
    rows = simulate(games=10, per_game=20, seed=11)
    w = ev.weight(rows, boot=50); s = ev.scores(rows, boot=50)
    assert w['c'] is not None and w['lo'] is None and w['hi'] is None and w['games'] == 10
    assert s['brier']['blend_minus_market']['lo'] is None and s['brier']['blend_minus_market']['mean'] is not None


def test_unfittable_rows_do_not_crash():
    rows = [dict(r, pm=r['pf']) for r in simulate(games=30, per_game=10, seed=12)]   # no gap: the weight can't be fit
    w = ev.weight(rows, boot=20)
    assert w['c'] is None and w['lo'] is None and w['failed'] == 20
    assert ev.report(rows, boot=20)['weight']['c'] is None


def test_scores_interval_brackets_the_mean_on_a_season():
    d = ev.scores(simulate(games=60, per_game=20, seed=13), boot=200)['log_loss']['model_minus_market']
    assert d['lo'] < d['mean'] < d['hi']


def test_latest_before_kickoff_keeps_one_row_per_line():
    r = {'id': 'p|E1|P1|Rec yds|60.5', 'eid': 'E1', 't': '2026-11-08T18:00:00Z', 'pm': .6, 'pf': .5, 'P': .55, 'y': 1}
    rows = [dict(r, snapshot_ts='2026-11-06T10:52:00+00:00', pf=.4), dict(r, snapshot_ts='2026-11-08T10:52:00+00:00'),
            dict(r, snapshot_ts='2026-11-08T19:00:00+00:00', pf=.9),   # after kickoff: never a forecast
            dict(r, id='p|E1|P1|Rec yds|61.5', snapshot_ts='2026-11-06T10:52:00+00:00')]
    kept = ev.latest_before_kickoff(rows)
    assert [(x['id'], x['pf']) for x in kept] == [('p|E1|P1|Rec yds|60.5', .5), ('p|E1|P1|Rec yds|61.5', .5)]
