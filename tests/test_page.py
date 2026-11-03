"""The built page must keep showing the same text in every view.

Replays the golden build (tests/golden/runner.py), serves the result from a local http.server, opens it in headless
Chromium (Playwright) with the clock frozen at the golden run's `now`, visits every view listed in
tests/golden/page_views.py and compares each view's text with tests/golden/expected_page.json.gz.

The page is served in two flavours, both made by editing the golden data.json (the golden data itself is untouched):
  * normal views: golden data plus a few made-up college prospects (the golden build has no CFBD key, so D.CF is null);
  * "rich/" views: the same plus two more NFL games, many prop picks and two college picks (the golden clock leaves
    one game and no college picks).

Nothing leaves the machine: requests to other hosts are blocked. The Sleeper and ESPN league APIs are answered by mocks
built from the golden data (so "My league" and "Start / sit -> My team" have content); the ESPN news call, Google Fonts
and images get empty answers.

A change that is meant to change what the page shows is accepted by re-blessing and committing the new file:
    python tests/test_page.py --bless
"""
import copy, functools, gzip, hashlib, http.server, json, os, re, shutil, statistics, subprocess, sys, tempfile, threading, time
from urllib.parse import urlparse

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(HERE, 'golden'))
sys.path.insert(0, ROOT)
import page_views  # noqa: E402
import runner  # noqa: E402  (tests/golden/runner.py: CODE_DIRS)
from schema.fields import FIELDS  # noqa: E402

RUNNER = os.path.join(HERE, 'golden', 'runner.py')
EXPECTED = os.path.join(HERE, 'golden', 'expected_page.json.gz')
NOW = json.load(open(os.path.join(HERE, 'golden', 'fixtures', 'meta.json')))['now']
CARD_MARK = ' ||player card|| '
PIXEL = bytes.fromhex('47494638396101000100800000000000ffffff21f90401000000002c00000000010001000002024401003b')

# Hostile feed text for the escaping test. The attribute payloads add a data-inj attribute (and an onmouseover) to
# whatever element they break out of, so a scan of the DOM shows which feed field reached the page unescaped.
IMG = '<img src=x onerror="window.__x=1">'
JS_URL = 'javascript:window.__x=1'
def attr(tag): return '" onmouseover="window.__x=1" data-inj="%s' % tag


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
    """Copy of the built site (top-level files plus the code directories the build copies) whose data.json went
    through edit(data). Returns its directory."""
    out = os.path.join(os.path.dirname(str(base)), name)
    os.makedirs(out, exist_ok=True)
    for f in os.listdir(base):
        if f != 'data.json' and os.path.isfile(os.path.join(base, f)): shutil.copy(os.path.join(base, f), os.path.join(out, f))
    for d in runner.CODE_DIRS:
        shutil.copytree(os.path.join(base, d), os.path.join(out, d), dirs_exist_ok=True)
    data = json.load(open(os.path.join(base, 'data.json'), encoding='utf-8'))
    edit(data)
    with open(os.path.join(out, 'data.json'), 'w', encoding='utf-8') as f: json.dump(data, f, separators=(',', ':'), ensure_ascii=False)
    return out


def site_data(directory):
    return json.load(open(os.path.join(directory, 'data.json'), encoding='utf-8'))


# ---------------------------------------------------------------- made-up data on top of the golden data

def prospect(name, pos, school, conf, cls, stars, hs, elig, grade, score, rank, board, **stats):
    """One CF.P row, in the order of schema.fields.FIELDS['CF.P'], computed like build.py: fantasy points from the stats;
    for a player on the consensus board (board = his CF.CB.P row) the consensus fields come from that row and the grade
    follows his rank (build.py: <=10 A+, <=25 A, <=50 A-, <=75 B+, else B)."""
    s = dict(pass_att=None, pass_pct=None, pass_yds=None, pass_td=None, pass_int=None, pass_ypa=None, rush_car=None, rush_yds=None,
             rush_td=None, rush_ypc=None, rec_rec=None, rec_yds=None, rec_td=None, rec_ypr=None, rec_yds_share=None, rush_yds_share=None)
    s.update(stats)
    z = lambda k: s[k] or 0
    ppr = z('pass_yds') * .04 + z('pass_td') * 4 - z('pass_int') * 2 + z('rush_yds') * .1 + z('rush_td') * 6 + z('rec_yds') * .1 + z('rec_td') * 6
    v = dict(name=name, pos=pos, team=school, conference=conf, class_year=cls, stars=stars, recruit_rank=rank, hs_class=hs,
             usage_pct=18, avg_ppa=.21, total_ppa=33.2, draft_eligible=elig, height=75 if pos in ('WR', 'TE', 'QB') else 71,
             weight=215 if pos != 'RB' else 205, dynasty_score=score, letter_grade=grade, ppr_total=round(ppr + z('rec_rec'), 1),
             std_total=round(ppr, 1), team_games=9, consensus_rank=None, avg_rank=None, boards=None, best_rank=None, worst_rank=None, **s)
    if board:
        r = board[0]
        v.update(consensus_rank=r, avg_rank=board[4], boards=board[5], best_rank=board[6], worst_rank=board[7],
                 letter_grade='A+' if r <= 10 else 'A' if r <= 25 else 'A-' if r <= 50 else 'B+' if r <= 75 else 'B')
    fields = FIELDS['CF.P']
    assert set(v) == set(fields), set(v) ^ set(fields)
    return [v[f] for f in fields]


