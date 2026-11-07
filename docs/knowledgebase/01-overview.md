# 01 — Overview

*Snapshot as of 2026-11-02, commit `74fbe2d` on `main`.*

## What it is

A personal football assistant published as a static site on GitHub Pages
(https://notonherb.github.io/football-dashboard/). It covers four areas:

| Area | What it shows |
|---|---|
| **NFL** | Player and team stats, advanced metrics, depth charts, injuries, matchups (skill positions, OL vs DL "trench edge"), player cards with game logs |
| **Fantasy & Dynasty** | PPR/Half/Std points, start/sit, recent form, snap share, dynasty trade values, Sleeper/ESPN league lookups, college prospects and a 2027 consensus big board |
| **Betting (NFL)** | Game lines from up to 10 books, fair odds (Pinnacle, no-vig), a team ratings model, player props with projections, picks, parlays, a pick log graded automatically, "My bets" slip |
| **Betting (College)** | All FBS games, lines by book, a ratings line, and "best number" picks with their own record |

The owner's long-term goal (from `ROADMAP.md`): start as a personal assistant for bets, fantasy lineups and
football knowledge, then open it up to other people, possibly with community features.

## Stack

- **Python 3.12 + pandas + numpy** for the data pipeline. No other dependencies, no `requirements.txt`.
- **One HTML file** (`template.html` → `index.html`, ~198 KB) of vanilla JS/CSS. No framework and no build step.
- **GitHub Actions** cron job (daily, 10:00 UTC) runs the pipeline and commits the results back to `main`.
- **GitHub Pages** serves `index.html` and `data.json` (~1.3 MB).
- **Claude scheduled tasks + a Claude Artifact** ("Analyst Desk") form an agent layer: a daily sync, a weekly
  researcher and a weekly skeptic. See [07-analyst-agent-layer.md](07-analyst-agent-layer.md).

There is no server, no database and no user accounts. All state lives in JSON files committed to git
(`odds/picks.json`, `odds/history.json`, `cfb/*.json`, `model.json`) or in the browser's localStorage.

## External data sources

| Source | Used for | Auth | Where called |
|---|---|---|---|
| nflverse (GitHub releases) | Season and weekly stats, depth charts, injuries, rosters, snaps, players, schedule | none | `sources.py`, `model_fit.py` |
| DynastyProcess (GitHub raw) | Dynasty values, cross-site player ID map | none | `sources.py` |
| CollegeFootballData.com | College stats, usage, PPA, rosters, recruits, games, lines | `CFBD_KEY` secret | `sources.py`, `cfb_fetch.py` |
| The Odds API | NFL lines and props, college lines (credit budgeted, free plan = 500/month) | `ODDS_API_KEY` secret | `sources.py` |
| Open-Meteo | Kickoff weather for outdoor games | none | `sources.py` |
| ESPN, Sleeper and others (browser side) | Player news, league imports | none | `template.html` (see [05-frontend.md](05-frontend.md)) |
| `boards/boards_2027.csv` | Consensus draft big board (hand-saved) | — | `build.py` |

## Repo layout

```
.github/workflows/refresh.yml   daily build + commit (the only automation in the repo)
sources.py        327 lines   every download; per-dataset column CONTRACTs; PROVIDERS registry; odds + weather
build.py         1057 lines   the whole pipeline as one top-to-bottom script → data.json + index.html
model_fit.py      111 lines   weekly refit of the prop projection model → model.json
cfb_fetch.py       35 lines   caches college games and lines into cfb/
template.html    1154 lines   the entire front end (CSS + HTML + JS, very long lines)
index.html                    template.html with __DATE__ / __VER__ stamped (generated, committed)
data.json         1.3 MB      everything the page renders (generated, committed daily)
model.json         86 KB      fitted model: quantiles, calibration, TD logistic, last-season priors
odds/                         state: pick ledger, line history, cached lines and props, college picks
cfb/              ~4.4 MB     cached college games and lines, 2022-2026
boards/                       hand-maintained consensus big board CSV
analyst/                      agent playbooks (README, SYNC, RESEARCHER, SKEPTIC), desk.html, lab.py, snapshot.py
README.md, ROADMAP.md
```

About 4,500 lines of code in total. The repo is small, and most of its weight is in a few very dense files.

## History and cadence

- **First commit:** 2026-10-26. Everything here was built in about one week.
- **107 commits:** 54 by "Claude", 45 by `github-actions` ("Refresh data"), 8 by NotOnHerb (uploads via the web UI).
- The owner works by directing Claude in chat sessions. The commit messages read like product changelogs
  ("Betting v3", "Projections v2", "Phone layout"). Development has been fast and feature-driven.
- `.git` is 2.7 MB packed after one week. 41 of the commits touch `data.json`.

## Current track record (from `data.json`, 2026-11-02)

These numbers are for context only. Every sample is far below the 100+ picks the analyst playbooks require.

| Ledger | Record | Units |
|---|---|---|
| NFL picks (all props so far) | 7-9 | -3.45 |
| NFL parlays | 0-3 | -3.00 |
| College "best number" picks | 5-6 | -1.57 |
| Team model walk-forward vs closing spread (wk 4+, gap ≥ 2.5) | 18-15-1 | — |
| Team model walk-forward vs closing total (gap ≥ 3) | 11-19 | — |
| College best-number backtest 2023-25 (hard-coded in `build.py`) | 314-249 | — |
