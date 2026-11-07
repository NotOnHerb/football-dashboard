"""Grading the prediction ledger: each row is graded for the side it holds (over, yes, home), whichever side was picked."""
import os, sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))   # repo root
from engine import grading, ledger_grading as lg  # noqa: E402


def finals(wk=9, a='AW', h='HM', asc=17, hsc=20):
    return {(wk, a, h): (asc, hsc), (wk, h): (a, h, asc, hsc), (wk, a): (a, h, asc, hsc)}


def grow(mk='spread', pt=-3, wk=9):
    return {'id': 'g|E1|%s|%s' % (mk, '' if pt is None else pt), 'k': 'g', 'wk': wk, 'a': 'AW', 'h': 'HM', 'mk': mk, 'pt': pt}


def prow(mk='Rec yds', pt=50.5, gid='P1', wk=9):
    return {'id': 'p|E1|%s|%s|%s' % (gid, mk, '' if pt is None else pt), 'k': 'p', 'wk': wk, 'tm': 'HM', 'opp': 'AW', 'gid': gid, 'mk': mk, 'pt': pt}


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


def test_player_who_did_not_play_is_void_once_the_games_stats_are_in():
    teammate = [log_row(9, 10)]                        # a teammate's week-9 row (opponent AW): the game's stats are posted
    assert res(prow(), logs={'P1': [log_row(8, 80)], 'P2': teammate}) == 'V'


def test_no_void_while_the_games_stats_have_not_posted():
    """LOGMAX is the latest week of any game, so another game's week-9 rows must not void this game's props."""
    other_game = [[9, 'ZZ'] + log_row(9, 10)[2:]]      # a week-9 row against a different opponent
    assert res(prow(), logs={'P1': [log_row(8, 80)], 'P2': other_game}, logmax=9) is None
    assert res(prow(), logs={'P1': [log_row(8, 80)]}) is None
    assert res(prow(), logs={'P1': [log_row(9, 80)]}) == 'W'   # a player who has a row is graded either way


def test_unknown_prop_market_is_left_ungraded():
    assert res(prow('Sacks', 0.5)) is None


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


# ---- real ledger rows (from the golden data.json) against the official pick grader

def test_golden_ledger_rows_grade_like_the_official_picks():
    """Rows built by ledger_rows from the golden slate, graded with invented scores and stats, agree with grade_pick on
    every official pick in ODD.PK (mirrored when the pick took the side the row doesn't hold)."""
    import gzip, json
    from engine import ledger
    O = json.load(gzip.open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'golden', 'expected_data.json.gz'), 'rt', encoding='utf-8'))['ODD']
    model = {'q': O['MQ'], 'cal': O['MC'], 'fit_at': None}
    rows = ledger.ledger_rows(O['G'], O['P'], model, O['MB'], O['PK'], '2000-01-01T00:00')   # nothing has kicked off
    fin = {}
    for i, g in enumerate(O['G']):
        asc, hsc = 17 + i % 7, 20 + (i * 3) % 11
        fin[(g['wk'], g['a'], g['h'])] = (asc, hsc); fin[(g['wk'], g['h'])] = fin[(g['wk'], g['a'])] = (g['a'], g['h'], asc, hsc)
    logs = {}
    for i, p in enumerate(O['P']):
        line = next((v[0] for v in p['b'].values() if v[0] is not None), None)
        val = 1 if p['mk'] == 'Anytime TD' and i % 2 else 0 if p['mk'] == 'Anytime TD' else int((line or 0) + (-5 if i % 2 else 5))
        w = next(g['wk'] for g in O['G'] if g['id'] == p['eid'])
        row = [w, p['opp'], 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
        for c in (6, 7, 8, 9, 10, 11): row[c] = val
        logs[p['gid']] = [row]
    out = lg.grade_rows(rows, fin, logs, 99)
    assert out and all(r['id'] in out for r in rows if r['k'] == 'g')   # every game row is graded
    checked = 0
    pk = {x['id']: x for x in O['PK']}
    for r in rows:
        if not r['pick']: continue
        pid = ('g|%s|%s|%s' % (r['eid'], r['mk'], r['sd'])) if r['k'] == 'g' else ('p|%s|%s|%s|%s' % (r['eid'], r['gid'], r['mk'], r['sd']))
        pick = dict(pk[pid]); pick.pop('res', None)
        grading.grade_pick(pick, fin, logs, 99)
        if r['id'] not in out:
            assert pick.get('res') in (None, 'V'); continue
        assert pick['res'] == lg.side_result(out[r['id']]['res'], r['sd'] in ledger.HOME_SIDES), pid
        checked += 1
    assert checked
