"""Writes data.json again as named-field JSON files under api/v1/, for agents and scripts.

data.json is built for the page: positional rows (``row[8]``) and short keys (``pk['pr']``). This turns the same
numbers into documents where every value has a name (``gsis_id``, ``price``), one topic per file:

  index.json      what is here: season, build time, week, record, pick rules, model calibration, file sizes
  players.json    every offensive player and defender, with game log
  teams.json      team stats, depth chart, what each team allows
  games.json      this week's games with every book's lines, the fair lines, our model, movement, final scores
  picks.json      current official picks (NFL and college), strongest first
  picks_by_book.json  picks as each sportsbook alone would show them (only when data.json has ODD.PKB)
  props.json      every player prop with every book's line and price
  pick_log.json   every pick ever made with its result, newest first
  dynasty.json    dynasty values, future draft picks, the Sleeper lookup
  college.json    college games, picks, log, prospects, consensus big board
  health.json     which sections of the last build worked
  data.schema.json  a copy of schema/data.schema.json (the shape of data.json itself)

Runs in the daily refresh after build.py with only requirements.txt installed: standard library plus schema/.
    python api_export.py [data.json] [out_dir]        (defaults: data.json, api/v1)
"""
import json, os, shutil, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from schema.fields import rows_named  # noqa: E402
from schema.health import CORE_SECTIONS  # noqa: E402

API_VERSION = 1

# Short pick keys in data.json -> names. Keys that are not here (id, kind, title, legs, note, ...) keep their name.
# 'legs' (parlays) holds picks, and 'first' holds the first price seen; both are renamed the same way.
PICK_KEYS = {
    'k': 'type',        # g game line, p player prop, x parlay
    'eid': 'event_id', 'wk': 'week', 't': 'kickoff', 'a': 'away', 'h': 'home',
    'n': 'player', 'gid': 'gsis_id', 'tm': 'team', 'opp': 'opponent',
    'mk': 'market', 'sd': 'side', 'pt': 'line', 'pr': 'price', 'bk': 'book',
    's': 'score', 'v': 'ev', 'ls': 'lean_score', 'vs': 'value_score', 'ms': 'model_score',
    'pj': 'projection', 'pc': 'our_chance', 'srt': 'sort_key',
    'res': 'result', 'u': 'units', 'val': 'actual', 'fin': 'final', 'at': 'seen_at', 'first': 'first_seen',
    'dec': 'decimal', 'be': 'break_even',
}
FIRST_KEYS = {'pr': 'price', 'pt': 'line', 'bk': 'book'}   # inside 'first_seen' ('at' keeps its name)
# College picks (CFB.PK, CFB.LG): gid is the CollegeFootballData game id there, not a player id.
COLLEGE_PICK_KEYS = {
    'k': 'type', 'gid': 'game_id', 'wk': 'week', 't': 'kickoff', 'a': 'away', 'h': 'home', 'sd': 'side',
    'pt': 'line', 'pr': 'price', 'bk': 'book', 'others': 'others_line', 's': 'score', 'lines': 'book_lines',
    'res': 'result', 'fin': 'final', 'u': 'units',
}


# A college game's book entry (CFB.G books[book]) by position; entries from CollegeFootballData alone have the first five.
COLLEGE_BOOK_FIELDS = ['home_spread', 'total', 'home_moneyline', 'away_moneyline', 'open_spread',
                       'home_spread_price', 'away_spread_price']


def rename(d, keys):
    """A dict with its keys renamed by KEYS; keys not in KEYS stay as they are."""
    return {keys.get(k, k): v for k, v in d.items()}


def name_pick(p, keys=PICK_KEYS):
    """One pick (or log record, or parlay with legs) with named fields. Nothing is dropped."""
    out = rename(p, keys)
    if isinstance(out.get('first_seen'), dict): out['first_seen'] = rename(out['first_seen'], FIRST_KEYS)
    if isinstance(out.get('legs'), list): out['legs'] = [name_pick(l, keys) for l in out['legs']]
    return out


