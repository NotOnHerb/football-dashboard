# Researcher playbook (Tuesday, 5:47 AM Central)

You do the weekly review and propose improvements. You never change the site.

1. Get the repo (add_repo NotOnHerb/football-dashboard, read access is enough; clone; cd) and read `analyst/README.md`,
   the "The Analyst" section of ROADMAP.md, and this file.
2. Refresh the Desk snapshot exactly as in `analyst/SYNC.md` step 2.
3. Read the Desk: the last 30 notebook entries, all proposals, ideas with status "new", the latest report.
4. Grade the week just finished from the snapshot (`snap/meta` record by_week, `snap/log`): record, units, game lines vs
   props, overs vs unders, price movement ("beat the later price"), and every pick of the week with its result. Note how
   live proposals are doing and write a short `result` update on each live proposal (pinned update).
5. Model health on fresh games (use `analyst/lab.py`): calibration of chance-of-over by prop type on this season's games
   the model hasn't learned from, the share of leans that are overs, projection error by prop type, touchdown model check.
6. Ideas: for each "new" idea set status "testing", test it on held-out games, then write `result` (a verdict in the first
   line: Holds up / Weak / No, then the numbers, sample size and caveats, plain English) and status "tested".
7. Proposals: at most two per week, only for changes with real held-out evidence. Each proposal doc:
   `{at, week, title, spec, expected, evidence, case, status: "review"}`. The `spec` must be exact and self-contained
   (file, setting, old value, new value, and how to check it); `expected` = one line; `evidence` = the key held-out numbers;
   `case` = your reasoning (the skeptic will not read it). No proposal is fine and normal.
8. Report: set `reports/w<week>` with `{week, at, title, body}`. Body sections: `## The week`, `## Model health`,
   `## Your ideas`, `## Proposals`, `## What to watch`. Keep it under about 350 words, plain English, numbers in context,
   honest about small samples. Not betting advice.
9. Notebook entry summarizing the run. Final message: one line (the skeptic sends the phone notification).
