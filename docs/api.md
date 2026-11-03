# Agent API

`data.json` is built for the page: positional rows (`row[8]`) and short keys (`pick['pr']`). For scripts and agents
the same numbers are also written with names: `api_export.py` turns `data.json` into JSON files under `api/v1/`, and
`mcp_server/` serves them over MCP. Nothing here changes `data.json`.

## The files

The daily refresh runs `python api_export.py` right after `build.py` and commits `api/`, so the files are published
next to the page: https://notonherb.github.io/football-dashboard/api/v1/index.json. Locally,
`python api_export.py [data.json] [out_dir]` writes them (default `api/v1/`), and removes any other `.json` file in that
folder, so nothing from an earlier build lingers. Prices are American odds. `schema/fields.py` is the source of the row names.

**The files are as of the build** (`built` in `index.json`, once a day). They still list games that have since kicked off;
the page hides those when you open it, and so do the MCP tools (see below). If you read the files directly, drop picks,
games and props whose `kickoff` has passed.

Rows are named objects, with these exceptions that are passed through from `data.json` as positional lists (their layout is in
`03-data-contract.md` on the knowledgebase branch): `teams.json` `depth_chart` and `allowed_per_position`, `games.json`
`context` (for example `rest` is `[away days, home days]`), `props.json` `usage`, and `college.json` `backtest`.
A `null` means the build had no such data that day; an empty list means there was data and none matched.

| File | Holds |
|---|---|
| `index.json` | `api_version`, `season`, `built`, `week`, `books`, `record` (pick records), `rules` (the pick thresholds), `model` (blend, calibration, quantiles), `lines_at`, `props_at`, `files`, `counts` |
| `players.json` | list. Offensive players (`kind: "offense"`, `vals` keyed by stat label) and defenders (`kind: "idp"`). Each has `name, team, pos, gsis_id, games, injury, depth_label, form` and a `log` of its games |
| `teams.json` | list of 32: `code, name, stats` (by column label), `depth_chart`, `allowed_per_position` |
| `games.json` | `{week, remaining, lines, finals}`. `lines`: per game `event_id, away, home, kickoff, books` (moneyline, spread, total per book), `fair`, `model`, `context`, `movement` |
| `picks.json` | list. Current official picks, strongest first, each with `sport` (`nfl` or `college`) |
| `picks_by_book.json` | `{book: [picks]}`, the picks each sportsbook alone would give. Written only when `data.json` has `ODD.PKB` (see below) |
| `props.json` | list. Every player prop: `player, gsis_id, market, books` (`over_line, over_price, under_line, under_price` per book), `fair`, `projection`, `recent` games |
| `pick_log.json` | list. Every pick ever logged, newest first, with `result` (`W L P V`, null while pending) and `units`. Parlays carry their `legs` |
| `dynasty.json` | `{players, draft_picks, sleeper_lookup}` |
| `college.json` | `{games, picks, log, record, backtest, prospects, big_board, big_board_sources}`. A game's `books` are `{book: {home_spread, total, home_moneyline, away_moneyline, open_spread, home_spread_price, away_spread_price}}` (the last two only for books from The Odds API). `log` holds the newest 200 picks (the build keeps no more). `prospects`, `big_board` and `big_board_sources` are `null` on days without college prospect data (`data.json` `CF` is null) |
| `health.json` | `sections` (status of each build section), `sources`, `failed`, `core_failed`, `ok` |
| `data.schema.json` | a copy of `schema/data.schema.json`, the shape of `data.json` itself |

### Pick field names

Picks in `picks.json`, `pick_log.json` and `picks_by_book.json` use these names for `data.json`'s short keys. Nothing is
dropped, and keys with no entry here (`id`, `kind`, `title`, `legs`, `note`) keep their name.

