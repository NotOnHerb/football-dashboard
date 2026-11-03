"""MCP server for the football dashboard: the week's games, picks, props, players, teams and the model, read-only.

Run it from the repo root (see .mcp.json.example):   python -m mcp_server.server
Tools only read, except add_idea, which appends one line to ideas/inbox.jsonl (a local file, never committed).
Data comes from the repo's files, or from the published API when FD_API_URL is set (see mcp_server/data.py).
Games, picks and props whose kickoff has passed are left out of the "current" tools, as the page leaves them out
(the pick log keeps them). Picks are explained from what the pick itself stored plus engine.rules; nothing here
recomputes a pick.
"""
import datetime, difflib, json, os, re, sys
from typing import Any

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))   # the repo root, for engine/ and api_export
from mcp.server.mcpserver import MCPServer  # noqa: E402
from mcp.types import ToolAnnotations  # noqa: E402

from engine import rules as R  # noqa: E402
from engine.odds import implied  # noqa: E402
from engine.picks import started  # noqa: E402
from engine.projections import p_over  # noqa: E402
from engine.rules import RULES  # noqa: E402
from mcp_server.data import ROOT, Source  # noqa: E402

KINDS = {'g': 'g', 'game': 'g', 'p': 'p', 'prop': 'p', 'x': 'x', 'parlay': 'x', 'c': 'c', 'college': 'c'}
RESULTS = {'w': 'W', 'win': 'W', 'l': 'L', 'loss': 'L', 'p': 'P', 'push': 'P', 'v': 'V', 'void': 'V'}
SIDE_NAMES = {'hs': 'home spread', 'as': 'away spread', 'ov': 'over', 'un': 'under', 'mh': 'home moneyline',
              'ma': 'away moneyline', 'o': 'over', 'u': 'under', 'y': 'yes (anytime TD)'}
Result = dict[str, Any]   # tools return a dict; this annotation makes the SDK send it as structured content too
DEFAULT_IDEAS = os.path.join(ROOT, 'ideas', 'inbox.jsonl')


def utcnow():
    return datetime.datetime.now(datetime.timezone.utc)


def norm(s):
    """Lowercase letters and digits only, words separated by single spaces: "Ja'Marr Chase" -> "jamarr chase"."""
    s = re.sub(r"['.’]", '', str(s).lower())
    return re.sub(r'[^a-z0-9]+', ' ', s).strip()


def score_name(query, name):
    """How well NAME matches QUERY, 0-100: exact 100, every query word starting a name word 80+, close spelling below."""
    q, n = norm(query), norm(name)
    if not q: return 0
    if q == n: return 100
    qw, nw = q.split(), n.split()
    if all(any(w.startswith(x) for w in nw) for x in qw): return 80 + 10 * len(qw) / max(len(nw), 1)
    r = difflib.SequenceMatcher(None, q, n).ratio()
    return r * 70 if r >= .75 else 0


def find_players(players, query, limit=5):
    """Players matching a gsis id (exactly) or a name (fuzzy), best first."""
    q = str(query).strip()
    by_id = [p for p in players if p['gsis_id'] == q]
    if by_id: return by_id
    scored = sorted(((score_name(q, p['name']), -i, p) for i, p in enumerate(players)), key=lambda x: (x[0], x[1]), reverse=True)
    return [p for sc, _, p in scored if sc > 0][:limit]


def resolve_team(teams, q):
    """A team entry from a code ('CHI'), a name ('Bears') or any unambiguous start of a name; None if unknown."""
    q = str(q).strip()
    for t in teams:
        if t['code'].upper() == q.upper(): return t
    hits = [t for t in teams if t['name'] and norm(q) and norm(t['name']).startswith(norm(q))]
    return hits[0] if len(hits) == 1 else None


def pick_teams(p):
    return {x for x in (p.get('team'), p.get('opponent'), p.get('away'), p.get('home')) if x}


def lean_text(pc, pr, ls):
    """The lean paragraph: our chance vs the price's implied chance, and the tier it earned (tiers from engine.rules)."""
    t = R.LEAN_TIERS
    return ('Lean: our chance %.1f%% (the model blended with the market) against %.1f%% implied by the price, an edge of %.1f points. '
            'Lean tiers are 1 at %.0f points, 2 at %.0f and 3 at %.0f; this scored %s, and a lean counts at most %d toward the total.' % (
                pc * 100, implied(pr) * 100, (pc - implied(pr)) * 100, t[0] * 100, t[1] * 100, t[2] * 100, ls, R.LEAN_MAX_SCORE))


