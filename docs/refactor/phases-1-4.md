# Refactor phases 1-4

The refactor branch is ready for a PR into `main`. The site looks and behaves the same, apart from the address bar
now tracking which view you're on. Before it merges, I'd like your call on the open decisions below, starting with
the analyst sync playbook.

## Your decisions

Here are the things I'd like to square away with you:

1. **`analyst/SYNC.md` needs an update.** It's your file, so I left it alone. Two changes:
   - Step 3 checks pick logic in `template.html`, and the page no longer has any. Picks now come only from the build
     (`engine/picks.py`, rules in `engine/rules.py`), and the page shows `ODD.PK` / `ODD.PKB`. The check that fits
     now is `pytest tests/test_pkb_page.py tests/test_page.py`.
   - After an offline build, it should restore `data.json data/ index.html`. Today it restores only `data.json`.
2. **Front-end pushes.** A push that changes `template.html`, `js/` or `assets/` goes live when the next refresh
   restamps `index.html`. The lighter path is the rule now in `AGENTS.md`: dispatch Refresh after the push. The
   sturdier path is a small restamp-only job on pushes to those paths. It costs a workflow file and no Odds API
   credits.
3. **Daily commit size.** Each refresh now also commits `api/v1/` (about 3.2 MB on current data) and `data/` (about
   1.3 MB), on top of `data.json`. Options: keep it as is, slim `api/v1/college.json`, or later drop the full
   `data.json` from Pages.
4. **The address bar.** Clicking around now updates the URL (`#betting/props`), so any view can be shared as a link.
   Say the word if you'd rather keep the URL fixed.
5. **Carried over from the plan:**
   - running the sync worker through PRs;
   - mirroring the Desk notebook into `decisions/`;
   - generating the Desk `RULES` from `engine.rules`.
6. **Two existing page quirks I kept as-is, so the refactor changes nothing you can see:**
   - the college prospects footnote prints "NaN season so far";
   - a college pick from a book with no spread price shows -110.

   Each is a small fix with a page re-bless, whenever you want it.

## Merging and the first refresh

- The PR's `test.yml` run on Ubuntu should be green before merge. The page snapshot was recorded on Windows. If
  Ubuntu renders a view differently, re-bless it there with `python tests/test_page.py --bless`.
- After merging, dispatch Refresh by hand and watch it. That first run is the first time `main` builds `data/`,
  `api/v1/` and the section health checks, and the first time the live page runs from `js/`.
- To roll back: revert the merge, then dispatch Refresh so `index.html` is restamped from the old template. Bets
  saved on the new page are kept under `fd:mybets` and reappear when the refactor comes back.

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
  - `mcp_server/` serves it over MCP.
  - `AGENTS.md` covers working in the repo, and `docs/api.md` covers the files and tools.
- **Health:** `check_health.py` turns the refresh red when `api/v1/` or `data/` is missing or comes from an older
  build. The site is still committed first.

## Running, re-blessing and MCP

`AGENTS.md` has the full instructions. In short:

- Tests: `PYTHONHASHSEED=0 PYTHONUTF8=1 uv run --no-project --python 3.12 --with-requirements requirements-dev.txt python -m pytest -q`
  (about 3.5 minutes, including the Playwright page test).
- Re-bless, after a change that is meant to change output:
  - data: `python tests/golden/runner.py bless <tmp-dir>`
  - page: `python tests/test_page.py --bless`
  - analyst snapshot: `python tests/test_snapshot.py bless`
- MCP: copy `.mcp.json.example` to `.mcp.json` and approve the server. It reads the repo's files by default, or the
  published `api/v1/` when `FD_API_URL` is set.