def _injury(v):
    return None if not v else {'status': v[0], 'injury': v[1], 'week': v[2]}


def _depth(v):
    return None if not v else {'label': v[0], 'starter': v[1]}


def _form(v):
    return None if not v else {'ppr_last3': v[0], 'std_last3': v[1], 'snap_pct_season': v[2], 'snap_pct_last3': v[3]}


def _tidy(row):
    """Gives the injury, depth label and form values of a named row their own field names."""
    if 'injury' in row: row['injury'] = _injury(row['injury'])
    if 'depth_label' in row: row['depth_label'] = _depth(row['depth_label'])
    if 'form' in row: row['form'] = _form(row['form'])
    return row


def players(data):
    """Offensive players (stats labelled by PC) then defenders, each with its game log."""
    log = data.get('LOG') or {}
    out = []
    for pos, rows in (data.get('P') or {}).items():
        labels = [c[0] for c in data['PC'][pos]]
        for r, row in zip(rows, rows_named('P', rows)):
            row['kind'] = 'offense'; row['pos'] = pos
            row['vals'] = dict(zip(labels, r[3]))
            out.append(row)
    for row in rows_named('X', data.get('X') or []):
        row['kind'] = 'idp'; out.append(row)
    for row in out:
        _tidy(row)
        row['log'] = rows_named('LOG', log.get(row['gsis_id'], []))
    return out


def teams(data):
    """One entry per team: name, stats by column label, depth chart, what the team allows to each position."""
    cols = [c[0] for c in data.get('TC') or []]
    names = data.get('N') or {}
    dep = (data.get('DEP') or {}).get('T') or {}
    alw = (data.get('ALW') or {}).get('T') or {}
    out = []
    for r in data.get('T') or []:
        code = r[0]
        out.append({'code': code, 'name': names.get(code), 'stats': dict(zip(cols, r[1:])),
                    'depth_chart': dep.get(code), 'allowed_per_position': alw.get(code)})
    return out


def _book_lines(b):
    """One game's book entry {m: [home ml, away ml], s: [home line, price, away line, price], o: [line, over, under]}."""
    out = {}
    if b.get('m'): out['moneyline'] = {'home': b['m'][0], 'away': b['m'][1]}
    if b.get('s'): out['spread'] = {'home_line': b['s'][0], 'home_price': b['s'][1], 'away_line': b['s'][2], 'away_price': b['s'][3]}
    if b.get('o'): out['total'] = {'line': b['o'][0], 'over_price': b['o'][1], 'under_price': b['o'][2]}
    return out


def games(data):
    """This week's games: books, fair lines, our model, context, line movement, plus finals so far."""
    odd = data.get('ODD') or {}
    labels = {(g['away'], g['home']): g['label'] for g in rows_named('G', data.get('G') or [])}
    lines = []
    for g in odd.get('G') or []:
        fair = g.get('fair') or {}
        mod = g.get('mod')
        lines.append({
            'event_id': g['id'], 'week': g['wk'], 'away': g['a'], 'home': g['h'], 'kickoff': g['t'],
            'label': labels.get((g['a'], g['h'])),
            'books': {bk: _book_lines(b) for bk, b in g['b'].items()},
            'fair': {'reference_books': fair.get('ref'),
                     'spread': None if not fair.get('s') else {'home_line': fair['s'][0], 'home_cover': fair['s'][1]},
                     'total': None if not fair.get('o') else {'line': fair['o'][0], 'over': fair['o'][1]},
                     'home_win': fair.get('m')},
            'model': None if not mod else {'home_margin': mod['m'], 'total': mod['t'], 'home_win': mod['wp']},
            'context': g.get('ctx'),
            'movement': [{'at': m[0], 'spread': m[1], 'total': m[2]} for m in g.get('mv') or []],
        })
    return {'week': lines[0]['week'] if lines else None,
            'remaining': rows_named('G', data.get('G') or []),
            'lines': lines,
            'finals': rows_named('ODD.FIN', odd.get('FIN') or [])}


