"""The built page must keep showing the same text in every view.

Replays the golden build (tests/golden/runner.py), serves the result from a local http.server, opens it in headless
Chromium (Playwright) with the clock frozen at the golden run's `now`, visits every view listed in
tests/golden/page_views.py and compares each view's text with tests/golden/expected_page.json.gz.

Nothing leaves the machine: requests to other hosts are blocked. The Sleeper league API is answered by a small mock
built from the golden data (so "My league" and "Start / sit -> My team" have content), the ESPN news call and Google
Fonts get empty answers.

A change that is meant to change what the page shows is accepted by re-blessing and committing the new file:
    python tests/test_page.py --bless
"""
import functools, gzip, http.server, json, os, subprocess, sys, tempfile, threading, time
from urllib.parse import urlparse

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, 'golden'))
import page_views  # noqa: E402

RUNNER = os.path.join(HERE, 'golden', 'runner.py')
EXPECTED = os.path.join(HERE, 'golden', 'expected_page.json.gz')
NOW = json.load(open(os.path.join(HERE, 'golden', 'fixtures', 'meta.json')))['now']
PAYLOAD = '<img src=x onerror="window.__x=1">'
CARD_MARK = ' ||player card|| '
PIXEL = bytes.fromhex('47494638396101000100800000000000ffffff21f90401000000002c00000000010001000002024401003b')


# ---------------------------------------------------------------- site: golden build served over http

def replay(workdir):
    """Runs the golden build into workdir (data.json, index.html, ...)."""
    env = dict(os.environ, PYTHONHASHSEED='0', PYTHONUTF8='1')
    r = subprocess.run([sys.executable, RUNNER, 'replay', str(workdir)], env=env, capture_output=True, text=True)
    assert r.returncode == 0, r.stdout[-3000:] + r.stderr[-3000:]


class Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a): pass


def serve(directory):
    """Serves directory on a free local port in a thread. Returns (url, server)."""
    srv = http.server.ThreadingHTTPServer(('127.0.0.1', 0), functools.partial(Quiet, directory=str(directory)))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return 'http://127.0.0.1:%d/' % srv.server_address[1], srv


def variant(base, name, edit):
    """Copy of the built site whose data.json went through edit(data). Returns its directory."""
    out = os.path.join(os.path.dirname(str(base)), name)
    os.makedirs(out, exist_ok=True)
    for f in os.listdir(base):
        if f != 'data.json' and os.path.isfile(os.path.join(base, f)):
            with open(os.path.join(base, f), 'rb') as a, open(os.path.join(out, f), 'wb') as b: b.write(a.read())
    data = json.load(open(os.path.join(base, 'data.json'), encoding='utf-8'))
    edit(data)
    with open(os.path.join(out, 'data.json'), 'w', encoding='utf-8') as f: json.dump(data, f, separators=(',', ':'), ensure_ascii=False)
    return out


def with_college(data):
    """The golden build has no CFBD key, so D.CF is null. Adds a few made-up prospects so the Fantasy -> College views
    have something to show (and a name that can be injected into)."""
    def row(name, pos, school, conf, cls, stars, elig, grade, cons, ppg):
        r = [None] * 41
        r[0:6] = [name, pos, school, conf, cls, stars]; r[6] = 12; r[8:11] = [18.5, .21, 33.2]; r[11] = elig
        r[14] = 1840; r[15] = 14; r[19] = 220; r[20] = 3; r[23] = 640; r[24] = 5
        r[28] = 75; r[29] = 215; r[30] = 71.4; r[31] = grade; r[32] = 188.4; r[33] = 160.1; r[34] = 9
        if cons: r[35:40] = [cons, cons + .5, 3, cons - 1, cons + 4]
        return r
    data['CF'] = {'P': [row('Sample Prospect A', 'WR', 'Ohio State', 'Big Ten', 3, 5, True, 'A+', 4, 1),
                        row('Sample Prospect B', 'QB', 'Texas', 'SEC', 4, 4, True, 'A', 9, 1),
                        row('Sample Prospect C', 'RB', 'Tulane', 'American', 4, 3, True, 'B', None, 1),
                        row('Sample Underclassman D', 'WR', 'Alabama', 'SEC', 2, 4, False, 'A-', None, 1),
                        row('Sample Underclassman E', 'TE', 'Oregon', 'Big Ten', 1, 3, False, 'B+', None, 1)],
                   'draft': 2027, 'tg': True,
                   'CB': {'P': [[4, 'Sample Prospect A', 'WR', 'Ohio State', 4.5, 3, 3, 8, 3, 4, 8],
                                [9, 'Sample Prospect B', 'QB', 'Texas', 9.5, 3, 8, 12, 8, 9, 12]],
                          'S': [['Sample Board 1', 'https://example.invalid/b1', '2026-10-01', 32],
                                ['Sample Board 2', 'https://example.invalid/b2', '2026-10-15', 50],
                                ['Sample Board 3', 'https://example.invalid/b3', '2026-10-20', 40]]}}


