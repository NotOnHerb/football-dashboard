"""The Picks view shows the build's picks: ODD.PK for "best available", ODD.PKB[book] for one sportsbook.

The page no longer chooses picks; it lists the ids in ODD.PK / ODD.PKB in their order, drops games that have started,
and renders each card from its ODD.G / ODD.P row. This test serves richer data (test_page.py's with_rich_week: three
games, many prop picks; plus two seeded nudges of every book's lines and prices so each book has its own best sides),
with PK and PKB recomputed for that data by the engine (tests/golden/pick_data.py), and for "best available" and every
sportsbook reads the pick cards the page renders (their saved-bet ids, player names, levels and the line, price and
book each card offers to save), with and without "Show all", and compares them with PK / PKB as the page caps them: the
pick of the week, then up to 6 game and 9 prop picks (30 and 60 with "Show all").
A second check edits ODD.PK and one book's ODD.PKB in the page (reversed, plus a started pick and ids missing from the
week's lines) and expects the cards to follow them, so the page cannot pass by computing the same picks on its own;
with no pick list at all the view says so.
Needs Chromium via Playwright, like test_page.py (helpers are imported from it).
"""
import copy, datetime, json, os, random, sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, 'golden'))
import test_page as tp  # noqa: E402
from pick_data import golden_now, recompute_picks  # noqa: E402

SEEDS = (0, 1, 2)   # 0 = with_rich_week as it is; the others nudge lines and prices with that seed
CAPS = {False: (6, 9), True: (30, 60)}   # game and prop cards after the pick of the week, without / with "Show all"

# The pick cards the Picks view renders for BOOK (with "Show all" when MORE), in page order:
# [saved-bet id, player name or null, card class, line, price, book]. The quote is the bet each card's save button saves,
# caught as the cards render (BETREG is keyed by bet id, which cloned test players share, so it can't be read after).
SHOWN = """([book, more]) => { BS.book = book; BS.v = 'picks'; BS.more = more;
  const saved = [], orig = saveBtn; saveBtn = (b, small) => { if (!small) saved.push(b); return orig(b, small); };
  try { renderB(); } finally { saveBtn = orig; }
  return [...document.querySelectorAll('#bo .bc .sv2[data-bet]')].map((b, i) => { const c = b.closest('.bc'), n = c.querySelector('a.pn'), q = saved[i];
    return [b.dataset.bet, n ? n.dataset.n : null, c.className, q.id === b.dataset.bet ? q.pt : 'not this card', q.pr, q.bk]; }); }"""


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


def started(iso):
    return datetime.datetime.fromisoformat(iso.replace('Z', '+00:00')) <= golden_now()


def expected(pk, more):
    """The cards the Picks view should show for pick list PK, as SHOWN returns them."""
    L = [x for x in pk if not started(x['t'])]
    if not L: return []
    ng, np_ = CAPS[more]
    shown = [L[0]] + [x for x in L[1:] if x['k'] == 'g'][:ng] + [x for x in L[1:] if x['k'] == 'p'][:np_]
    return [[x['id'], x.get('n'), 'bc l%d%s' % (min(3, x['s']), ' hero' if i == 0 else ''), x['pt'], x['pr'], x['bk']]
            for i, x in enumerate(shown)]


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


def open_site(browser, built, name, edit):
    """Serves a variant of the build made by edit(data) and opens its page. Returns (data, page, log, warnings, server)."""
    site = tp.variant(built, name, edit)
    data = json.load(open(os.path.join(site, 'data.json'), encoding='utf-8'))
    url, srv = tp.serve(site)
    page, log = tp.new_page(browser, tp.mocks_for(data))
    warns = []
    page.on('console', lambda m: warns.append(m.text) if m.type == 'warning' else None)
    page.goto(url + 'index.html', wait_until='load')
    page.wait_for_selector('#ld[hidden]', state='attached', timeout=20000)
    return data, page, log, warns, srv


