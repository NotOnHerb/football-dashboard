"""The Desk's RULES prompt (analyst/desk.html) must be what engine/rules.py says.

desk.html carries a generated copy of the prompt between markers; `python analyst/desk_rules.py` rewrites it.
If someone changes a threshold in engine/rules.py (or edits the block by hand) and does not regenerate, this fails.
"""
import copy, os, re, sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, 'analyst'))
sys.path.insert(0, ROOT)
import desk_rules  # noqa: E402
from engine.rules import LEAN_MAX_SCORE, LEAN_TIERS, RULES  # noqa: E402


def desk_html():
    return open(os.path.join(ROOT, 'analyst', 'desk.html'), encoding='utf-8').read()   # universal newlines: CRLF checkouts too


def test_desk_rules_match_engine():
    got = desk_rules.current_block(desk_html())
    assert got is not None, 'analyst/desk.html lost its BEGIN/END GENERATED RULES markers'
    assert got == desk_rules.desk_block(), 'desk.html RULES differ from engine/rules.py: run python analyst/desk_rules.py'


def test_desk_rules_carry_the_engine_numbers():
    text = ' '.join(desk_rules.prompt_parts())
    t = ['%g' % round(x * 100, 6) for x in LEAN_TIERS]
    assert 'by %s+ points (I), %s+ (II), %s+ (III)' % tuple(t) in text
    assert 'no TD picks above +%d' % RULES['tdmax'] in text
    assert 'no moneylines above +%d or below -%d' % (RULES['mlmax'], -RULES['mlmin']) in text


def test_changing_a_rule_changes_the_desk_prompt():
    """The generator reads the rules, so a drifted desk.html is caught instead of passing by coincidence."""
    base = desk_rules.desk_block()
    r = copy.deepcopy(RULES)
    r['tdmax'], r['mlmax'], r['mlmin'] = 350, 200, -250
    block = desk_rules.desk_block(r, (.05, .08, .125))
    assert block != base and base == desk_rules.current_block(desk_html())
    assert 'no TD picks above +350; no moneylines above +200 or below -250' in block
    assert 'by 5+ points (I), 8+ (II), 12.5+ (III)' in block   # a fractional tier is not rounded
    assert 'a pick needs level %s,' % desk_rules._ROMAN[r['pick']] in block


def test_hand_edit_of_the_block_is_caught():
    html = desk_html()
    now = 'no TD picks above ' + desk_rules._price(RULES['tdmax'])
    edited = html.replace(now, 'no TD picks above ' + desk_rules._price(RULES['tdmax'] + 50))
    assert edited != html and desk_rules.current_block(edited) != desk_rules.desk_block()


def test_a_pick_rule_the_sentence_cannot_state_is_refused():
    r = copy.deepcopy(RULES)
    r['pick'] = LEAN_MAX_SCORE + 1
    with pytest.raises(ValueError):
        desk_rules.desk_block(r)


def test_one_generated_block_and_one_rules_assignment():
    html = desk_html()
    assert html.count(desk_rules.BEGIN) == 1 and html.count(desk_rules.END) == 1
    writes = re.findall(r'\bRULES\s*(\+?=)(?!=)', html)
    assert writes == ['='] and html.count('var RULES=') == 1   # no second assignment or += that changes the block's prompt
