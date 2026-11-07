# 06 — Models and betting logic

All of this lives in `build.py:458-1044`, with the prop model fitted in `model_fit.py`.
Parts of the pick logic are re-implemented in `template.html` (single-book views) and `analyst/snapshot.py`.

## Odds math primitives (`build.py:484-503`)

| Function | What it does |
|---|---|
| `prob(a)` | American odds → implied probability |
| `dec(a)` | American → decimal |
| `novig(p1, p2)` | Removes the bookmaker's cut with **Shin's method** (binary search on z) |
| `mode`, `med` | Consensus line (most common, ties broken toward the median) |
| `Phi` | Normal CDF for win probability from a margin (`σ = 13.5`) |

## NFL team model (`build.py:504-537`)

- Ridge regression on margins: `home − away = R[h] − R[a] + HFA`, `λ = 8`.
- A second ridge on points scored gives offense/defense ratings and a projected total.
- **Prior**: half of last season's ratings.
- **Walk-forward record (`MR`)**: from week 4, refit on prior weeks and score against nflverse closing lines when the
  model differs by ≥ 2.5 (spread) or ≥ 3 (total). As of 2026-11-02: spreads 18-15-1, totals 11-19.
- The model gives context on game cards, and adds one strength point to a spread pick when it agrees by ≥ 2.5.

## Fair odds (`build.py:539-551` games, `build.py:612-623` props)

The no-vig chances below use Shin's method (`engine/odds.py` `no_vig_shin`); Anytime TD and the blend's off-line
fallback are the exceptions noted below.

- **Game lines** (spread, total, moneyline): Pinnacle no-vig when Pinnacle posts the market, at Pinnacle's own line
  (which can differ from the consensus line; `game_ev` then moves the chance to the line being priced). Otherwise
  the median no-vig of the other books, which needs at least 3 books (at the consensus line for spreads and totals).
  `fair.ref` records which source each market used (`Pinnacle` or `market`); for spreads and totals it says
  `market` even when fewer than 3 books leave the chance empty.
- **Props**: the median no-vig across every book quoting both sides at the consensus line, which needs at least
  3 books. Pinnacle is one of those books when it posts the prop, with no special weight. Fewer than 3 books leaves
  the prop with no fair chance.
- **Anytime TD**: books post only "yes", so the fair chance is the median implied chance across books divided by
  1.12 (a typical cut), capped at 0.95.

The blend (step 4 below) prices each side at its best quote. When that quote's line isn't the prop's fair line, or
the prop has no fair chance, the market chance comes from the first book (in the Odds API's book order) posting
both sides of that line, with the cut split proportionally rather than by Shin (`engine/picks.py` `market_over`).

## Game-line picks (`build.py:654-756`)

Rules live in `RU` (`build.py:655`) and are shipped to the page in `ODD.RU`:

| Rule | Value |
|---|---|
| Value tiers (EV vs fair) | 2.5% / 4.5% / 7% → strength 1/2/3 |
| Stale price (too good to be real) | EV > 10% → not a pick |
| Moneyline range | −300 … +250 |
| Model agreement bonus | +1 if model edge ≥ 2.5 pts |
| Pick threshold | strength ≥ 2 |
| Anytime TD max price | +300 |
| Minimum prop lines | Pass yds 150, Rush/Rec yds 25, Rec 2.5, Pass TD 0.5 |

`gev` adjusts the fair probability when the best available line differs from the fair line, at 2% per half-point
for spreads and 1.5% for totals, plus 3% for crossing 3 or 7.

## Prop projections and picks (`build.py:600-763`)

1. Match the Odds API player name → our player by normalized name, preferring a player on one of the two teams.
2. **Projection** `pj = base × fac`:
   - `base` = 0.85·season + 0.15·last3, shrunk toward last season (`K0 = 4`).
   - `fac` = matchup factor from points allowed to that position: `1 + 0.5·(opp/league − 1)`, clamped to 0.8–1.25.
3. **Chance of over** `pover`: share of model quantiles above `line / pj`, plus the calibration nudge, clamped to 0.01–0.99.
4. **Blend**: `P = 0.5·pover + 0.5·market fair`.
5. **Edge tiers** on `P − implied`: 4% / 7% / 10% → 1/2/3. Needs ≥ 4 games and the minimum line.
6. Value score from fair-odds EV as for game lines. A side is never picked if our own chance says it loses at that price.
7. Anytime TD: logistic usage model × matchup factor, capped at 0.9, blended with market fair (books' "yes" median ÷ 1.12).
8. Injured players (Out / IR / Reserve / Doubtful) are excluded. Picks are sorted by `srt`.

## Parlays (`build.py:764-880`)

- **Parlay of the week**: 2-3 of the strongest non-TD picks, from different games, all priced at **one** book (not Pinnacle).
- **Anytime TD parlay**: likeliest scorers (≥ 30%, price ≤ +300), different games, one book.
- **Parlay of the game**: QB over + his receiver over that have cleared together in ≥ 50% of shared games (≥ 4).
  The joint chance is allowed up to 1.25× the independent product.
- All are logged and graded as their own record.

## Pick ledger and grading (`build.py:881-941`)

- Each refresh drops ungraded picks whose games haven't started, then re-adds today's picks, keeping the `first` seen
  price. The effect: **a pick is whatever was a pick at the last refresh before kickoff.** With a daily 10:00 UTC
  refresh, that means a Sunday pick is based on Sunday-morning lines.
- Game picks are graded from nflverse final scores. Props are graded from that week's `LOG` row. A player with no row
  is graded `V` (void).
- Units: win = decimal − 1, loss = −1, push/void = 0.

## College betting (`build.py:942-1044`)

- Ratings: ridge on margins, prior = 0.6 × last season, neutral-site aware. These are shown as context only. The note
  says the model vs the close is "about 50%".
- Lines come from CFBD (DraftKings, ESPN Bet, Bovada, Caesars) merged with the Odds API college pull (Fri/Sat only,
  budget-aware). Team names are matched with an alias table and a 36-hour window.
- **"Best number" rule**: with 3+ books, take the one book whose spread is 1-3 points off the median of the others.
  Gap 1.5-3 is strength 2, gap 1-1.5 is strength 1. Skip if the price is worse than −118.
  The backtest (2023-25: 314-249, 55.8%) is **hard-coded** in the output, not recomputed.

## Prop model fit (`model_fit.py`)

See [04-backend-pipeline.md](04-backend-pipeline.md#model_fitpy-projection-model-111-lines). One thing matters for
correctness: the swing quantiles `q` are learned on **last season**, and calibration `cal` is measured on **this
season**. That keeps the two from fitting the same games twice.

## Where the logic is duplicated

| Logic | `build.py` | `template.html` | `snapshot.py` | `model_fit.py` / `lab.py` |
|---|---|---|---|---|
| Implied prob / decimal | ✔ (twice: NFL and college) | ✔ | ✔ | |
| No-vig | Shin | see [05](05-frontend.md) | **proportional** | |
| Best price across books | `gq`, `pq` | ✔ (single-book views) | `best` | |
| `pover` (chance of over) | ✔ | ✔ | ✔ | ✔ (calibration) |
| Projection recipe | inline | | | `base`, `current_recipe` |
| Pick rules `RU` | defines | reads `ODD.RU`, re-applies | | |

The analyst sync playbook already asks the agent to confirm that `template.html` and `build.py` still produce the same
pick ids. The playbook is working around the duplication. Shared logic would remove it.
