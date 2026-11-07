# 08 — Honest assessment

*Static review of commit `74fbe2d` (2026-11-02). The code was read but not executed. See "What this review did not do"
at the bottom.*

## Bottom line

This is a working, feature-rich product built in one week by an owner directing Claude. **The product thinking and the
statistical hygiene are well ahead of the code structure.** The code is shaped for one agent editing whole files in
context: a single-script pipeline, a single-file page, positional data, logic copied where it's needed. That shape
made the first week fast. It's also what will slow down the next phase: new modules, more contributors, agent access
and public users.

This doesn't need a rewrite. Each problem below has an incremental fix, and the existing seams (`sources.py`
contracts, `snapshot.py`'s named view, the analyst governance model) are the right places to grow from.

## What's genuinely good

- **Ingestion contracts.** `sources.py` has per-dataset column contracts, a provider registry, and freshness metadata
  that surfaces in the UI. This is the right pattern for adding paid feeds later.
- **Statistical discipline.** Shin's no-vig, Pinnacle as the fair-odds reference, quantiles learned on last season with
  calibration on this season, walk-forward model records, held-out testing rules, and a "stale price" guard against
  too-good-to-be-true lines. The playbooks explicitly warn about multiple testing and small samples.
- **Cost awareness.** The Odds API credit budget, a reserve floor, a props schedule by plan, caching, and an offline
  mode that spends nothing.
- **The agent governance design.** Proposer/skeptic separation with information hiding, an owner approval gate, an
  append-only notebook, and versioned writes. It's more careful than most production agent setups.
- **UX care.** Accessibility attributes throughout, a deliberate mobile layout, plain-English explanations and a glossary.
- **Docs that match reality.** README, ROADMAP and the analyst playbooks are short, current and accurate.

## Risks and debt, ranked

Severity is judged against the stated goals: new modules, agentic access, and eventually opening the app to other people.

| # | Issue | Severity | Evidence | Why it matters |
|---|---|---|---|---|
| 1 | **Pick and odds logic exists in up to four copies** (build.py, template.html, snapshot.py, Desk `RULES` prose). The page ignores `ODD.PK` and recomputes picks. | **High** | [05](05-frontend.md#business-logic-in-the-browser), [06](06-models-and-betting.md#where-the-logic-is-duplicated) | The picks shown can drift from the picks logged and graded. Any model change has to be made 2-4 times. The only parity check is an agent driving a browser. |
| 2 | **Positional arrays with no schema.** Fields are read by index on both sides (`r[30]`, `x[13]`, dynasty weights keyed by column number). | **High** | [03](03-data-contract.md) | Every new column is a coordinated, untested edit in two languages. Agents can't use the data without reverse-engineering `build.py`. |
| 3 | **No tests, and failures are silent by design.** Each `build.py` section and two CI steps swallow exceptions. The page's init chain has no isolation. | **High** | `build.py` try/except per section; `refresh.yml` `|| echo` | A broken upstream feed or a bad edit ships a site with sections missing and nobody notices. This matters more once an agent edits code. |
| 4 | **The analyst sync pushes straight to `main`.** No PR, no CI gate. | **High** (once more agents join) | `analyst/SYNC.md` step 3 | The only gate is the agent's own checks. That's fine for one trusted worker, but it doesn't scale to more agents or contributors. |
| 5 | **Unescaped external strings in `innerHTML`.** Sleeper/ESPN team names, Odds API player names, board URLs in `href`. | **Medium** (High if public) | 65 `innerHTML` writes vs 14 `esc()` calls | League-mate team names are attacker-controlled input. Today the blast radius is one person's localStorage. With accounts it becomes a real vulnerability. |
| 6 | **Git is the database.** ~1.3 MB `data.json` plus ledgers committed daily. The workflow has no `concurrency:` group. | **Medium** | 41 data commits in 7 days; `.git` already 2.7 MB packed | History grows by roughly tens of MB a year. Pushes can race with the analyst sync. Pick ledgers have no audit trail beyond diffs. |
| 7 | **`build.py` is one 1,057-line script with shared globals.** Names are reused with different meanings (`INJ`, `dv`, `done`, `fin`). | **Medium** | [04](04-backend-pipeline.md#things-to-know-before-editing-buildpy) | Moving or extracting a section can break things in ways that don't raise errors. You can't import one piece without running the whole build. |
| 8 | **The front end is one 198 KB file with no routing or registry.** A new section touches about 8 places. | **Medium** | [05](05-frontend.md#cost-to-add-a-new-section-today) | This is the direct cost of every new module. Logic fused into string-building renderers can't be reused or tested. |
| 9 | **1.33 MB eager payload.** College (32%) and dynasty (19%) load even for a betting-only visit. | **Medium** (mobile) | [03](03-data-contract.md#top-level-keys-2026-11-02-build-133-mb) | Slow first paint on phones. Sharding would also create natural per-domain endpoints. |
| 10 | **Institutional memory lives outside the repo.** Reports, proposals and the notebook are in one person's Claude Artifact. | **Medium** | [07](07-analyst-agent-layer.md) | Collaborators (including you) can't see why the model is the way it is. |
| 11 | **Environment fragility.** Unpinned pandas/numpy. Central time hard-coded as UTC-5 (wrong from 2026-11-01). `%-I` breaks on Windows and silently falls back to stale October games. | **Low-Med** | `refresh.yml`; `sources.py:189`; `build.py:18, 103` | Surprises when running locally or after an upstream release. |
| 12 | **Hard-coded facts in code.** The college backtest record, a stale `G_FALLBACK`, team, book and name alias tables. | **Low** | `build.py:103, 1041` | Numbers shown to users don't update when the strategy changes. |
| 13 | **Dead code and dense naming.** | **Low** | [05](05-frontend.md#code-quality-notes) | Onboarding cost for humans. Agents cope with it better than people do. |

## The track record, in context

NFL picks are 7-9 (−3.45u), parlays 0-3, college picks 5-6 (−1.57u). That's about 30 graded bets in total, so the
results say nothing yet in either direction. The project's own rules require 100+ picks before drawing conclusions.
The college "best number" rule's 55.8% backtest is the most substantive edge claim. It's worth re-deriving in code
rather than displaying as a hard-coded number.

## Readiness for the stated goals

| Goal | Ready? | Main blockers |
|---|---|---|
| Add new modules (e.g. home screen, trade analyzer, playoff SOS from the ROADMAP) | Possible, but each one costs more than it should | #2, #7, #8 |
| Agentic read access (an agent answering questions about picks/players) | Partly. The Desk's Ask tab works, but only inside the Artifact | #2, #1 |
| Agentic write access (agents changing the model safely) | Works for one trusted worker | #3, #4, #1 |
| Open to other users | Not yet | #5, #6, #9, plus accounts/storage/legal (the ROADMAP's About page) |

## What this review did not do

- **Did not run anything.** The offline build, `model_fit.py` and the page were not executed. A local offline build in a
  scratch copy was attempted and blocked pending permission. Claims about runtime behavior (e.g. the Windows fallback)
  are from reading the code.
- **Did not check the live site** or GitHub Actions run history for past failures.
- **Did not see the Analyst Desk's contents** (reports, proposals, notebook). They live in the owner's Claude account.
- Front-end findings come from a delegated full read of `template.html` and `desk.html`, with key claims spot-checked
  (no `ODD.PK` use, no routing, 65/14 `innerHTML`/`esc`, fallback `RU` without `tdmax`, the init chain).
