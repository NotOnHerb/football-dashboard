"""Writes the Desk's RULES prompt from engine/rules.py, so the Desk and the engine cannot drift apart.

python analyst/desk_rules.py          rewrite the generated block in analyst/desk.html
python analyst/desk_rules.py --check  exit 1 if the block in desk.html differs from what the engine gives

analyst/desk.html is a page published to the Desk, so it cannot import Python: it carries a copy of the prompt between
the BEGIN/END markers below. tests/test_desk_rules.py fails when that copy differs from `desk_block()`. The numbers in
the prompt (lean tiers, the longest anytime-TD price, the moneyline range, the score a pick needs) come from
engine.rules; the sentences around them, including how the projection works, are written here.
"""
import os, re, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from engine.rules import LEAN_MAX_SCORE, LEAN_TIERS, RULES

DESK = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'desk.html')
BEGIN = '// BEGIN GENERATED RULES (analyst/desk_rules.py; edit engine/rules.py, then run it)'
END = '// END GENERATED RULES'
_ROMAN = {1: 'I', 2: 'II', 3: 'III'}


def _price(n):
    """An American price as the prompt writes it: +300, -300."""
    return ('+' if n > 0 else '-') + str(abs(int(n)))


def _js(s):
    """A JS single-quoted string literal."""
    return "'" + s.replace('\\', '\\\\').replace("'", "\\'") + "'"


def prompt_parts(rules=None, lean_tiers=None):
    """The prompt as the JS string pieces that desk.html joins with '+', from the pick rules (default: engine.rules)."""
    rules = RULES if rules is None else rules
    t = ['%g' % round(x * 100, 6) for x in (LEAN_TIERS if lean_tiers is None else lean_tiers)]
    # "a pick needs level II": a lean adds at most LEAN_MAX_SCORE to a prop's score, so the sentence is only true when the
    # score a pick needs is that level. Any other rule needs the sentence reworded here, so refuse instead of misstating it.
    if rules['pick'] != LEAN_MAX_SCORE or rules['pick'] not in _ROMAN:
        raise ValueError('RULES["pick"]=%r with LEAN_MAX_SCORE=%r: reword the pick sentence in analyst/desk_rules.py'
                         % (rules['pick'], LEAN_MAX_SCORE))
    level = _ROMAN[rules['pick']]
    return [
        'You are the Analyst for a personal NFL dashboard (football-dashboard). You help its owner understand the betting '
        'picks, player props, games and the projection model, and you keep refining the model with him through weekly '
        'reports and proposals. ',
        'How the model works: projections are 85%% season average + 15%% last 3 games, plus about 4 games of last season '
        'early on, adjusted for the opponent (matchup factor, capped -20%% to +25%%). For props, the chance of going over '
        'comes from how that stat swings game to game, nudged weekly by a calibration, then blended 50/50 with the '
        'sportsbooks’ fair odds (Pinnacle with its cut removed, or the middle of the books). A lean needs our chance to '
        'beat the price’s break-even by %s+ points (I), %s+ (II), %s+ (III); a pick needs level %s, or a smaller lean '
        'plus a better-than-fair price. Anytime TD chance comes from usage (carries, targets, position); no TD picks '
        'above %s; no moneylines above %s or below %s. ' % (
            t[0], t[1], t[2], level, _price(rules['tdmax']), _price(rules['mlmax']), _price(rules['mlmin'])),
        'Rules: use the tools to look things up before answering anything about data; say when a sample is too small to '
        'mean much; never present betting as a sure thing; never suggest stake sizes; this is not betting advice. You '
        'cannot change the model or the site yourself: changes go through a weekly proposal that a separate skeptic '
        'checks and the owner approves. If the owner asks to queue something to test, use add_idea. Answer in plain '
        'English, short and direct, like a sharp friend who knows football and numbers. Today is ',
    ]


def desk_block(rules=None, lean_tiers=None):
    """The generated lines of desk.html (LF line ends), markers included."""
    a, b, c = prompt_parts(rules, lean_tiers)
    return '\n'.join([
        BEGIN,
        'var RULES=' + _js(a) + '+',
        ' ' + _js(b) + '+',
        ' ' + _js(c) + '+new Date().toDateString()+\'.\';',
        END,
    ])


def current_block(html):
    """The block now in desk.html (markers included), or None when the markers are missing."""
    m = re.search(re.escape(BEGIN) + r'.*?' + re.escape(END), html, re.S)
    return m.group(0).replace('\r\n', '\n') if m else None


def main(argv):
    html = open(DESK, encoding='utf-8', newline='').read()   # newline='': keep the file's own line endings
    crlf = '\r\n' in html
    want = desk_block()
    if '--check' in argv:
        if current_block(html) == want:
            return 0
        print('analyst/desk.html RULES differ from engine/rules.py: run python analyst/desk_rules.py', file=sys.stderr)
        return 1
    if current_block(html) is None:
        print('desk.html has no generated RULES block (markers missing)', file=sys.stderr)
        return 1
    new = want.replace('\n', '\r\n') if crlf else want
    html = re.sub(re.escape(BEGIN) + r'.*?' + re.escape(END), lambda m: new, html, flags=re.S)
    open(DESK, 'w', encoding='utf-8', newline='').write(html)
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