def with_college(data):
    """The golden build has no CFBD key, so D.CF is null. Adds a few made-up prospects so Fantasy -> College has
    something to show (and a name that can be injected into). Rows have the 40 fields build.py writes."""
    assert len(FIELDS['CF.P']) == 40
    bp = [[4, 'Sample Prospect A', 'WR', 'Ohio State', 4.5, 3, 3, 8, 3, 4, 8],
          [9, 'Sample Prospect B', 'QB', 'Texas', 9.5, 3, 8, 12, 8, 9, 12]]  # CF.CB.P rows: ... best, worst, then one rank per board
    data['CF'] = {
        'P': [prospect('Sample Prospect A', 'WR', 'Ohio State', 'Big Ten', 3, 5, 2024, True, 'A+', 78.2, 4, bp[0], rec_rec=58, rec_yds=912, rec_td=8, rec_ypr=15.7, rec_yds_share=31),
              prospect('Sample Prospect B', 'QB', 'Texas', 'SEC', 4, 4, 2023, True, 'A+', 74.9, 9, bp[1], pass_att=262, pass_pct=66.4, pass_yds=2310, pass_td=19, pass_int=4, pass_ypa=8.8, rush_car=48, rush_yds=190, rush_td=3, rush_ypc=4.0),
              prospect('Sample Prospect C', 'RB', 'Tulane', 'American Athletic', 4, 3, 2023, True, 'B', 61.0, 120, None, rush_car=151, rush_yds=801, rush_td=9, rush_ypc=5.3, rec_rec=21, rec_yds=160, rec_td=1, rec_ypr=7.6, rush_yds_share=44),
              prospect('Sample Underclassman D', 'WR', 'Alabama', 'SEC', 2, 4, 2025, False, 'A-', 70.3, 31, None, rec_rec=41, rec_yds=588, rec_td=5, rec_ypr=14.3, rec_yds_share=24),
              prospect('Sample Underclassman E', 'TE', 'Oregon', 'Big Ten', 1, 3, 2026, False, 'B+', 64.4, 210, None, rec_rec=24, rec_yds=301, rec_td=3, rec_ypr=12.5, rec_yds_share=17)],
        'draft': 2027, 'tg': True,
        'CB': {'P': bp,
               'S': [['Sample Board 1', 'https://example.invalid/b1', '2026-10-01', 32],
                     ['Sample Board 2', 'https://example.invalid/b2', '2026-10-15', 50],
                     ['Sample Board 3', 'https://example.invalid/b3', '2026-10-20', 40]]}}


