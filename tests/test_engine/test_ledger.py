"""The prediction ledger: one row per priced line, the same chances the picks use, pick flags that match ODD.PK."""
import datetime, gzip, json, math, os, sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))   # repo root
from engine import ledger, odds, picks  # noqa: E402

NOW = datetime.datetime(2026, 11, 2, 12, tzinfo=datetime.timezone.utc)
LATER = '2026-11-08T18:00:00Z'
TS = '2026-11-02T10:52'
MODEL = {'q': {'Rec yds': [i / 50 for i in range(101)]}, 'cal': {'Rec yds': .01}, 'fit_at': '2026-10-30T00:03:17+00:00'}
GOLDEN = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'golden', 'expected_data.json.gz')


def game(b=None, fair=None, mod=None):
    return {'id': 'E1', 'wk': 9, 'a': 'AW', 'h': 'HM', 't': LATER,
            'b': b if b is not None else {'X': {'s': [-3, 110, 3, -125], 'o': [44.5, -110, -110], 'm': [-150, 130]},
                                          'Pinnacle': {'s': [-3.5, 105, 3.5, -115], 'm': [-145, 125]}},
            'fair': fair if fair is not None else {'ref': {'s': 'Pinnacle', 'o': 'market', 'm': 'Pinnacle'},
                                                   's': [-3.5, .48], 'o': [44.5, .5], 'm': .58},
            'mod': mod if mod is not None else {'m': 6.0, 't': 44.0, 'wp': .67}}


def yds_prop(b=None, fair=(60.5, .5), pj=70.0, gid='P2'):
    return {'eid': 'E1', 'ko': LATER, 'n': 'Some Receiver', 't': 'HM', 'pos': 'WR', 'gid': gid, 'opp': 'AW', 'mk': 'Rec yds',
            'b': b if b is not None else {'X': [60.5, -110, 60.5, -110], 'Y': [59.5, -120, 59.5, 100],
                                          'Z': [60.5, -105, 60.5, -115], 'Pinnacle': [60.5, -108, 60.5, -112]},
            'fair': list(fair) if fair else None, 'v': [[w, 'AW', 70] for w in range(1, 6)], 'avg': 70.0, 'l3': 70.0,
            'pj': pj, 'md': None, 'fac': 1.0, 'use': None}


def td_prop(gid='P1', pj=.5):
    return {'eid': 'E1', 'ko': LATER, 'n': 'Some Back', 't': 'HM', 'pos': 'RB', 'gid': gid, 'opp': 'AW', 'mk': 'Anytime TD',
            'b': {'X': [None, 150, None, None], 'Y': [None, 140, None, None]}, 'fair': [None, .4],
            'v': [[w, 'AW', 1] for w in range(1, 6)], 'avg': 1.0, 'l3': 1.0, 'pj': pj, 'md': None, 'fac': 1.0, 'use': [15.0, 2.0]}


def rows_for(games, props, model=MODEL, blend=.5):
    pk = picks.official_picks(games, props, model, blend, NOW, {})
    return ledger.ledger_rows(games, props, model, blend, pk, TS), pk


def by_id(rows): return {r['id']: r for r in rows}


# ---- one row per line, never both sides

def test_one_row_per_prop_line():
    rows, _ = rows_for([], [yds_prop()])
    assert [(r['mk'], r['pt']) for r in rows] == [('Rec yds', 59.5), ('Rec yds', 60.5)]
    assert [r['id'] for r in rows] == ['p|E1|P2|Rec yds|59.5', 'p|E1|P2|Rec yds|60.5']


def test_one_row_per_game_line():
    rows, _ = rows_for([game()], [])
    assert [r['id'] for r in rows] == ['g|E1|spread|-3.5', 'g|E1|spread|-3', 'g|E1|total|44.5', 'g|E1|ml|']


def test_anytime_td_is_one_yes_row():
    rows, _ = rows_for([], [td_prop()])
    assert len(rows) == 1 and rows[0]['id'] == 'p|E1|P1|Anytime TD|' and rows[0]['pt'] is None
    assert rows[0]['u'] is None and rows[0]['o'] == {'pr': 150, 'bk': 'X'}


# ---- the three forecasts

def test_prop_row_forecasts_at_the_consensus_line():
    r = by_id(rows_for([], [yds_prop()])[0])['p|E1|P2|Rec yds|60.5']
    pm = picks.model_p_over(MODEL, 'Rec yds', 70.0, 60.5)
    assert math.isclose(r['pm'], round(pm, 4))
    assert (r['pf'], r['pf_src'], r['pf_n']) == (.5, 'median', 3)   # X, Z and Pinnacle quote both sides of 60.5
    assert math.isclose(r['pin'], round(odds.no_vig_shin(-108, -112), 4))
    assert math.isclose(r['P'], round(.5 * pm + .5 * .5, 4))
    assert r['o'] == {'pr': -105, 'bk': 'Z'} and r['u'] == {'pr': -110, 'bk': 'X'}


