"""Grading the pick log (odds/picks.json) from final scores and weekly stats.

FINALS maps (week, away, home) -> (away score, home score) and (week, team) -> (away, home, away score, home score)
for every finished game. LOGS is data.json LOG (gsis id -> weekly rows) and LOGMAX the latest week it covers.
A result is 'W', 'L', 'P' (push) or 'V' (void: the player didn't play); 'u' is units won on a 1-unit stake.
"""
from engine.odds import decimal
from engine.picks import started

# prop type -> column in a LOG row
STAT = {'Pass yds': 7, 'Rush yds': 8, 'Rec yds': 9, 'Receptions': 6, 'Pass TDs': 10, 'Anytime TD': 11}


def grade_pick(rec, finals, logs, logmax):
    """Grades one game or prop pick in place: sets 'res' and 'fin' (games) or 'val' (props). Leaves it ungraded when
    the score or that week's stats aren't in yet."""
    r_, fin, LOG, SI = rec, finals, logs, STAT
    if r_['k'] == 'g':
        sc = fin.get((r_['wk'], r_['a'], r_['h']))
        if not sc: return
        asc, hsc = sc
        if r_['mk'] == 'spread': c_ = ((hsc - asc) if r_['sd'] == 'hs' else (asc - hsc)) + r_['pt']
        elif r_['mk'] == 'total': c_ = ((asc + hsc) - r_['pt']) * (1 if r_['sd'] == 'ov' else -1)
        else: c_ = (hsc - asc) * (1 if r_['sd'] == 'mh' else -1)
        r_['res'] = 'W' if c_ > 0 else 'L' if c_ < 0 else 'P'; r_['fin'] = [asc, hsc]
    else:
        gm = fin.get((r_['wk'], r_.get('tm')))
        if not gm or logmax < r_['wk']: return
        row = [x for x in LOG.get(r_['gid'], []) if x[0] == r_['wk']]
        if not row: r_['res'] = 'V'; return
        val = row[0][SI[r_['mk']]]; r_['val'] = val
        if r_['sd'] == 'y': r_['res'] = 'W' if val >= 1 else 'L'
        else:
            c_ = (val - r_['pt']) * (1 if r_['sd'] == 'o' else -1); r_['res'] = 'W' if c_ > 0 else 'L' if c_ < 0 else 'P'


def grade_log(log, finals, logs, logmax, now):
    """Grades every ungraded record in LOG (the pick log dict, id -> record) whose game started by NOW, in place, and
    sets its units 'u'. A parlay loses on any losing leg; otherwise, once every leg is graded, it pays the winning legs
    (pushes and voids drop out), at its own price when every leg won at one book."""
    for r_ in (log.values() if isinstance(log, dict) else log):
        if r_.get('res') is not None or not started(r_['t'], now) or r_.get('wk') is None: continue
        if r_['k'] == 'x':
            for l in r_['legs']:
                if l.get('res') is None and started(l['t'], now): grade_pick(l, finals, logs, logmax)
            rs = [l.get('res') for l in r_['legs']]
            if 'L' in rs: r_['res'] = 'L'; r_['u'] = -1
            elif None not in rs:
                d = 1.0
                for l in r_['legs']:
                    if l['res'] == 'W': d *= decimal(l['pr'])
                if r_['bk'] != 'mixed' and all(x == 'W' for x in rs): d = r_['dec']   # every leg won: the parlay's own price
                r_['res'] = 'W' if any(x == 'W' for x in rs) else 'P'; r_['u'] = round(d - 1, 3) if r_['res'] == 'W' else 0
            continue
        grade_pick(r_, finals, logs, logmax)
        if r_.get('res'): r_['u'] = round(decimal(r_['pr']) - 1, 3) if r_['res'] == 'W' else -1 if r_['res'] == 'L' else 0


def summarize(records):
    """Win-loss record and units: {'w','l','p','u'} (voids count as pushes)."""
    rs = list(records)
    return {'w': sum(1 for r in rs if r.get('res') == 'W'), 'l': sum(1 for r in rs if r.get('res') == 'L'), 'p': sum(1 for r in rs if r.get('res') in ('P', 'V')), 'u': round(sum(r.get('u', 0) or 0 for r in rs), 2)}
