"""Game and prop sides, the official pick list, and parlays."""
import datetime, math, os, sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))   # repo root
from engine import odds, parlays, picks  # noqa: E402
from engine.rules import RULES  # noqa: E402

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


# ---- per-book picks (data.json ODD.PKB)

GOLDEN = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'golden')
SHOWN_GAMES, SHOWN_PROPS = 6, 9   # picks the Picks page lists beyond the pick of the week before "Show all"


def am(x): return '–' if x is None else ('+' if x > 0 else '') + str(x)


def card_text(x):
    """The title and price line of a pick's card on the Picks page (minus the kickoff time), from the pick."""
    if x['k'] == 'g':
        team = x['h'] if x['sd'] in ('hs', 'mh') else x['a']
        title = ('Over %s' % x['pt']) if x['sd'] == 'ov' else ('Under %s' % x['pt']) if x['sd'] == 'un' else \
            '%s to win' % team if x['mk'] == 'ml' else '%s %s' % (team, 'PK' if x['pt'] == 0 else ('+' if x['pt'] > 0 else '') + str(x['pt']))
        return '%s %s %s %s · %s at %s' % (['', 'I', 'II', 'III'][min(3, max(1, x['s']))], title, am(x['pr']), x['bk'], x['a'], x['h'])
    title = 'Anytime TD' if x['sd'] == 'y' else '%s %s %s' % ('Over' if x['sd'] == 'o' else 'Under', x['pt'], x['mk'])
    return '%s %s %s %s %s · %s vs %s' % (['', 'I', 'II', 'III'][min(3, max(1, x['s']))], x['n'], title, am(x['pr']), x['bk'], x['tm'], x['opp'])


def test_pkb_matches_page():
    """Every sportsbook's Picks view on the page shows the picks in ODD.PKB for that book: the pick of the week, then
    up to 6 game picks and 9 prop picks, each with the same player or team, market, side, line, book and price."""
    import gzip, json
    data = json.load(gzip.open(os.path.join(GOLDEN, 'expected_data.json.gz'), 'rt', encoding='utf-8'))
    page = json.load(gzip.open(os.path.join(GOLDEN, 'expected_page.json.gz'), 'rt', encoding='utf-8'))
    O = data['ODD']
    assert list(O['PKB']) == O['books']
    checked = 0
    for view, text in page.items():
        if not view.startswith('betting/nfl/picks/') or view.endswith('player-card'): continue
        name = view.split('betting/nfl/picks/', 1)[1]
        pk = O['PK'] if name == 'best-available' else O['PKB'][name]
        top, rest = (pk[0], pk[1:]) if pk else (None, [])
        shown = ([top] if top else []) + [x for x in rest if x['k'] == 'g'][:SHOWN_GAMES] + [x for x in rest if x['k'] == 'p'][:SHOWN_PROPS]
        assert text.count('What you need:') == len(shown), view
        assert text.count('PICK OF THE WEEK') == (1 if top else 0), view
        if not shown: assert 'No picks clear the bar right now' in text, view
        at = text.index('PICK OF THE WEEK') if top else 0
        for x in shown:
            label = card_text(x)
            i = text.find(label, at)
            assert i >= 0, '%s: %r not shown after position %d' % (view, label, at)
            at = i + len(label)
        checked += len(shown)
    assert checked   # the golden clock leaves at least one pick to compare


def test_picks_by_book_looks_at_one_book_at_a_time():
    gs, ps = [game('E1')], [td_prop('P1', price=150), yds_prop('P2')]
    by = picks.picks_by_book(['X', 'Y'], gs, ps, None, 1.0, NOW, {}, weeks={'E1': 9})
    assert list(by) == ['X', 'Y']
    assert [x['id'] for x in by['X']] == [x['id'] for x in picks.official_picks(gs, ps, None, 1.0, NOW, {}, {'X'}, {'E1': 9})]
    assert {x['bk'] for x in by['X']} == {'X'} and 'g|E1|spread|hs' in [x['id'] for x in by['X']]
    assert by['Y'] == []


def test_official_picks_sorts_games_and_props_together():
    gs, ps = [game('E1')], [td_prop('P1')]
    pk = picks.official_picks(gs, ps, None, 1.0, NOW, {})
    assert len(pk) == 2 and [x['srt'] for x in pk] == sorted((x['srt'] for x in pk), reverse=True)
    assert pk == picks.official_picks(gs, ps, None, 1.0, NOW, {}, None)
