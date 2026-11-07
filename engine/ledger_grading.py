"""Grading the prediction ledger (engine/ledger.py) from final scores and weekly stats.

A ledger row holds the chance of one side only (over, yes, home), so each row is graded for that side, whichever side
the model leaned: 'W' means the over/yes/home side won, 'L' that it lost, 'P' a push, 'V' void (the player didn't
play). The other side's result is the mirror image (W and L swap; P and V stay). The result is keyed by the row id,
so the same line seen at several refreshes is graded once. Grading reuses engine.grading.grade_pick, so a ledger row
and an official pick at the same line always get the same result.

FINALS, LOGS and LOGMAX are the same as in engine.grading (build.py builds them from nflverse scores and data.json LOG).
"""
from engine.grading import grade_pick

HOME_GAME_SIDE = {'spread': 'hs', 'total': 'ov', 'ml': 'mh'}   # the side whose chance a game row holds (ledger HOME_SIDES)
FLIP = {'W': 'L', 'L': 'W', 'P': 'P', 'V': 'V'}


def _rec(row):
    """The pick-shaped record for the side ROW holds, or None for a row grade_pick can't handle."""
    if row.get('wk') is None: return None
    if row['k'] == 'g':
        sd = HOME_GAME_SIDE.get(row['mk'])
        if sd is None: return None
        return {'k': 'g', 'wk': row['wk'], 'a': row['a'], 'h': row['h'], 'mk': row['mk'], 'sd': sd, 'pt': row['pt']}
    return {'k': 'p', 'wk': row['wk'], 'tm': row['tm'], 'gid': row['gid'], 'mk': row['mk'],
            'sd': 'y' if row['mk'] == 'Anytime TD' else 'o', 'pt': row['pt']}


def grade_row(row, finals, logs, logmax):
    """The result for ROW's held side: {'res': 'W'|'L'|'P'|'V'} plus 'fin' [away, home] (games) or 'val' (the player's
    stat; props), or None while the score or that week's stats aren't in yet."""
    rec = _rec(row)
    if rec is None: return None
    grade_pick(rec, finals, logs, logmax)
    if rec.get('res') is None: return None
    out = {'res': rec['res']}
    if 'fin' in rec: out['fin'] = rec['fin']
    if 'val' in rec: out['val'] = rec['val']
    return out


def grade_rows(rows, finals, logs, logmax, done=None):
    """Results for every row in ROWS that can be graded now: {row id: result}. Rows whose id is already in DONE (an
    earlier results dict) are left alone, and rows sharing an id are graded once."""
    out = {}
    for row in rows:
        rid = row['id']
        if rid in out or (done and rid in done): continue
        res = grade_row(row, finals, logs, logmax)
        if res is not None: out[rid] = res
    return out


def side_result(res, side_is_held):
    """The result 'W'|'L'|'P'|'V' of a side given the held side's result RES; SIDE_IS_HELD False reads the other side."""
    return res if side_is_held else FLIP[res]
