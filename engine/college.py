"""The college "best number" rule, shared by the live picks (build.py) and the backtest that reports its record.

With COLLEGE_MIN_BOOKS+ books posting a spread, the one book whose spread is furthest from the median of the other books
is the candidate; it is a pick when that gap is COLLEGE_GAP_MIN up to (not including) COLLEGE_GAP_MAX points. One bet per
game. The thresholds are in engine/rules.py, so changing COLLEGE_GAP_MIN, COLLEGE_GAP_MAX, COLLEGE_GAP_STRONG or
COLLEGE_MIN_BOOKS changes both the picks and the record this module derives.

The record's basis is narrower than the live picks': only the CollegeFootballData books (CFBD_BOOKS), at their saved
(closing) lines, with no price filter because those lines carry no price (about -110 is assumed). COLLEGE_MIN_PRICE
and the Odds API books therefore change the picks but not the record, and neither does COLLEGE_EXCLUDED_BOOKS while it
lists only books outside CFBD_BOOKS (today just Pinnacle).
"""
import statistics

from engine.rules import (COLLEGE_EXCLUDED_BOOKS, COLLEGE_GAP_MAX, COLLEGE_GAP_MIN, COLLEGE_GAP_STRONG, COLLEGE_MIN_BOOKS)

BACKTEST_SEASONS = (2023, 2024, 2025)   # the seasons the record is counted over (earlier ones have too few books posting)
# A season's saved files are complete enough when this many finished FBS games have lines from COVERAGE_BOOKS+ books. This
# is a property of the inputs, not of the rule (a stricter rule makes fewer bets from the same files). Real seasons have 684-732.
COVERAGE_BOOKS = 3
MIN_COVERED_GAMES = 500

# CollegeFootballData provider name -> the book name the page uses (providers not listed are ignored)
CFBD_BOOKS = {'DraftKings': 'DraftKings', 'ESPN Bet': 'ESPN BET', 'Bovada': 'Bovada', 'William Hill (New Jersey)': 'Caesars',
              'Caesars Sportsbook (Colorado)': 'Caesars'}


def best_number(books):
    """The book furthest from the others: (gap, book, its home spread), or None. books is {book: [home spread, ...]};
    the gap is that spread minus the median of the other books' spreads (positive: the book is better for the home side).
    A book in COLLEGE_EXCLUDED_BOOKS never supplies the number but its spread counts in the median. Ties go to the book
    listed first."""
    best = None
    for bn, v in books.items():
        if v[0] is None or bn in COLLEGE_EXCLUDED_BOOKS: continue
        others = [w[0] for b2, w in books.items() if b2 != bn and w[0] is not None]
        if not others: continue
        d = v[0] - statistics.median(others)
        if best is None or abs(d) > abs(best[0]): best = (d, bn, v[0])
    return best


def books_from_lines(lines):
    """{book: [home spread, total, home ML, away ML, opening spread]} from one CollegeFootballData game's lines
    (cfb/lines_<year>.json, ['lines']), as build.py reads them: only CFBD_BOOKS, a later provider with the same book name wins."""
    books = {}
    for l in lines:
        if l['provider'] in CFBD_BOOKS:
            books[CFBD_BOOKS[l['provider']]] = [l.get('spread'), l.get('overUnder'), l.get('homeMoneyline'), l.get('awayMoneyline'), l.get('spreadOpen')]
    return books


def backtest(games, lines):
    """What the rule above would have done on finished games: {'record': [w, l], 'l2': [w, l], 'l1': [w, l], 'push': n, 'covered': n}.
    covered is how many of the games had lines from COVERAGE_BOOKS+ books, whatever the rule chose (the completeness check).
    games: cfb/games_<year>.json rows (both teams FBS, completed, with points are used); lines: cfb/lines_<year>.json rows.
    l2 is gaps of COLLEGE_GAP_STRONG or more, l1 the smaller gaps. Closing lines, no price filter (the lines carry no price);
    pushes are counted apart. The caller adds up seasons."""
    by_id = {x['id']: x for x in lines}
    out = {'l2': [0, 0], 'l1': [0, 0], 'push': 0, 'covered': 0}
    for g in games:
        if not (g['homeClassification'] == 'fbs' and g['awayClassification'] == 'fbs' and g['completed']
                and g['homePoints'] is not None and g['awayPoints'] is not None):
            continue
        books = books_from_lines((by_id.get(g['id']) or {}).get('lines') or [])
        posted = sum(v[0] is not None for v in books.values())
        if posted >= COVERAGE_BOOKS: out['covered'] += 1
        if posted < COLLEGE_MIN_BOOKS: continue
        best = best_number(books)
        if best is None or not COLLEGE_GAP_MIN <= abs(best[0]) < COLLEGE_GAP_MAX: continue
        d, _, s0 = best
        cover = (g['homePoints'] - g['awayPoints'] + s0) if d > 0 else (g['awayPoints'] - g['homePoints'] - s0)
        if cover == 0: out['push'] += 1; continue
        out['l2' if abs(d) >= COLLEGE_GAP_STRONG else 'l1'][0 if cover > 0 else 1] += 1
    out['record'] = [out['l2'][0] + out['l1'][0], out['l2'][1] + out['l1'][1]]
    return out


def backtest_seasons(read, seasons=BACKTEST_SEASONS):
    """CFB.BT for data.json: the rule in words and the record over SEASONS, derived from the saved games and lines.
    read(kind, year) returns the parsed cfb/<kind>_<year>.json ('games' or 'lines'). by_season is the level II (big gap)
    record of each season, as the page has always shown it."""
    per = {y: backtest(read('games', y), read('lines', y)) for y in seasons}
    for y, r in per.items():
        if r['covered'] < MIN_COVERED_GAMES:
            raise ValueError('college backtest %d: only %d finished games have lines from %d+ books in cfb/games_%d.json and '
                             'cfb/lines_%d.json (expected at least %d); the saved files look incomplete'
                             % (y, r['covered'], COVERAGE_BOOKS, y, y, MIN_COVERED_GAMES))
    tot = lambda k: [sum(r[k][0] for r in per.values()), sum(r[k][1] for r in per.values())]
    return {'rule': 'with %d+ books, one book %g to %g points off the others' % (COLLEGE_MIN_BOOKS, COLLEGE_GAP_MIN, COLLEGE_GAP_MAX),
            'record': [tot('l2')[0] + tot('l1')[0], tot('l2')[1] + tot('l1')[1]], 'l2': tot('l2'), 'l1': tot('l1'),
            'seasons': '%d-%02d' % (seasons[0], seasons[-1] % 100),
            'by_season': {str(y): '%d-%d' % tuple(per[y]['l2']) for y in seasons},
            'model_vs_close': 'about 50% (context only)'}
