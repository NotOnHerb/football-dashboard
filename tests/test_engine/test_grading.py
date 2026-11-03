"""Grading the pick log from final scores and weekly stats: wins, losses, pushes, voids, parlays."""
import datetime, os, sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))   # repo root
from engine import grading, odds  # noqa: E402

NOW = datetime.datetime(2026, 11, 2, 12, tzinfo=datetime.timezone.utc)
PLAYED = '2026-10-26T17:00:00Z'
UPCOMING = '2026-11-08T18:00:00Z'


def finals(wk=8, a='AW', h='HM', asc=17, hsc=20):
    return {(wk, a, h): (asc, hsc), (wk, h): (a, h, asc, hsc), (wk, a): (a, h, asc, hsc)}


def gpick(mk='spread', sd='hs', pt=-3, pr=-110, t=PLAYED, wk=8):
    return {'id': 'g|E|%s|%s' % (mk, sd), 'k': 'g', 'wk': wk, 't': t, 'a': 'AW', 'h': 'HM', 'mk': mk, 'sd': sd, 'pt': pt, 'pr': pr, 's': 2, 'res': None}


def ppick(gid='P1', mk='Rec yds', sd='o', pt=50.5, pr=-110, wk=8):
    return {'id': 'p|E|%s|%s|%s' % (gid, mk, sd), 'k': 'p', 'wk': wk, 't': PLAYED, 'tm': 'HM', 'gid': gid, 'mk': mk, 'sd': sd,
            'pt': pt, 'pr': pr, 's': 2, 'res': None}


def log_row(wk, rec_yds=0, anytd=0):
    # week, opp, ppr, std, yds, td, receptions, pass yds, rush yds, rec yds, pass td, rush+rec td
    return [wk, 'AW', 0, 0, rec_yds, anytd, 0, 0, 0, rec_yds, 0, anytd]


def test_grade_push_and_void():
    push = gpick(pt=-3)                       # home won by exactly 3
    grading.grade_pick(push, finals(), {}, 8)
    assert push['res'] == 'P' and push['fin'] == [17, 20]
    void = ppick()                            # the player has no game row that week: didn't play
    grading.grade_pick(void, finals(), {'P1': [log_row(7, 80)]}, 8)
    assert void['res'] == 'V'
    log = {r['id']: r for r in (gpick(pt=-3), ppick())}
    grading.grade_log(log, finals(), {'P1': [log_row(7, 80)]}, 8, NOW)
    assert [(r['res'], r['u']) for r in log.values()] == [('P', 0), ('V', 0)]
    assert grading.summarize(log.values()) == {'w': 0, 'l': 0, 'p': 2, 'u': 0}


def test_grade_game_sides():
    for mk, sd, pt, res in (('spread', 'hs', -2.5, 'W'), ('spread', 'as', 2.5, 'L'), ('total', 'ov', 36.5, 'W'),
                            ('total', 'un', 36.5, 'L'), ('ml', 'mh', None, 'W'), ('ml', 'ma', None, 'L')):
        r = gpick(mk, sd, pt)
        grading.grade_pick(r, finals(), {}, 8)
        assert r['res'] == res, (mk, sd)


def test_grade_props_and_waits_for_stats():
    over = ppick(pt=50.5)
    grading.grade_pick(over, finals(), {'P1': [log_row(8, 51)]}, 8)
    assert over['res'] == 'W' and over['val'] == 51
    td = ppick(mk='Anytime TD', sd='y', pt=None)
    grading.grade_pick(td, finals(), {'P1': [log_row(8, 0, 0)]}, 8)
    assert td['res'] == 'L'
    early = ppick()
    grading.grade_pick(early, finals(), {'P1': []}, 7)   # weekly stats not posted for week 8 yet
    assert early['res'] is None


def test_grade_log_units_and_skips_unplayed():
    win, loss, later = gpick(pt=-2.5, pr=150), gpick('total', 'un', 36.5), gpick(t=UPCOMING)
    log = {'a': win, 'b': loss, 'c': later}
    grading.grade_log(log, finals(), {}, 8, NOW)
    assert (win['res'], win['u']) == ('W', round(odds.decimal(150) - 1, 3))
    assert (loss['res'], loss['u']) == ('L', -1)
    assert later['res'] is None and 'u' not in later
    assert grading.summarize([win, loss, later]) == {'w': 1, 'l': 1, 'p': 0, 'u': .5}


def parlay(legs, dec=4.0, bk='X'):
    return {'id': 'x|week|wk8', 'k': 'x', 'wk': 8, 't': PLAYED, 'bk': bk, 'dec': dec, 'legs': legs, 's': 0, 'res': None}


def test_parlay_with_push_pays_remaining_legs():
    r = parlay([gpick('spread', 'hs', -2.5, 100), gpick('total', 'ov', 37, -110)])   # home 20-17: spread wins, total 37 pushes
    grading.grade_log({'x': r}, finals(), {}, 8, NOW)
    assert [l['res'] for l in r['legs']] == ['W', 'P']
    assert r['res'] == 'W' and r['u'] == round(odds.decimal(100) - 1, 3)


def test_parlay_all_won_pays_its_own_price_and_any_loss_loses():
    won = parlay([gpick('spread', 'hs', -2.5, 100), gpick('total', 'ov', 36.5, -110)], dec=3.9)
    lost = parlay([gpick('spread', 'hs', -2.5, 100), gpick('total', 'un', 36.5, -110)])
    pushed = parlay([gpick('spread', 'hs', -3, 100)])
    grading.grade_log({'w': won, 'l': lost, 'p': pushed}, finals(), {}, 8, NOW)
    assert (won['res'], won['u']) == ('W', 2.9)
    assert (lost['res'], lost['u']) == ('L', -1)
    assert (pushed['res'], pushed['u']) == ('P', 0)