def test_prop_row_off_the_consensus_line_uses_one_book():
    r = by_id(rows_for([], [yds_prop()])[0])['p|E1|P2|Rec yds|59.5']
    assert r['pf_src'] == 'book' and r['pf_n'] == 1
    assert math.isclose(r['pf'], round(odds.no_vig_proportional(-120, 100), 4))
    assert r['pin'] is None   # Pinnacle doesn't post 59.5
    assert r['o'] == {'pr': -120, 'bk': 'Y'} and r['u'] == {'pr': 100, 'bk': 'Y'}


def test_prop_without_market_or_model_has_no_blend():
    r = rows_for([], [yds_prop(b={'X': [60.5, -110, None, None]}, fair=None)])[0][0]
    assert r['pf'] is None and r['pf_src'] is None and r['pf_n'] == 0 and r['P'] is None
    r = rows_for([], [yds_prop()], model=None)[0][1]
    assert r['pm'] is None and r['P'] is None and r['pf'] == .5 and r['model_fit_at'] is None


def test_anytime_td_forecasts():
    r = rows_for([], [td_prop()])[0][0]
    assert (r['pm'], r['pf'], r['pf_src'], r['pf_n'], r['pin']) == (.5, .4, 'td', 2, None)
    assert math.isclose(r['P'], .45)


def test_game_rows_carry_fair_and_pinnacle_chances():
    rows = by_id(rows_for([game()], [])[0])
    s35, s3, tot, ml = (rows[k] for k in ('g|E1|spread|-3.5', 'g|E1|spread|-3', 'g|E1|total|44.5', 'g|E1|ml|'))
    assert (s35['pf'], s35['pf_src'], s35['pf_n']) == (.48, 'Pinnacle', 1)
    assert math.isclose(s35['pin'], round(odds.no_vig_shin(105, -115), 4))
    assert s3['pf_src'] == 'Pinnacle+adj' and math.isclose(s3['pf'], .48 + .02)   # half a point, onto 3 but not across it
    assert s3['pin'] is None and s3['o'] == {'pr': 110, 'bk': 'X'} and s3['u'] == {'pr': -125, 'bk': 'X'}
    assert (tot['pf'], tot['pf_src'], tot['pf_n'], tot['pin']) == (.5, 'market', 1, None)
    assert (ml['pm'], ml['pf'], ml['pf_src']) == (.67, .58, 'Pinnacle')
    assert ml['o'] == {'pr': -145, 'bk': 'Pinnacle'} and ml['u'] == {'pr': 130, 'bk': 'X'}
    assert all(r['P'] is None and r['ls'] is None for r in rows.values())   # game lines aren't blended or tiered
    assert s35['pm'] is None and s35['mod'] == {'m': 6.0, 't': 44.0, 'wp': .67}


def test_row_carries_inputs_and_stamps():
    r = rows_for([game()], [yds_prop()])[0]
    p = [x for x in r if x['k'] == 'p'][0]
    assert p['pj'] == 70.0 and p['wk'] == 9 and p['t'] == LATER and (p['n'], p['gid'], p['tm'], p['opp']) == ('Some Receiver', 'P2', 'HM', 'AW')
    assert {x['model_fit_at'] for x in r} == {MODEL['fit_at']} and {x['snapshot_ts'] for x in r} == {TS}


# ---- agreement with the picks engine

def test_scored_row_matches_prop_side():
    p = yds_prop(); x = picks.prop_side(p, MODEL, .5)
    rows = rows_for([], [p])[0]
    scored = [r for r in rows if r['sd']]
    assert len(scored) == 1 and scored[0]['pt'] == x['q']['pt']
    r = scored[0]
    assert (r['sd'], r['ls'], r['vs'], r['s']) == (x['sd'], x['ls'], x['vs'], x['s'])
    assert math.isclose(r['P'] if x['sd'] == 'o' else 1 - r['P'], x['P'], abs_tol=1e-4)
    assert all(r['ls'] is None and r['s'] is None for r in rows if not r['sd'])


def test_pick_flags_agree_with_official_picks():
    gs, ps = [game()], [yds_prop(), td_prop(), td_prop('P3', pj=.7)]
    rows, pk = rows_for(gs, ps)
    assert pk   # the fixture has picks to compare
    flagged = [r for r in rows if r['pick']]
    assert len(flagged) == len(pk)
    for x in pk:
        r = [r for r in flagged if r['eid'] == x['eid'] and r['mk'] == x['mk'] and r['sd'] == x['sd'] and r.get('gid') == x.get('gid')]
        assert len(r) == 1
        assert r[0]['o' if x['sd'] in ('o', 'y', 'hs', 'ov', 'mh') else 'u']['pr'] == x['pr']


