# Roadmap

The dream: a football app that's fun and powerful to use, starting as a personal assistant for bets,
fantasy lineups and football knowledge, then opened up to help other people too.

## Done recently
- Player cards (Oct 27): tap any player name for headshot, bio, stats, game log chart, this week's
  matchup, dynasty value, live ESPN news with the RotoWire fantasy note, and his props this week.
- Colored stat cells site-wide, personalized start/sit, NFL / Fantasy / Betting layout.
- Betting tab v2: Picks (pick of the week, game-line picks, prop picks with reasons), Games (card per game: every line, win % bar, our model, ATS and over records, rest, line movement), Props (lean, projection, last-games dots, hit rate, opponent grade, price value). Sportsbook picker: best available or one book. Value = price vs fair odds (Pinnacle with its cut removed by Shin's method; market middle when Pinnacle is missing).
- Projections v2 (backtested on 2025-26 games): 85% season + 15% last 3, plus about 4 games of last season; props use chance-of-going-over from how each stat swings game to game, blended 50/50 with the sportsbooks' fair odds; anytime TD from usage (carries, targets, position), no picks above +300. Fantasy start/sit uses the same base. model_fit.py refits weekly into model.json.
- Betting v3: our picks logged each refresh, locked at kickoff, graded automatically (Results view, running record in units). My bets slip (saved per browser, grades itself, stakes and profit). Weather at kickoff for outdoor games (Open-Meteo). Same-game combos (QB + receiver who hit together). Line moves list. Long shots past +250 and stale prices (10%+ better than fair) are never picks.

## Next up (agreed Oct 27, 2026)
1. Home screen, "This week at a glance": your lineup moves, biggest matchup edges, injury news for
   your players, top diamonds.
2. Bet and prediction tracker: log bets, picks and start/sit calls, then see your record and profit.
   The "keeps score on you" idea from day one. (Partly done: My bets and Results on the Betting tab;
   start/sit calls still to add.)
3. Install like an app on a phone home screen (icon, full screen).
4. Trade analyzer: enter a 2-for-1 or 3-for-2 deal, see who wins on value, team before and after.
5. Playoff schedule strength: soft matchups in fantasy playoff weeks 14 to 17.
6. About page: credit data sources, note it's not betting advice, before sharing widely.

## The Analyst (built Oct 29, 2026; details and playbooks in analyst/README.md)
A research assistant that keeps refining the model toward the dream. Lives outside the build chat.
Free route: runs on the existing Claude plan, no API key, no per-question cost.
- One front door, the Analyst Desk: a private page in the Claude account (works on a phone) with an
  ask box, an idea inbox, grades and weekly reports.
- Behind it:
  - Site code grades every pick and tracks closing-line value (plain code, already mostly exists).
  - Researcher: weekly scheduled run (Tuesday after Monday night). Reviews the week, checks the model
    for tilts, tests queued ideas on past seasons it hasn't seen, writes proposals with numbers.
  - Skeptic: a separate run that never sees the researcher's reasoning. Labels each proposal
    Solid, Shaky or Fails. Can only block what fails on unseen games; rejected ones stay visible.
  - Ask box: quick answers about the data any time.
- Authority: owner > skeptic > researcher. Every change needs the owner's approval; both sides are
  shown on every proposal. Approved changes are logged in an analyst notebook and tracked afterward.
- Phone notification when the weekly report is ready.
- Guardrails: tested on unseen games, judged on closing-line value and long-run units, never places
  bets or sets stakes. Realistic target: about 53-56% at normal prices over hundreds of picks.
- Optional later: public ask box on the site (needs a paid API key; roughly $1/month on the light
  model or $15/month on the smart one at 10 questions a day), and an nfelo-style game model.
- Decided: daily sync 6:13 AM CT, researcher Tuesday 5:47 AM, skeptic Tuesday 7:57 AM (phone notification); all three
  workers from day one; public ask box not now.

## Later
- Kicker, defense and IDP projections in start/sit and lineups.
- Trimmed default columns per position with an "All stats" toggle.
- Team colors as accents.
- Blocking grades for linemen (ESPN block win rates or PFF).
- College scores, standings and team pages; could become its own top tab.
- Paid live data feed for real-time stats, injuries and odds (plug into sources.py).
- Community: forum, pick'em, mini-games, leaderboards (needs user accounts).

## Waiting on
- ESPN league 464142 made public by the commissioner, to verify the ESPN connection on a real league.
- Odds API $30 plan: set repo variable ODDS_PLAN=paid (props refresh every run, any day) and backtest leans on historical odds.
- Big board consensus refresh every few weeks (boards/boards_2027.csv).
