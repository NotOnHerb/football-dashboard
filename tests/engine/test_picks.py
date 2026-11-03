"""Game and prop sides, the official pick list, and parlays."""
import datetime
import math

from engine import odds, parlays, picks
from engine.rules import RULES

NOW = datetime.datetime(2026, 11, 2, 12, tzinfo=datetime.timezone.utc)
LATER = '2026-11-08T18:00:00Z'
EARLIER = '2026-11-01T18:00:00Z'


def game(gid='E1', t=LATER, b=None, fair=None, mod=None, wk=9):
    return {'id': gid, 'wk': wk, 'a': 'AW', 'h': 'HM', 't': t,
            'b': b if b is not None else {'X': {'s': [-3, 110, 3, -125]}, 'Y': {'s': [-3, -105, 3, -115]}},
            'fair': fair if fair is not None else {'ref': {'s': 'Pinnacle'}, 's': [-3, .5]},
            'mod': mod if mod is not None else {'m': 6.0, 't': 44.0, 'wp': .67}}


# ---- game sides

def test_half_point_crossing_three_adds_3pct():
    # half a point better across 3 is worth the usual 2% plus 3% more; the same half point elsewhere is just 2%
    cross = picks.game_ev({'pt': 3.5, 'pr': 100}, {'pt': 2.5, 'p': .5, 'sp': 1})
    plain = picks.game_ev({'pt': 4.5, 'pr': 100}, {'pt': 3.5, 'p': .5, 'sp': 1})
    assert math.isclose(cross, (.5 + .04 + .03) * 2 - 1)
    assert math.isclose(cross - plain, .03 * odds.decimal(100))


def test_half_point_crossing_seven_adds_3pct():
    cross = picks.game_ev({'pt': 7.5, 'pr': 100}, {'pt': 6.5, 'p': .5, 'sp': 1})
    assert math.isclose(cross, (.5 + .04 + .03) * 2 - 1)


def test_half_point_crossing_three_the_wrong_way_takes_3pct():
    worse = picks.game_ev({'pt': -3.5, 'pr': 100}, {'pt': -2.5, 'p': .5, 'sp': 1})
    assert math.isclose(worse, (.5 - .04 - .03) * 2 - 1)


def test_totals_get_no_key_number_bonus():
    ev = picks.game_ev({'pt': 43.5, 'pr': 100}, {'pt': 44.5, 'p': .5, 'ov': True})
    assert math.isclose(ev, (.5 + .03) * 2 - 1)


def test_game_ev_ignores_lines_more_than_two_points_off():
    assert picks.game_ev({'pt': 6, 'pr': 100}, {'pt': 3, 'p': .5, 'sp': 1}) is None
    assert picks.game_ev(None, {'pt': 3, 'p': .5}) is None


def test_best_game_quote_prefers_better_line_then_price():
    g = game(b={'X': {'s': [-3, 110, 3, -125]}, 'Y': {'s': [-2.5, -120, 2.5, 100]}, 'Z': {'s': [-3, 120, 3, -140]}})
    assert picks.best_game_quote(g, 'hs') == {'pt': -2.5, 'pr': -120, 'bk': 'Y'}
    assert picks.best_game_quote(g, 'as') == {'pt': 3, 'pr': -125, 'bk': 'X'}
    assert picks.best_game_quote(g, 'hs', books={'X', 'Z'}) == {'pt': -3, 'pr': 120, 'bk': 'Z'}
    assert picks.best_game_quote(g, 'hs', books={'nobody'}) is None
    assert picks.best_game_quote(g, 'ov') is None


def test_stale_price_is_not_a_pick():
    g = game(b={'X': {'s': [-3, 150, 3, -125]}}, mod={'m': 0.0, 't': 44.0, 'wp': .5})
    x = picks.game_side(g, 'hs')
    assert x['v'] > RULES['stale']
    assert x['vs'] == 0 and x['flag'] == 'stale'


def test_moneyline_outside_range_is_not_a_value_pick():
    g = game(b={'X': {'m': [-400, 320]}}, fair={'ref': {}, 'm': .82})
    x = picks.game_side(g, 'mh')
    assert x['vs'] == 0 and x['flag'] == 'range'


def test_game_side_value_and_model_scores():
    x = picks.game_side(game(), 'hs')
    assert x['q'] == {'pt': -3, 'pr': 110, 'bk': 'X'}
    assert math.isclose(x['v'], .5 * 2.1 - 1)
    assert x['vs'] == 2                      # 5% edge
    assert x['me'] == 3.0 and x['ms'] == 1   # model 6, line 3: 3 points of model edge
    assert x['s'] == 3