def explain(pick, rules, others=None):
    """Plain-language reasons for a pick, from the fields it stored and the pick rules. Returns {'reasons', 'scores'}.
    Every threshold quoted comes from the rules passed in or from engine.rules; nothing is recomputed."""
    reasons, p = [], pick
    v, pc, pr, pt = p.get('ev'), p.get('our_chance'), p.get('price'), p.get('line')
    kind, market = p.get('type'), p.get('market')
    side = SIDE_NAMES.get(p.get('side'), p.get('side'))
    scores = {'total': p.get('score'), 'needed_for_a_pick': rules['pick']}
    if kind == 'x':
        reasons.append('Parlay of %d legs at %s, paying %s to 1 if every leg wins (price %+d). Our chance all legs win %s; '
                       'break-even is %s.' % (len(p.get('legs') or []), p.get('book'), p.get('decimal') and round(p['decimal'] - 1, 2),
                                              pr or 0, p.get('our_chance'), p.get('break_even')))
        if p.get('note'): reasons.append(p['note'])
        for l in p.get('legs') or []:
            reasons.append('Leg: %s' % describe(l))
    elif kind == 'c':
        scores['needed_for_a_pick'] = R.COLLEGE_MIN_SCORE
        reasons.append('College %s %s at %s; this book is %.1f points off the median of the other books (they are at %s).' % (
            side, fmt_quote(pt, pr), p.get('book'), p.get('gap') or 0, p.get('others_line')))
        reasons.append('College spread rule: with at least %d books posting, one book %s to under %s points off the median of the others '
                       '(%s never supply the odd number), at a price of %+d or better. Every pick that passes is official: score %s from a gap of %s '
                       'points, else %s. This one scored %s.' % (
                           R.COLLEGE_MIN_BOOKS, R.COLLEGE_GAP_MIN, R.COLLEGE_GAP_MAX, ', '.join(R.COLLEGE_EXCLUDED_BOOKS),
                           R.COLLEGE_MIN_PRICE, R.COLLEGE_STRONG_SCORE, R.COLLEGE_GAP_STRONG, R.COLLEGE_MIN_SCORE, p.get('score')))
    else:
        reasons.append('%s: %s %s at %s.' % (describe(p), side, fmt_quote(pt, pr), p.get('book')))
        vs, ls, ms = p.get('value_score'), p.get('lean_score'), p.get('model_score')
        cuts = rules['val']
        if market == 'Anytime TD':
            scores.update(lean=ls)
            reasons.append('Value: the value score is not used for anytime TDs, so they are scored on lean alone (the market\'s fair chance still goes into our chance).')
            if pc is not None and pr is not None: reasons.append(lean_text(pc, pr, ls))
            reasons.append('An anytime TD earns a lean only at a price of +%d or shorter and with at least %d games of history.' % (
                rules['tdmax'], R.LEAN_MIN_GAMES))
        else:
            scores.update(value=vs)
            if v is None:
                reasons.append('Value: no expected value (the fair line is not at this number), so it scores 0 on value.')
            else:
                reasons.append('Value: expected value %+.1f%% per unit at the best price. Value scores are 1 at %.1f%%, 2 at %.1f%% and 3 at %.1f%%; '
                               'this one scored %s. (Above %.0f%% a price is treated as stale, not a pick.)' % (
                                   v * 100, cuts[0] * 100, cuts[1] * 100, cuts[2] * 100, vs, rules['stale'] * 100))
            if kind == 'p':
                scores.update(lean=ls)
                if pc is not None and pr is not None: reasons.append(lean_text(pc, pr, ls))
                if p.get('projection') is not None:
                    reasons.append('Projection %s against the line %s.' % (p['projection'], pt))
                reasons.append('A prop needs a line of at least %s for %s to earn a lean, and the player needs at least %d games of history.' % (
                    rules['minl'].get(market, 'n/a'), market, R.LEAN_MIN_GAMES))
            else:
                scores.update(model=ms)
                if ms is not None and market == 'spread':
                    reasons.append('Team model: %s (1 when our model beats the line by %s points or more).' % (
                        'it does' if ms else 'it does not', rules['model']))
                if pc is not None:
                    reasons.append('Our chance %.1f%% at this price (fair chance adjusted for the line and the price).' % (pc * 100))
        reasons.append('Total score %s (needed %s for an official pick).' % (p.get('score'), rules['pick']))
    fs = p.get('first_seen')
    if fs and (fs.get('price') != pr or fs.get('line') != pt):
        reasons.append('First seen at %s %s on %s; now %s.' % (fs.get('book'), fmt_quote(fs.get('line'), fs.get('price')), fs.get('at'),
                                                              fmt_quote(pt, pr)))
    if others:
        reasons.append('Other books for the same side: ' + '; '.join(others))
    if p.get('result'):
        reasons.append('Result: %s%s, %s units.' % (p['result'], '' if p.get('actual') is None else ' (actual %s)' % p['actual'], p.get('units')))
    return {'reasons': reasons, 'scores': scores}