`k` type (`g` game line, `p` prop, `x` parlay, `c` college) · `eid` event_id · `wk` week · `t` kickoff · `a` away · `h` home ·
`n` player · `gid` gsis_id (a prop) or game_id (college) · `tm` team · `opp` opponent · `mk` market · `sd` side ·
`pt` line · `pr` price · `bk` book · `s` score · `v` ev · `ls` lean_score · `vs` value_score · `ms` model_score ·
`pj` projection · `pc` our_chance · `srt` sort_key · `res` result · `u` units · `val` actual · `fin` final ·
`at` seen_at · `first` first_seen (`price, line, book, at`) · `dec` decimal · `be` break_even.

Sides: `hs`/`as` home/away spread, `ov`/`un` over/under a total, `mh`/`ma` home/away moneyline, `o`/`u`/`y` prop over/under/anytime-TD yes.
The mapping is `PICK_KEYS` and `COLLEGE_PICK_KEYS` in `api_export.py`.

### Per-book picks (`ODD.PKB`)

`get_picks(book)` and `picks_by_book.json` depend on `data.json` carrying `ODD.PKB`, `{book name: [picks in ODD.PK's
shape]}` (added by the build separately from this API). Until the build writes it there is no `picks_by_book.json`, and
`get_picks(book)` falls back to the subset of current picks whose best price is at that book (not what that book alone would
pick). The tool result says which one you got (`source`). An unknown book name is an error that lists the known books. The export assumes the `{book: [picks]}` shape; if `PKB` is shaped differently, adjust `picks_by_book` in `api_export.py`.

## The MCP server

`python -m mcp_server.server` (from the repo root; setup in `AGENTS.md` and `.mcp.json.example`) speaks MCP over stdio.

Where the data comes from: the repo's `api/v1/` files by default; if that folder is missing, or `data.json` was built later
than `api/v1/index.json` (a local `build.py` run), it builds the same documents in memory from `data.json`. Files are
re-read when they change on disk; published files are re-fetched after 5 minutes. A network failure is an error, not an
empty answer. Games, picks and props whose kickoff has passed are left out of `get_week_games`, `get_picks`, `get_props`,
`get_team` and `get_player` (the pick log and `explain_pick` keep them). Set `FD_API_URL` (for example `https://notonherb.github.io/football-dashboard/api/v1`) to read
the published files instead; `calibration` then uses the model summary in `index.json` rather than `model.json`.
The server never touches the network unless `FD_API_URL` is set; its tools are marked as reaching outside systems
(`openWorldHint`) only in that case.

| Tool | Does |
|---|---|
| `get_week_games()` | this week's games with every book's lines, fair line, our model, movement, and the ids of the picks on each |
| `get_picks(book=None)` | current official picks; with `book`, that sportsbook's own picks (see above) |
| `get_pick_log(kind, week, result, limit=50)` | the log filtered by `kind` (game, prop, parlay, college), `week`, `result` (W, L, P, V, pending); returns the record and units of everything matching and up to `limit` picks |
| `get_player(query)` | one player by name (fuzzy, typos and missing punctuation are fine) or gsis id: stats, injury, depth, form, game log, dynasty value, props and picks |
| `get_props(player=None, game=None, limit=100)` | props filtered by fuzzy player name and/or game (`CHI`, `CHI@SEA`, or an event id) |
| `explain_pick(pick_id)` | the reasons behind a pick (NFL game lines, props including anytime TDs, parlays and college spreads each by their own rule), from the scores it stored and the thresholds in `engine/rules.py` (`RULES` and the named constants beside it). It explains; it does not recompute the pick |
| `get_team(code)` | a team by code or name: stats, depth chart, what it allows, this week's game, its picks |
| `calibration(prop, projection=None, line=None)` | how the model's projections behave for a prop type (`model.json`): quantiles of actual over projection, the calibration nudge, sample size; with `projection` and `line`, the model's chance of going over |
| `health()` | build health plus how fresh the lines and props are |
| `add_idea(text, tags=None)` | the only write: appends a line to `ideas/inbox.jsonl` (local, git-ignored) |

All tools except `add_idea` are marked read-only. Errors for an unknown player, team, pick id or prop type come back as
`{"error": ...}` with hints, not as protocol errors.
