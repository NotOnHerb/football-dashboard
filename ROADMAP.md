# Roadmap

The dream: a football app that's fun and powerful to use, starting as a personal assistant for bets,
fantasy lineups and football knowledge, then opened up to help other people too.

## Done recently
- Player cards (Oct 27): tap any player name for headshot, bio, stats, game log chart, this week's
  matchup, dynasty value, live ESPN news with the RotoWire fantasy note, and his props this week.
- Colored stat cells site-wide, personalized start/sit, NFL / Fantasy / Betting layout.
- Betting tab v2: Picks (pick of the week, game-line picks, prop picks with reasons), Games (card per game: every line, win % bar, our model, ATS and over records, rest, line movement), Props (lean, projection, last-games dots, hit rate, opponent grade, price value). Sportsbook picker: best available or one book. Value = price vs the market's no-vig fair odds.

## Next up (agreed Oct 27, 2026)
   Needs a free key from the-odds-api.com, stored as a GitHub secret (never in the page).
1. Betting next: grade our picks automatically every week and show the running record; "My bets" slip saved per person; alerts when a line moves a lot.
2. Home screen, "This week at a glance": your lineup moves, biggest matchup edges, injury news for
   your players, top diamonds.
3. Bet and prediction tracker: log bets, picks and start/sit calls, then see your record and profit.
   The "keeps score on you" idea from day one.
4. Install like an app on a phone home screen (icon, full screen).
5. Trade analyzer: enter a 2-for-1 or 3-for-2 deal, see who wins on value, team before and after.
6. Playoff schedule strength: soft matchups in fantasy playoff weeks 14 to 17.
7. About page: credit data sources, note it's not betting advice, before sharing widely.

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
