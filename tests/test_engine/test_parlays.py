"""Parlays from hand-made boards: the anytime TD parlay and the parlay of the game (the golden fixture has neither)."""
import datetime, os, sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))   # repo root
from engine import odds, parlays  # noqa: E402

NOW = datetime.datetime(2026, 11, 2, 12, tzinfo=datetime.timezone.utc)
LATER = '2026-11-08T18:00:00Z'
EARLIER = '2026-11-01T18:00:00Z'
GAMES = [{'id': 'E1', 'wk': 9, 'a': 'AW', 'h': 'HM', 't': LATER, 'b': {}, 'fair': {'ref': {}}, 'mod': None},
         {'id': 'E2', 'wk': 9, 'a': 'A2', 'h': 'H2', 't': LATER, 'b': {}, 'fair': {'ref': {}}, 'mod': None}]
BOOKS = {'X': 2, 'Y': 2}
MODEL = {'q': {'Pass yds': [i / 50 for i in range(101)], 'Rec yds': [i / 50 for i in range(101)]}, 'cal': {}}


def prop(gid, eid, mk, pos, b, fair, vals, pj, ko=LATER, team='HM'):
    return {'eid': eid, 'ko': ko, 'n': 'Player ' + gid, 't': team, 'pos': pos, 'gid': gid, 'opp': 'AW', 'mk': mk, 'b': b,
            'fair': fair, 'v': [[w + 1, 'AW', v] for w, v in enumerate(vals)], 'avg': 0, 'l3': 0, 'pj': pj, 'md': None, 'fac': 1.0, 'use': None}


def td(gid, eid, pj, prices, **kw):
    return prop(gid, eid, 'Anytime TD', 'RB', {bk: [None, pr, None, None] for bk, pr in prices.items()}, [None, .35], [1, 0, 1, 0, 1], pj, **kw)


def test_anytime_td_parlay_takes_likeliest_scorers_from_different_games_at_one_book():
    props = [td('P1', 'E1', .45, {'X': 150, 'Y': 140}),
             td('P2', 'E2', .40, {'X': 170, 'Y': 160}),
             td('P3', 'E2', .60, {'X': 200, 'Y': 200}),                  # out: skipped
             td('P4', 'E1', .70, {'X': 120, 'Y': 120}, ko=EARLIER)]      # already started: skipped
    px = parlays.build_parlays([], props, GAMES, BOOKS, None, 1.0, NOW, {'P3': 'Out'})
    assert [x['id'] for x in px] == ['x|td|wk9']
    x = px[0]
    assert [l['id'] for l in x['legs']] == ['p|E1|P1|Anytime TD|y', 'p|E2|P2|Anytime TD|y']
    assert x['bk'] == 'X' and [l['pr'] for l in x['legs']] == [150, 170]
    assert x['dec'] == round(odds.decimal(150) * odds.decimal(170), 3) and x['pr'] == odds.american_from_decimal(x['dec'])
    assert x['pc'] == round(.45 * .40, 4) and x['joint'] is None
    assert all('_p' not in l and 'e' not in l for l in x['legs'])


def test_parlay_of_the_game_pairs_a_qb_and_his_receiver_who_hit_together():
    qb = prop('Q1', 'E1', 'Pass yds', 'QB', {'X': [230.5, 100, 230.5, -120], 'Y': [230.5, -105, 230.5, -115]}, [230.5, .6],
              [250, 240, 200, 260, 235], 245.0)
    wr = prop('W1', 'E1', 'Rec yds', 'WR', {'X': [60.5, 100, 60.5, -120], 'Y': [60.5, -110, 60.5, -110]}, [60.5, .6],
              [70, 65, 40, 80, 62], 66.0)
    # blend 0: our chance is the market's fair 60% on each leg, 10 points over the +100 price
    px = parlays.build_parlays([], [qb, wr], GAMES, BOOKS, MODEL, 0.0, NOW, {})
    assert [x['id'] for x in px] == ['x|game|wk9']
    x = px[0]
    assert [l['id'] for l in x['legs']] == ['p|E1|Q1|Pass yds|o', 'p|E1|W1|Rec yds|o']
    assert x['bk'] == 'X' and x['dec'] == 4.0 and x['pr'] == 300
    assert x['joint'] == .8                              # both cleared their lines in 4 of 5 games
    assert x['pc'] == round(min(.8, .36 * 1.25), 4)      # teammates: up to 25% over the independent .36, capped at the joint rate
    assert 'in 4 of 5 games' in x['note']


def test_no_game_parlay_when_they_rarely_hit_together():
    qb = prop('Q1', 'E1', 'Pass yds', 'QB', {'X': [230.5, 100, 230.5, -120]}, [230.5, .6], [250, 200, 250, 200, 250], 245.0)
    wr = prop('W1', 'E1', 'Rec yds', 'WR', {'X': [60.5, 100, 60.5, -120]}, [60.5, .6], [40, 70, 40, 70, 40], 66.0)
    assert parlays.build_parlays([], [qb, wr], GAMES, BOOKS, MODEL, 0.0, NOW, {}) == []


def test_build_parlays_needs_the_books_to_price_at():
    with pytest.raises(ValueError):
        parlays.build_parlays([], [], GAMES, None, None, 1.0, NOW, {})
