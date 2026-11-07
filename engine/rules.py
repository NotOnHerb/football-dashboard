"""The pick rules: one set of thresholds for the build, the page (data.json ODD.RU) and the analyst Desk.

RULES keys:
  val    expected value at the best price for value scores 1, 2 and 3
  stale  an expected value above this is treated as a stale price, not a pick
  mlmax, mlmin  moneylines outside this range never score on value
  model  points of model edge on a spread for the model score
  minl   smallest prop line that can earn a lean score, per prop type
  pick   total score a side needs to be an official pick
  tdmax  longest anytime-TD price that can earn a lean score
"""

RULES = {'val': [.025, .045, .07], 'stale': .10, 'mlmax': 250, 'mlmin': -300, 'model': 2.5,
         'minl': {'Pass yds': 150, 'Rush yds': 25, 'Rec yds': 25, 'Receptions': 2.5, 'Pass TDs': .5}, 'pick': 2, 'tdmax': 300}


def value_score(ev):
    """0-3 from expected value at the price (None scores 0)."""
    v = ev
    return 0 if v is None else 3 if v >= RULES['val'][2] else 2 if v >= RULES['val'][1] else 1 if v >= RULES['val'][0] else 0


def lean_tier(edge):
    """0-3 from our chance minus the price's implied chance on a prop."""
    e = edge
    return 3 if e >= LEAN_TIERS[2] else 2 if e >= LEAN_TIERS[1] else 1 if e >= LEAN_TIERS[0] else 0


# Fixed parts of the pick rules that RULES (serialized into data.json) does not carry. Named here so the build, the
# engine and the MCP server's explanations read one number. Changing one changes picks.
LEAN_TIERS = (.04, .07, .10)    # lean tier 1, 2, 3: our chance minus the price's implied chance on a prop
LEAN_MIN_GAMES = 4              # a prop needs at least this many games of history to earn a lean
LEAN_MAX_SCORE = 2              # a lean adds at most this much to a prop's (or anytime TD's) score
# College spread picks (build.py): with COLLEGE_MIN_BOOKS+ books, one book's spread COLLEGE_GAP_MIN to just under
# COLLEGE_GAP_MAX points off the median of the others, at a price of COLLEGE_MIN_PRICE or better. COLLEGE_EXCLUDED_BOOKS
# never supply the odd number. Every college pick listed is official: score 2 at a gap of COLLEGE_GAP_STRONG or more, else 1.
COLLEGE_MIN_BOOKS = 3
COLLEGE_GAP_MIN = 1
COLLEGE_GAP_MAX = 3
COLLEGE_GAP_STRONG = 1.5
COLLEGE_MIN_PRICE = -118
COLLEGE_UNPRICED_PRICE = -110   # a pick from a book that posts no spread price shows none and, when it wins, is paid as if it were this
COLLEGE_EXCLUDED_BOOKS = ('Pinnacle',)
COLLEGE_MIN_SCORE = 1           # a listed college pick scores this, or COLLEGE_STRONG_SCORE from a gap of COLLEGE_GAP_STRONG
COLLEGE_STRONG_SCORE = 2
