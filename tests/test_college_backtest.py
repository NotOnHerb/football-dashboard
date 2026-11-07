"""The college best-number record (CFB.BT) is derived from the saved games and lines with the same rule the live picks use.

It used to be a fixed 314-249 in build.py. engine/college.py now has the rule (best_number) and counts what it would have
done on the 2023-25 games (backtest_seasons); build.py calls both, so changing a threshold in engine/rules.py changes the
picks and the record together.
"""
import gzip, json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
from engine import college  # noqa: E402

CFB_FIXTURES = os.path.join(HERE, 'golden', 'fixtures', 'repo', 'cfb')


def read_fixture(kind, year):
    return json.load(gzip.open(os.path.join(CFB_FIXTURES, '%s_%d.json.gz' % (kind, year)), 'rt', encoding='utf-8'))


def game(i, home_pts, away_pts, cls='fbs', completed=True):
    return {'id': i, 'homeClassification': cls, 'awayClassification': 'fbs', 'completed': completed,
            'homePoints': home_pts, 'awayPoints': away_pts}


def lines(i, dk=None, espn=None, bovada=None, caesars=None):
    """One game's lines row (home spreads by book); a book left out does not post."""
    names = {'DraftKings': dk, 'ESPN Bet': espn, 'Bovada': bovada, 'Caesars Sportsbook (Colorado)': caesars}
    return {'id': i, 'lines': [{'provider': p, 'spread': s} for p, s in names.items() if s is not None]}


def test_backtest_counts_what_the_rule_would_have_done():
    games = [
        game(1, 30, 20),   # DraftKings home -4.5, the rest -3: gap 1.5, away side at +4.5; home wins by 10 -> loss, level II
        game(2, 20, 30),   # same lines; away wins -> win, level II
        game(3, 24, 20),   # DraftKings home -1 vs -3: gap 2, home side at -1; home wins by 4 -> win, level II
        game(4, 21, 20),   # DraftKings home -1.75 vs -3: gap 1.25, home side at -1.75; home wins by 1 -> loss, level I
        game(5, 27, 20),   # same lines as game 1; home wins by 7 -> loss, level II
        game(6, 30, 20, cls='fcs'),        # not FBS against FBS: skipped
        game(7, 30, 20, completed=False),  # not finished: skipped
        game(8, 30, 20),   # only two books post: skipped
        game(9, 30, 20),   # gap 3.5 is past the window: skipped
    ]
    rows = [
        lines(1, -4.5, -3, -3, -3), lines(2, -4.5, -3, -3, -3), lines(3, -1, -3, -3, -3), lines(4, -1.75, -3, -3, -3),
        lines(5, -4.5, -3, -3, -3), lines(6, -4.5, -3, -3, -3), lines(7, -4.5, -3, -3, -3), lines(8, -4.5, -3),
        lines(9, -6.5, -3, -3, -3),
    ]
    r = college.backtest(games, rows)
    assert r['l2'] == [2, 2] and r['l1'] == [0, 1] and r['push'] == 0 and r['record'] == [2, 3]


def test_a_push_is_neither_a_win_nor_a_loss():
    # DraftKings home -7 vs -8.5: gap 1.5 toward the home side at -7; home wins by exactly 7
    r = college.backtest([game(1, 27, 20)], [lines(1, -7, -8.5, -8.5, -8.5)])
    assert r['push'] == 1 and r['record'] == [0, 0]
    # DraftKings home -10 vs -8.5: away side at +10; home wins by 7 -> the away side covers
    r = college.backtest([game(1, 27, 20)], [lines(1, -10, -8.5, -8.5, -8.5)])
    assert r['l2'] == [1, 0] and r['push'] == 0


def test_best_number_is_the_book_furthest_from_the_others():
    books = {'DraftKings': [-4.5], 'ESPN BET': [-3.0], 'Bovada': [-3.0], 'Caesars': [None]}
    assert college.best_number(books) == (-1.5, 'DraftKings', -4.5)
    assert college.best_number({'DraftKings': [None]}) is None


def test_an_excluded_book_counts_in_the_median_but_never_supplies_the_number():
    books = {'Pinnacle': [-6.0], 'DraftKings': [-3.0], 'ESPN BET': [-3.0]}
    # with Pinnacle in the median DraftKings' others are -6 and -3 (median -4.5): gap +1.5; ESPN BET ties, and the first listed wins
    assert college.best_number(books) == (1.5, 'DraftKings', -3.0)


def test_a_season_with_too_few_bets_is_refused_not_published():
    import pytest
    def read(kind, year):
        rows = read_fixture(kind, year)
        return rows[:50] if kind == 'lines' else rows   # lines for only some games
    with pytest.raises(ValueError, match='look incomplete'):
        college.backtest_seasons(read)
    college.backtest_seasons(read_fixture)   # the full files pass


def test_the_record_follows_the_strategy(monkeypatch):
    g, l = read_fixture('games', 2025), read_fixture('lines', 2025)
    base = sum(college.backtest(g, l)['record'])
    monkeypatch.setattr(college, 'COLLEGE_GAP_MAX', 2)
    assert sum(college.backtest(g, l)['record']) < base
    monkeypatch.setattr(college, 'COLLEGE_GAP_MAX', 3)
    monkeypatch.setattr(college, 'COLLEGE_MIN_BOOKS', 4)
    assert sum(college.backtest(g, l)['record']) < base
    monkeypatch.setattr(college, 'MIN_BETS_PER_SEASON', 0)   # a stricter rule leaves fewer bets than the real-data floor
    assert college.backtest_seasons(read_fixture, (2025,))['rule'] == 'with 4+ books, one book 1 to 3 points off the others'


def test_derived_record_matches_the_figures_the_page_always_showed():
    """The record derived from the saved 2023-25 data is the one that was hard-coded in build.py. If a strategy change moves
    it on purpose, update these numbers in the same commit (the golden data.json moves with them)."""
    bt = college.backtest_seasons(read_fixture)
    assert bt['record'] == [314, 249] and bt['l2'] == [150, 115] and bt['l1'] == [164, 134]
    assert bt['by_season'] == {'2023': '75-64', '2024': '43-33', '2025': '32-18'}
    assert bt['seasons'] == '2023-25' and bt['rule'] == 'with 3+ books, one book 1 to 3 points off the others'