def rich(seed):
    """An edit: with_rich_week, then (seed > 0) nudged lines and prices, with PK / PKB recomputed for them."""
    def edit(data):
        tp.with_rich_week(data)
        if seed:
            nudge(data['ODD'], random.Random(seed))
            data['ODD']['PK'], data['ODD']['PKB'] = recompute_picks(data)
    return edit


def test_page_shows_build_picks(browser, built):
    games = props = picks = 0
    for seed in SEEDS:
        data, page, log, warns, srv = open_site(browser, built, 'pkb_seed%d' % seed, rich(seed))
        try:
            O = data['ODD']
            assert (O['PK'], O['PKB']) == recompute_picks(data), 'seed %d: the served PK / PKB are stale' % seed
            for name, want in [('best', O['PK'])] + [(b, O['PKB'][b]) for b in O['books']]:
                for more in (False, True):
                    got = page.evaluate(SHOWN, [name, more])
                    assert got == expected(want, more), 'seed %d, %s, show all %s: cards differ from the build\'s picks' % (seed, name, more)
                picks += len(want); games += sum(x['k'] == 'g' for x in want); props += sum(x['k'] == 'p' for x in want)
            assert not log['errors'], log['errors']
            assert not warns, 'seed %d: %s' % (seed, warns[:5])   # every card found its row and quotes the pick's line, price and book
        finally:
            page.context.close(); srv.shutdown()
    # not vacuous: both kinds of pick, and more than the 6 + 9 the Picks view shows before "Show all"
    assert games > 20 and props > 50 and picks > 100, (games, props, picks)


def test_page_follows_edited_picks(browser, built):
    """Cards follow ODD.PK and ODD.PKB[book] as given: their order, minus started games and ids not in this week's
    lines (each skipped with a console warning, and nothing else breaks). Without a pick list the view says so."""
    data, page, log, warns, srv = open_site(browser, built, 'pkb_edited', rich(1))
    try:
        O = data['ODD']; PK = O['PK']
        assert any(x['k'] == 'g' for x in PK) and sum(x['k'] == 'p' for x in PK) > 10   # more props than "Show all" hides
        book = max(O['books'], key=lambda b: len(O['PKB'][b])); PB = O['PKB'][book]
        assert len(PB) > 2 and PB != PB[::-1]
        def edit(L):
            g0 = next(x for x in L if x['k'] == 'g'); p0 = next(x for x in L if x['k'] == 'p')
            gone_g = dict(copy.deepcopy(g0), id='g|nope|spread|hs', eid='nope')
            gone_p = dict(copy.deepcopy(p0), id='p|nope|00-0000000|Rec yds|o', eid='nope', gid='00-0000000')
            old = dict(copy.deepcopy(p0), t='2026-11-01T17:00:00Z')   # kicked off before the golden clock
            return [gone_g, old] + L[::-1] + [gone_p]
        page.evaluate('([pk, book, pb]) => { D.ODD.PK = pk; D.ODD.PKB[book] = pb }', [edit(PK), book, edit(PB)])
        for name, L in (('best', PK), (book, PB)):
            for more in (False, True):
                got = page.evaluate(SHOWN, [name, more])
                assert got == expected(L[::-1], more), '%s, show all %s: cards do not follow the edited pick list' % (name, more)
        assert sum('nope' in w for w in warns) == 8, warns   # four renders, two missing ids each
        assert len(warns) == 8, warns
        page.evaluate('book => { D.ODD.PK = null; delete D.ODD.PKB[book] }', book)
        for name in ('best', book):
            assert page.evaluate(SHOWN, [name, False]) == []
            assert 'Picks aren’t available in this update' in page.inner_text('#bo'), name
        assert sum('No pick list' in w for w in warns) == 2, warns
        assert not log['errors'], log['errors']
    finally:
        page.context.close(); srv.shutdown()
