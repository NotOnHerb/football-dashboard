# Refactor phases 1-4

This PR is ready to merge once the Test check is green. Two things are on your side after it merges: updating
`analyst/SYNC.md`, and turning on "Allow auto-merge" with the Test check required on `main`, so the sync worker's PRs
can merge themselves.

## Where your review landed

- **Knowledgebase:** `AGENTS.md` points at `docs/knowledgebase/` on `main`, and notes that it describes the
  pre-refactor baseline (`74fbe2d`).
- **Front-end pushes:** a push to `main` that changes `template.html`, `js/` or `assets/` now goes live through the
  restamp workflow (`.github/workflows/restamp.yml`). It restamps `index.html` from the data already built, with no
  Odds API calls, and commits only `index.html`. `AGENTS.md` has the credits note: never dispatch Refresh just to
  restamp, and never run the build online locally.
- **Ideas:** the MCP server is fully read-only. Ideas have one inbox, the Desk's Ideas tab.
- **`AGENTS.md`:** the site is described as stats + fantasy + betting, and the broken `py` launcher note says it's
  Thomas's Windows machine.
- **Sync worker:** it moves to PRs that auto-merge when the Test check passes. Your approval on the Desk stays the one
  human sign-off. This needs "Allow auto-merge" turned on and the Test check required on `main`.
- **`analyst/SYNC.md`:** yours to update after the merge. Here's what changed under it:
  - Picks now come only from the build (`engine/picks.py`, rules in `engine/rules.py`), and the page shows `ODD.PK` /
    `ODD.PKB`. The check that fits step 3 now is `pytest tests/test_pkb_page.py tests/test_page.py`.
  - After an offline build, restore `data.json data/ index.html`.
- **The address bar:** it keeps tracking the view (`#betting/props`), so any view can be shared as a link.
- **Daily commit size:** handled in the Pages deploy PR, stacked on this one. The refresh deploys the site through a
  Pages artifact, and git keeps only the ledgers (`odds/`, `cfb/`, `model.json`).

## Follow-up PRs

- Generate the Desk `RULES` from `engine/rules.py`.
- Fix the two page quirks this PR kept as-is: the college prospects footnote that prints "NaN season so far", and the
  -110 shown for a college pick from a book with no spread price. Each comes with a page re-bless.
- Re-derive the college best-number backtest record (314-249) in code. Today it is a fixed value in `build.py`.
- Still open from the plan: mirroring the Desk notebook into `decisions/`.

## Merging and the first refresh

- The merge itself triggers the restamp, so the new page goes live right away. It reads `data.json` until the first
  refresh builds `data/`.
- Watch the next daily refresh. It's the first time `main` builds `data/`, `api/v1/` and the section health checks.
- To roll back: revert the merge, then dispatch Refresh once so `index.html` is restamped from the old template (the
  restamp workflow leaves with the revert). Bets saved on the new page are kept under `fd:mybets` and reappear when
  the refactor comes back.

## What changed

- **Named fields** (`schema/fields.py`): every position of every row in `data.json` has a name. `data.json` carries
  them as `SCHEMA`, and `schema/data.schema.json` describes the whole file.
- **One betting engine** (`engine/`): odds math, pick rules, picks, parlays and grading live in one package, shared
  by `build.py`, `model_fit.py`, `analyst/lab.py` and `analyst/snapshot.py`. The move changed no output.
- **Per-book picks in the build:** `ODD.PKB` holds each book's picks, and the page reads `ODD.PK` / `ODD.PKB`
  directly.
- **Modular page:** `template.html` is the skeleton.
  - `assets/site.css` and `js/` hold the rest, as classic scripts with no build step.
  - Each section registers itself. A section that fails shows a note and leaves the rest of the page working.
  - Every feed name is escaped, and links are http(s) only.
  - Saved settings and bets move to `fd:`-prefixed storage keys. The old keys are copied and left in place.
- **Lazy data:** the page loads `data/core.json` first and each section's file on first visit. First load drops
  from about 1.3 MB to about 250 KB. Each file carries a build stamp, so a tab left open across a refresh asks you
  to reload instead of mixing two days' numbers.
- **Agent surface:**
  - `api_export.py` writes named-field JSON to `api/v1/`.
  - `mcp_server/` serves it over MCP, read-only.
  - `AGENTS.md` covers working in the repo, and `docs/api.md` covers the files and tools.
- **Restamp:** `restamp.py` stamps `index.html` from `template.html`. `build.py` uses it, and so does the restamp
  workflow.
- **Health:** `check_health.py` turns the refresh red when `api/v1/` or `data/` is missing or comes from an older
  build. The site is still committed first.

## Running, re-blessing and MCP

`AGENTS.md` has the full instructions. In short:

- Tests: `PYTHONHASHSEED=0 PYTHONUTF8=1 uv run --no-project --python 3.12 --with-requirements requirements-dev.txt python -m pytest -q`
  (about 3.5 minutes, including the Playwright page test). In a cloud session that can't install the packages, the
  Test check on the PR runs them.
- Re-bless, after a change that is meant to change output:
  - data: `python tests/golden/runner.py bless <tmp-dir>`
  - page: `python tests/test_page.py --bless`
  - analyst snapshot: `python tests/test_snapshot.py bless`
- MCP: copy `.mcp.json.example` to `.mcp.json` and approve the server. It reads the repo's files by default, or the
  published `api/v1/` when `FD_API_URL` is set.
