"""Parlays (for fun, tracked as their own record): parlay of the week, anytime TD parlay, parlay of the game.

Every parlay is placed at one sportsbook, so each is built from the legs one book offers, at that book's prices.
"""
from engine.odds import american_from_decimal, decimal, implied
from engine.picks import GAME_SIDES, best_prop_quote, is_hurt, market_over, model_p_over, started


def prop_leg(p, sd, model, blend, weeks):
    """One prop side as a parlay leg: best price, our blended chance, edge vs the price."""
    MB = blend
    if sd == 'y':
        q = best_prop_quote(p, 'y')
        if not q or p['pj'] is None or not p['fair']: return None
        P = MB * p['pj'] + (1 - MB) * p['fair'][1]
    else:
        q = best_prop_quote(p, sd)
        if not q: return None
        P = None
        po = model_p_over(model, p['mk'], p['pj'], q['pt'])
        fo = market_over(p, q['pt'])
        if po is None or fo is None: return None
        P = MB * po + (1 - MB) * fo; P = P if sd == 'o' else 1 - P
    return {'id': 'p|%s|%s|%s|%s' % (p['eid'], p['gid'], p['mk'], sd), 'k': 'p', 'eid': p['eid'], 'wk': weeks.get(p['eid']), 't': p['ko'], 'n': p['n'], 'gid': p['gid'], 'tm': p['t'], 'opp': p['opp'], 'mk': p['mk'], 'sd': sd, 'pt': q['pt'], 'pr': q['pr'], 'bk': q['bk'], 'pc': round(P, 4), 'e': round(P - implied(q['pr']), 4), '_p': p}


def at_book(leg, bn, games):
    """The leg's price at one book on the same line, or None."""
    if leg['k'] == 'p':
        x = leg['_p']['b'].get(bn)
        if not x: return None
        if leg['sd'] == 'u': return x[3] if x[2] == leg['pt'] else None
        if leg['sd'] == 'y': return x[1]
        return x[1] if x[0] == leg['pt'] else None
    g = next((g for g in games if g['id'] == leg['eid']), None); x = g and g['b'].get(bn)
    if not x: return None
    m = GAME_SIDES[leg['sd']]; y = x.get(m[0])
    if not y: return None
    if m[1] is not None and y[m[1]] != leg['pt']: return None
    return y[m[2]]


def price_parlay(legs, books, games):
    """(decimal price, book) at the book paying most for all the legs, or the product of the legs' own prices
    and 'mixed' when no single book has every leg."""
    best = None
    for bn in books:
        ps = [at_book(l, bn, games) for l in legs]
        if any(p_ is None for p_ in ps): continue
        d = 1.0
        for p_ in ps: d *= decimal(p_)
        if best is None or d > best[0]: best = (d, bn)
    if best: return round(best[0], 3), best[1]
    d = 1.0
    for l in legs: d *= decimal(l['pr'])
    return round(d, 3), 'mixed'


def one_book(cands, books, games, want=3, need=2, distinct=True):
    """Best set of legs that ONE sportsbook offers (a parlay is placed at one book): each leg at that book's own price and
    still above break-even there; the book with the best expected return wins."""
    top = None
    for bn in books:
        if bn == 'Pinnacle': continue   # the sharp reference; not open to US bettors
        legs = []; seen = set()
        for c in cands:
            if distinct and c['eid'] in seen: continue
            pr_ = at_book(c, bn, games)
            if pr_ is None or c['pc'] <= implied(pr_) - .02: continue
            l = dict(c); l['pr'] = pr_; l['bk'] = bn; l['e'] = round(c['pc'] - implied(pr_), 4); legs.append(l); seen.add(c['eid'])
            if len(legs) == want: break
        if len(legs) < need: continue
        ch = 1.0; d = 1.0
        for l in legs: ch *= l['pc']; d *= decimal(l['pr'])
        if top is None or ch * d > top[0]: top = (ch * d, legs)
    return top[1] if top else None


def make_parlay(kind, title, legs, note, books, games, joint=None):
    """The parlay record (data.json ODD.PX row) for LEGS."""
    d, bn = price_parlay(legs, books, games); ch = 1.0
    for l in legs: ch *= l['pc']
    if joint is not None: ch = max(ch, min(joint, ch * 1.25))   # teammates hit together a bit more often than independent legs would
    clean_ = [{k: v for k, v in l.items() if k not in ('_p', 'e')} for l in legs]
    return {'id': 'x|%s|wk%s' % (kind, legs[0]['wk']), 'k': 'x', 'kind': kind, 'title': title, 'wk': legs[0]['wk'], 't': min(l['t'] for l in legs), 'legs': clean_,
            'dec': d, 'pr': american_from_decimal(d), 'bk': bn, 'pc': round(ch, 4), 'be': round(1 / d, 4), 'note': note, 'joint': joint, 's': 0}