def test_picks_from_elsewhere_are_not_flagged():
    rows = ledger.ledger_rows([game()], [td_prop()], MODEL, .5, [], TS)
    assert not any(r['pick'] for r in rows)


def test_game_scored_side_matches_game_picks():
    g = game()
    rows, pk = rows_for([g], [])
    for x in pk:
        r = [r for r in rows if r['pick'] and r['mk'] == x['mk']][0]
        home_side = x['sd'] in ('hs', 'ov', 'mh')
        assert math.isclose(r['pf'] if home_side else 1 - r['pf'], x['pc'], abs_tol=1e-4)
        assert r['s'] == x['s'] and r['vs'] == x['vs']


# ---- a real slate (the golden build)

def golden():
    O = json.load(gzip.open(GOLDEN, 'rt', encoding='utf-8'))['ODD']
    return O, {'q': O['MQ'], 'cal': O['MC'], 'fit_at': 'FIT'}


def test_golden_slate_rows_are_unique_and_match_prop_side():
    O, model = golden()
    rows = ledger.ledger_rows(O['G'], O['P'], model, O['MB'], O['PK'], O['at'])
    ids = [r['id'] for r in rows]
    assert len(ids) == len(set(ids))   # no row written twice
    rid = by_id(rows); checked = 0
    for p in O['P']:
        x = picks.prop_side(p, model, O['MB'])
        if not x: continue
        r = rid['p|%s|%s|%s|%s' % (p['eid'], p['gid'], p['mk'], '' if x['q']['pt'] is None or x['sd'] == 'y' else x['q']['pt'])]
        assert r['sd'] == x['sd'] and r['s'] == x['s']
        if x['P'] is not None:
            assert math.isclose(r['P'] if x['sd'] in ('o', 'y') else 1 - r['P'], x['P'], abs_tol=1e-4); checked += 1
    assert checked
    assert sum(r['pick'] for r in rows) == len(O['PK'])


def test_ledger_rows_are_json_and_deterministic():
    O, model = golden()
    a = ledger.ledger_rows(O['G'], O['P'], model, O['MB'], O['PK'], O['at'])
    assert json.dumps(a) == json.dumps(ledger.ledger_rows(O['G'], O['P'], model, O['MB'], O['PK'], O['at']))


def test_away_spread_pick_lands_on_the_home_line_row():
    g = game(b={'X': {'s': [-3, -140, 3, 110]}}, fair={'ref': {'s': 'market'}, 's': [-3, .5]}, mod={'m': -2.0, 't': 44.0, 'wp': .4})
    rows, pk = rows_for([g], [])
    assert [x['id'] for x in pk] == ['g|E1|spread|as'] and pk[0]['pt'] == 3
    (r,) = [r for r in rows if r['pick']]
    assert r['id'] == 'g|E1|spread|-3' and r['sd'] == 'as' and r['u'] == {'pr': 110, 'bk': 'X'}
    assert math.isclose(1 - r['pf'], pk[0]['pc'], abs_tol=1e-4)


def test_events_started_by_the_snapshot_are_left_out():
    early = '2026-11-02T10:00:00Z'
    g = dict(game(), t=early); p = dict(td_prop(), ko=early)
    rows = ledger.ledger_rows([g, dict(game(), id='E2')], [p, td_prop('P5')], MODEL, .5, [], '2026-11-02T10:52:27+00:00')
    assert {r['eid'] for r in rows if r['k'] == 'g'} == {'E2'} and [r['gid'] for r in rows if r['k'] == 'p'] == ['P5']
    assert not ledger.ledger_rows([g], [p], MODEL, .5, [], TS)   # a stamp without a zone is read as UTC


def test_moved_game_chance_counts_books_at_its_own_line():
    b = {'X': {'s': [-3, 110, 3, -125]}, 'Y': {'s': [-3, 105, 3, -120]}, 'Z': {'s': [-3.5, 100, 3.5, -120]},
         'W': {'s': [-3.5, 102, 3.5, -122]}, 'V': {'s': [-3.5, 101, 3.5, -121]}}
    rows = by_id(rows_for([game(b=b, fair={'ref': {'s': 'market'}, 's': [-3.5, .48]})], [])[0])
    assert (rows['g|E1|spread|-3.5']['pf_src'], rows['g|E1|spread|-3.5']['pf_n']) == ('market', 3)
    assert (rows['g|E1|spread|-3']['pf_src'], rows['g|E1|spread|-3']['pf_n']) == ('market+adj', 2)
