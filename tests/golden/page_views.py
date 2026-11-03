"""Every view of the dashboard page and how to reach it from a fresh page load (read by tests/test_page.py).

VIEWS is a list of (name, actions). An action is one of:
    'css'                     click the first element matching css
    ('select', css, value)    choose an <option> (by value) in a <select>
    ('fill', css, text)       type into a text box (fires its input event)
    ('wait', css)             wait until an element matching css exists

The list follows the section map in the knowledgebase (05-frontend.md): NFL (Teams, Players, Matchups, Compare),
Fantasy (My league, Start/sit, Rankings, College), Betting (Picks, Games, Props, My bets, Results, College) and the
player card. Betting -> Picks is visited once per sportsbook in the golden data's ODD.books, plus "best available".
"""
import gzip, json, os

HERE = os.path.dirname(os.path.abspath(__file__))
EXPECTED_DATA = os.path.join(HERE, 'expected_data.json.gz')

SLEEPER_USER = 'mockuser'  # the test's Sleeper mock answers for this user (see tests/test_page.py)
LOAD_LEAGUE = [('fill', '#fsu', SLEEPER_USER), '#fsgo', ('wait', '#fmo .wrap')]

NFL = '#sec [data-s="nfl"]'
FAN = '#sec [data-s="fan"]'
BET = '#sec [data-s="bet"]'


def tab(v): return '#tabs [data-v="%s"]' % v
def fan(x): return '#fv [data-x="%s"]' % x
def bet(v): return '#bv [data-v="%s"]' % v
def fmt(f): return '#fmt [data-f="%s"]' % f
def pick_book(b): return ('select', '#bbk', b)


def books():
    """The sportsbooks in the golden data, in the page's order."""
    with gzip.open(EXPECTED_DATA, 'rt', encoding='utf-8') as f:
        return json.load(f)['ODD']['books']


