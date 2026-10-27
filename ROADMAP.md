# Roadmap

The dream: a football app that's fun and powerful to use, starting as a personal assistant for bets,
fantasy lineups and football knowledge, then opened up to help other people too.

## In progress
- Player cards: tap any player for headshot, stats, game log, this week's matchup, dynasty value,
  latest news, and (later) prop lines with hit rates.

## Next up (agreed Oct 27, 2026)
1. Betting tab: game lines, player props next to averages and matchups, flagged lines that look off.
   Needs a free key from the-odds-api.com, stored as a GitHub secret (never in the page).
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
- the-odds-api.com free key for the Betting tab.
- Big board consensus refresh every few weeks (boards/boards_2027.csv).
