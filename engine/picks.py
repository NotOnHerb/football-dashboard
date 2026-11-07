"""Game and prop sides and the official pick list (data.json ODD.PK).

A side scores on value (expected value at the best price vs the fair chance, 0-3) plus, for spreads, the team model
(1 when it beats the line by RULES['model'] points) or, for props, our lean (blended chance vs the price, 0-2).
A side is an official pick at RULES['pick'] or more.

Shapes are data.json's: a game is an ODD.G row ({'id','wk','a','h','t','b':{book:{'s','o','m'}},'fair','mod',...}) and
a prop an ODD.P row ({'eid','ko','n','t','pos','gid','opp','mk','b':{book:[over pt, over price, under pt, under price]},
'fair','v','pj',...}). books=None takes the best price across every book; a set of book names only looks at those.
"""
import datetime

from engine.odds import decimal, implied, no_vig_proportional
from engine.projections import p_over
from engine.rules import LEAN_MAX_SCORE, LEAN_MIN_GAMES, RULES, lean_tier, value_score

# game side -> (market, index of the line, index of the price) in a book's market list
GAME_SIDES = {'hs': ('s', 0, 1), 'as': ('s', 2, 3), 'ov': ('o', 0, 1), 'un': ('o', 0, 2), 'mh': ('m', None, 0), 'ma': ('m', None, 1)}
HURT = ('Out', 'IR', 'Reserve', 'Doubtful')


def started(iso, now):
    """True when the ISO kickoff time is at or before NOW (an aware datetime)."""
    return datetime.datetime.fromisoformat(iso.replace('Z', '+00:00')) <= now


def is_hurt(injured, gid):
    """True when the injury map (gsis id -> report status) has the player out, doubtful or on a reserve list."""
    return injured.get(gid) in HURT


def best_game_quote(game, side, books=None):
    """Best {'pt','pr','bk'} for a game side: the better line first, then the better price."""
    m = GAME_SIDES[side]; best = None
    for bn, x in game['b'].items():
        if books is not None and bn not in books: continue
        x = x.get(m[0])
        if not x or x[m[2]] is None: continue
        q = {'pt': None if m[1] is None else x[m[1]], 'pr': x[m[2]], 'bk': bn}
        if best is None: best = q
        elif q['pt'] is not None and q['pt'] != best['pt']:
            if ((best['pt'] - q['pt']) if side == 'ov' else (q['pt'] - best['pt'])) > 0: best = q
        elif q['pr'] > best['pr']: best = q
    return best


def game_fair(game, side):
    """The fair line and chance for a game side ({'pt','p'} plus 'sp' for spreads, 'ov' for totals), or None."""
    f = game['fair']
    if side in ('hs', 'as'):
        if not f.get('s') or f['s'][1] is None: return None
        return {'pt': f['s'][0] if side == 'hs' else -f['s'][0], 'p': f['s'][1] if side == 'hs' else 1 - f['s'][1], 'sp': 1}
    if side in ('ov', 'un'):
        if not f.get('o') or f['o'][1] is None: return None
        return {'pt': f['o'][0], 'p': f['o'][1] if side == 'ov' else 1 - f['o'][1], 'ov': side == 'ov'}
    return None if f.get('m') is None else {'pt': None, 'p': f['m'] if side == 'mh' else 1 - f['m']}


def game_ev(quote, fair):
    """Expected value per unit of a quote against the fair chance. A different line moves the chance 2% per half point
    on spreads (plus 3% when it crosses 3 or 7) and 1.5% on totals; lines more than 2 points apart give None."""
    q, fr = quote, fair
    if not q or not fr: return None
    p = fr['p']
    if fr['pt'] is not None and q['pt'] != fr['pt']:
        d = (fr['pt'] - q['pt']) if fr.get('ov') else (q['pt'] - fr['pt'])
        if abs(d) > 2: return None
        p += d / .5 * (.02 if fr.get('sp') else .015)
        if fr.get('sp'):
            lo, hi = min(abs(q['pt']), abs(fr['pt'])), max(abs(q['pt']), abs(fr['pt']))
            if (lo < 3 < hi) or (lo < 7 < hi): p += (.03 if d > 0 else -.03)
    return p * decimal(q['pr']) - 1


