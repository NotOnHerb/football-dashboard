# Refactor Phases 1-4 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give `data.json` named fields, put the betting/projection logic in one shared Python package, split the
front end into modules with a section registry, and give agents a documented API and an MCP server. The site's
behavior stays the same throughout.

**Architecture:** The work runs in three waves of parallel tasks, each task in its own git worktree off
`refactor/phase-0`. Every task is gated by two tests:
- the existing **data golden test**, which checks that `data.json` is unchanged;
- a new **page snapshot test**, which checks that every view's rendered text is unchanged and the console is clean.

A task that intentionally changes the output re-blesses, and its diff must be limited to the paths it names.

**Tech Stack:** Python 3.12, pandas 3.1.0, numpy 2.5.4, pytest, freezegun, Playwright (Chromium), jsonschema,
the `mcp` Python SDK, and vanilla JS (classic scripts, no bundler) on GitHub Pages.

**Spec:** `docs/knowledgebase/09-refactor-roadmap.md` on branch `repo-knowledgebase` (PR #1). Read it with
`git show repo-knowledgebase:docs/knowledgebase/09-refactor-roadmap.md`. The data layout is in `…/03-data-contract.md`
and the front-end map is in `…/05-frontend.md` on the same branch.

## Global Constraints

- **Never push.** Commit only on your worktree branch. Every commit message ends with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.
- **Never commit generated site output:** `data.json`, `index.html`, `odds/`, `cfb/`, `model.json`.
- **Leave the owner's Analyst setup alone** (`analyst/SYNC.md`, `RESEARCHER.md`, `SKEPTIC.md`, `desk.html`). Changing those is the owner's call.
- **Python:** run it only through `uv run --no-project --python 3.12 --with-requirements requirements-dev.txt …`, with `PYTHONHASHSEED=0 PYTHONUTF8=1`. The `py` launcher on this machine is broken.
- **Page constraints:** static files on GitHub Pages; no build step, bundler, framework or new CDN. `build.py` stamps `__VER__`/`__DATE__` into `template.html` → `index.html`.
- **Golden tests stay green.** Re-bless (`python tests/golden/runner.py bless <tmp>`) only when your task says the output changes, and only for the paths it names.
- **Keep `data.json` itself.** `analyst/snapshot.py` and the Desk sync depend on it, so it keeps every current top-level key.
- **Code style:**
  - New modules (`engine/`, `schema/`, `mcp/`, `js/`) get readable names and short docstrings, like `model_fit.py`.
  - Lines you don't otherwise touch in `build.py` keep their existing dense style.
- **Pin new dependencies** in `requirements-dev.txt` (test-only) or `requirements.txt` (runtime), with exact versions.

## Review Focus

1. **New files don't reach the live site.** `refresh.yml` commits only named paths, so new shard/API folders would go unpublished.
   Expected: the workflow adds them. Pinned by `tests/test_workflow.py::test_refresh_commits_all_outputs` (Task 8).
2. **Stale cached JS against a new `index.html`.** GitHub Pages caches for about 10 minutes, so a visitor can get mismatched files.
   Expected: every local script/style URL carries `?v=__VER__`. Pinned by `tests/test_page.py::test_assets_are_versioned` (Task 5).
3. **Saved My bets disappear after the storage rename.** Expected: existing localStorage keys are migrated.
   Pinned by `tests/test_page.py::test_saved_bets_survive` (Task 5).
4. **Empty week (Mon/Tue, off-season, failed schedule).** Expected: no console errors, games-unavailable message, empty pick lists.
   Pinned by `tests/test_page.py::test_empty_week` (Task 3).
5. **Hostile names from feeds** (Odds API player names, Sleeper/ESPN team names). Expected: shown as text, never run as code.
   Pinned by `tests/test_page.py::test_feed_names_are_escaped` (Task 3, `xfail(strict=True)` until Task 5).

---

## Wave 1 (Tasks 1-3 in parallel)

### Task 1: Field dictionary and schema (Phase 1)

**Files:**
- Create: `schema/__init__.py`, `schema/fields.py`, `schema/data.schema.json`, `tests/test_schema.py`
- Modify: `build.py`. Only the final `json.dumps({...})` line, to add `'SCHEMA':schema.fields.export(PCout,TC)`.
- Modify: `requirements-dev.txt` (+ `jsonschema`)

**Interfaces:**
- Produces:
  - `schema.fields.FIELDS: dict[str, list[str]]`. Keys are block paths: `'P'`, `'X'`, `'LOG'`, `'OLP'`, `'DY.P'`, `'DY.K'`, `'DY.L'`, `'CF.P'`, `'CF.CB.P'`, `'CF.CB.S'`, `'T'`, `'G'`, `'ODD.FIN'`. Values are snake_case field names in row order, from `docs/knowledgebase/03-data-contract.md`.
    - Verify each one against `build.py`.
    - For `P`, index 3 is `vals`. Its labels come from `PC[pos]`.
  - `schema.fields.export(pc, tc) -> dict`: FIELDS plus `{'P.vals': {pos: [labels]}, 'T.cols': [labels]}`. Emitted as `data.json` key `SCHEMA`.
  - `schema.fields.named(block: str, row: list) -> dict` and `rows_named(block, rows) -> list[dict]`.
  - The JS side reads `D.SCHEMA`. Task 5 adds a `F(block, row, name)` accessor on top of it.

- [ ] Write `tests/test_schema.py::test_row_lengths_match_fields`:
  - Run the golden replay. For each FIELDS block, every row's length equals `len(FIELDS[block])`.
  - `P` rows: `len(row[3]) == len(PC[pos])`.
- [ ] Write `test_data_validates_against_schema`: `jsonschema.validate(data, json.load(open('schema/data.schema.json')))`.
  The schema is hand-written and covers top-level keys, types and the `ODD` dict keys.
- [ ] Write `test_named_roundtrip`: `named('P', row)['gsis_id'] == row[8]` and `named('CF.P', row)['dynasty_score'] == row[30]`.
- [ ] Run them and see them fail. Implement. Re-bless; the golden diff must be `$.SCHEMA` only. Run the full suite green. Commit.

### Task 2: Extract `engine/` from build.py (Phase 2, pure refactor)

**Files:**
- Create: `engine/__init__.py`, `engine/odds.py`, `engine/rules.py`, `engine/projections.py`, `engine/team_model.py`, `engine/picks.py`, `engine/parlays.py`, `engine/grading.py`
- Create: `tests/engine/test_odds.py`, `test_picks.py`, `test_grading.py`, `test_projections.py`
- Modify: `build.py` (betting sections 458-1044 and the college ridge). **Don't touch** its last 15 lines, the `META`/`ok`/`bad` health lines, or the `json.dumps` line (Task 1 owns those).
- Modify: `model_fit.py` (`base` → `engine.projections.base_projection`), `analyst/lab.py` (`current_recipe` uses it), `analyst/snapshot.py` (imports `engine.odds`/`engine.projections` instead of its copies)
- Create: `tests/test_snapshot.py`, which compares the output of `snapshot.py` on the golden `data.json` before and after

**Interfaces (Produces; signatures are exact):**
- `engine.odds`:
  - `implied(american) -> float` (was `prob`)
  - `decimal(american) -> float` (was `dec`)
  - `american_from_decimal(d) -> int`
  - `no_vig_shin(a1, a2) -> float` (was `novig`)
  - `no_vig_proportional(a1, a2) -> float`
  - `consensus_line(xs) -> float|None` (was `mode`)
  - `median(xs)`
  - `normal_cdf(x)`
- `engine.rules`:
  - `RULES: dict` (the current `RU`, values unchanged)
  - `value_score(ev) -> int` (was `valS`)
  - `lean_tier(edge) -> int` (was `ptier`)
- `engine.projections`:
  - `base_projection(hist, prior, w, k0) -> float`
  - `matchup_factor(opp_allowed, league_avg) -> float` (clamped 0.8-1.25)
  - `p_over(q, cal, mu, line) -> float|None`
  - `td_chance(td_model, usage, pos) -> float|None`
- `engine.team_model`:
  - `fit_nfl(games, teams, prior=None, lam=8.0) -> (ratings, hfa, off, deff, mu)`
  - `project(fit, home, away) -> (margin, total)`
  - `fit_ridge_margins(games, prior, lam) -> (ratings, hfa)`
- `engine.picks`:
  - `best_game_quote(game, side, books=None)`
  - `game_side(game, side, books=None)`
  - `best_prop_quote(prop, side, books=None)`
  - `prop_side(prop, model, blend, books=None)`
  - `game_picks(games, now, books=None) -> list[dict]`
  - `prop_picks(props, model, blend, now, injured, books=None) -> list[dict]`
  - `books=None` means best across all books (today's behavior). A set restricts it to those books (Task 4 uses this).
- `engine.parlays.build_parlays(picks, props, games, books, model, blend, now, injured) -> list[dict]`
- `engine.grading`:
  - `grade_pick(rec, finals, logs, logmax) -> None` (mutates `res`/`u`/`val`/`fin` as today)
  - `grade_log(log, finals, logs, logmax, now) -> None`
  - `summarize(records) -> {'w','l','p','u'}`

Steps:
- [ ] Write unit tests:
  - `test_shin_two_way_sums_to_one`
  - `test_implied_minus110 == 110/210`
  - `test_decimal_plus150 == 2.5`
  - `test_half_point_crossing_three_adds_3pct` (`gev` across 3 and 7)
  - `test_grade_push_and_void`
  - `test_parlay_with_push_pays_remaining_legs`
  - `test_stale_price_is_not_a_pick` (EV > 0.10 → `vs` 0)
- [ ] Move the code. `build.py` imports from `engine`.
- [ ] The golden test must pass **without re-blessing**, and `tests/test_snapshot.py` must match.
- [ ] Commit in two steps: engine + build, then model_fit/lab/snapshot.

### Task 3: Page snapshot test (front-end safety net)

**Files:**
- Create: `tests/test_page.py`, `tests/golden/page_views.py` (the list of views and how to reach each), `tests/golden/expected_page.json.gz`
- Modify: `requirements-dev.txt` (+ `playwright`), `.github/workflows/test.yml` (add `python -m playwright install --with-deps chromium`)

**Interfaces:**
- Produces:
  - `tests/golden/page_views.py: VIEWS: list[tuple[name, list[action]]]`. An action is a click on a CSS selector or `('select', css, value)`. Covers every view in `05-frontend.md`'s section map, including Betting→Picks once per book in `D.ODD.books` and the "best available" option.
  - Fixture `site(tmp_path) -> url`: golden replay plus a local `http.server` thread.
  - Page clock frozen at `fixtures/meta.json` `now` via `page.clock.set_fixed_time`.
- Snapshot per view = `main` `innerText`, with whitespace collapsed.

Steps:
- [ ] `test_views_match_snapshot`: each view's text equals the expected text, and the console has no errors.
- [ ] `test_empty_week`: post-process `data.json` (`G=[]`, `ODD.G=[]`, `health.schedule='failed: x'`). Expect no console errors, the games-unavailable text present, and `#hl` visible.
- [ ] `test_feed_names_are_escaped`, marked `xfail(strict=True, reason='Task 5')`:
  - Inject `<img src=x onerror="window.__x=1">` into `ODD.P[0].n`, one `DY.L` name and one `CF.P` name.
  - Visit all views. Expect `window.__x` to be undefined.
- [ ] Record `expected_page.json.gz` with a `--bless` flag (`python tests/test_page.py --bless`). Run the suite green. Commit.

## Wave 2 (Tasks 4-6 in parallel, after wave 1 merges)

### Task 4: Per-book picks computed in the build (Phase 2)

**Files:** modify `build.py` (odds block), `engine/picks.py`, `tests/engine/test_picks.py`.

**Interfaces:**
- Produces `data.json` `ODD.PKB: {book_name: [pick dict, same shape as ODD.PK]}` for every book in `ODD.books`.
  It's computed with `books={book}`, using the same "started" cutoff the build uses.

Steps:
- [ ] Write `test_pkb_matches_page`: for the golden fixture, the pick ids in `PKB[book]` equal the ids the page shows for that
  book. Read them from Task 3's snapshot (`tests/golden/expected_page.json.gz`, Betting→Picks per-book views).
- [ ] Implement it. Re-bless; the golden diff must be `$.ODD.PKB` only. Commit.

### Task 5: Modular front end (Phase 3)

**Files:**
- Create: `assets/site.css` and `js/` with:
  - `core.js`: `$`, `esc`, an `html` tagged template (escapes every interpolation unless wrapped with `raw()`), a `store` namespaced localStorage wrapper with key migration, `F(block,row,name)`
  - `ui.js`: table, sort, gloss, colorize
  - `scene.js`, `glossary.js`
  - `registry.js`: `register({id, label, parent, dataKeys, init, render})`, plus nav generation for `#sec` and `#bnav`
  - `router.js`: `#<section>/<view>[?k=v]`
  - `sections/*.js`: one file per row of `05-frontend.md`'s section map; the betting pick functions go in `sections/betting-engine.js`, moved unchanged
  - `main.js`: boot, with each init/render in try/catch so one section can't take down the rest
- Modify: `template.html`, which shrinks to its skeleton plus `<link>`/`<script src="…?v=__VER__">`. Keep the inline `onfocus`/`onerror` behavior via listeners.
- Modify: `tests/test_page.py`. Remove the xfail; add `test_assets_are_versioned`, `test_saved_bets_survive` (seed old key `mybets` → My bets shows it), and `test_deep_link` (`#betting/props` opens Props).

Steps:
- [ ] Split mechanically first. Classic scripts keep today's globals, so no module scoping changes yet.
- [ ] `test_views_match_snapshot` must pass with **no re-bless**.
- [ ] Add the registry, router and error isolation. Snapshot still unchanged. Commit.
- [ ] Route every dynamic string through `html`/`esc`, until `test_feed_names_are_escaped` passes. Snapshot unchanged. Commit.

### Task 6: Agent surface (Phase 4)

**Files:**
- Create: `api_export.py`, `docs/api.md`, `mcp_server/__init__.py`, `mcp_server/server.py`, `mcp_server/data.py`, `.mcp.json.example`, `AGENTS.md`, `CLAUDE.md` (one line: see AGENTS.md), `decisions/README.md`
- Create: `tests/test_api_export.py`, `tests/test_mcp.py`
- Modify: `.github/workflows/refresh.yml`. Run `python api_export.py` after `build.py`; `git add api`.
- Modify: `requirements-dev.txt` (+ `mcp`)

**Interfaces:**
- Consumes: `schema.fields.rows_named`, `engine.*` (Tasks 1-2).
- Produces:
  - `api_export.export(data: dict, out_dir='api/v1') -> list[str]`. Writes named-field `index.json`, `players.json`, `teams.json`, `games.json`, `picks.json`, `props.json`, `pick_log.json`, `dynasty.json`, `college.json`, `health.json`, and copies `schema/data.schema.json`.
  - MCP tools, read-only except `add_idea`, which writes `ideas/inbox.jsonl` locally:
    - `get_week_games()`
    - `get_picks(book: str|None)`
    - `get_pick_log(kind, week, result, limit=50)`
    - `get_player(query: str)` (fuzzy name or gsis_id)
    - `get_props(player=None, game=None)`
    - `explain_pick(pick_id)`
    - `get_team(code)`
    - `calibration(prop)` (from `model.json`, no network)
    - `health()`
  - Data source: repo files by default; `FD_API_URL` reads the published `api/v1/`.

Steps:
- [ ] Tests:
  - `test_export_rows_are_named` (`players.json[0]` has `gsis_id`, `team`)
  - `test_export_is_lossless_for_picks`
  - `test_mcp_tools_list`
  - `test_get_picks_matches_data`
  - `test_explain_pick_has_reasons`
  - `test_get_player_by_name`

  Use the `mcp` SDK's in-memory client session against the golden output.
- [ ] Implement it, and run the suite green.
- [ ] `AGENTS.md` covers: what the repo is, the knowledgebase link, test commands, how to re-bless, "never push to main", and the MCP setup.
- [ ] `decisions/README.md` sets out a one-file-per-decision template, so the owner can choose to mirror the Desk notebook there. Commit.

## Wave 3 (Tasks 7-8 in parallel, after wave 2 merges)

### Task 7: Page uses build picks; delete the browser pick engine

**Files:** modify `js/sections/betting*.js`; delete `js/sections/betting-engine.js` (pick parts only; display helpers stay).

- [ ] Picks and single-book views read `D.ODD.PK` / `D.ODD.PKB[book]`. The "already started" filter stays client-side using `t`.
- [ ] `test_views_match_snapshot` must be unchanged for every per-book view. Commit.

### Task 8: Shard `data.json` and lazy-load it

**Files:**
- Modify: `build.py` (also write `data/core.json`, `data/players.json`, `data/dynasty.json`, `data/college.json`, `data/odds.json`, split by top-level keys; keep `data.json`)
- Modify: `js/main.js` and `registry.js`. Load core first, then a section's `dataKeys` shards on first visit.
- Modify: `.github/workflows/refresh.yml` (`git add data`)
- Create: `tests/test_workflow.py`

Steps:
- [ ] `test_shards_union_equals_data_json`.
- [ ] `test_refresh_commits_all_outputs`: parse `refresh.yml`; it adds `data`, `api`, `index.html`, `data.json`.
- [ ] Page snapshot unchanged. Measure first-load bytes before and after, and record them in the commit message. Commit.

## Final

- [ ] Run the full suite on the merged branch. Do a whole-branch review with superpowers:requesting-code-review.
- [ ] Write `docs/refactor/phases-1-4.md`: what changed, how to run, re-bless and use MCP, and the owner decisions still open
  (sync worker via PRs, mirroring decisions, generating the Desk `RULES` from `engine.rules`).