def sleeper_mock(data):
    """Answers for the Sleeper calls the page makes, as {path after /v1/: json}. One four-team dynasty league made of
    the golden data's own players (dealt out in order of dynasty value), team 1 belongs to SLEEPER_USER."""
    L = data['DY']['L']
    pool = sorted((k for k, x in L.items() if x[1] in ('QB', 'RB', 'WR', 'TE') and (x[8] or 0) >= 3), key=lambda k: (-(L[k][4] or 0), k))[:64]
    rosters = [[] for _ in range(4)]
    for i, k in enumerate(pool):
        rnd, pos = divmod(i, 4)
        rosters[pos if rnd % 2 == 0 else 3 - pos].append(k)
    users = [{'user_id': 'u%d' % i, 'display_name': 'Owner %d' % i, 'metadata': {'team_name': 'Mock Team %d' % i}} for i in range(1, 5)]
    league = {'league_id': 'L1', 'name': 'Mock Dynasty League', 'season': '2026', 'settings': {'type': 2, 'draft_rounds': 4},
              'roster_positions': ['QB', 'RB', 'RB', 'WR', 'WR', 'TE', 'FLEX', 'SUPER_FLEX', 'BN', 'BN', 'BN', 'BN'],
              'scoring_settings': {'rec': 1}}
    ros = [{'roster_id': i + 1, 'owner_id': 'u%d' % (i + 1), 'players': r, 'starters': r[:8], 'reserve': None, 'taxi': None,
            'settings': {'wins': 5 - i, 'losses': 2 + i, 'fpts': 900 - 30 * i, 'fpts_decimal': 40}} for i, r in enumerate(rosters)]
    return {'user/' + page_views.SLEEPER_USER: {'user_id': 'u1', 'username': page_views.SLEEPER_USER, 'display_name': 'Owner 1'},
            'state/nfl': {'season': '2026', 'league_season': '2026'},
            'user/u1/leagues/nfl/2026': [{'league_id': 'L1', 'name': league['name'], 'settings': league['settings']}],
            'league/L1': league, 'league/L1/rosters': ros, 'league/L1/users': users, 'league/L1/traded_picks': []}


# ---------------------------------------------------------------- browser

def new_page(browser, base_url, mock):
    """A fresh browser context (empty localStorage) on a page that cannot reach the internet. Returns (page, log)."""
    ctx = browser.new_context(viewport={'width': 1280, 'height': 900}, locale='en-US', timezone_id='UTC')
    log = {'errors': [], 'blocked': [], 'ctx': ctx}

    def route(r):
        u = urlparse(r.request.url)
        if u.hostname == '127.0.0.1': return r.continue_()
        if u.hostname == 'api.sleeper.app':
            key = u.path.split('/v1/', 1)[1]
            if key in mock: return r.fulfill(json=mock[key])
            return r.fulfill(status=404, json={})
        if u.hostname == 'fonts.googleapis.com': return r.fulfill(body='', content_type='text/css')
        if u.hostname == 'site.web.api.espn.com': return r.fulfill(json={})
        if r.request.resource_type == 'image': return r.fulfill(body=PIXEL, content_type='image/gif')  # headshots
        log['blocked'].append(r.request.url); r.abort()
    ctx.route('**/*', route)
    page = ctx.new_page()
    page.set_default_timeout(10000)
    page.on('console', lambda m: log['errors'].append('console: ' + m.text) if m.type == 'error' else None)
    page.on('pageerror', lambda e: log['errors'].append('pageerror: %s' % e))
    page.clock.set_fixed_time(NOW)
    return page, log


def settle(page):
    """Lets the page's own async work (fetches, the MutationObserver that colors tables) finish."""
    page.evaluate('new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r)))')
    page.wait_for_timeout(120)


def do(page, action):
    if isinstance(action, str): page.locator(action).first.click()
    elif action[0] == 'select': page.locator(action[1]).first.select_option(action[2])
    elif action[0] == 'fill': page.locator(action[1]).first.fill(action[2])
    elif action[0] == 'wait': page.wait_for_selector(action[1], state='attached', timeout=10000)
    else: raise ValueError(action)


def page_text(page):
    """The text of <main> (plus the player card when it is open), whitespace collapsed."""
    t = page.evaluate("document.querySelector('main').innerText")
    if page.evaluate("!document.getElementById('pc').hidden"):
        t += CARD_MARK + page.evaluate("document.getElementById('pc').innerText")
    return ' '.join(t.split())


def open_view(browser, url, mock, actions):
    page, log = new_page(browser, url, mock)
    page.goto(url + 'index.html', wait_until='load')
    page.wait_for_selector('#ld[hidden]', state='attached', timeout=20000)
    for a in actions: do(page, a)
    settle(page)
    return page, log


