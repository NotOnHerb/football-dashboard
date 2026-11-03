"""The betting and projection logic shared by build.py, model_fit.py and the analyst tools.

  odds         implied chances, decimal prices, removing the bookmaker's cut, consensus lines
  rules        the pick thresholds (RULES) and the value / lean scores
  projections  the player projection recipe, matchup factor, chance of over, anytime-TD chance
  team_model   NFL and college team ratings from game scores
  picks        game and prop sides, the official pick list
  parlays      parlay of the week, of the game, anytime TD parlay
  grading      grading the pick log from final scores and weekly stats
"""
