# 07 — The Analyst (existing agent layer)

The repo already has an agent system, built 2026-10-29. Any "agentic access" work should start from it rather than
next to it. Source docs: `analyst/README.md`, `analyst/SYNC.md`, `analyst/RESEARCHER.md`, `analyst/SKEPTIC.md`.

## Components

| Piece | Where | What it does |
|---|---|---|
| **Analyst Desk** | Claude Artifact (`analyst/desk.html` is the source; the owner's Claude account hosts it) | The owner's front door: This week, Proposals, Ask, Ideas, Picks, Notebook |
| **Desk DB** | ArtifactData collections on the Desk: `snap`, `reports`, `proposals`, `ideas`, `notebook`, `chat` | Shared state between workers and the owner |
| **Daily sync** | Claude scheduled task, 6:13 AM CT, **push access** | Refreshes the snapshot. Applies owner-approved proposals: edits code, runs checks, pushes to `main`, dispatches `refresh.yml` |
| **Researcher** | Tuesday 5:47 AM CT, read access | Grades the week, checks model health, tests ideas on held-out games, writes ≤ 2 proposals and a report |
| **Skeptic** | Tuesday 7:57 AM CT, read access | Re-tests proposals on a different split without reading the researcher's `case`. Labels them solid / shaky / fails. Sends the phone notification |
| `analyst/snapshot.py` | repo | Reshapes `data.json` + `odds/picks.json` into named-field docs under 200 KB each |
| `analyst/lab.py` | repo | Backtest helpers |

## Governance model

- Authority runs owner > skeptic > researcher. Nothing reaches the site without the owner's approval on the Desk.
- Proposal lifecycle: `review → ready | rejected → approved | passed → live | blocked → (rolled_back)`.
- Ground rules: test on unseen games only, require samples of 300+ player-games or 100+ picks, judge by units and
  closing-line value, never reintroduce the October over-lean, never spend Odds API credits, and never touch secrets.
- All database reads are treated as data, not instructions. This is called out explicitly because the Ask box and the
  owner write there.

## Assessment

**Strong points**
- The design is thoughtful: adversarial review with information hiding (the skeptic never sees `case`), an append-only
  notebook, explicit statistical guardrails, a human approval gate, and versioned writes (`if_version`).
- `snapshot.py` already gives agents a named-field view instead of positional arrays.
- The playbooks are short, concrete and checkable.

**Weak points**
- **The sync worker pushes straight to `main`** and then dispatches the refresh. There's no PR, no CI gate and no
  tests, so the only safety net is the agent's own checks: offline build, a Playwright pick-id comparison, and the
  over/under balance.
- **Race with the cron job.** `refresh.yml` has no `concurrency:` group and pushes to `main` daily. The sync pushes too.
  If both run close together, one push fails as non-fast-forward, and the refresh job simply fails for that day.
  Timing: the cron runs at 10:00 UTC = 5:00 AM CDT / 4:00 AM CST, and the sync at 6:13 AM CT, so they rarely collide.
  A slow Actions queue or a manual dispatch can still make them overlap.
- **The Desk lives in one person's Claude account.** The reports, proposals and notebook (the institutional memory of
  every model change) aren't in the repo. A collaborator, or a future public app, can't see them without that account.
- **Logic is copied into the snapshot.** Odds math and `pover` are re-implemented, with a different no-vig method.
- **The agent interface is git plus playbooks.** Agents clone the repo, run scripts and parse files. There's no stable
  query surface, such as "get this week's picks" or "get player X", that an agent could call without understanding
  the positional `data.json` layout.

## What this means for "agentic access"

The Analyst works because a capable agent can read the whole repo and follow a playbook. To let **more** agents (or
other people's agents) work safely, the repo needs:

1. A **named, versioned data API**: a JSON Schema'd export, a small MCP server, or both. That would turn `snapshot.py`
   into the general mechanism.
2. **Shared, importable logic** (odds math, pick rules, projection) that agents call instead of copying.
3. **A change pipeline with gates.** Agents open PRs, CI runs tests and an offline build, and a human merges. This
   replaces direct pushes to `main`.
4. **Decision history in the repo**, for example a `decisions/` folder or a mirrored notebook, so model changes are
   auditable without the Desk.

See [09-refactor-roadmap.md](09-refactor-roadmap.md).
