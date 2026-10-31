"""Caches college football games and betting lines from CollegeFootballData (CFBD_KEY secret) into cfb/.
Past seasons are fetched once; the current season is refreshed every run (2 API calls).
Writes cfb/games_<year>.json, cfb/lines_<year>.json and cfb/fetch_log.txt (what happened, for checking without logs)."""
import os, json, datetime
import sources

SEASON = sources.SEASON
FIRST = SEASON - 4
os.makedirs('cfb', exist_ok=True)
log = []

def pick(d, keys): return {k: d.get(k) for k in keys}

def fetch(year):
    g = sources._cfbd('games?year=%d&seasonType=regular&classification=fbs' % year)
    games = [pick(x, ['id', 'week', 'startDate', 'neutralSite', 'conferenceGame', 'homeTeam', 'homeConference', 'homeClassification',
                      'homePoints', 'homePregameElo', 'awayTeam', 'awayConference', 'awayClassification', 'awayPoints', 'awayPregameElo',
                      'completed']) for x in g]
    L = sources._cfbd('lines?year=%d&seasonType=regular' % year)
    keep = ['provider', 'spread', 'spreadOpen', 'overUnder', 'overUnderOpen', 'homeMoneyline', 'awayMoneyline']
    lines = [{'id': x.get('id'), 'week': x.get('week'), 'homeTeam': x.get('homeTeam'), 'awayTeam': x.get('awayTeam'),
              'homeScore': x.get('homeScore'), 'awayScore': x.get('awayScore'), 'lines': [pick(l, keep) for l in (x.get('lines') or [])]} for x in L]
    json.dump(games, open('cfb/games_%d.json' % year, 'w'), separators=(',', ':'))
    json.dump(lines, open('cfb/lines_%d.json' % year, 'w'), separators=(',', ':'))
    provs = {}
    for x in lines:
        for l in x['lines']: provs[l['provider']] = provs.get(l['provider'], 0) + 1
    log.append('%d: %d games, %d with lines, providers %s' % (year, len(games), sum(1 for x in lines if x['lines']), provs))

for y in range(FIRST, SEASON + 1):
    if y == SEASON or not os.path.exists('cfb/lines_%d.json' % y):
        try: fetch(y)
        except Exception as ex: log.append('%d: failed: %s' % (y, ex))
open('cfb/fetch_log.txt', 'w').write(datetime.datetime.now(datetime.timezone.utc).isoformat()[:16] + '\n' + '\n'.join(log) + '\n')
print('\n'.join(log))
