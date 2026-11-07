"""The prediction ledger: every line the engine prices at one refresh, one row each, so every lean can be graded.

A row is one (event, player or team, market, line) and holds the chance of one side only: the over (props, totals),
yes (anytime TD), the home team covering its line (spreads) or winning (moneyline). The other side is one minus it,
so no event is logged twice. Each row carries the forecasts to score head to head on the same events:

  pm      the model's own chance, before blending (props: model_p_over, or pj for anytime TD; moneyline: the team
          model's win chance; spreads and totals: None, the team model gives a margin, kept in 'mod')
  pf      the market's fair chance at this line, with pf_src and pf_n (the books behind it):
            props   'median'  cross-book median no-vig at the consensus line (prop 'fair', 3+ books)
                    'book'    one book posting both sides of this line, cut split proportionally (market_over)
                    'td'      anytime TD: median implied chance / 1.12
            games   'Pinnacle' or 'market' (game 'fair.ref'); '+adj' when this line is off the fair line and the
                    chance is moved the way game_ev moves it
  pin     Pinnacle's no-vig chance (Shin) when Pinnacle posts both sides of this line, else None
  P       the blended chance the dashboard uses, blend * pm + (1 - blend) * pf (props only; games aren't blended)
  o, u    the best {'pr','bk'} for the over/yes/home side and the under/away side at this line (u is None for TD)

plus the engine's scoring: sd, ls, vs, s are the side prop_side or better_game_side scored, with its lean tier (props),
value score and score, on the row at that side's line (None on the other rows); pick is True when that side is in the
official picks passed in. Stamps: pj (props), mod (games), model_fit_at, snapshot_ts. Chances are rounded to 4 places.

ledger_rows is pure: it reads data.json's ODD.G and ODD.P rows and returns new dicts.
"""
from engine.odds import no_vig_shin
from engine.picks import GAME_MARKETS, best_game_quote, best_prop_quote, better_game_side, game_ev, game_fair, \
    market_over, model_p_over, prop_side

HOME_SIDES = ('o', 'y', 'hs', 'ov', 'mh')   # the side whose chance a row holds


def _r(x): return None if x is None else round(x, 4)


def _price(q): return None if q is None else {'pr': q['pr'], 'bk': q['bk']}


def _key(pt): return '' if pt is None else str(pt)


def _scored(row, x, pick_pt):
    """Fill the engine's scoring for side X (prop_side or game_side output) into ROW, and the pick flag."""
    row.update(sd=x['sd'] if 'sd' in x else x['k'], ls=x.get('ls'), vs=x['vs'], s=x['s'], pick=pick_pt is not None and pick_pt[0] == x['q']['pt'])


def _blank(row): row.update(sd=None, ls=None, vs=None, s=None, pick=False)


def prop_rows(prop, model, blend, pick_pts, week, stamps):
    """Ledger rows for one ODD.P row: one per line any book posts (one 'yes' row for anytime TD)."""
    p = prop; b = p['b']; x = prop_side(p, model, blend)
    base = {'k': 'p', 'eid': p['eid'], 'wk': week, 't': p['ko'], 'gid': p['gid'], 'n': p['n'], 'tm': p['t'], 'opp': p['opp'], 'mk': p['mk']}
    if p['mk'] == 'Anytime TD':
        pf = p['fair'][1] if p['fair'] else None; pm = p['pj']
        row = dict(base, id='p|%s|%s|%s|' % (p['eid'], p['gid'], p['mk']), pt=None, pm=_r(pm), pf=_r(pf),
                   pf_src='td' if pf is not None else None, pf_n=sum(1 for v in b.values() if v[1] is not None) if pf is not None else 0,
                   pin=None, P=_r(None if pm is None or pf is None else blend * pm + (1 - blend) * pf),
                   o=_price(best_prop_quote(p, 'y')), u=None)
        _scored(row, x, pick_pts.get('p|%s|%s|%s|y' % (p['eid'], p['gid'], p['mk']))) if x else _blank(row)
        return [dict(row, **stamps)]
    lines = sorted({v[0] for v in b.values() if v[0] is not None and v[1] is not None} | {v[2] for v in b.values() if v[2] is not None and v[3] is not None})
    rows = []
    for pt in lines:
        both = [v for v in b.values() if v[0] == pt and v[2] == pt and v[1] is not None and v[3] is not None]
        pm = model_p_over(model, p['mk'], p['pj'], pt); pf = market_over(p, pt)
        on_fair = bool(p['fair']) and p['fair'][0] == pt
        pin = b.get('Pinnacle')
        row = dict(base, id='p|%s|%s|%s|%s' % (p['eid'], p['gid'], p['mk'], _key(pt)), pt=pt, pm=_r(pm), pf=_r(pf),
                   pf_src=None if pf is None else 'median' if on_fair else 'book', pf_n=0 if pf is None else len(both) if on_fair else 1,
                   pin=_r(no_vig_shin(pin[1], pin[3])) if pin and pin[0] == pt and pin[2] == pt and pin[1] is not None and pin[3] is not None else None,
                   P=_r(None if pm is None or pf is None else blend * pm + (1 - blend) * pf),
                   o=_price(best_prop_quote(p, 'o', {bn for bn, v in b.items() if v[0] == pt})),
                   u=_price(best_prop_quote(p, 'u', {bn for bn, v in b.items() if v[2] == pt})))
        if x and x['q']['pt'] == pt: _scored(row, x, pick_pts.get('p|%s|%s|%s|%s' % (p['eid'], p['gid'], p['mk'], x['sd'])))
        else: _blank(row)
        rows.append(dict(row, **stamps))
    return rows


