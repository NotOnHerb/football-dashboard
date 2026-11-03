# Football Dashboard — Knowledgebase

A map of the repo as it stands, plus an assessment and a refactor plan, written to support new modules and agent access.
Baseline: commit `74fbe2d` on `main`, 2026-11-02.

| Page | Read it for |
|---|---|
| [01-overview.md](01-overview.md) | What the app is, stack, data sources, repo layout, history, current track record |
| [02-architecture.md](02-architecture.md) | Daily pipeline and agent loop diagrams, where state lives, env vars |
| [03-data-contract.md](03-data-contract.md) | Every `data.json` key and the positional row layouts, pick ids, other committed JSON |
| [04-backend-pipeline.md](04-backend-pipeline.md) | `sources.py`, a section-by-section map of `build.py`, `model_fit.py`, `cfb_fetch.py`, analyst helpers |
| [05-frontend.md](05-frontend.md) | `template.html` sections → functions → data, state, browser-side logic, `desk.html` |
| [06-models-and-betting.md](06-models-and-betting.md) | Team model, fair odds, pick rules, props, parlays, grading, college "best number", duplication table |
| [07-analyst-agent-layer.md](07-analyst-agent-layer.md) | The existing Claude-based Analyst: components, governance, gaps |
| [08-assessment.md](08-assessment.md) | Strengths, ranked risks and debt, readiness for the goals, what wasn't verified |
| [09-refactor-roadmap.md](09-refactor-roadmap.md) | Phased plan: safety net → data contract → one engine → modular front end → agent surface |

## Five things to know first

1. `build.py` → `data.json` → `index.html` is the whole system. A daily GitHub Action runs it and commits the result to `main`.
2. `data.json` rows are **positional arrays**, so field meaning lives only in the code. [03](03-data-contract.md) is the decoder ring.
3. The pick logic runs in **both** Python and the browser (and is partly copied again for the analyst). Change one copy and you must change the others.
4. The build swallows errors section by section, so a "green" run can still ship a site with missing sections.
5. An agent system (the Analyst) already exists and can push to `main`. Read [07](07-analyst-agent-layer.md) before adding agents.

## Keeping this current

Line numbers drift. When a page here disagrees with the code, the code wins. Update the page in the same PR as the change.