def test_game_picks_ids_and_started_games():
    pk = picks.game_picks([game('E1'), game('E0', t=EARLIER)], NOW)
    assert [x['id'] for x in pk] == ['g|E1|spread|hs']
    x = pk[0]
    assert (x['pt'], x['pr'], x['bk'], x['s'], x['wk']) == (-3, 110, 'X', 3, 9)
    assert x['pc'] == round((x['v'] + 1) / odds.decimal(110), 4)


def test_game_picks_one_book():
    pk = picks.game_picks([game('E1')], NOW, books={'Y'})
    # at Y the home spread is -105: no value edge, and the model edge alone scores 1, under the pick bar
    assert pk == []


# ---- props

def td_prop(gid='P1', eid='E1', pj=.5, price=150, ko=LATER, n_games=5):
    return {'eid': eid, 'ko': ko, 'n': 'Some Back', 't': 'HM', 'pos': 'RB', 'gid': gid, 'opp': 'AW', 'mk': 'Anytime TD',
            'b': {'X': [None, price, None, None]}, 'fair': [None, .4], 'v': [[w, 'AW', 1] for w in range(1, n_games + 1)],
            'avg': 1.0, 'l3': 1.0, 'pj': pj, 'md': None, 'fac': 1.0, 'use': [15.0, 2.0]}


def yds_prop(gid='P2', eid='E1', fair=(60.5, .5), b=None, pj=70.0):
    return {'eid': eid, 'ko': LATER, 'n': 'Some Receiver', 't': 'HM', 'pos': 'WR', 'gid': gid, 'opp': 'AW', 'mk': 'Rec yds',
            'b': b if b is not None else {'X': [60.5, 150, 60.5, -190]}, 'fair': list(fair) if fair else None,
            'v': [[w, 'AW', 70] for w in range(1, 6)], 'avg': 70.0, 'l3': 70.0, 'pj': pj, 'md': None, 'fac': 1.0, 'use': None}


def test_best_prop_quote_sides():
    p = yds_prop(b={'X': [60.5, -110, 60.5, -110], 'Y': [59.5, -120, 59.5, 100], 'Z': [60.5, -105, 60.5, -115]})
    assert picks.best_prop_quote(p, 'o') == {'pt': 59.5, 'pr': -120, 'bk': 'Y'}
    assert picks.best_prop_quote(p, 'u') == {'pt': 60.5, 'pr': -110, 'bk': 'X'}
    assert picks.best_prop_quote(p, 'o', books={'X', 'Z'}) == {'pt': 60.5, 'pr': -105, 'bk': 'Z'}


def test_prop_side_anytime_td():
    x = picks.prop_side(td_prop(), None, 1.0)
    assert x['sd'] == 'y' and x['P'] == .5
    assert x['ls'] == picks.lean_tier(.5 - odds.implied(150)) and x['s'] == min(x['ls'], 2)


def test_stale_prop_price_is_not_a_value_pick():
    model = {'q': {'Rec yds': [i / 50 for i in range(101)]}, 'cal': {}}
    x = picks.prop_side(yds_prop(), model, .5)
    assert x['sd'] == 'o'
    assert x['v'] > RULES['stale'] and x['vs'] == 0


def test_prop_picks_skip_hurt_started_and_label_week():
    props = [td_prop('P1'), td_prop('P3', ko=EARLIER), td_prop('P4')]
    pk = picks.prop_picks(props, None, 1.0, NOW, {'P4': 'Out', 'P1': 'Questionable'}, weeks={'E1': 9})
    assert [x['id'] for x in pk] == ['p|E1|P1|Anytime TD|y']
    assert pk[0]['wk'] == 9 and pk[0]['pc'] == .5


# ---- parlays

def test_parlay_of_the_week_at_one_book():
    gs = [game('E1'), game('E2')]
    pk = picks.game_picks(gs, NOW)
    px = parlays.build_parlays(pk, [], gs, {'X': 2, 'Y': 2}, None, 1.0, NOW, {})
    assert [x['id'] for x in px] == ['x|week|wk9']
    x = px[0]
    assert x['bk'] == 'X' and x['dec'] == round(2.1 * 2.1, 3) and x['pr'] == odds.american_from_decimal(round(2.1 * 2.1, 3))
    assert [l['id'] for l in x['legs']] == ['g|E1|spread|hs', 'g|E2|spread|hs']
    assert x['pc'] == round(.5 * .5, 4)


def test_no_parlays_without_picks():
    assert parlays.build_parlays([], [], [], {}, None, 1.0, NOW, {}) == []