def describe(p):
    """A short label for a pick: 'Colston Loveland Rec yds (CHI vs SEA)' or 'CHI @ SEA spread'."""
    if p.get('type') == 'p': return '%s %s (%s vs %s)' % (p.get('player'), p.get('market'), p.get('team'), p.get('opponent'))
    if p.get('type') == 'g': return '%s @ %s %s' % (p.get('away'), p.get('home'), p.get('market'))
    return str(p.get('id'))


def fmt_quote(line, price):
    """'44.5 @ -117', or just '-150' when there is no line (a moneyline)."""
    return ('' if line is None else '%s @ ' % line) + ('n/a' if price is None else '%+d' % price)


def book_prices(pick, props):
    """What each book posts for a prop pick's side, as short strings, for the 'other books' reason (props only)."""
    if pick.get('type') != 'p': return []
    for pr in props or []:
        if pr['event_id'] == pick['event_id'] and pr['gsis_id'] == pick['gsis_id'] and pr['market'] == pick['market']:
            out = []
            for bk, x in pr['books'].items():
                if pick['side'] == 'o': ln, price = x['over_line'], x['over_price']
                elif pick['side'] == 'u': ln, price = x['under_line'], x['under_price']
                else: ln, price = None, x['over_price']
                if price is not None: out.append('%s %s%+d' % (bk, '' if ln is None else '%s @ ' % ln, price))
            return out
    return []