def game_side(game, side, books=None):
    """Scores one game side: {'k','q','v','vs','me','ms','s','flag'}, or None when no book has it."""
    k = side
    q = best_game_quote(game, k, books)
    if not q: return None
    v = game_ev(q, game_fair(game, k)); vs = value_score(v); me = None; ms = 0; flag = None
    if v is not None and v > RULES['stale']: vs = 0; flag = 'stale'
    if k in ('mh', 'ma') and (q['pr'] > RULES['mlmax'] or q['pr'] < RULES['mlmin']): vs = 0; flag = flag or 'range'
    if game['mod'] and k in ('hs', 'as'):
        me = (game['mod']['m'] if k == 'hs' else -game['mod']['m']) + q['pt']; ms = 1 if me >= RULES['model'] else 0
    return {'k': k, 'q': q, 'v': v, 'vs': vs, 'me': me, 'ms': ms, 's': vs + ms, 'flag': flag}


def best_prop_quote(prop, side, books=None):
    """Best {'pt','pr','bk'} for a prop side ('o' over, 'u' under, 'y' anytime TD yes): the better line, then price."""
    sd = side; best = None
    for bn, x in prop['b'].items():
        if books is not None and bn not in books: continue
        q = {'pt': x[2], 'pr': x[3], 'bk': bn} if sd == 'u' else {'pt': x[0], 'pr': x[1], 'bk': bn}
        if q['pr'] is None or (sd != 'y' and q['pt'] is None): continue
        if best is None: best = q
        elif q['pt'] != best['pt']:
            if (q['pt'] > best['pt']) if sd == 'u' else (q['pt'] < best['pt']): best = q
        elif q['pr'] > best['pr']: best = q
    return best


def model_p_over(model, mk, mu, line):
    """p_over with the quantiles and calibration for prop type MK from model.json; None without a model."""
    if not model or not mu or mu <= 0: return None
    return p_over(model['q'][mk], model.get('cal', {}).get(mk, 0), mu, line)


def market_over(prop, pt):
    """The over chance for line PT: the prop's fair chance when it is on that line, else the first book posting both
    sides of it with the cut split proportionally; None if no book does."""
    p = prop
    if p['fair'] and p['fair'][0] == pt: return p['fair'][1]
    pr_ = [x for x in p['b'].values() if x[0] == pt and x[2] == pt and x[1] is not None and x[3] is not None]
    return no_vig_proportional(pr_[0][1], pr_[0][3]) if pr_ else None


def prop_side(prop, model, blend, books=None):
    """The better-scoring side of a prop: {'sd','q','ls','vs','v','s','srt','P'}, or None. Our chance P blends the
    model's (weight BLEND) with the market's fair chance."""
    p = prop; MB = blend
    n = len(p['v'])
    if p['mk'] == 'Anytime TD':
        q = best_prop_quote(p, 'y', books)
        if not q: return None
        im = implied(q['pr']); pf = p['fair'][1] if p['fair'] else None
        P = None if p['pj'] is None or pf is None else MB * p['pj'] + (1 - MB) * pf
        ls = lean_tier(P - im) if (P is not None and n >= LEAN_MIN_GAMES and q['pr'] <= RULES['tdmax']) else 0
        return {'sd': 'y', 'q': q, 'ls': ls, 'vs': 0, 'v': None, 's': min(ls, LEAN_MAX_SCORE), 'srt': (P - im) if P is not None else 0, 'P': P}

    def side(q, dr):
        if not q: return None
        po = model_p_over(model, p['mk'], p['pj'], q['pt'])
        fo = market_over(p, q['pt'])
        P = None
        if po is not None and fo is not None: P = MB * po + (1 - MB) * fo; P = P if dr > 0 else 1 - P
        e = None if P is None else P - implied(q['pr'])
        ls = lean_tier(e) if (e is not None and n >= LEAN_MIN_GAMES and q['pt'] >= RULES['minl'].get(p['mk'], 0)) else 0
        v = None
        if p['fair'] and p['fair'][0] == q['pt']: v = (p['fair'][1] if dr > 0 else 1 - p['fair'][1]) * decimal(q['pr']) - 1
        vs = value_score(v)
        if v is not None and v > RULES['stale']: vs = 0
        if e is not None and e < 0: vs = 0   # never pick a side our own chance says loses at this price
        return {'sd': 'o' if dr > 0 else 'u', 'q': q, 'ls': ls, 'vs': vs, 'v': v, 's': min(ls, LEAN_MAX_SCORE) + vs, 'srt': e or 0, 'P': P}
    o, u = side(best_prop_quote(p, 'o', books), 1), side(best_prop_quote(p, 'u', books), -1)
    if o and u: return u if u['s'] > o['s'] or (u['s'] == o['s'] and u['srt'] > o['srt']) else o
    return o or u