def _game_market(game, side, pt):
    """(fair chance of SIDE ('hs', 'ov' or 'mh') at line PT, moved off the fair line as game_ev moves it; True when
    moved), or (None, False)."""
    fr = game_fair(game, side)
    if fr is None: return None, False
    if fr['pt'] == pt: return fr['p'], False
    ev = game_ev({'pt': pt, 'pr': 100}, fr)   # at even money expected value is 2p - 1
    return (None, False) if ev is None else ((ev + 1) / 2, True)


def game_rows(game, pick_pts, stamps):
    """Ledger rows for one ODD.G row: one per spread line (the home team's), per total, and the moneyline."""
    g = game; b = g['b']; f = g['fair']; ref = f.get('ref', {}); pin = b.get('Pinnacle', {}); rows = []
    for s1, s2, mk in GAME_MARKETS:
        x = better_game_side(g, s1, s2)
        if mk == 'spread': lines = sorted({v['s'][0] for v in b.values() if 's' in v})
        elif mk == 'total': lines = sorted({v['o'][0] for v in b.values() if 'o' in v})
        else: lines = [None] if any('m' in v for v in b.values()) else []
        for pt in lines:
            if mk == 'spread':
                at1 = {bn for bn, v in b.items() if 's' in v and v['s'][0] == pt}; at2 = {bn for bn, v in b.items() if 's' in v and v['s'][2] == -pt}
                fair_n = sum(1 for v in b.values() if 's' in v and f.get('s') and v['s'][0] == f['s'][0])
                pv = no_vig_shin(pin['s'][1], pin['s'][3]) if 's' in pin and pin['s'][0] == pt else None
                x_pt = None if x is None else x['q']['pt'] if x['k'] == 'hs' else -x['q']['pt']
            elif mk == 'total':
                at1 = at2 = {bn for bn, v in b.items() if 'o' in v and v['o'][0] == pt}
                fair_n = sum(1 for v in b.values() if 'o' in v and f.get('o') and v['o'][0] == f['o'][0])
                pv = no_vig_shin(pin['o'][1], pin['o'][2]) if 'o' in pin and pin['o'][0] == pt else None
                x_pt = None if x is None else x['q']['pt']
            else:
                at1 = at2 = None; fair_n = sum(1 for v in b.values() if 'm' in v)
                pv = no_vig_shin(pin['m'][0], pin['m'][1]) if 'm' in pin else None
                x_pt = None
            pf, moved = _game_market(g, s1, pt)
            src = ref.get({'spread': 's', 'total': 'o', 'ml': 'm'}[mk]) if pf is not None else None
            row = {'id': 'g|%s|%s|%s' % (g['id'], mk, _key(pt)), 'k': 'g', 'eid': g['id'], 'wk': g['wk'], 't': g['t'], 'a': g['a'], 'h': g['h'],
                   'mk': mk, 'pt': pt, 'pm': _r(g['mod']['wp']) if mk == 'ml' and g.get('mod') else None, 'pf': _r(pf),
                   'pf_src': None if src is None else src + ('+adj' if moved else ''), 'pf_n': 0 if src is None else 1 if src == 'Pinnacle' else fair_n,
                   'pin': _r(pv), 'P': None, 'o': _price(best_game_quote(g, s1, at1)), 'u': _price(best_game_quote(g, s2, at2))}
            if x and x_pt == pt:
                _scored(row, x, pick_pts.get('g|%s|%s|%s' % (g['id'], mk, x['k'])))
            else: _blank(row)
            rows.append(dict(row, pj=None, mod=g.get('mod'), **stamps))
    return rows


def ledger_rows(games, props, model, blend, picks, snapshot_ts):
    """Every ledger row for one refresh: ODD.G rows GAMES and ODD.P rows PROPS priced with MODEL (model.json) and BLEND,
    flagged against the official picks PICKS (ODD.PK), stamped with SNAPSHOT_TS. Games first, then props, in input order."""
    pick_pts = {x['id']: (x.get('pt'),) for x in picks}
    weeks = {g['id']: g['wk'] for g in games}
    rows = []
    for g in games:
        rows += game_rows(g, pick_pts, {'model_fit_at': (model or {}).get('fit_at'), 'snapshot_ts': snapshot_ts})
    for p in props:
        rows += prop_rows(p, model, blend, pick_pts, weeks.get(p['eid']), {'pj': p['pj'], 'model_fit_at': (model or {}).get('fit_at'), 'snapshot_ts': snapshot_ts})
    return rows