def create_server(source=None, ideas_path=None, now=None):
    """The MCP server. SOURCE is a mcp_server.data.Source (default: from the environment); IDEAS_PATH is where add_idea writes;
    NOW is a function returning the current time as an aware datetime (tests pass a fixed one)."""
    src = source or Source.from_env()
    ideas = ideas_path or DEFAULT_IDEAS
    clock = now or utcnow
    # The tools read files here, or the published API (a network read) when FD_API_URL is set.
    read_only = ToolAnnotations(readOnlyHint=True, destructiveHint=False, idempotentHint=True, openWorldHint=bool(src.base_url))
    writes_local_file = ToolAnnotations(readOnlyHint=False, destructiveHint=False, idempotentHint=False, openWorldHint=False)
    server = MCPServer('football-dashboard', instructions=(
        'NFL and college betting dashboard data. Start with health() to see how fresh it is, get_week_games() for the slate, '
        'get_picks() for official picks and explain_pick(pick_id) for the reasoning. All prices are American odds. '
        'Games, picks and props already kicked off are left out of the current tools. Everything is read-only except add_idea.'))

    def doc(name):
        d = src.get(name)
        if d is None: raise ValueError('no %s.json in %s (run build.py and api_export.py, or set FD_API_URL)' % (name, src.where))
        return d

    def rules():
        ix = src.get('index') or {}
        return ix.get('rules') or RULES

    def live(rows):
        """ROWS (picks, games, props) whose kickoff has not passed, like the page's past() check; rows without a kickoff stay."""
        t = clock()
        return [r for r in rows if not r.get('kickoff') or not started(r['kickoff'], t)]

    def book_names():
        ix = src.get('index') or {}
        return sorted(ix.get('books') or [])

    @server.tool(annotations=read_only)
    def get_week_games() -> Result:
        """This week's NFL games that have not kicked off, with every book's moneyline, spread and total, the fair line, our model's
        number, line movement and the ids of the official picks on each game. Prices are American odds; spread lines are from the home team's view."""
        g = doc('games'); picks = live(doc('picks'))
        lines = [dict(x, picks=[p['id'] for p in picks if p.get('event_id') == x['event_id']]) for x in live(g['lines'])]
        # The schedule rows (G) stay unless their odds line shows the game has started; a game with no posted lines stays too.
        started_games = {(x['away'], x['home']) for x in g['lines']} - {(x['away'], x['home']) for x in lines}
        return {'week': g['week'], 'as_of': clock().isoformat(), 'games': lines,
                'remaining': [r for r in g['remaining'] if (r['away'], r['home']) not in started_games], 'finals_this_season': len(g['finals'])}

    @server.tool(annotations=read_only)
    def get_picks(book: str | None = None) -> Result:
        """Current official picks for games that have not kicked off, strongest first. With book (for example 'DraftKings'), the picks that
        sportsbook alone would give (its own lines and prices); when the data has no per-book picks, only the subset of current picks whose
        best price is at that book (the result's source says which)."""
        picks = live(doc('picks'))
        if book is None: return {'book': None, 'source': 'all books, best price', 'count': len(picks), 'picks': picks}
        pbb = src.get('picks_by_book')
        known = sorted(pbb) if pbb else book_names()
        key = next((k for k in known if k.lower() == book.lower()), None)
        if key is None: return {'book': book, 'error': 'no such book', 'books': known}
        if pbb:
            sel = live(pbb[key])
            return {'book': key, 'source': 'picks_by_book (that book only)', 'count': len(sel), 'picks': sel}
        sel = [p for p in picks if str(p.get('book', '')).lower() == key.lower()]
        return {'book': key, 'source': 'SUBSET of the current picks: those whose best price is at this book. It is not what this book alone '
                                       'would pick (no per-book picks in this data)', 'count': len(sel), 'picks': sel}

    @server.tool(annotations=read_only)
    def get_pick_log(kind: str | None = None, week: int | None = None, result: str | None = None, limit: int = 50) -> Result:
        """The pick log, newest first. kind: game, prop, parlay or college (or g, p, x, c). result: W, L, P (push), V (void) or
        pending. Returns the win-loss record and units of everything matching, and up to limit records."""
        k = KINDS.get(kind.lower()) if kind else None
        if kind and k is None: return {'error': 'kind must be one of game, prop, parlay, college', 'kind': kind}
        r = None
        if result:
            r = 'pending' if result.lower() == 'pending' else RESULTS.get(result.lower(), result.upper())
        rows = [p for p in doc('pick_log')
                if (k is None or p.get('type') == k) and (week is None or p.get('week') == week)
                and (r is None or (p.get('result') is None if r == 'pending' else p.get('result') == r))]
        rec = {'w': sum(1 for p in rows if p.get('result') == 'W'), 'l': sum(1 for p in rows if p.get('result') == 'L'),
               'p': sum(1 for p in rows if p.get('result') in ('P', 'V')), 'units': round(sum(p.get('units') or 0 for p in rows), 2)}
        return {'matching': len(rows), 'record': rec, 'picks': rows[:max(0, limit)]}

    @server.tool(annotations=read_only)
    def get_player(query: str) -> Result:
        """One player by name (fuzzy: 'jsn', 'smith-njigba' and 'Jaxon Smith Njigba' all work) or gsis id ('00-0038543'): season stats by label,
        injury, depth chart slot, recent form, game log, dynasty value, and the props and picks for games not yet kicked off. Other close matches are listed."""
        hits = find_players(doc('players'), query)
        if not hits: return {'error': 'no player matches %r' % query, 'query': query}
        p = hits[0]; gid = p['gsis_id']
        dy = next((d for d in doc('dynasty')['players'] if d.get('gsis_id') == gid), None)
        return {'player': p, 'dynasty': dy,
                'props': [x for x in live(doc('props')) if x['gsis_id'] == gid],
                'picks': [x for x in live(doc('picks')) if x.get('gsis_id') == gid],
                'other_matches': [{'name': h['name'], 'team': h['team'], 'pos': h['pos'], 'gsis_id': h['gsis_id']} for h in hits[1:]]}

    @server.tool(annotations=read_only)
    def get_props(player: str | None = None, game: str | None = None, limit: int = 100) -> Result:
        """Player props for games not yet kicked off, with every book's line and price, our projection and the fair line. Filter by
        player (fuzzy name) and/or game (team code like 'CHI', 'CHI@SEA', or an event id). limit caps the list."""
        rows = live(doc('props'))
        if player: rows = [x for x in rows if score_name(player, x['player']) > 0]
        if game:
            codes = {t['code'] for t in doc('teams')}
            want = {w.upper() for w in re.split(r'@|/|-|\s+|\bvs\.?\b|\bat\b', game, flags=re.I) if w.upper() in codes}
            rows = [x for x in rows if x['event_id'] == game or (want and want <= {x['team'], x['opponent']})]
        return {'matching': len(rows), 'props': rows[:max(0, limit)]}

    @server.tool(annotations=read_only)
    def explain_pick(pick_id: str) -> Result:
        """Why a pick is a pick, from the scores it stored (value, lean, model) and the pick rules. pick_id is the id from get_picks
        or get_pick_log, for example 'p|<eventId>|<gsis id>|Rec yds|u'. Works for current picks and past ones."""
        pool = doc('picks') + doc('pick_log')
        found = next((p for p in pool if p['id'] == pick_id), None)
        if found is None:
            legs = [l for p in pool for l in p.get('legs') or [] if l['id'] == pick_id]
            found = legs[0] if legs else None
        if found is None:
            return {'error': 'no pick with id %r' % pick_id, 'hint': 'ids come from get_picks or get_pick_log'}
        x = explain(found, rules(), book_prices(found, src.get('props')))
        return {'id': pick_id, 'summary': describe(found), 'reasons': x['reasons'], 'scores': x['scores'], 'rules': rules(), 'pick': found}

    @server.tool(annotations=read_only)
    def get_team(code: str) -> Result:
        """A team by code ('CHI') or name ('Bears'): season stats by column, depth chart (line, front seven, secondary), what it allows
        to each position, its game this week if not yet kicked off, and the current picks that involve it."""
        teams = doc('teams'); t = resolve_team(teams, code)
        if t is None: return {'error': 'no team matches %r' % code, 'codes': sorted(x['code'] for x in teams)}
        c = t['code']
        games = [g for g in live(doc('games')['lines']) if c in (g['away'], g['home'])]
        return {'team': t, 'games': games, 'picks': [p for p in live(doc('picks')) if c in pick_teams(p)]}

    @server.tool(annotations=read_only)
    def calibration(prop: str, projection: float | None = None, line: float | None = None) -> Result:
        """How the projection model behaves for a prop type ('Rec yds', 'Receptions', 'Pass yds', 'Rush yds', 'Pass TDs', 'Anytime TD'):
        the swing of actual vs projection, the calibration nudge, sample size, blend with the market. Give projection and line to get
        the model's chance of going over."""
        model = src.model()
        ix = src.get('index') or {}
        m = ix.get('model') or {}
        quant = (model or {}).get('q') or m.get('quantiles') or {}
        cal = (model or {}).get('cal') or m.get('calibration') or {}
        names = {k.lower(): k for k in list(quant) + ['Anytime TD']}
        key = names.get(prop.strip().lower())
        if key is None: return {'error': 'unknown prop type %r' % prop, 'available': sorted(names.values())}
        out = {'prop': key, 'source': 'model.json' if model else 'index.json (published model summary)',
               'blend_with_market': (model or {}).get('blend', m.get('blend')),
               'fit_at': (model or {}).get('fit_at') or (m.get('fit') or {}).get('fit_at'),
               'sample_size': ((model or {}).get('n') or {}).get(key),
               'smallest_line_that_earns_a_lean': rules()['minl'].get(key)}
        if key == 'Anytime TD':
            out['note'] = 'Anytime TD uses a usage model (carries and targets per game, position), not a swing pattern.'
            out['model'] = (model or {}).get('td')
            return out
        q = quant[key]
        out['calibration_shift'] = cal.get(key, 0)
        out['actual_over_projection'] = {'p%d' % i: q[i] for i in (5, 10, 25, 50, 75, 90, 95)}
        out['meaning'] = ('Quantiles of actual / projection from past games. p50 %s means the typical game lands at %s of the projection; '
                          'the chance of going over a line is the share of quantiles above line / projection, plus the shift.' % (q[50], q[50]))
        if projection is not None and line is not None:
            out['model_chance_over'] = p_over(q, cal.get(key, 0), projection, line)
        return out

    @server.tool(annotations=read_only)
    def health() -> Result:
        """How fresh the data is and which sections of the last build worked (core sections: schedule, injuries, depth, weekly, odds)."""
        h = dict(doc('health')); ix = src.get('index') or {}
        h.update(lines_at=ix.get('lines_at'), props_at=ix.get('props_at'), odds_plan=ix.get('odds_plan'), week=ix.get('week'),
                 data_from=src.where)
        return h

    @server.tool(annotations=writes_local_file)
    def add_idea(text: str, tags: list[str] | None = None) -> Result:
        """Saves an idea or note for the owner to ideas/inbox.jsonl (one JSON line, local file, not committed). The only tool that writes."""
        if not text.strip(): return {'error': 'text is empty'}
        os.makedirs(os.path.dirname(ideas) or '.', exist_ok=True)
        rec = {'at': clock().astimezone(datetime.timezone.utc).replace(microsecond=0).isoformat(), 'text': text.strip(), 'tags': tags or []}
        with open(ideas, 'a', encoding='utf-8') as f: f.write(json.dumps(rec, ensure_ascii=False) + '\n')
        return {'saved': True, 'file': ideas, 'idea': rec}

    return server


def main():
    create_server().run('stdio')


if __name__ == '__main__':
    main()