def build_parlays(picks, props, games, books, model, blend, now, injured):
    """Parlay of the week (from PICKS), anytime TD parlay and parlay of the game (from PROPS), for games not started by
    NOW and players not hurt. If one fails, it prints why and returns the parlays built so far, as the build always has.

    BOOKS here is required and means something different from picks' optional books filter: it is the ordered list (or
    dict, iterated in order) of every book to price parlays at, the books seen on the board. The first book wins ties."""
    if books is None:
        raise ValueError('build_parlays needs the ordered list of books to price at (BOOKS), not None')
    weeks = {g['id']: g['wk'] for g in games}
    PK, PR = picks, props
    PX = []
    try:
        # parlay of the week: 2-3 of the strongest non-TD picks from different games, at one book
        cands = []
        for x in PK:
            if x['sd'] == 'y' or x.get('pc') is None or x['pc'] <= implied(x['pr']) or x['pr'] < -200: continue
            l = dict(x); l.pop('srt', None)
            if x['k'] == 'p': l['_p'] = next(p for p in PR if p['gid'] == x['gid'] and p['mk'] == x['mk'] and p['eid'] == x['eid'])
            cands.append(l)
        legs = one_book(cands[:10], books, games)
        if legs: PX.append(make_parlay('week', 'Parlay of the week', legs, 'Our strongest picks from different games, all at one sportsbook.', books, games))
        # anytime TD parlay: the most likely scorers priced near or better than our chance, different games, at one book
        tds = []
        for p in PR:
            if p['mk'] != 'Anytime TD' or started(p.get('ko') or '2000-01-01T00:00:00Z', now) or is_hurt(injured, p['gid']) or len(p['v']) < 4: continue
            l = prop_leg(p, 'y', model, blend, weeks)
            if l and l['pc'] >= .30 and l['e'] >= -.02 and l['pr'] <= 300: tds.append(l)
        tds.sort(key=lambda l: -(l['pc'] + l['e']))
        legs = one_book(tds[:10], books, games)
        if legs: PX.append(make_parlay('td', 'Anytime TD parlay of the week', legs, 'The likeliest scorers on the board, from different games, all at one sportsbook.', books, games))
        # parlay of the game: QB over + his receiver over that have hit together most this season
        best = None
        byteam = {}
        for p in PR:
            if started(p.get('ko') or '2000-01-01T00:00:00Z', now) or is_hurt(injured, p['gid']) or len(p['v']) < 4: continue
            byteam.setdefault((p['eid'], p['t']), []).append(p)
        for (eid, tm), ps in byteam.items():
            qbs = [p for p in ps if p['mk'] in ('Pass yds', 'Pass TDs')]; recs = [p for p in ps if p['mk'] in ('Rec yds', 'Receptions', 'Anytime TD') and p['pos'] in ('WR', 'TE')]
            for a in qbs:
                la = prop_leg(a, 'o', model, blend, weeks)
                if not la or la['e'] < -.02: continue
                for r in recs:
                    lr = prop_leg(r, 'y' if r['mk'] == 'Anytime TD' else 'o', model, blend, weeks)
                    if not lr or lr['e'] < -.02: continue
                    wr = {v[0]: v[2] for v in r['v']}
                    both = [(v[2] > la['pt']) and ((wr[v[0]] >= 1) if lr['sd'] == 'y' else (wr[v[0]] > lr['pt'])) for v in a['v'] if v[0] in wr]
                    if len(both) < 4: continue
                    j = sum(both) / len(both)
                    sc = j + la['e'] + lr['e']
                    if j >= .5:
                        pair = one_book([la, lr], books, games, want=2, need=2, distinct=False)
                        if pair and (best is None or sc > best[0]): best = (sc, pair, round(j, 3), len(both))
        if best:
            px = make_parlay('game', 'Parlay of the game', best[1], 'A quarterback and his receiver who have cleared these lines together in %d of %d games this season. Same-game parlays usually pay less than this; check your book.' % (round(best[2] * best[3]), best[3]), books, games, joint=best[2])
            PX.append(px)
    except Exception as ex_: print('parlays skipped:', ex_)
    return PX
