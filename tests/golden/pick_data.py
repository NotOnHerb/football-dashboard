"""Recomputes the official picks for a data.json that tests have edited.

The page snapshot tests serve the golden data.json after editing it (tests/test_page.py: with_rich_week adds games and
props, and so on), so the ODD.PK / ODD.PKB stored in that file no longer describe the edited ODD.G / ODD.P rows.
recompute_picks(data) runs the engine on the edited rows, with the same inputs build.py uses, and returns fresh
picks for the edited data:

    PK, PKB = recompute_picks(data)      # PK: best across books; PKB: {book: picks at that book only}

Use it to keep PK/PKB consistent with the edited rows, or to compare them with what the page computes on its own
(tests/test_pkb_page.py does this today; once the page reads ODD.PK / ODD.PKB, the "rich/" test variants set them with it).
"""
import datetime, json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
if ROOT not in sys.path: sys.path.insert(0, ROOT)
from engine.picks import official_picks, picks_by_book  # noqa: E402


def golden_now():
    """The frozen clock of the golden build (tests/golden/fixtures/meta.json), as an aware datetime."""
    with open(os.path.join(HERE, 'fixtures', 'meta.json')) as f: iso = json.load(f)['now']
    return datetime.datetime.fromisoformat(iso.replace('Z', '+00:00'))


def injuries(data):
    """{gsis id: report status} from the player table, the way build.py builds INJ."""
    return {r[8]: r[5][0] for rows in data['P'].values() for r in rows if r[5] and r[8]}


def recompute_picks(data, now=None):
    """(PK, PKB) for data's current ODD.G and ODD.P: the official picks at the best price across books, and one list per
    sportsbook in ODD.books priced at that book alone. NOW defaults to the golden clock."""
    O = data['ODD']
    now = now or golden_now()
    model = {'q': O['MQ'], 'cal': O['MC'] or {}} if O['MQ'] else None
    weeks = {g['id']: g['wk'] for g in O['G']}
    inj = injuries(data)
    PK = official_picks(O['G'], O['P'], model, O['MB'], now, inj, weeks=weeks)
    PKB = picks_by_book(O['books'], O['G'], O['P'], model, O['MB'], now, inj, weeks=weeks)
    return PK, PKB
