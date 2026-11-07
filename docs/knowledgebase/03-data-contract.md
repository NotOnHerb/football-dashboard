# 03 — The data contract (`data.json`)

`data.json` is the only interface between the pipeline and the page, and it's the natural surface for agents.
It has `META.schema = 2`, but no schema document exists outside the code. This page is the first written one.
Field positions below come from reading `build.py`. **Verify them against the code before relying on them,**
because nothing enforces them.

## Top-level keys (2026-11-02 build, ~1.33 MB)

| Key | Type | Size | What it holds | Built at |
|---|---|---|---|---|
| `META` | dict | 1 KB | `schema`, `season`, `sources` (freshness per dataset), `built`, `model` | throughout; `build.py:1045` |
| `PRI` | dict | 30 KB | gsis_id → `[PPR/g, Std/g]` last season (model priors) | `build.py:1046-1051` |
| `P` | dict | 65 KB | Offensive players by position `QB/RB/WR/TE/K` → rows | `build.py:53-59, 120, 436-437` |
| `PC` | dict | 1 KB | Column labels and decimals for each position's `vals` array | `build.py:60, 121` |
| `T` | list | 7 KB | One row per team: `[code, …58 stats in TC order]` | `build.py:77-95` |
| `TC` | list | 2 KB | Team columns: `(label, decimals, higherIsBetter, group, views)` | `build.py:63-74` |
| `N` | dict | 0.5 KB | Team code → nickname | `build.py:427` |
| `X` | list | 105 KB | Defenders (IDP) rows | `build.py:106-111, 438` |
| `DEP` | dict | 39 KB | Depth charts: `{dt, T: team → {s: scheme, ol, fr, db, sk, n}}` | `build.py:141-202` |
| `PL` | dict | 201 KB | Player card extras: gsis_id → `[headshot, espn_id, height, weight, birth_date]` | `build.py:440-456` |
| `LOG` | dict | 105 KB | Game logs: gsis_id → rows (see below) | `build.py:445-446` |
| `OLP` | list | 10 KB | Offensive linemen rows | `build.py:203-209` |
| `ALW` | dict | 12 KB | Points allowed/scored by position, schedule-adjusted (`aa`), league average | `build.py:212-248` |
| `DY` | dict | 251 KB | Dynasty: `P` players, `K` future picks, `L` Sleeper lookup, `E` ESPN→Sleeper id map | `build.py:264-310` |
| `CF` | dict | 426 KB | College prospects `P`, draft year, `tg`, consensus board `CB` | `build.py:312-426` |
| `ODD` | dict | 40 KB | NFL betting (see below) | `build.py:459-941` |
| `CFB` | dict | 32 KB | College betting: `G` games, `PK` picks, `LG` log, `REC` record, `BT` backtest note, `at` | `build.py:943-1044` |
| `G` | list | <1 KB | This week's remaining games `[away, home, label]` | `build.py:103-104` |

`CF` (32%) and `DY` (19%) together are over half of the payload, and the page downloads all of it on every load.

## Positional row layouts

Almost every row is a **positional array**: fields are identified by index, not by name. Both Python and JS
read them by index (`r[5]`, `r[30]`, `row[16]` …).

### `P[pos][i]` — offensive player
| idx | field |
|---|---|
| 0 | display name |
| 1 | team |
| 2 | games |
| 3 | `vals[]`, ordered by `PC[pos]` (PPR/g, Yds/g, TD, Opps/g, Tgt %, then position-specific) |
| 4 | Std fantasy pts/g |
| 5 | injury `[status, injury, week]` or null |
| 6 | depth label `[label, isStarter]` e.g. `["WR1", true]` |
| 7 | `[last3 PPR, last3 Std, snap% season, snap% last3]` |
| 8 | gsis_id |

### `X[i]` — defender (IDP)
0 name, 1 team, 2 pos, 3 games, 4 tackles, 5 solo, 6 tackles/g, 7 TFL, 8 sacks, 9 QB hits, 10 INT, 11 PD, 12 FF,
13 FR, 14 TD, 15 IDP pts, 16 IDP pts/g, 17 injury, 18 depth label, 19 `[null, null, snap% season, snap% last3]`, 20 gsis_id

### `LOG[gsis_id][i]` — one game
0 week, 1 opponent, 2 PPR pts, 3 Std pts, 4 position yards, 5 TDs, 6 receptions, 7 pass yds, 8 rush yds, 9 rec yds,
10 pass TDs, 11 rush+rec TDs. Prop types map onto these indexes (`build.py:606`, `891`).

