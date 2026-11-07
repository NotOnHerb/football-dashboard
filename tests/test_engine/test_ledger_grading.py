"""Grading the prediction ledger: each row is graded for the side it holds (over, yes, home), whichever side was picked."""
import os, sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))   # repo root
from engine import grading, ledger_grading as lg  # noqa: E402


def finals(wk=9, a='AW', h='HM', asc=17, hsc=20):
    return {(wk, a, h): (asc, hsc), (wk, h): (a, h, asc, hsc), (wk, a): (a, h, asc, hsc)}


def grow(mk='spread', pt=-3, wk=9):
    return {'id': 'g|E1|%s|%s' % (mk, '' if pt is None else pt), 'k': 'g', 'wk': wk, 'a': 'AW', 'h': 'HM', 'mk': mk, 'pt': pt}


def prow(mk='Rec yds', pt=50.5, gid='P1', wk=9):
    return {'id': 'p|E1|%s|%s|%s' % (gid, mk, '' if pt is None else pt), 'k': 'p', 'wk': wk, 'tm': 'HM', 'gid': gid, 'mk': mk, 'pt': pt}


def log_row(wk, rec_yds=0, anytd=0):
    # week, opp, ppr, std, yds, td, receptions, pass yds, rush yds, rec yds, pass td, rush+rec td
    return [wk, 'AW', 0, 0, rec_yds, anytd, 0, 0, 0, rec_yds, 0, anytd]


def res(row, fin=None, logs=None, logmax=9):
    r = lg.grade_row(row, finals() if fin is None else fin, logs or {}, logmax)
    return None if r is None else r['res']


# ---- games: the held side is home (spread), over (total), home (moneyline). Default final: AW 17, HM 20.

def test_spread_row_holds_the_home_team_at_its_line():
    assert res(grow('spread', -2.5)) == 'W'       # home won by 3, so it covers -2.5
    assert res(grow('spread', -3)) == 'P'
    assert res(grow('spread', -3.5)) == 'L'
    lost = finals(asc=24, hsc=20)                 # home lost by 4
    assert [res(grow('spread', pt), lost) for pt in (3.5, 4, 4.5)] == ['L', 'P', 'W']


def test_total_row_holds_the_over():
    assert [res(grow('total', pt)) for pt in (36.5, 37, 37.5)] == ['W', 'P', 'L']   # the game totals 37


def test_moneyline_row_holds_home():
    assert res(grow('ml', None)) == 'W'
    assert res(grow('ml', None), finals(asc=24, hsc=20)) == 'L'
    assert res(grow('ml', None), finals(asc=20, hsc=20)) == 'P'


def test_game_result_carries_the_score():
    assert lg.grade_row(grow('spread', -2.5), finals(), {}, 9) == {'res': 'W', 'fin': [17, 20]}


# ---- props: the held side is the over (yes for anytime TD)

def test_prop_row_holds_the_over():
    logs = {'P1': [log_row(9, 80)]}
    assert [res(prow(pt=pt), logs=logs) for pt in (79.5, 80, 80.5)] == ['W', 'P', 'L']
    assert lg.grade_row(prow(pt=79.5), finals(), logs, 9) == {'res': 'W', 'val': 80}


def test_anytime_td_row_holds_yes():
    assert res(prow('Anytime TD', None), logs={'P1': [log_row(9, anytd=1)]}) == 'W'
    assert res(prow('Anytime TD', None), logs={'P1': [log_row(9, anytd=0)]}) == 'L'


def test_player_who_did_not_play_is_void():
    assert res(prow(), logs={'P1': [log_row(8, 80)]}) == 'V'


def test_ungraded_until_the_score_and_stats_are_in():
    logs = {'P1': [log_row(9, 80)]}
    assert res(grow(), fin={}) is None                 # game not final
    assert res(prow(), fin={}, logs=logs) is None
    assert res(prow(), logs=logs, logmax=8) is None    # the week's stats aren't in yet
    assert res(grow(wk=None)) is None and res(prow(wk=None), logs=logs) is None   # no week on the row


# ---- agrees with the official pick grader, on either side

def test_ledger_result_matches_grade_pick_for_the_picked_side():
    """A pick on the held side gets the ledger result; a pick on the other side gets its mirror image."""
    logs = {'P1': [log_row(9, 80)]}
    for pt in (79.5, 80, 80.5):
        row = prow(pt=pt); held = res(row, logs=logs)
        for sd, is_held in (('o', True), ('u', False)):
            pick = {'k': 'p', 'wk': 9, 'tm': 'HM', 'gid': 'P1', 'mk': 'Rec yds', 'sd': sd, 'pt': pt}
            grading.grade_pick(pick, finals(), logs, 9)
            assert pick['res'] == lg.side_result(held, is_held)
    for fin in (finals(), finals(asc=24, hsc=20), finals(asc=20, hsc=20)):
        for mk, pt, held_sd, other_sd in (('spread', -3, 'hs', 'as'), ('total', 40.5, 'ov', 'un'), ('ml', None, 'mh', 'ma')):
            held = res(grow(mk, pt), fin)
            for sd, is_held in ((held_sd, True), (other_sd, False)):
                pick = {'k': 'g', 'wk': 9, 'a': 'AW', 'h': 'HM', 'mk': mk, 'sd': sd, 'pt': pt if sd != 'as' else 3}
                grading.grade_pick(pick, fin, {}, 9)
                assert pick['res'] == lg.side_result(held, is_held), (mk, sd)


def test_side_result_mirrors_wins_and_losses_only():
    assert [lg.side_result(r, False) for r in 'WLPV'] == ['L', 'W', 'P', 'V']
    assert [lg.side_result(r, True) for r in 'WLPV'] == ['W', 'L', 'P', 'V']


# ---- many rows

def test_grade_rows_grades_each_id_once_and_skips_done():
    rows = [grow('spread', -2.5), grow('spread', -2.5), grow('total', 37.5), prow(), grow(wk=None)]
    logs = {'P1': [log_row(9, 80)]}
    out = lg.grade_rows(rows, finals(), logs, 9)
    assert out == {'g|E1|spread|-2.5': {'res': 'W', 'fin': [17, 20]}, 'g|E1|total|37.5': {'res': 'L', 'fin': [17, 20]},
                   'p|E1|P1|Rec yds|50.5': {'res': 'W', 'val': 80}}   # wk=None, id g|E1|spread|-3, stays ungraded
    assert lg.grade_rows(rows, finals(), logs, 9, done=out) == {}
    assert list(lg.grade_rows(rows, finals(), logs, 9, done={'g|E1|total|37.5': {'res': 'L'}})) == ['g|E1|spread|-2.5', 'p|E1|P1|Rec yds|50.5']
