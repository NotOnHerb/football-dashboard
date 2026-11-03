# AGENTS.md

Instructions for AI agents (and new humans) working in this repo.

## What this repo is

A static NFL and college football dashboard for stats, fantasy and betting, published on GitHub Pages
(https://notonherb.github.io/football-dashboard/). There is no server and no build step for the page.

- `sources.py` is the only file that downloads data. `build.py` turns it into `data.json` (also split by top-level
  key into `data/`, the files the page loads: `schema/shards.py`) and stamps `index.html` from `template.html`. `model_fit.py` fits the projection model (`model.json`); `cfb_fetch.py` fetches college data.
- `engine/` holds the betting logic (odds math, pick rules, picks, grading, parlays) that `build.py` and the analyst
  tools share. `schema/` names every position of every row in `data.json` (`schema/fields.py`) and holds the JSON
  schema for the whole file.
- `.github/workflows/refresh.yml` runs the whole thing daily and commits the result. Generated files (`data.json`,
  `data/`, `index.html`, `model.json`, `odds/`, `cfb/`, `api/`) are committed by that workflow, not by hand.
- The page's source is `template.html` (markup), `assets/site.css` and `js/` (classic scripts: `core.js`,
  `registry.js`, `router.js`, one file per section in `js/sections/`, `main.js` boots). `restamp.py` (run by
  `build.py`, and on its own by the restamp workflow) stamps every `?v=__VER__` in `template.html` into `index.html`.
- `api_export.py` writes named-field JSON for agents to `api/v1/`; `mcp_server/` serves it over MCP. See `docs/api.md`.

## Knowledgebase

The architecture notes live in `docs/knowledgebase/`. They describe the code before the refactor (commit `74fbe2d`),
so their line numbers in `03`, `05` and `06` no longer match; when a page disagrees with the code, the code wins.
Useful pages: `03-data-contract.md` (every key and row of `data.json`), `05-frontend.md`, `09-refactor-roadmap.md`.

## Running things

Run Python from the repo root with the pinned packages, for example through uv. (The bare `py` launcher is broken on
Thomas's Windows machine, so use uv or `py -3.12` there. The owner works in Claude cloud sessions, which can't always
install the test packages; there the Test check on the PR runs the suite.)

    PYTHONHASHSEED=0 PYTHONUTF8=1 uv run --no-project --python 3.12 --with-requirements requirements-dev.txt python -m pytest -q

That runs everything, including the Playwright page test (about 2.5 minutes). While iterating, run one file
(`... python -m pytest -q tests/test_mcp.py`) or use `-k`. Run the full suite once before committing.

Never commit generated output from a local run: `data.json`, `data/`, `index.html`, `model.json`, `odds/`, `cfb/`, `api/`.
If a run rewrote them, `git checkout -- <path>` (or delete `api/`). Add files by name; avoid `git add -A`.

## Golden files

Three recorded outputs guard against accidental changes. A change that is meant to change them is accepted by
re-blessing, and the diff you commit should be limited to what you meant to change.

- `tests/golden/expected_data.json.gz`, the `data.json` that `build.py` makes from recorded inputs:
  `python tests/golden/runner.py bless <tmp-dir>` (run it with the same uv prefix as above, `PYTHONHASHSEED=0`)
- `tests/golden/expected_page.json.gz`, what the page shows in each view:
  `python tests/test_page.py --bless`
- `tests/golden/expected_snapshot.json.gz`, the analyst snapshot:
  `python tests/test_snapshot.py bless`

## Rules

- **Never push to `main`.** Work on a branch and open a PR; the owner merges. (The refresh and restamp workflows are
  the only things that commit to `main` directly.)
- The page stays static: no bundler, framework or new CDN.
- A push to `main` that changes `template.html`, `js/` or `assets/` goes live through the restamp workflow
  (`.github/workflows/restamp.yml`), which restamps `index.html` from the data already built. It needs nothing from you.
- **Odds API credits are scarce.** The free plan has 500 a month, and a full Refresh spends about 3. Never dispatch
  Refresh just to restamp the page, and never run the build online locally: run it with `ODDS_OFFLINE=1`, or use the
  golden runner (`tests/golden/runner.py`), which replays recorded inputs.
- Keep every current top-level key in `data.json`; the analyst Desk sync (`analyst/snapshot.py`) depends on them.
- Pin new dependencies exactly in `requirements.txt` (runtime) or `requirements-dev.txt` (tests only).
  `build.py` and `api_export.py` run in the refresh with only `requirements.txt` installed.
- Decisions worth remembering go in `decisions/`, one file each (template in `decisions/README.md`).

## MCP server

`mcp_server/` lets an agent query the dashboard directly: the week's games, picks and why, props, players, teams,
the pick log, model calibration and build health. Every tool is read-only. Ideas for the owner have one inbox, the
Desk's Ideas tab (collection `ideas` in the Desk database, `analyst/README.md`).

Setup: copy `.mcp.json.example` to `.mcp.json` in the repo root (Claude Code reads it from the project folder) and
approve the server. It starts with `python -m mcp_server.server`, which needs the pinned `mcp` package (in
`requirements-dev.txt`). By default it reads the repo's files (`api/v1/`, or `data.json` if there is no `api/v1/`).
Set `FD_API_URL` to read the published `api/v1/` instead. Tool list and the file formats are in `docs/api.md`.
