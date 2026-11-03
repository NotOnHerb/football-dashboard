"""ODD.PK / ODD.PKB (the engine's picks) must be the picks the page computes for itself, in the same order.

tests/test_engine/test_picks.py::test_pkb_matches_page checks the golden data's page snapshot, but the golden clock leaves
one pick, so ordering and the per-view caps are not exercised there. This test serves richer data (test_page.py's
with_rich_week: three games, many prop picks; plus two seeded nudges of every book's lines and prices so each book has
its own best sides), recomputes PK and PKB for it with the engine (tests/golden/pick_data.py), then asks the page's own
picks() for every sportsbook view and for "best available" and compares pick ids, lines, prices, books, scores and order.
Needs Chromium via Playwright, like test_page.py (helpers are imported from it; nothing in it is edited).
"""
import json, os, random, sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, 'golden'))
import test_page as tp  # noqa: E402
from pick_data import recompute_picks  # noqa: E402

SEEDS = (0, 1, 2)   # 0 = with_rich_week as it is; the others nudge lines and prices with that seed

# The page's own picks(), as plain rows: the pick id the build would write, its quote and its score, in the page's order.
PAGE_PICKS = """(book) => { BS.book = book; return picks().map(c => c.t === 'g'
    ? {id: 'g|' + c.g.id + '|' + gmk(c.x.k) + '|' + c.x.k, pt: c.x.q.pt, pr: c.x.q.pr, bk: c.x.q.bk, s: c.s}
    : {id: 'p|' + c.p.eid + '|' + c.p.gid + '|' + c.p.mk + '|' + (c.x.td ? 'y' : c.x.b.dir > 0 ? 'o' : 'u'),
       pt: c.x.b.q.pt, pr: c.x.b.q.pr, bk: c.x.b.q.bk, s: c.s}); }"""


def nudge(O, rnd):
    """Randomly moves each book's lines and prices a little and drops some books from some props (ODD.G / ODD.P in place)."""
    def pr(x): return x if x is None or abs(x) <= 60 else x + rnd.choice([-12, -8, -4, 0, 0, 4, 8, 12, 25, 40])
    for g in O['G']:
        for m in g['b'].values():
            if 's' in m:
                d = rnd.choice([0, 0, .5, -.5, 1]); m['s'] = [m['s'][0] + d, pr(m['s'][1]), m['s'][2] - d, pr(m['s'][3])]
            if 'o' in m:
                d = rnd.choice([0, 0, .5, -.5, 1, -1]); m['o'] = [m['o'][0] + d, pr(m['o'][1]), pr(m['o'][2])]
            if 'm' in m: m['m'] = [pr(m['m'][0]), pr(m['m'][1])]
    for p in O['P']:
        for x in p['b'].values():
            d = rnd.choice([0, 0, 0, 1, -1, 2.5, -2.5, 5, -5])
            if x[0] is not None: x[0] += d
            if x[2] is not None: x[2] += d
            x[1] = pr(x[1]); x[3] = pr(x[3])
        for bn in list(p['b']):
            if rnd.random() < .15 and len(p['b']) > 2: del p['b'][bn]


@pytest.fixture(scope='module')
def browser():
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        b = p.chromium.launch()
        yield b
        b.close()


@pytest.fixture(scope='module')
def built(tmp_path_factory):
    base = tmp_path_factory.mktemp('pkbpage') / 'site'
    tp.replay(base)
    return base


def test_page_picks_match_engine_picks(browser, built):
    games = props = picks = 0
    for seed in SEEDS:
        def edit(data, seed=seed):
            tp.with_rich_week(data)
            if seed: nudge(data['ODD'], random.Random(seed))
        site = tp.variant(built, 'pkb_seed%d' % seed, edit)
        data = json.load(open(os.path.join(site, 'data.json'), encoding='utf-8'))
        PK, PKB = recompute_picks(data)
        url, srv = tp.serve(site)
        page, log = tp.new_page(browser, tp.mocks_for(data))
        try:
            page.goto(url + 'index.html', wait_until='load')
            page.wait_for_selector('#ld[hidden]', state='attached', timeout=20000)
            for name, want in [('best', PK)] + [(b, PKB[b]) for b in data['ODD']['books']]:
                got = page.evaluate(PAGE_PICKS, name)
                rows = lambda L: [(x['id'], x['pt'], x['pr'], x['bk'], x['s']) for x in L]
                assert rows(got) == rows(want), 'seed %d, %s: page picks differ from the engine\'s' % (seed, name)
                picks += len(want); games += sum(x['k'] == 'g' for x in want); props += sum(x['k'] == 'p' for x in want)
        finally:
            page.context.close(); srv.shutdown()
    # not vacuous: both kinds of pick, and more than the 6 + 9 the Picks view shows before "Show all"
    assert games > 20 and props > 50 and picks > 100, (games, props, picks)
