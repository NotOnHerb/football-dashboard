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
    return 3 if e >= .10 else 2 if e >= .07 else 1 if e >= .04 else 0
