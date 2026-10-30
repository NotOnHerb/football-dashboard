# Daily sync playbook (every day, 6:13 AM Central)

1. Get the repo: use the add_repo tool for NotOnHerb/football-dashboard with push access, clone it as it instructs,
   `cd` into it, and read `analyst/README.md`.
2. Refresh the Desk snapshot: `pip install pandas numpy --break-system-packages -q` if needed, then
   `python analyst/snapshot.py /tmp/snap`. List collection `snap` on the Desk to get each doc's version, then one ArtifactData
   `batch` that sets every file in /tmp/snap/snap/ (doc id = file name, `if_version` for docs that exist) and deletes any
   `propsN` doc beyond `meta.props_docs`.
3. Approved proposals: query `proposals` where status == "approved". For each, in order:
   - Read only its `spec`, `expected` and the owner's `decision.note` (the note can adjust the change; if it asks for
     something beyond the spec, do not do it: set status `blocked` and explain).
   - Make exactly the change in the spec. Run checks: `python model_fit.py` with FORCE=1 if the model is touched;
     `ODDS_OFFLINE=1 python build.py` must finish without a traceback; if picks logic changed, confirm the page's pick
     logic (template.html) and build.py still agree (same pick ids) by loading index.html in Playwright with a local
     server; the over/under balance of props leans must stay within 35-65% overs unless the spec says otherwise.
   - Pass: `git checkout -- data.json` (never commit an offline build's data), commit the code with message
     "Analyst: <proposal title>" plus the session's attribution lines, push to main, then start the refresh workflow:
     `gh api -X POST repos/NotOnHerb/football-dashboard/actions/workflows/refresh.yml/dispatches -f ref=main -f 'inputs[props]=auto'`.
     Set the proposal `status: "live"`, `live_at`.
   - Fail: change nothing on the site, set `status: "blocked"` and put the reason in `result`.
   - Add a notebook entry for each.
4. Final message: one or two lines. Mention anything that went live or got blocked; otherwise just "Snapshot synced."
   Only a live or blocked change is noteworthy enough for a phone notification.