def props(data):
    """Every player prop: books as {book: {over_line, over_price, under_line, under_price}}, recent games, projection."""
    out = []
    for p in (data.get('ODD') or {}).get('P') or []:
        out.append({
            'event_id': p['eid'], 'kickoff': p['ko'], 'player': p['n'], 'team': p['t'], 'pos': p['pos'],
            'gsis_id': p['gid'], 'opponent': p['opp'], 'market': p['mk'],
            'books': {bk: {'over_line': x[0], 'over_price': x[1], 'under_line': x[2], 'under_price': x[3]} for bk, x in p['b'].items()},
            'fair': None if not p.get('fair') else {'line': p['fair'][0], 'over': p['fair'][1]},
            'recent': [{'week': v[0], 'opponent': v[1], 'value': v[2]} for v in p.get('v') or []],
            'season_avg': p.get('avg'), 'last3_avg': p.get('l3'), 'projection': p.get('pj'),
            'median': p.get('md'), 'matchup_factor': p.get('fac'), 'usage': p.get('use'),
        })
    return out


def current_picks(data):
    """NFL picks then college picks, each with 'sport'; ODD.PK is already strongest first."""
    odd, cfb = data.get('ODD') or {}, data.get('CFB') or {}
    return ([dict(name_pick(p), sport='nfl') for p in odd.get('PK') or []]
            + [dict(name_pick(p, COLLEGE_PICK_KEYS), sport='college') for p in cfb.get('PK') or []])


def picks_by_book(data):
    """{book: [picks]} from ODD.PKB (per-sportsbook picks), or None when the build did not write it."""
    pkb = (data.get('ODD') or {}).get('PKB')
    if not isinstance(pkb, dict): return None
    return {bk: [dict(name_pick(p), sport='nfl') for p in ps] for bk, ps in pkb.items()}


def pick_log(data):
    """Every logged pick, newest first: NFL log then college log, each with 'sport'."""
    odd, cfb = data.get('ODD') or {}, data.get('CFB') or {}
    return ([dict(name_pick(p), sport='nfl') for p in odd.get('LG') or []]
            + [dict(name_pick(p, COLLEGE_PICK_KEYS), sport='college') for p in cfb.get('LG') or []])


def dynasty(data):
    """Dynasty values by player, values of future draft picks, and the Sleeper id lookup."""
    dy = data.get('DY') or {}
    return {'players': [_tidy(r) for r in rows_named('DY.P', dy.get('P') or [])],
            'draft_picks': rows_named('DY.K', dy.get('K') or []),
            'sleeper_lookup': {sid: _tidy(named) for sid, named in
                               zip((dy.get('L') or {}).keys(), rows_named('DY.L', list((dy.get('L') or {}).values())))}}


def college(data):
    """College games, picks, log, record, prospects (CF is null on days without CollegeFootballData access)."""
    cfb, cf = data.get('CFB') or {}, data.get('CF')
    games_ = [{'game_id': g['id'], 'week': g['wk'], 'kickoff': g['t'], 'away': g['a'], 'home': g['h'],
               'away_conference': g.get('ac'), 'home_conference': g.get('hc'), 'neutral': g.get('neutral'),
               'books': {bk: dict(zip(COLLEGE_BOOK_FIELDS, v)) for bk, v in (g.get('books') or {}).items()},
               'spread': g.get('sp'), 'total': g.get('ou'), 'home_win': g.get('wp'),
               'model_spread': g.get('mod')} for g in cfb.get('G') or []]
    cb = (cf or {}).get('CB')
    sources = rows_named('CF.CB.S', cb.get('S') or []) if cb else None
    board = None   # null (not empty) when the day's build had no college prospect data
    if cb:
        board = []
        for r in cb.get('P') or []:
            row = rows_named('CF.CB.P', [r])[0]
            row['ranks'] = {s['source']: rank for s, rank in zip(sources, r[len(row):])}
            board.append(row)
    return {'games': games_,
            'picks': [name_pick(p, COLLEGE_PICK_KEYS) for p in cfb.get('PK') or []],
            'log': [name_pick(p, COLLEGE_PICK_KEYS) for p in cfb.get('LG') or []],
            'record': cfb.get('REC'), 'backtest': cfb.get('BT'), 'lines_at': cfb.get('at'),
            'prospects': rows_named('CF.P', cf.get('P') or []) if cf else None,
            'draft_year': cf.get('draft') if cf else None,
            'big_board': board, 'big_board_sources': sources}