### `DY.P[i]` — dynasty player
0 name, 1 pos, 2 team, 3 age, 4 draft year, 5 draft round, 6 college, 7 value 1QB, 8 value 2QB, 9 games, 10 PPR/g,
11 last3 PPR, 12 snap% season, 13 snap% last3, 14 injury, 15 depth label, 16 gsis_id

### `DY.L[sleeper_id]` — Sleeper lookup
0 name, 1 pos, 2 team, 3 age, 4 v1QB, 5 v2QB, 6 PPR/g, 7 Std/g, 8 games, 9 last3 PPR, 10 IDP/g or K pts/g,
11 injury, 12 depth label, 13 last3 Std, 14 gsis_id

### `CF.P[i]` — college prospect (40 fields)
0 name, 1 pos, 2 team, 3 conference, 4 class year, 5 stars, 6 recruit rank, 7 HS class, 8 usage %, 9 avg PPA,
10 total PPA, 11 draft eligible, 12-17 passing (ATT, PCT, YDS, TD, INT, YPA), 18-21 rushing (CAR, YDS, TD, YPC),
22-25 receiving (REC, YDS, TD, YPR), 26 rec yds share, 27 rush yds share, 28 height, 29 weight,
**30 dynasty score, 31 letter grade**, 32 PPR total, 33 Std total, 34 team games,
35 consensus rank, 36 boards count, 37 best rank, 38 worst rank, 39 name key.
The dynasty score weights are defined by index (`build.py:373`, e.g. `(26,.35)` = rec share × 0.35).

## `ODD` — NFL betting block

| Key | Meaning |
|---|---|
| `MQ` | Model quantiles per prop type (101 values of actual ÷ projection) |
| `MC` | Calibration nudge per prop type |
| `MB` | Blend weight: our chance vs the market's fair chance (0.5) |
| `G` | Games: `{id, wk, a, h, t, b: {book: {m, s, o}}, fair, mod: {m, t, wp}, ctx: {div, rest, roof, wx, a, h}, mv}` |
| `P` | Props: `{eid, ko, n, t, pos, gid, opp, mk, b: {book: [overPt, overPr, underPt, underPr]}, fair, v, avg, l3, pj, md, fac, use}` |
| `books` | Book display order |
| `MR` | Team model walk-forward record vs closing lines |
| `PK` | Current picks (game `g|…` and prop `p|…`) |
| `PX` | Parlays (`x|kind|wkN`) |
| `LG` | Full pick log, newest first |
| `REC` | Records: `x` parlays, `all`, `g` game lines, `p` props, `s3` strength-3 picks |
| `RU` | Pick rules (thresholds), also used by the page |
| `FIN` | Final scores this season `[wk, away, home, aScore, hScore]` |
| `at`, `pat`, `left`, `plan` | Lines time, props time, credits left, odds plan |

### Pick IDs
- Game line: `g|<eventId>|<spread|total|ml>|<hs|as|ov|un|mh|ma>`
- Prop: `p|<eventId>|<gsis_id>|<prop label>|<o|u|y>`
- Parlay: `x|<week|td|game>|wk<N>`
- College: `c|<cfbdGameId>|<hs|as>`

These IDs are the join key between `build.py`, the page (single-book views recompute picks with the same
rules) and the analyst sync's "same pick ids" check.

## Other committed JSON

| File | Shape |
|---|---|
| `model.json` | `{season, fit_at, w, k0, blend, q: {prop: [101]}, cal: {prop: x}, td: {mu, sd, w}, prior_cols, priors: {gsis: [...]}, n}` |
| `odds/picks.json` | pick id → pick record + `res` (W/L/P/V), `u` units, `first` (first-seen price), `val`, `fin` |
| `odds/history.json` | event id → `[[time, consensus spread, consensus total, fair ML], …]` (≤ 30) |
| `odds/lines.json` | `{fetched, data: <raw Odds API response>}` |
| `odds/props/<eventId>.json` | `{fetched, data: <raw Odds API event odds>}` |
| `odds/ncaaf.json` | `{fetched, markets, data, credits_left, used}` |
| `cfb/games_YYYY.json`, `cfb/lines_YYYY.json` | Trimmed CFBD responses |

## Agent-facing snapshot (`analyst/snapshot.py`)

The analyst layer doesn't read `data.json` directly. `snapshot.py` reshapes the betting block into
**named-field** documents (`meta`, `picks`, `log`, `games`, `props1..N`, each under 200 KB) for the Desk database.
That's the only named-field view of the data that exists today, and it's a useful precedent for an agent-facing API.