GAME_MARKETS = (('hs', 'as', 'spread'), ('ov', 'un', 'total'), ('mh', 'ma', 'ml'))   # (side 1, side 2, market)


def better_game_side(game, s1, s2, books=None):
    """The better-scoring of two opposite game sides (game_side), S1 on a tie; None when no book has either."""
    x1, x2 = game_side(game, s1, books), game_side(game, s2, books)
    return x2 if x1 and x2 and x2['s'] > x1['s'] else (x1 or x2)


def game_picks(games, now, books=None):
    """Official game picks (spread, total, moneyline; the better side of each) for games not started by NOW,
    strongest first."""
    PK = []
    for g in games:
        if started(g['t'], now): continue
        for a1, a2, mk_ in GAME_MARKETS:
            x = better_game_side(g, a1, a2, books)
            if x and x['s'] >= RULES['pick']:
                q = x['q']; PK.append({'id': 'g|%s|%s|%s' % (g['id'], mk_, x['k']), 'k': 'g', 'eid': g['id'], 'wk': g['wk'], 't': g['t'], 'a': g['a'], 'h': g['h'], 'mk': mk_, 'sd': x['k'], 'pt': q['pt'], 'pr': q['pr'], 'bk': q['bk'], 's': x['s'], 'v': None if x['v'] is None else round(x['v'], 4), 'ms': x['ms'], 'vs': x['vs'], 'pc': None if x['v'] is None else round((x['v'] + 1) / decimal(q['pr']), 4), 'srt': x['s'] + (x['v'] or 0) * 5})
    PK.sort(key=lambda x: -x['srt'])
    return PK


def prop_picks(props, model, blend, now, injured, books=None, weeks=None):
    """Official prop picks for props whose game hasn't started by NOW and whose player isn't hurt (INJURED: gsis id ->
    report status), strongest first. WEEKS (event id -> week) labels each pick's week; the build passes the games'."""
    weeks = weeks or {}; PK = []
    # a prop with no kickoff time is never a pick (the page lists only these picks); the Odds API always sends
    # commence_time, so real data has none
    for p in props:
        if not p.get('ko') or started(p['ko'], now) or is_hurt(injured, p['gid']): continue
        x = prop_side(p, model, blend, books)
        if x and x['s'] >= RULES['pick']:
            q = x['q']; PK.append({'id': 'p|%s|%s|%s|%s' % (p['eid'], p['gid'], p['mk'], x['sd']), 'k': 'p', 'eid': p['eid'], 'wk': weeks.get(p['eid']), 't': p['ko'], 'n': p['n'], 'gid': p['gid'], 'tm': p['t'], 'opp': p['opp'], 'mk': p['mk'], 'sd': x['sd'], 'pt': q['pt'], 'pr': q['pr'], 'bk': q['bk'], 's': x['s'], 'v': None if x['v'] is None else round(x['v'], 4), 'ls': x['ls'], 'vs': x['vs'], 'pj': p['pj'], 'pc': None if x.get('P') is None else round(x['P'], 4), 'srt': x['s'] + x['srt'] + (x['v'] or 0) * 5})
    PK.sort(key=lambda x: -x['srt'])
    return PK


def official_picks(games, props, model, blend, now, injured, books=None, weeks=None):
    """Every official pick, games and props together, strongest first (ODD.PK). BOOKS=None prices each side at the best
    quote across all books; a set of book names only looks at those books."""
    pk = game_picks(games, now, books) + prop_picks(props, model, blend, now, injured, books, weeks)
    pk.sort(key=lambda x: -x['srt'])
    return pk


def picks_by_book(book_names, games, props, model, blend, now, injured, weeks=None):
    """{book: official picks when only that book's quotes are available} for each name in BOOK_NAMES (ODD.PKB). The page's
    sportsbook selector shows these lists."""
    return {b: official_picks(games, props, model, blend, now, injured, {b}, weeks) for b in book_names}