def visit_all(browser, url, mock, check=None):
    """Visits every view on its own fresh page. Returns ({view: text}, {view: [console errors]}); check(page) runs on each."""
    texts, errors = {}, {}
    for name, actions in page_views.VIEWS:
        t0 = time.time()
        page, log = open_view(browser, url, mock, actions)
        if os.environ.get('PAGE_TIMING'): print('%6.2fs %s' % (time.time() - t0, name), flush=True)
        try:
            texts[name] = page_text(page)
            if log['errors']: errors[name] = log['errors']
            if check: check(name, page)
        finally:
            log['ctx'].close()
    return texts, errors


# ---------------------------------------------------------------- fixtures

@pytest.fixture(scope='module')
def built(tmp_path_factory):
    base = tmp_path_factory.mktemp('page') / 'site'
    replay(base)
    return base


@pytest.fixture(scope='module')
def site(built, tmp_path_factory):
    """URL of the golden build (plus the made-up college prospects) served locally."""
    d = variant(built, 'site_college', with_college)
    url, srv = serve(d)
    yield url
    srv.shutdown()


@pytest.fixture(scope='module')
def browser():
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        b = p.chromium.launch()
        yield b
        b.close()


def site_data(directory):
    return json.load(open(os.path.join(directory, 'data.json'), encoding='utf-8'))


# ---------------------------------------------------------------- tests

def test_views_match_snapshot(site, browser, built):
    mock = sleeper_mock(site_data(os.path.join(os.path.dirname(str(built)), 'site_college')))
    got, errors = visit_all(browser, site, mock)
    assert not errors, 'console errors:\n' + '\n'.join('%s: %s' % (k, v[:3]) for k, v in list(errors.items())[:10])
    exp = json.load(gzip.open(EXPECTED, 'rt', encoding='utf-8'))
    problems = ['missing from the snapshot: ' + n for n in got if n not in exp] + ['not visited any more: ' + n for n in exp if n not in got]
    for n in got:
        if n in exp and exp[n] != got[n]:
            a, b = exp[n], got[n]
            i = next((i for i in range(min(len(a), len(b))) if a[i] != b[i]), min(len(a), len(b)))
            problems.append('%s differs at char %d:\n    expected ...%r\n    got      ...%r' % (n, i, a[max(0, i - 60):i + 100], b[max(0, i - 60):i + 100]))
    assert not problems, '%d of %d views differ from the snapshot (re-bless with: python tests/test_page.py --bless):\n%s' % (
        len(problems), len(got), '\n'.join(problems[:10]))


def test_empty_week(built, browser, tmp_path_factory):
    def edit(d):
        d['G'] = []; d['ODD']['G'] = []; d['META']['health']['schedule'] = 'failed: x'
    url, srv = serve(variant(built, 'site_empty', edit))
    try:
        mock = {}
        startsit = [page_views.FAN, page_views.fan('s'), '#fsm [data-m="all"]']
        for actions in ([], startsit, [page_views.BET, page_views.bet('games')], [page_views.tab('n')]):
            page, log = open_view(browser, url, mock, actions)
            try:
                assert not log['errors'], log['errors']
                assert page.is_visible('#hl')
                assert 'this week’s games' in page.inner_text('#hl')
                if actions == startsit:
                    assert 'No upcoming games or matchup data right now' in page.inner_text('main')
            finally:
                log['ctx'].close()
    finally:
        srv.shutdown()


@pytest.mark.xfail(strict=True, reason='Task 5')
def test_feed_names_are_escaped(built, browser):
    def edit(d):
        with_college(d)
        d['ODD']['P'][0]['n'] = PAYLOAD
        d['CF']['P'][0][0] = PAYLOAD
        mine = sleeper_mock(d)['league/L1/rosters'][0]['players']
        d['DY']['L'][mine[0]][0] = PAYLOAD
    out = variant(built, 'site_escape', edit)
    url, srv = serve(out)
    try:
        hits = []
        def check(name, page):
            if page.evaluate('window.__x') is not None: hits.append(name)
        visit_all(browser, url, sleeper_mock(site_data(out)), check)
        assert not hits, 'feed names reached the DOM as markup in: ' + ', '.join(hits)
    finally:
        srv.shutdown()


# ---------------------------------------------------------------- python tests/test_page.py --bless

def bless():
    from playwright.sync_api import sync_playwright
    with tempfile.TemporaryDirectory() as tmp:
        base = os.path.join(tmp, 'site'); replay(base)
        out = variant(base, 'site_college', with_college)
        url, srv = serve(out)
        try:
            with sync_playwright() as p:
                b = p.chromium.launch()
                texts, errors = visit_all(b, url, sleeper_mock(site_data(out)))
                b.close()
        finally:
            srv.shutdown()
    assert not errors, 'console errors, not blessing: %r' % errors
    with open(EXPECTED, 'wb') as f:
        f.write(gzip.compress(json.dumps(texts, indent=0, sort_keys=True, ensure_ascii=False).encode('utf-8'), 9, mtime=0))
    print('saved %s (%d views)' % (EXPECTED, len(texts)))


if __name__ == '__main__':
    if sys.argv[1:] == ['--bless']: bless()
    else: sys.exit('usage: python tests/test_page.py --bless')