def health(data):
    """Build health: each section's status, where the data came from, and whether a core section failed."""
    meta = data.get('META') or {}
    h = meta.get('health') or {}
    core = CORE_SECTIONS   # the sections check_health.py fails the run on
    failed = sorted(k for k, v in h.items() if str(v).startswith('failed'))
    return {'built': meta.get('built'), 'season': meta.get('season'), 'sections': h, 'sources': meta.get('sources'),
            'failed': failed, 'core_failed': [k for k in failed if k in core] + [k for k in core if k not in h],
            'ok': not [k for k in failed if k in core] and all(k in h for k in core)}


def index(data, docs):
    """The front page of the API: what is in it and the numbers an agent asks for first."""
    meta, odd = data.get('META') or {}, data.get('ODD') or {}
    gl = odd.get('G') or []
    return {'api_version': API_VERSION, 'data_schema': meta.get('schema'), 'season': meta.get('season'),
            'built': meta.get('built'), 'week': gl[0]['wk'] if gl else None,
            'books': odd.get('books'), 'record': odd.get('REC'), 'model_record_vs_close': odd.get('MR'),
            'rules': odd.get('RU'),
            'model': {'fit': meta.get('model'), 'blend': odd.get('MB'), 'calibration': odd.get('MC'),
                      'quantiles': odd.get('MQ')},
            'lines_at': odd.get('at'), 'props_at': odd.get('pat'), 'odds_plan': odd.get('plan'),
            'files': sorted(k + '.json' for k in docs) + ['index.json', 'data.schema.json'],
            'counts': {k: len(v) for k, v in docs.items() if isinstance(v, list)}}


def build(data):
    """Every document as {file name without .json: document}. index.json comes last (it counts the others' items)."""
    docs = {'players': players(data), 'teams': teams(data), 'games': games(data), 'picks': current_picks(data),
            'props': props(data), 'pick_log': pick_log(data), 'dynasty': dynasty(data), 'college': college(data),
            'health': health(data)}
    pbb = picks_by_book(data)
    if pbb is not None: docs['picks_by_book'] = pbb
    docs['index'] = index(data, docs)
    return docs


def export(data, out_dir='api/v1'):
    """Writes the API files for a data.json dict into OUT_DIR, removes any other .json file there, and returns the paths written."""
    os.makedirs(out_dir, exist_ok=True)
    written = []
    for name, doc in build(data).items():
        path = os.path.join(out_dir, name + '.json')
        with open(path, 'w', encoding='utf-8') as f: json.dump(doc, f, ensure_ascii=False, separators=(',', ':'))
        written.append(path)
    path = os.path.join(out_dir, 'data.schema.json')
    shutil.copyfile(os.path.join(HERE, 'schema', 'data.schema.json'), path)
    written.append(path)
    for f in os.listdir(out_dir):   # a file from an earlier build that this one did not write (e.g. picks_by_book.json) is stale
        if f.endswith('.json') and os.path.join(out_dir, f) not in written: os.remove(os.path.join(out_dir, f))
    return written


def main():
    src = sys.argv[1] if len(sys.argv) > 1 else 'data.json'
    out = sys.argv[2] if len(sys.argv) > 2 else 'api/v1'
    with open(src, encoding='utf-8') as f: data = json.load(f)
    written = export(data, out)
    print('api export ok: %d files in %s (%d bytes)' % (len(written), out, sum(os.path.getsize(p) for p in written)))


if __name__ == '__main__':
    main()
