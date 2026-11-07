# 04 — Backend pipeline (Python)

## `sources.py`: the ingestion layer (327 lines). Best-structured file in the repo.

- One loader per dataset, each returning `(DataFrame, info)`. `info` feeds the page's freshness line through `META.sources`.
- **CONTRACT column lists** at the top (`SEASON_STATS`, `WEEKLY_STATS`, `DEPTH`, …) and `_need()` validate that
  the columns exist. A missing column raises an error instead of shipping bad data.
- `PROVIDERS` dict maps dataset name → loader, so a paid feed can swap in without touching `build.py` (`sources.py:242`).
- Also contains: the Odds API client with credit budgeting and caching (`odds_update`, `odds_ncaaf`), stadium
  coordinates plus Open-Meteo weather (`weather_at`), and the CFBD client (`_cfbd`, `cfbd_college`).

Gaps in the abstraction:
- Contracts only check that **columns exist**, not their types or ranges. Season stats also gets a row-count floor.
- Several callers bypass `PROVIDERS`: `model_fit.weekly()` builds nflverse URLs with `sources._get` directly,
  `cfb_fetch.py` calls `sources._cfbd` directly, and `build.py` calls `sources.load('schedule')` twice (lines 22 and 505),
  which downloads it twice.
- Odds and weather are not in `PROVIDERS`. They're called as functions with side effects (they write cache files).
- "US Central" is hard-coded as UTC-5 (`sources.py:189, 205, 300`). That's correct only during daylight time.
  From 2026-11-01 Central is UTC-6, so day-of-week gating is off by an hour around midnight.

## `build.py`: the whole pipeline in one script (1,057 lines)

`build.py` has no `main()`. It runs top to bottom at import time, with module-level globals shared between
sections. Each section is wrapped in its own `try/except Exception: print(...)` so one failure doesn't stop the build.
The code style is very dense: one-letter names, multiple statements per line, lambdas inline.

### Section map

| Lines | Section | Produces | Fails to |
|---|---|---|---|
| 1-26 | Setup, `load()` wrapper, team aliases, schedule → this week's games | `META`, `ALIAS`, `games_from`, `get_games` | — |
| 27-60 | Season stats → per-position derived stats | `df`, `c`, `PC`, `P` | **hard failure** (no try) |
| 61-97 | Team table (58 stats) + league sanity checks | `T`, `TC`, `TG` | hard failure |
| 98-121 | DL/OL lists, IDP scoring, kickers | `DL`, `OL`, `X`, `K`, `P['K']` | hard failure |
| 103-105 | This week's games (hard-coded `G_FALLBACK` from Oct 22) | `G` | stale fallback |
| 124-140 | Injuries + reserve lists | `INJ` | `{}` |
| 141-202 | Depth charts, scheme (3-4/4-3), OL/front/DB starters, skill depth, "trench edge" tiers | `DEP`, `OLSTART`, `DLAB` | `None` |
| 203-210 | OL player list | `OLP` | — |
| 212-248 | Weekly stats → points allowed by position, schedule-adjusted | `ALW`, `WK` | `None` |
| 249-262 | Recent form, snap share | `FORM`, `SNAP` | `{}` |
| 263-310 | Dynasty board, future picks, Sleeper/ESPN lookups | `DY` | `None` |
| 311-426 | College prospects: stats, usage, PPA, recruiting, college fantasy, dynasty score, consensus big board | `CF` | `None` |
| 427-457 | `clean()` for JSON, row enrichment, player cards, game logs | `PL`, `LOG` | `{}` |
| 458-941 | **NFL betting** (see [06](06-models-and-betting.md)) | `ODD`, writes `odds/picks.json`, `odds/history.json` | `None` |
| 942-1044 | **College betting** | `CFB`, writes `odds/cfb_picks.json` | `None` |
| 1045-1057 | Priors, write `data.json`, stamp `index.html` | files | — |

### Things to know before editing `build.py`

- **Name reuse across sections.** All of these are globals in one namespace:
  - `INJ` is the injury dict `{gsis: [status, injury, week]}` at line 140. It's silently **redefined** at line 698
    as `{gsis: status}`, inside the betting section.
  - `dv` is a safe-divide lambda at line 76, then becomes the dynasty DataFrame at line 266.
  - `done` and `fin` are reused between the NFL and college betting sections.

  Moving or reordering sections can break things in ways that don't raise errors.
- **Silent degradation.** If depth charts, weekly stats, dynasty, college or odds fail, the build still succeeds.
  The site ships without that section, and the only signal is a `print` in the Actions log.
- **Windows incompatibility.** `strftime('%-I')` (line 18) is Linux-only. On Windows, `get_games` throws, the error is
  caught, and the build quietly uses the hard-coded October 22 `G_FALLBACK` games.
- **Side effects inside the build.** The betting sections read and write ledgers in `odds/`. That's skipped only under
  `ODDS_OFFLINE`. A local online build will mutate the real pick ledger.
- **Hard-coded constants** worth knowing: team nickname map `N`, dome list (line 588), stadium coordinates, book name
  maps (482, 962, 967), college team aliases (968), big-board name aliases (393), the college backtest record (1041).
- **Logging is diagnostic `print`s with sanity checks**, e.g. giveaways vs takeaways and PPR allowed vs scored. These are
  useful, but nothing asserts on them.

## `model_fit.py`: projection model (111 lines)

Clean and readable, with `main()` and docstrings. Weekly, it:
1. Downloads weekly stats for the current season and the two before it.
2. Walks every player-game (from game 4 on), projecting with the recipe
   `base = 0.85·season_avg + 0.15·last3`, shrunk toward last season's per-game number with weight `K0 = 4` games.
3. **`q`**: 101 quantiles of `actual / projection` per prop type, learned from **last season**.
4. **`cal`**: on **this season's** games, the gap between predicted and actual "over" rates at lines from 0.8× to 1.2× projection,
   shrunk by `n/(n+100)`.
5. **`td`**: a hand-rolled L2 logistic regression for anytime TD on carries/g, targets/g, isRB, isTE.
6. **`priors`**: last-season per-game numbers for players with 4+ games.

The recipe (`base`) is duplicated in `analyst/lab.py:current_recipe` and inline in `build.py:633-635`.

## `cfb_fetch.py` (35 lines)

A script with no `main()`. It caches FBS games and lines for `SEASON-4 … SEASON`, re-fetching only the current season,
and writes `cfb/fetch_log.txt`, which `build.py` reads for the "as of" time.

## `analyst/lab.py`, `analyst/snapshot.py`

- `lab.py`: backtest helpers (`rows`, `mae`, `calibration`) built on `model_fit.weekly`. Small and reusable.
- `snapshot.py`: reshapes `data.json` and `odds/picks.json` into named-field Desk documents. It has its **own copies**
  of implied probability, no-vig (proportional here, while `build.py` uses Shin's method), `pover`, and best-price logic.

## Tests, tooling, packaging

- **No tests.** No `tests/` directory and no test runner. Verification happens through printed sanity checks and the
  analyst's backtests.
- **No dependency pinning** (`pip install pandas numpy` in CI). No `requirements.txt` or `pyproject.toml`.
- **No linting or formatting config.**
- **No local run instructions** beyond the analyst playbooks' `ODDS_OFFLINE=1 python build.py`.