def with_rich_week(data):
    """Two more NFL games (copies of the real CHI-SEA row with other teams and kickoffs), ten more prop picks, a few more
    props in the new games, and two college picks (shaped like build.py's CFB.PK rows). For the "rich/" views.
    Cloned props keep the source player's gid and stats (only name, team, opponent and kickoff change), so they share
    his game log, injury status and hit rates."""
    O, base = data['ODD'], data['ODD']['G'][0]
    new = [('BUF', 'KC', '2026-11-08T18:00:00Z', 'Wk 8, Sun Nov 08, 1:00 PM ET', -1.0, 2.0),
           ('DAL', 'PHI', '2026-11-08T21:25:00Z', 'Wk 8, Sun Nov 08, 4:25 PM ET', 1.5, -3.0)]
    for a, h, t, label, ds, dt in new:
        g = copy.deepcopy(base)
        g.update(id=hashlib.md5((a + h).encode()).hexdigest(), a=a, h=h, t=t)
        for bk in g['b'].values():
            bk['s'][0] += ds; bk['s'][2] -= ds; bk['o'][0] += dt
        g['fair']['s'][0] += ds; g['fair']['o'][0] += dt
        O['G'].append(g); data['G'].append([a, h, label])
    G = O['G'][1:]
    lov = next(p for p in O['P'] if p['n'] == 'Colston Loveland' and p['mk'] == 'Rec yds')
    extra = []
    def put(src, name, i):
        g = G[i % 2]; flip = (i // 2) % 2
        p = copy.deepcopy(src); p.update(n=name, t=g['h'] if flip else g['a'], opp=g['a'] if flip else g['h'], ko=g['t'], eid=g['id'])
        extra.append(p)
    for i in range(10): put(lov, 'Sample Receiver %d' % (i + 1), i)
    for i, src in enumerate(O['P'][:6]): put(src, 'Sample Prop %d' % (i + 1), i)
    O['P'].extend(extra)
    # College picks the way build.py writes them (1008-1028): a game with 3+ spreads; the picked book (not Pinnacle) is
    # 1 to 3 points off the median of the others; sd 'hs' when its home spread is above that median (the better number
    # for the home side), 'as' when below; price from the book's own home (hs) or away (as) price.
    C = data['CFB']
    picks = []
    games = [g for g in C['G'] if sum(w[0] is not None for w in g['books'].values()) >= 2][:2]
    for g, (bk, off) in zip(games, (('BetMGM', 2.0), ('Caesars', -1.5))):
        first = next(w for w in g['books'].values() if w[0] is not None)
        for extra_bk in ('BetMGM', 'Caesars'):  # the golden college games have 2 books; add copies of the first so the rule has 3
            if sum(w[0] is not None for w in g['books'].values()) < 3 and extra_bk not in g['books']:
                g['books'][extra_bk] = (first + [None] * 7)[:5] + [-110, -110]
        g['books'].setdefault(bk, (first + [None] * 7)[:5] + [-110, -110])
        others = [w[0] for b, w in g['books'].items() if b != bk and w[0] is not None]
        med = statistics.median(others)
        g['books'][bk][0] = med + off
        g['sp'] = statistics.median(w[0] for w in g['books'].values() if w[0] is not None)
        sd = 'hs' if off > 0 else 'as'
        s0 = g['books'][bk][0]
        picks.append({'id': 'c|%s|%s' % (g['id'], sd), 'k': 'c', 'gid': g['id'], 'wk': g['wk'], 't': g['t'], 'a': g['a'], 'h': g['h'], 'sd': sd,
                      'pt': s0 if sd == 'hs' else -s0, 'pr': g['books'][bk][5 if sd == 'hs' else 6], 'bk': bk, 'gap': round(abs(off), 1),
                      'others': round(med if sd == 'hs' else -med, 1), 's': 2 if abs(off) >= 1.5 else 1,
                      'lines': {b: (w[0] if sd == 'hs' else -w[0]) for b, w in g['books'].items() if w[0] is not None}})
    assert len(picks) == 2
    C['PK'] = picks


def skill_pool(data):
    """Sleeper ids of QB/RB/WR/TE with games, best dynasty value first."""
    L = data['DY']['L']
    return sorted((k for k, x in L.items() if x[1] in ('QB', 'RB', 'WR', 'TE') and (x[8] or 0) >= 3), key=lambda k: (-(L[k][4] or 0), k))


def deal(pool, n_teams=4, size=16):
    """Snake-deals the first n_teams*size of pool into n_teams rosters."""
    rosters = [[] for _ in range(n_teams)]
    for i, k in enumerate(pool[:n_teams * size]):
        rnd, pos = divmod(i, n_teams)
        rosters[pos if rnd % 2 == 0 else n_teams - 1 - pos].append(k)
    return rosters


def sleeper_mock(data, inject=False):
    """Answers for the Sleeper calls the page makes, as {path after /v1/: json}. One four-team dynasty league made of
    the golden data's own players (dealt out in order of dynasty value); team 1 belongs to SLEEPER_USER."""
    rosters = deal(skill_pool(data))
    users = [{'user_id': 'u%d' % i, 'display_name': 'Owner %d' % i, 'metadata': {'team_name': 'Mock Team %d' % i}} for i in range(1, 5)]
    league = {'league_id': 'L1', 'name': 'Mock Dynasty League', 'season': '2026', 'settings': {'type': 2, 'draft_rounds': 4},
              'roster_positions': ['QB', 'RB', 'RB', 'WR', 'WR', 'TE', 'FLEX', 'SUPER_FLEX', 'BN', 'BN', 'BN', 'BN'],
              'scoring_settings': {'rec': 1}}
    if inject:
        league['name'] = attr('sleeper-league'); users[0]['metadata']['team_name'] = attr('sleeper-team'); users[2]['metadata']['team_name'] = attr('sleeper-team-2')
    ros = [{'roster_id': i + 1, 'owner_id': 'u%d' % (i + 1), 'players': r, 'starters': r[:8], 'reserve': None, 'taxi': None,
            'settings': {'wins': 5 - i, 'losses': 2 + i, 'fpts': 900 - 30 * i, 'fpts_decimal': 40}} for i, r in enumerate(rosters)]
    return {'user/' + page_views.SLEEPER_USER: {'user_id': 'u1', 'username': page_views.SLEEPER_USER, 'display_name': 'Owner 1'},
            'state/nfl': {'season': '2026', 'league_season': '2026'},
            'user/u1/leagues/nfl/2026': [{'league_id': 'L1', 'name': league['name'], 'settings': league['settings']}],
            'league/L1': league, 'league/L1/rosters': ros, 'league/L1/users': users, 'league/L1/traded_picks': []}


def espn_mock(data, inject=False):
    """The ESPN league answer: four teams from the golden data's players that have an ESPN id; team 2 is the user's
    (page_views.LOAD_ESPN types team id 2). Team 2 also rosters one player the page cannot match to its data."""
    L, E = data['DY']['L'], data['DY']['E']
    to_espn = {v: k for k, v in E.items()}
    rosters = deal([k for k in skill_pool(data) if k in to_espn])
    pid = {'QB': 1, 'RB': 2, 'WR': 3, 'TE': 4}
    slots = [0, 2, 2, 4, 4, 6, 23, 23, 23]
    names = ['ESPN Team %d' % i for i in range(1, 5)]
    league_name = 'Mock ESPN League'
    if inject: league_name = attr('espn-league'); names[2] = attr('espn-team')
    teams = []
    for i, r in enumerate(rosters):
        entries = [{'playerId': int(to_espn[k]), 'lineupSlotId': slots[j] if j < len(slots) else 20,
                    'playerPoolEntry': {'player': {'fullName': L[k][0], 'defaultPositionId': pid[L[k][1]]}}} for j, k in enumerate(r)]
        if i == 1:
            entries.append({'playerId': 999999999, 'lineupSlotId': 20, 'playerPoolEntry': {'player': {
                'fullName': IMG if inject else 'Unmatched Test Player', 'defaultPositionId': 3}}})
        teams.append({'id': i + 1, 'name': names[i], 'owners': ['m%d' % (i + 1)], 'record': {'overall': {'wins': 5 - i, 'losses': 2 + i, 'pointsFor': 900.5 - 30 * i}},
                      'roster': {'entries': entries}})
    return {'settings': {'name': league_name, 'rosterSettings': {'lineupSlotCounts': {'0': 1, '2': 2, '4': 2, '6': 1, '23': 1, '20': 6}},
                         'scoringSettings': {'scoringItems': [{'statId': 53, 'points': 1}]}},
            'members': [{'id': 'm%d' % i, 'firstName': 'Manager', 'lastName': str(i)} for i in range(1, 5)], 'teams': teams}


def mocks_for(data, inject=False):
    return {'sleeper': sleeper_mock(data, inject), 'espn': espn_mock(data, inject)}


# ---------------------------------------------------------------- browser

def new_page(browser, mocks):
    """A fresh browser context (empty localStorage) on a page that cannot reach the internet. Returns (page, log)."""
    ctx = browser.new_context(viewport={'width': 1280, 'height': 900}, locale='en-US', timezone_id='UTC')
    log = {'errors': [], 'blocked': [], 'ctx': ctx}

    def route(r):
        u = urlparse(r.request.url)
        if u.hostname == '127.0.0.1': return r.continue_()
        if u.hostname == 'api.sleeper.app':
            key = u.path.split('/v1/', 1)[1]
            if key in mocks['sleeper']: return r.fulfill(json=mocks['sleeper'][key])
            return r.fulfill(status=404, json={})
        if u.hostname == 'lm-api-reads.fantasy.espn.com':
            if u.path.rstrip('/').endswith('/leagues/' + page_views.ESPN_LEAGUE): return r.fulfill(json=mocks['espn'])
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


def open_view(browser, url, mocks, actions):
    page, log = new_page(browser, mocks)
    page.goto(url + 'index.html', wait_until='load')
    page.wait_for_selector('#ld[hidden]', state='attached', timeout=20000)
    for a in actions: do(page, a)
    settle(page)
    return page, log


def visit_all(browser, url_for, mocks, check=None):
    """Visits every view on its own fresh page (url_for(view name) says which site). Returns ({view: text},
    {view: {errors, blocked}}); check(name, page) runs on each loaded view."""
    texts, errors = {}, {}
    for name, actions in page_views.VIEWS:
        t0 = time.time()
        page, log = open_view(browser, url_for(name), mocks, actions)
        if os.environ.get('PAGE_TIMING'): print('%6.2fs %s' % (time.time() - t0, name), flush=True)
        try:
            texts[name] = page_text(page)
            if log['errors']: errors[name] = {'errors': log['errors'], 'blocked': log['blocked']}
            if check: check(name, page)
        finally:
            log['ctx'].close()
    return texts, errors


def describe_errors(errors):
    return '\n'.join('%s: %s (blocked requests: %s)' % (n, e['errors'][:3], e['blocked'][:5]) for n, e in list(errors.items())[:10])


# ---------------------------------------------------------------- did each view reach the state it was meant to show?

# Text the page shows when something went wrong or a section is empty (curly apostrophes as in template.html).
BAD_TEXT = ['Couldn’t', 'aren’t loaded', 'isn’t available', 'aren’t available', 'Odds aren’t', 'Loading', 'No players match',
            'No linemen match', 'No starters match', 'No big boards loaded', 'No upcoming games', 'No games match', 'No props match',
            'undefined', '[object']
# (view name regex, strings that view is meant to show even though they are in BAD_TEXT)
ALLOWED_BAD = [(r'^betting/college/games/picks-only$', ['No games match'])]  # golden clock: no college picks
# Views that are short on purpose (the league forms before anything is loaded).
SHORT_OK = r'/my-league/(sleeper|espn)-form$'
MIN_BODY = 300
# (view name regex, text it must contain / must not contain)
MUST = [(r'sleeper-loaded$', 'Mock Dynasty League'), (r'espn-loaded$', 'Mock ESPN League'), (r'redraft/my-league/espn-loaded$', 'Unmatched Test Player'),
        (r'start-sit/my-team$', 'Your best lineup this week'), (r'card$', CARD_MARK), (r'card$', 'Latest news'),
        (r'^rich/nfl/matchups/game-1', 'BUF at KC'), (r'^rich/nfl/matchups/game-2', 'DAL at PHI'),
        (r'^rich/betting/nfl/picks/show-all$', 'Sample Receiver 10'), (r'^rich/betting/nfl/games$', 'DAL'),
        (r'^rich/betting/nfl/props/game-', 'Sample'), (r'^rich/betting/college/picks$', 'Better number'),
        (r'^rich/betting/college/games/picks-only$', 'Pick:'), (r'^fantasy/college/(draft-prospects|breakouts|college-fantasy)$', 'Sample '),
        (r'^betting/nfl/my-bets/one-saved$', 'Colston Loveland')]
MUST_NOT = [(r'^betting/nfl/my-bets/one-saved$', 'No saved bets yet'), (r'^rich/betting/nfl/picks/show-all$', 'Show all'),
            (r'^rich/betting/nfl/picks$', 'Sample Receiver 10')]


def body_of(text):
    """The part of a view's text between the fixed header (title, scene buttons, section nav) and the footnote."""
    a = text.index('NFL Fantasy Betting ') + len('NFL Fantasy Betting ')
    b = text.find('Real stats from nflverse')
    return text[a:b if b > a else len(text)]


def check_content(texts):
    """Problems with what the views show, as a list of strings (empty when every view reached its intended state)."""
    bad = []
    for name, t in texts.items():
        body = body_of(t)
        card = t.split(CARD_MARK, 1)[1] if CARD_MARK in t else ''
        if len(body) < MIN_BODY and not re.search(SHORT_OK, name): bad.append('%s: only %d chars of section text' % (name, len(body)))
        allowed = [s for rx, ss in ALLOWED_BAD if re.search(rx, name) for s in ss]
        for s in BAD_TEXT:
            if s not in allowed and (s in body or s in card): bad.append('%s: shows %r' % (name, s))
        for rx, s in MUST:
            if re.search(rx, name) and s not in t: bad.append('%s: should show %r' % (name, s))
        for rx, s in MUST_NOT:
            if re.search(rx, name) and s in t: bad.append('%s: should not show %r' % (name, s))
    picks = {n: t for n, t in texts.items() if re.match(r'^betting/nfl/picks/(?!player-card)', n)}
    for n, t in picks.items():
        if not any(t != u for m, u in picks.items() if m != n): bad.append('%s: identical to every other picks view' % n)
    return bad


def test_content_guard_fires():
    """check_content must flag a view that shows an error, is empty, or leaks a JavaScript value."""
    text = lambda body: 'Football dashboard NFL Fantasy Betting ' + body + ' Real stats from nflverse footnote'
    fine = 'Teams Players ' * 40
    assert not check_content({'a/b': text(fine)})
    assert check_content({'a/b': text('Couldn’t reach Sleeper (x). ' + fine)})
    assert check_content({'a/b': text('')})
    assert check_content({'a/b': text(fine + ' undefined')})
    assert check_content({'a/b': text(fine + ' [object Object]')})
    assert not check_content({'betting/college/games/picks-only': text(fine + ' No games match.')})  # allowed there


# ---------------------------------------------------------------- fixtures

@pytest.fixture(scope='module')
def built(tmp_path_factory):
    base = tmp_path_factory.mktemp('page') / 'site'
    replay(base)
    return base


@pytest.fixture(scope='module')
def sites(built):
    """URLs of the two served flavours of the golden build: {'': normal, 'rich/': with the extra week}."""
    def rich(d): with_college(d); with_rich_week(d)
    a, sa = serve(variant(built, 'site_college', with_college))
    b, sb = serve(variant(built, 'site_rich', rich))
    yield {'': a, 'rich/': b}
    sa.shutdown(); sb.shutdown()


@pytest.fixture(scope='module')
def browser():
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        b = p.chromium.launch()
        yield b
        b.close()


def url_for_sites(sites):
    return lambda name: sites['rich/'] if name.startswith('rich/') else sites['']


# ---------------------------------------------------------------- tests

def test_views_match_snapshot(sites, browser, built):
    got, errors = visit_all(browser, url_for_sites(sites), mocks_for(site_data(built)))
    assert not errors, 'console errors:\n' + describe_errors(errors)
    content = check_content(got)
    assert not content, 'views not in their intended state:\n' + '\n'.join(content[:15])
    exp = json.load(gzip.open(EXPECTED, 'rt', encoding='utf-8'))
    problems = ['missing from the snapshot: ' + n for n in got if n not in exp] + ['not visited any more: ' + n for n in exp if n not in got]
    for n in got:
        if n in exp and exp[n] != got[n]:
            a, b = exp[n], got[n]
            i = next((i for i in range(min(len(a), len(b))) if a[i] != b[i]), min(len(a), len(b)))
            problems.append('%s differs at char %d:\n    expected ...%r\n    got      ...%r' % (n, i, a[max(0, i - 60):i + 100], b[max(0, i - 60):i + 100]))
    assert not problems, '%d of %d views differ from the snapshot (re-bless with: python tests/test_page.py --bless):\n%s' % (
        len(problems), len(got), '\n'.join(problems[:10]))


def test_empty_week(built, browser):
    def edit(d):
        d['G'] = []; d['ODD']['G'] = []; d['META']['health']['schedule'] = 'failed: x'
    url, srv = serve(variant(built, 'site_empty', edit))
    try:
        startsit = [page_views.FAN, page_views.fan('s'), '#fsm [data-m="all"]']
        for actions in ([], startsit, [page_views.BET, page_views.bet('games')], [page_views.tab('n')]):
            page, log = open_view(browser, url, mocks_for(site_data(built)), actions)
            try:
                assert not log['errors'], (log['errors'], log['blocked'])
                assert page.is_visible('#hl')
                assert 'this week’s games' in page.inner_text('#hl')
                if actions == startsit:
                    assert 'No upcoming games or matchup data right now' in page.inner_text('main')
            finally:
                log['ctx'].close()
    finally:
        srv.shutdown()


def test_assets_are_versioned(built):
    """Every local script and stylesheet the page loads carries the build stamp (?v=<stamp>), so a browser never mixes
    a new index.html with cached old code; every file under js/ and assets/ is loaded, and nothing loaded is missing."""
    page = open(os.path.join(built, 'index.html'), encoding='utf-8').read()
    assert '__VER__' not in page
    refs = re.findall(r'<script\b[^>]*\bsrc="([^"]+)"|<link\b[^>]*\bhref="([^"]+)"', page)
    local = [a or b for a, b in refs if not re.match(r'https?://', a or b)]
    assert any(u.startswith('js/') for u in local) and any(u.startswith('assets/') for u in local), local
    stamps, paths = set(), []
    for u in local:
        m = re.fullmatch(r'([^?#]+)\?v=(\d{12})', u)
        assert m, 'not versioned with the build stamp: ' + u
        stamps.add(m.group(2)); paths.append(m.group(1))
        assert os.path.isfile(os.path.join(built, m.group(1))), 'loaded but not shipped: ' + m.group(1)
    assert len(stamps) == 1, stamps
    assert len(paths) == len(set(paths)), 'loaded twice: %s' % paths
    shipped = {os.path.relpath(os.path.join(d, f), built).replace(os.sep, '/')
               for top in ('js', 'assets') for d, _, fs in os.walk(os.path.join(built, top)) for f in fs}
    assert shipped == set(paths), 'shipped but not loaded: %s' % sorted(shipped - set(paths))


def test_deep_link(sites, browser, built):
    """#betting/props opens Betting -> Props straight away, showing what clicking there shows; moving around rewrites
    the hash, and changing the hash moves the page."""
    exp = json.load(gzip.open(EXPECTED, 'rt', encoding='utf-8'))
    page, log = new_page(browser, mocks_for(site_data(built)))
    try:
        page.goto(sites[''] + 'index.html#betting/props', wait_until='load')
        page.wait_for_selector('#ld[hidden]', state='attached', timeout=20000)
        settle(page)
        assert page.is_visible('#sb') and page.is_visible('#bctl') and not page.is_visible('#vt')
        assert page.get_attribute(page_views.bet('props'), 'aria-pressed') == 'true'
        assert page_text(page) == exp['betting/nfl/props/best-available']
        page.locator(page_views.bet('games')).click()
        assert page.evaluate('location.hash') == '#betting/games'
        page.evaluate("location.hash = '#nfl/matchups'")
        page.wait_for_selector('#vn:not([hidden])', state='attached')
        assert page.get_attribute(page_views.NFL, 'aria-pressed') == 'true' and not page.is_visible('#sb')
        assert not log['errors'], (log['errors'], log['blocked'])
    finally:
        log['ctx'].close()


def test_broken_section_is_isolated(built, browser):
    """A section whose init throws (here Fantasy -> College, on a malformed CF block) is reported on the page and in
    the console, and every other section still loads and works."""
    def edit(d): d['CF'] = {'P': 'not a list'}
    url, srv = serve(variant(built, 'site_broken', edit))
    try:
        page, log = open_view(browser, url, mocks_for(site_data(built)), [page_views.BET])
        try:
            assert 'Fantasy → College' in page.inner_text('#hlerr')
            assert len(log['errors']) == 1 and 'Fantasy → College' in log['errors'][0], log['errors']
            assert page.is_visible('#sb') and page.locator('#bo .bc, #bo .card').count() > 0
            do(page, page_views.NFL); do(page, page_views.tab('p'))
            assert page.locator('#pt tr').count() > 50
        finally:
            log['ctx'].close()
    finally:
        srv.shutdown()


def num(x):
    """A number as JavaScript prints it (45.0 -> '45')."""
    return ('%r' % x)[:-2] if float(x).is_integer() else repr(x)


def test_saved_bets_survive(sites, browser, built):
    """A bet the old page saved under its bare localStorage key ('mybets') still shows in My bets, and every other
    setting saved under a bare key moves under the store's namespace with its value (and still takes effect)."""
    d = site_data(built)
    p = next(x for x in d['ODD']['P'] if x['n'] == 'Colston Loveland' and x['mk'] == 'Rec yds')
    bk, q = next((b, v) for b, v in sorted(p['b'].items()) if v[0] is not None and v[1] is not None)
    g = next(x for x in d['ODD']['G'] if p['t'] in (x['a'], x['h']))
    # the shape toggleBet saves: {saved, stake} + pBet(p, 'o', {pt, pr, bk})
    bet = {'saved': '2026-11-01T15:00:00.000Z', 'stake': '25', 'id': 'p|%s|%s|%s|o' % (p['eid'], p['gid'], p['mk']), 'k': 'p',
           'label': '%s over %s %s' % (p['n'], num(q[0]), p['mk'].lower()), 'sub': '%s vs %s' % (p['t'], p['opp']), 'wk': g.get('wk'),
           't': p['ko'], 'gid': p['gid'], 'tm': p['t'], 'mk': p['mk'], 'sd': 'o', 'pt': q[0], 'pr': q[1], 'bk': bk}
    old = {'mybets': json.dumps([bet]), 'book': page_views.books()[0], 'blg': 'nfl', 'fmt': 'dyn', 'colors': 'on', 'motion': 'off',
           'scene': 'snow', 'theme': 'light', 'sleeper_user': page_views.SLEEPER_USER, 'espn_league': page_views.ESPN_LEAGUE,
           'espn_team': '2', 'last_league': json.dumps({'p': 's', 'u': page_views.SLEEPER_USER, 'id': 'L1'})}
    page, log = new_page(browser, mocks_for(d))
    try:
        page.add_init_script('(o => { if (!sessionStorage.seeded) { for (const k in o) localStorage.setItem(k, o[k]); sessionStorage.seeded = 1 } })(%s)' % json.dumps(old))
        page.goto(sites[''] + 'index.html', wait_until='load')
        page.wait_for_selector('#ld[hidden]', state='attached', timeout=20000)
        for a in (page_views.BET, page_views.bet('mine')): do(page, a)
        settle(page)
        text = page.inner_text('#bo')
        assert bet['label'] in text and 'No saved bets yet' not in text, text[:500]
        assert 'to win $' in text  # the $25 stake came along
        ns = page.evaluate('store.NS')
        moved = page.evaluate('ks => ks.map(k => [k, localStorage.getItem(k), localStorage.getItem(%s + k)])' % json.dumps(ns), sorted(old))
        assert moved == [[k, None, old[k]] for k in sorted(old)], moved
        assert page.evaluate("document.documentElement.dataset.scene") == 'snow'
        assert page.input_value('#bbk') == old['book'] and page.input_value('#fsu') == old['sleeper_user']
        assert not log['errors'], (log['errors'], log['blocked'])
    finally:
        log['ctx'].close()


SCAN = """() => {
  const out = new Set();
  if (window.__x !== undefined) out.add('window.__x set');
  if (document.querySelector('img[src="x"]')) out.add('<img src=x> element');
  document.querySelectorAll('[data-inj]').forEach(e => out.add('attribute break-out: ' + e.getAttribute('data-inj')));
  document.querySelectorAll('*').forEach(e => { for (const a of e.attributes) if (/^on/i.test(a.name) && /__x/.test(a.value)) out.add(a.name + ' handler on <' + e.tagName.toLowerCase() + '>'); });
  if (document.querySelector('a[href^="javascript:"]')) out.add('javascript: link');
  return [...out];
}"""


@pytest.mark.xfail(strict=True, raises=AssertionError, reason='Task 5')
def test_feed_names_are_escaped(built, browser):
    """Feed text must reach the page as text. The first three injections (an odds-feed player, a dynasty-list player,
    a college prospect) use an <img onerror>; the rest are attribute and URL break-outs in the fields the knowledgebase
    names as the real injection path (league and team names typed by other people, board links placed in an href)."""
    def edit(d):
        with_college(d); with_rich_week(d)
        d['ODD']['P'][0]['n'] = IMG
        d['CF']['P'][0][0] = IMG
        d['DY']['L'][deal(skill_pool(d))[0][0]][0] = IMG  # a player on the Sleeper mock user's roster
        d['CF']['CB']['S'][0][1] = JS_URL
        d['CF']['CB']['S'][1][1] = 'https://example.invalid/b2' + attr('cf-board-url')
    out = variant(built, 'site_escape', edit)
    url, srv = serve(out)
    found = {}
    def check(name, page):
        for k in page.evaluate(SCAN): found.setdefault(k, []).append(name)
    try:
        visit_all(browser, lambda n: url, mocks_for(site_data(out), inject=True), check)
    finally:
        srv.shutdown()
    assert not found, 'feed text reached the DOM as markup:\n' + '\n'.join('%s (%d views, first: %s)' % (k, len(v), v[0]) for k, v in sorted(found.items()))


# ---------------------------------------------------------------- python tests/test_page.py --bless

def bless():
    from playwright.sync_api import sync_playwright
    with tempfile.TemporaryDirectory() as tmp:
        base = os.path.join(tmp, 'site'); replay(base)
        def rich(d): with_college(d); with_rich_week(d)
        a, sa = serve(variant(base, 'site_college', with_college))
        b, sb = serve(variant(base, 'site_rich', rich))
        try:
            with sync_playwright() as p:
                br = p.chromium.launch()
                texts, errors = visit_all(br, url_for_sites({'': a, 'rich/': b}), mocks_for(site_data(base)))
                br.close()
        finally:
            sa.shutdown(); sb.shutdown()
    assert not errors, 'console errors, not blessing:\n' + describe_errors(errors)
    content = check_content(texts)
    assert not content, 'views not in their intended state, not blessing:\n' + '\n'.join(content)
    with open(EXPECTED, 'wb') as f:
        f.write(gzip.compress(json.dumps(texts, indent=0, sort_keys=True, ensure_ascii=False).encode('utf-8'), 9, mtime=0))
    print('saved %s (%d views)' % (EXPECTED, len(texts)))


if __name__ == '__main__':
    if sys.argv[1:] == ['--bless']: bless()
    else: sys.exit('usage: python tests/test_page.py --bless')
