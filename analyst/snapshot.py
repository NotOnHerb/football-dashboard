"""Builds the Analyst Desk snapshot from the site's data, as JSON files ready for the Desk's database.

python analyst/snapshot.py OUT_DIR
Writes OUT_DIR/snap/<doc>.json (each under ~200 KB): meta, picks, log, games, props1..N.
The weekly analyst and the daily sync upload these with ArtifactData (collection "snap", doc id = file name).
"""
import json, os, sys, datetime

def i2p(a):
    a = float(a); return 100 / (a + 100) if a > 0 else -a / (-a + 100)

def novig(a, b):
    x, y = i2p(a), i2p(b); return x / (x + y)

def main(out):
    D = json.load(open('data.json')); O = D.get('ODD') or {}
    try: LOG = json.load(open('odds/picks.json'))
    except Exception: LOG = {}
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()[:16]
    MQ, MC, MB = O.get('MQ') or {}, O.get('MC') or {}, O.get('MB', .5)

    def pover(mk, mu, L):
        q = MQ.get(mk)
        if not q or not mu or mu <= 0: return None
        x = L / mu; p = sum(1 for v in q if v > x) / len(q) + (MC or {}).get(mk, 0)
        return min(.99, max(.01, p))

    # price movement on locked/graded picks: did the market move toward our side after we first posted it?
    def move(r):
        f = r.get('first')
        if not f or f.get('pr') is None or r.get('pr') is None: return None
        d = i2p(r['pr']) - i2p(f['pr'])          # + = price got worse for a new bettor = we beat the later price
        if r.get('pt') is not None and f.get('pt') is not None and r['pt'] != f['pt']:
            better_now = (r['pt'] < f['pt']) if r['sd'] in ('o', 'ov') else (r['pt'] > f['pt'])
            d += (-.02 if better_now else .02) * abs(r['pt'] - f['pt']) / .5
        return round(d, 4)

    logs = sorted(LOG.values(), key=lambda r: r['t'], reverse=True)
    for r in logs: r['move'] = move(r)
    graded = [r for r in logs if r.get('res')]
    def summ(rs):
        w = sum(r['res'] == 'W' for r in rs); l = sum(r['res'] == 'L' for r in rs); p = sum(r['res'] in ('P', 'V') for r in rs)
        mv = [r['move'] for r in rs if r.get('move') is not None]
        return {'w': w, 'l': l, 'p': p, 'u': round(sum(r.get('u') or 0 for r in rs), 2), 'n': len(rs),
                'beat_move': sum(1 for m in mv if m > 0), 'moved_n': len(mv), 'avg_move': round(sum(mv) / len(mv), 4) if mv else None}
    weeks = sorted({r['wk'] for r in graded if r.get('wk')})
    meta = {'at': now, 'built': D['META'].get('built'), 'season': D['META'].get('season'), 'model': D['META'].get('model'),
            'calibration': MC, 'blend': MB, 'rules': O.get('RU'), 'model_record_vs_close': O.get('MR'),
            'record': {'all': summ(graded), 'game_lines': summ([r for r in graded if r['k'] == 'g']), 'props': summ([r for r in graded if r['k'] == 'p']),
                       'by_week': {str(w): summ([r for r in graded if r.get('wk') == w]) for w in weeks}},
            'odds_credits_left': O.get('left'), 'lines_at': O.get('at'), 'props_at': O.get('pat'),
            'counts': {'games': len(O.get('G', [])), 'props': len(O.get('P', [])), 'picks_now': len(O.get('PK', [])), 'picks_logged': len(logs)}}

    def best(b, i_pt, i_pr, low):
        bq = None
        for bk, x in b.items():
            if x[i_pr] is None or (i_pt is not None and x[i_pt] is None): continue
            q = (None if i_pt is None else x[i_pt], x[i_pr], bk)
            if bq is None or (q[0] != bq[0] and ((q[0] < bq[0]) if low else (q[0] > bq[0]))) or (q[0] == bq[0] and q[1] > bq[1]): bq = q
        return bq

    props = []
    for p in O.get('P', []):
        td = p['mk'] == 'Anytime TD'
        row = {'n': p['n'], 't': p['t'], 'opp': p['opp'], 'pos': p['pos'], 'mk': p['mk'], 'ko': p.get('ko'), 'gid': p['gid'],
               'avg': p.get('avg'), 'l3': p.get('l3'), 'proj_mean': p.get('pj'), 'typical': p.get('md'), 'matchup': p.get('fac'),
               'last_games': p.get('v'), 'books': len(p['b'])}
        if td:
            y = best(p['b'], None, 1, True); row['yes'] = y and [y[1], y[2]]
            pf = p['fair'][1] if p.get('fair') else None
            row['chance_scores'] = None if p.get('pj') is None or pf is None else round(MB * p['pj'] + (1 - MB) * pf, 3)
            row['usage'] = p.get('use')
        else:
            o = best(p['b'], 0, 1, True); u = best(p['b'], 2, 3, False)
            row['over'] = o and list(o); row['under'] = u and list(u)
            L = (o or u)[0]; po = pover(p['mk'], p.get('pj'), L)
            fo = p['fair'][1] if p.get('fair') and p['fair'][0] == L else None
            if fo is None:
                pr = [x for x in p['b'].values() if x[0] == L and x[2] == L and x[1] is not None and x[3] is not None]
                fo = novig(pr[0][1], pr[0][3]) if pr else None
            row['line'] = L; row['model_chance_over'] = po and round(po, 3); row['market_chance_over'] = fo and round(fo, 3)
            row['our_chance_over'] = None if po is None or fo is None else round(MB * po + (1 - MB) * fo, 3)
        props.append(row)

    games = []
    for g in O.get('G', []):
        f = g.get('fair') or {}; c = g.get('ctx') or {}
        games.append({'a': g['a'], 'h': g['h'], 't': g['t'], 'wk': g.get('wk'), 'home_spread': (f.get('s') or [None])[0],
                      'total': (f.get('o') or [None])[0], 'home_win_chance': f.get('m'), 'fair_from': f.get('ref'), 'model': g.get('mod'),
                      'context': {k: c.get(k) for k in ('div', 'rest', 'roof', 'wx', 'a', 'h')}, 'line_history': g.get('mv'),
                      'books': {bk: x for bk, x in g['b'].items()}})

    os.makedirs(os.path.join(out, 'snap'), exist_ok=True)
    def put(name, obj):
        json.dump(obj, open(os.path.join(out, 'snap', name + '.json'), 'w'), separators=(',', ':'))
    put('meta', meta)
    put('picks', {'at': now, 'items': O.get('PK', [])})
    put('log', {'at': now, 'items': logs[:300]})
    put('games', {'at': now, 'items': games})
    chunk, size, n = [], 0, 0
    for r in props:
        s = len(json.dumps(r, separators=(',', ':')))
        if chunk and size + s > 190000:
            n += 1; put('props%d' % n, {'at': now, 'items': chunk}); chunk, size = [], 0
        chunk.append(r); size += s
    n += 1; put('props%d' % n, {'at': now, 'items': chunk, 'last': True})
    meta['props_docs'] = n; put('meta', meta)
    for f in sorted(os.listdir(os.path.join(out, 'snap'))):
        print(f, os.path.getsize(os.path.join(out, 'snap', f)))

if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else 'analyst_out')
