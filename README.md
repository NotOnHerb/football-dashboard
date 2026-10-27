# football-dashboard

Live site: https://notonherb.github.io/football-dashboard/

## How it works

- `sources.py` is the only file that downloads data. Each dataset (season stats, game-by-game stats,
  depth charts, injury report, roster status, schedule) has one loader that returns a fixed set of
  columns, listed as a CONTRACT at the top of the file.
- `build.py` turns those datasets into `data.json`, and stamps `index.html` from `template.html`.
- `index.html` is the page. It loads `data.json` when it opens, so fresh data never needs a new page.
- `.github/workflows/refresh.yml` runs the build every day at about 6 AM Eastern and saves the result.

## Plugging in a paid or live data feed later

1. Add a loader to `sources.py` (for example `sportradar_injuries()`) that returns the same columns as
   that dataset's CONTRACT, plus an info dict for the freshness line.
2. Point that dataset at it in `PROVIDERS`.
3. Put the API key in the repo's GitHub Secrets and read it with `os.environ` in the loader. Never put
   a key in the page or in this repo's files.
4. Make the workflow run more often if the feed updates faster (the `cron` line).

Data from nflverse is licensed CC-BY 4.0.