def build_views():
    V = []
    add = lambda name, *actions: V.append((name, list(actions)))
    book_list = books()

    # ---- NFL
    for w, label in (('W', 'whole'), ('O', 'offense'), ('D', 'defense'), ('S', 'special')):
        add('nfl/teams/' + label, '#tv [data-w="%s"]' % w)
    add('nfl/teams/detail', '#tt tr[data-t]')
    add('nfl/teams/detail-defense', '#tv [data-w="D"]', '#tt tr[data-t]')
    for p in ('ALL', 'QB', 'RB', 'WR', 'TE', 'OL', 'K'):
        add('nfl/players/offense/' + p, tab('p'), '#pos [data-p="%s"]' % p)
    for s in ('half', 'std'):
        add('nfl/players/offense/ALL/' + s, tab('p'), '#sc [data-s="%s"]' % s)
    add('nfl/players/offense/RB/std', tab('p'), '#pos [data-p="RB"]', '#sc [data-s="std"]')
    add('nfl/players/offense/ALL/usage-25', tab('p'), ('select', '#mn', '25'))
    add('nfl/players/offense/ALL/team-CHI', tab('p'), ('select', '#tm', 'CHI'))
    add('nfl/players/offense/ALL/search', tab('p'), ('fill', '#q', 'jo'))
    for g in ('ALL', 'DL', 'LB', 'CB', 'S'):
        add('nfl/players/defense/' + g, tab('p'), '#side [data-d="D"]', '#xg [data-g="%s"]' % g)
    add('nfl/players/card', tab('p'), '#pt td.nm', ('wait', '#pc:not([hidden])'))
    add('nfl/matchups/trenches', tab('n'))
    add('nfl/matchups/skill', tab('n'), '#mv [data-m="s"]')
    for p in ('QB', 'RB', 'WR', 'TE'):
        add('nfl/compare/' + p, tab('c'), '#cpos [data-p="%s"]' % p)
    add('nfl/glossary', '#gls summary')

    # ---- Fantasy (dynasty and redraft formats)
    for f, label in (('dyn', 'dynasty'), ('red', 'redraft')):
        base = [FAN, fmt(f)]
        add('fantasy/%s/my-league/sleeper-form' % label, *base)
        add('fantasy/%s/my-league/espn-form' % label, *base, '#fpl [data-p="e"]')
        add('fantasy/%s/my-league/sleeper-loaded' % label, *base, *LOAD_LEAGUE)
        add('fantasy/%s/start-sit/no-league' % label, *base, fan('s'))
        add('fantasy/%s/start-sit/all-starters' % label, *base, fan('s'), '#fsm [data-m="all"]')
        for p in ('QB', 'RB', 'WR', 'TE'):
            add('fantasy/%s/start-sit/all-starters/%s' % (label, p), *base, fan('s'), '#fsm [data-m="all"]', '#fpos [data-p="%s"]' % p)
        add('fantasy/%s/start-sit/all-starters/half' % label, *base, fan('s'), '#fsm [data-m="all"]', '#fsc [data-s="half"]')
        add('fantasy/%s/start-sit/my-team' % label, *base, *LOAD_LEAGUE, fan('s'), ('wait', '#fmy table'))
    for q, qlabel in (('1', '1qb'), ('2', 'superflex')):
        for v, vlabel in (('b', 'value-board'), ('g', 'diamonds'), ('k', 'rookie-picks')):
            add('fantasy/rankings/%s/%s' % (vlabel, qlabel), FAN, fan('r'), '#dv [data-x="%s"]' % v, '#dfmt [data-f="%s"]' % q)
    for p in ('QB', 'RB', 'WR', 'TE'):
        add('fantasy/rankings/value-board/1qb/' + p, FAN, fan('r'), '#dpos [data-p="%s"]' % p)
    add('fantasy/rankings/value-board/1qb/search', FAN, fan('r'), ('fill', '#dq', 'jo'))
    for c, label in (('d', 'draft-prospects'), ('g', 'big-board'), ('b', 'breakouts'), ('f', 'college-fantasy')):
        add('fantasy/college/' + label, FAN, fan('c'), '#cv2 [data-c="%s"]' % c)
    add('fantasy/college/college-fantasy/std', FAN, fan('c'), '#cv2 [data-c="f"]', '#csc [data-s="std"]')
    add('fantasy/college/draft-prospects/conference-SEC', FAN, fan('c'), ('select', '#ccf', 'SEC'))
    add('fantasy/college/draft-prospects/WR', FAN, fan('c'), '#dpos [data-p="WR"]')

    # ---- Betting, NFL
    add('betting/nfl/picks/best-available', BET)
    for b in book_list:
        add('betting/nfl/picks/' + b, BET, pick_book(b))
    add('betting/nfl/games/best-available', BET, bet('games'))
    add('betting/nfl/games/' + book_list[0], BET, bet('games'), pick_book(book_list[0]))
    add('betting/nfl/props/best-available', BET, bet('props'))
    for m in ('Pass yds', 'Rush yds', 'Rec yds', 'Receptions', 'Pass TDs', 'Anytime TD'):
        add('betting/nfl/props/market/' + m, BET, bet('props'), '#bmk [data-m="%s"]' % m)
    add('betting/nfl/props/picks-and-leans-only', BET, bet('props'), 'label:has(#blo)')
    add('betting/nfl/props/game-CHI-at-SEA', BET, bet('props'), ('select', '#bgm', 'SEA'))
    add('betting/nfl/props/search', BET, bet('props'), ('fill', '#bq', 'jo'))
    add('betting/nfl/props/book-' + book_list[0], BET, bet('props'), pick_book(book_list[0]))
    add('betting/nfl/my-bets/empty', BET, bet('mine'))
    add('betting/nfl/my-bets/one-saved', BET, '#bo [data-bet]', bet('mine'))
    add('betting/nfl/results', BET, bet('results'))
    add('betting/nfl/picks/player-card', BET, '#bo a.pn', ('wait', '#pc:not([hidden])'))

    # ---- Betting, college
    cfb = '#blg [data-l="cfb"]'
    add('betting/college/picks', BET, cfb)
    add('betting/college/games', BET, cfb, bet('games'))
    add('betting/college/games/power-4', BET, cfb, bet('games'), ('select', '#cconf', 'P4'))
    add('betting/college/games/picks-only', BET, cfb, bet('games'), 'label:has(#cpo)')
    add('betting/college/games/search', BET, cfb, bet('games'), ('fill', '#cq', 'ohio'))
    add('betting/college/results', BET, cfb, bet('results'))
    add('betting/college/my-bets', BET, cfb, bet('mine'))
    return V


VIEWS = build_views()
