"""Data sources for the football dashboard.

Every dataset the site uses comes through ONE function in this file. build.py never
downloads anything itself. To switch a dataset to a different (for example paid, live)
provider, write a new loader that returns a DataFrame with the SAME columns listed in
its CONTRACT below, and point PROVIDERS at it. Nothing else has to change.

Each loader returns (dataframe, info) where info is a small dict describing freshness,
for example {'provider': 'nflverse', 'asof': '2026-10-26'}. The site shows it.
"""
import io, os, urllib.request
import pandas as pd

SEASON = int(os.environ.get('SEASON', 2026))
NFLVERSE = 'https://github.com/nflverse/nflverse-data/releases/download/'


def _get(url, headers=None):
    h = {'User-Agent': 'football-dashboard'}
    h.update(headers or {})
    req = urllib.request.Request(url, headers=h)
    return io.BytesIO(urllib.request.urlopen(req, timeout=120).read())


def _need(df, cols, name):
    missing = set(cols) - set(df.columns)
    if missing:
        raise ValueError('%s is missing columns %s, not updating the site' % (name, sorted(missing)))
    return df


# ---------------------------------------------------------------- contracts
# Season totals, one row per player.
SEASON_STATS = ['player_id', 'player_display_name', 'position', 'position_group', 'recent_team', 'games',
                'fantasy_points', 'fantasy_points_ppr', 'attempts', 'carries', 'targets', 'def_sacks']
# One row per player per game. opponent_team is what makes "points allowed" possible.
WEEKLY_STATS = ['player_id', 'position', 'team', 'opponent_team', 'week', 'game_id', 'season', 'season_type',
                'fantasy_points', 'fantasy_points_ppr', 'passing_yards', 'rushing_yards', 'receiving_yards',
                'passing_tds', 'rushing_tds', 'receiving_tds', 'receptions']
# Depth chart snapshots. Only the newest snapshot (max dt) is used.
DEPTH = ['dt', 'team', 'player_name', 'gsis_id', 'pos_grp', 'pos_abb', 'pos_rank']
# Injury report rows. gsis_id must match player_id in the stats.
INJURIES = ['season', 'week', 'gsis_id', 'report_status', 'report_primary_injury']
# Weekly roster status. status RES means a reserve list (injured reserve and similar).
ROSTERS = ['week', 'gsis_id', 'team', 'status', 'status_description_abbr']
# Snap counts per player per game (linked to players by pfr_player_id).
SNAPS = ['game_id', 'week', 'pfr_player_id', 'team', 'offense_pct', 'defense_pct']
# Player bios and IDs.
PLAYERS = ['gsis_id', 'pfr_id', 'display_name', 'birth_date', 'college_name', 'draft_year', 'draft_round', 'draft_pick']
# Dynasty trade values (players and future rookie picks) and an ID map to gsis_id.
DYNASTY = ['player', 'pos', 'team', 'age', 'value_1qb', 'value_2qb', 'fp_id', 'scrape_date']
# College (CollegeFootballData.com, needs the CFBD_KEY secret). Long-form season stats, one row per stat.
CFB_STATS = ['playerId', 'player', 'position', 'team', 'conference', 'category', 'statType', 'stat']
# Schedule, one row per game. Scores are blank for games not played yet.
SCHEDULE = ['season', 'game_type', 'week', 'gameday', 'gametime', 'away_team', 'home_team', 'away_score']


# ---------------------------------------------------------------- nflverse (free, refreshes about daily)
def nflverse_season_stats():
    path = os.environ.get('CSV_PATH')
    df = pd.read_csv(path if path else _get(NFLVERSE + 'stats_player/stats_player_regpost_%d.csv' % SEASON))
    if len(df) < 1000:
        raise ValueError('Season stats file looks too small (%d rows), not updating the site' % len(df))
    return _need(df, SEASON_STATS, 'season stats'), {'provider': 'nflverse', 'rows': len(df)}


def nflverse_weekly_stats():
    df = pd.read_csv(_get(NFLVERSE + 'stats_player/stats_player_week_%d.csv' % SEASON))
    df = _need(df, WEEKLY_STATS, 'weekly stats')
    return df, {'provider': 'nflverse', 'week': int(df.week.max())}


def nflverse_depth():
    df = pd.read_csv(_get(NFLVERSE + 'depth_charts/depth_charts_%d.csv' % SEASON), usecols=DEPTH)
    return df, {'provider': 'nflverse', 'asof': str(df.dt.max())[:10]}


def nflverse_injuries():
    df = _need(pd.read_csv(_get(NFLVERSE + 'injuries/injuries_%d.csv' % SEASON)), INJURIES, 'injuries')
    return df, {'provider': 'nflverse', 'week': int(df.week.max())}


def nflverse_rosters():
    df = _need(pd.read_csv(_get(NFLVERSE + 'weekly_rosters/roster_weekly_%d.csv' % SEASON)), ROSTERS, 'rosters')
    return df, {'provider': 'nflverse', 'week': int(df.week.max())}


def nflverse_snaps():
    df = _need(pd.read_csv(_get(NFLVERSE + 'snap_counts/snap_counts_%d.csv' % SEASON)), SNAPS, 'snap counts')
    return df, {'provider': 'nflverse', 'week': int(df.week.max())}


def nflverse_players():
    return _need(pd.read_csv(_get(NFLVERSE + 'players/players.csv')), PLAYERS, 'players'), {'provider': 'nflverse'}


DYNASTYPROCESS = 'https://raw.githubusercontent.com/dynastyprocess/data/master/files/'


def dynastyprocess_values():
    """Free dynasty trade values from DynastyProcess (based on FantasyPros expert rankings).
    Returns values joined to gsis_id (blank for picks and unmatched players)."""
    local = os.environ.get('DP_DIR')
    src = (lambda f: os.path.join(local, f)) if local else (lambda f: _get(DYNASTYPROCESS + f))
    v = _need(pd.read_csv(src('values.csv')), DYNASTY, 'dynasty values')
    ids = pd.read_csv(src('db_playerids.csv'), usecols=['fantasypros_id', 'gsis_id'])
    ids = ids.dropna().drop_duplicates('fantasypros_id')
    v = v.merge(ids, left_on='fp_id', right_on='fantasypros_id', how='left')
    return v, {'provider': 'DynastyProcess', 'asof': str(v.scrape_date.max())}


def dynastyprocess_ids():
    """Cross-site player ID map (Sleeper, FantasyPros, nflverse gsis and more)."""
    local = os.environ.get('DP_DIR')
    f = os.path.join(local, 'db_playerids.csv') if local else _get(DYNASTYPROCESS + 'db_playerids.csv')
    df = pd.read_csv(f, usecols=['sleeper_id', 'espn_id', 'gsis_id', 'name', 'position', 'team', 'age'])
    return df, {'provider': 'DynastyProcess'}


CFBD = 'https://apinext.collegefootballdata.com/'


def _cfbd(path):
    key = os.environ.get('CFBD_KEY')
    if not key:
        raise RuntimeError('no CFBD_KEY secret set')
    import json
    return json.load(_get(CFBD + path, {'Authorization': 'Bearer ' + key}))


def cfbd_college():
    """Everything the college pages need, about 12 API calls. Returns a dict of DataFrames:
    stats (CFB_STATS), usage, ppa, roster and recruits."""
    yr = SEASON
    stats = pd.concat([pd.DataFrame(_cfbd('stats/player/season?year=%d&category=%s' % (yr, c))) for c in ('passing', 'rushing', 'receiving')])
    _need(stats, CFB_STATS, 'college stats')
    usage = pd.json_normalize(_cfbd('player/usage?year=%d' % yr))
    ppa = pd.json_normalize(_cfbd('ppa/players/season?year=%d' % yr))
    roster = pd.DataFrame(_cfbd('roster?year=%d' % yr))
    recruits = pd.concat([pd.DataFrame(_cfbd('recruiting/players?year=%d&classification=HighSchool' % y)) for y in range(yr - 4, yr + 1)])
    try:
        games = pd.DataFrame(_cfbd('games?year=%d&seasonType=regular' % yr))
    except Exception:
        games = None
    return {'stats': stats, 'usage': usage, 'ppa': ppa, 'roster': roster, 'recruits': recruits, 'games': games}, {'provider': 'CollegeFootballData.com', 'season': yr}


ODDS = 'https://api.the-odds-api.com/v4/sports/americanfootball_nfl/'
PROP_MARKETS = 'player_pass_yds,player_rush_yds,player_reception_yds,player_receptions,player_pass_tds,player_anytime_td'
ODDS_RESERVE = 40   # never let a refresh take credits below this
# Up to 10 named books cost the same as one region. Pinnacle is the sharp reference for fair odds.
ODDS_BOOKS = os.environ.get('ODDS_BOOKS') or 'pinnacle,draftkings,fanduel,betmgm,williamhill_us,espnbet,fanatics,betrivers,bovada,betonlineag'


def odds_update(week_pairs, team_of_name, cache_dir='odds'):
    """Game lines every run (about 3 credits) plus player props on a schedule, cached in cache_dir.
    week_pairs: set of (away, home) team codes for this week's games. team_of_name: full name -> code.
    Free plan (default): props on Thursday for Thursday games and on Friday for the rest of the week.
    ODDS_PLAN=paid: props for games in the next 4 days, refreshed when older than 6 hours.
    ODDS_PROPS=all fetches props for every game this week that isn't cached yet (one-off)."""
    import json, datetime as dt
    key = os.environ.get('ODDS_API_KEY')
    if os.environ.get('ODDS_OFFLINE'):   # local testing: use the saved odds, spend no credits
        L = json.load(open(os.path.join(cache_dir, 'lines.json')))
        evs = [e for e in L['data'] if (team_of_name.get(e['away_team']), team_of_name.get(e['home_team'])) in week_pairs]
        pr = {}
        for e in evs:
            f = os.path.join(cache_dir, 'props', e['id'] + '.json')
            if os.path.exists(f): pr[e['id']] = json.load(open(f))
        return {'lines': L['data'], 'events': evs, 'props': pr}, {'provider': 'The Odds API', 'lines_at': L['fetched'], 'props_games': len(pr),
                'props_fetched_now': 0, 'credits_used_now': 0, 'credits_left': None, 'plan': 'offline'}
    if not key:
        raise RuntimeError('no ODDS_API_KEY secret set')
    os.makedirs(os.path.join(cache_dir, 'props'), exist_ok=True)
    state = {'remaining': None, 'used_now': 0}

    def call(path):
        req = urllib.request.Request(ODDS + path + ('&' if '?' in path else '?') + 'apiKey=' + key, headers={'User-Agent': 'football-dashboard'})
        r = urllib.request.urlopen(req, timeout=60)
        rem = r.headers.get('x-requests-remaining'); last = r.headers.get('x-requests-last')
        if rem is not None: state['remaining'] = int(float(rem))
        if last is not None: state['used_now'] += int(float(last))
        return json.load(r)

    now = dt.datetime.now(dt.timezone.utc)
    lines = call('odds?bookmakers=%s&markets=h2h,spreads,totals&oddsFormat=american' % ODDS_BOOKS)
    json.dump({'fetched': now.isoformat(), 'data': lines}, open(os.path.join(cache_dir, 'lines.json'), 'w'))
    plan, mode = os.environ.get('ODDS_PLAN', 'free'), os.environ.get('ODDS_PROPS', 'auto')
    local = now.astimezone(dt.timezone(dt.timedelta(hours=-5)))  # US Central (close enough for scheduling)
    events = []
    for ev in lines:
        pair = (team_of_name.get(ev['away_team']), team_of_name.get(ev['home_team']))
        if pair in week_pairs:
            events.append(ev)
    props, fetched = {}, 0
    for ev in events:
        f = os.path.join(cache_dir, 'props', ev['id'] + '.json')
        cached = json.load(open(f)) if os.path.exists(f) else None
        start = dt.datetime.fromisoformat(ev['commence_time'].replace('Z', '+00:00'))
        if start < now:
            if cached: props[ev['id']] = cached
            continue
        age_h = (now - dt.datetime.fromisoformat(cached['fetched'])).total_seconds() / 3600 if cached else None
        days_out = (start - now).total_seconds() / 86400
        start_local = start.astimezone(dt.timezone(dt.timedelta(hours=-5)))
        if mode == 'off':
            want = False
        elif mode == 'all':
            want = cached is None
        elif plan == 'paid':
            want = days_out <= 4 and (cached is None or age_h > 6)
        else:
            dow = local.weekday()  # Mon 0 .. Sun 6
            want = ((dow == 3 and start_local.weekday() in (3, 4)) or (dow == 4 and start_local.weekday() in (5, 6, 0))) and (cached is None or age_h > 20)
        if want and (state['remaining'] is None or state['remaining'] - 6 >= ODDS_RESERVE):
            try:
                data = call('events/%s/odds?bookmakers=%s&markets=%s&oddsFormat=american' % (ev['id'], ODDS_BOOKS, PROP_MARKETS))
                cached = {'fetched': now.isoformat(), 'data': data}
                json.dump(cached, open(f, 'w')); fetched += 1
            except Exception as ex:
                print('props fetch failed for', ev['id'], ex)
        if cached:
            props[ev['id']] = cached
    keep = {e['id'] for e in lines}
    for fn in os.listdir(os.path.join(cache_dir, 'props')):
        if fn[:-5] not in keep:
            os.remove(os.path.join(cache_dir, 'props', fn))
    info = {'provider': 'The Odds API', 'lines_at': now.isoformat(), 'props_games': len(props), 'props_fetched_now': fetched,
            'credits_used_now': state['used_now'], 'credits_left': state['remaining'], 'plan': plan}
    return {'lines': lines, 'events': events, 'props': props}, info


def nflverse_schedule():
    df = _need(pd.read_csv(_get(NFLVERSE + 'schedules/games.csv')), SCHEDULE, 'schedule')
    return df, {'provider': 'nflverse'}


# ---------------------------------------------------------------- which loader feeds each dataset
# To plug in a paid feed later, add e.g. def sportradar_injuries(): ... returning the INJURIES
# columns, then change the entry below to sportradar_injuries. Keep API keys in GitHub
# Secrets (read them with os.environ), never in this file or the page.
PROVIDERS = {
    'season_stats': nflverse_season_stats,
    'weekly_stats': nflverse_weekly_stats,
    'depth': nflverse_depth,
    'injuries': nflverse_injuries,
    'rosters': nflverse_rosters,
    'snaps': nflverse_snaps,
    'players': nflverse_players,
    'dynasty_values': dynastyprocess_values,
    'player_ids': dynastyprocess_ids,
    'college': cfbd_college,
    'schedule': nflverse_schedule,
}


def load(name):
    """Load one dataset. Returns (dataframe, info)."""
    return PROVIDERS[name]()


# ---------------------------------------------------------------- weather (Open-Meteo, free, no key)
# Home stadium coordinates (roughly; good enough for a forecast). Domes are skipped using the schedule's roof field.
STADIUMS = {'ARI': (33.528, -112.263), 'ATL': (33.755, -84.401), 'BAL': (39.278, -76.623), 'BUF': (42.774, -78.787), 'CAR': (35.226, -80.853),
            'CHI': (41.862, -87.617), 'CIN': (39.095, -84.516), 'CLE': (41.506, -81.700), 'DAL': (32.748, -97.093), 'DEN': (39.744, -105.020),
            'DET': (42.340, -83.046), 'GB': (44.501, -88.062), 'HOU': (29.685, -95.411), 'IND': (39.760, -86.164), 'JAX': (30.324, -81.637),
            'KC': (39.049, -94.484), 'LV': (36.091, -115.184), 'LAC': (33.953, -118.339), 'LA': (33.953, -118.339), 'MIA': (25.958, -80.239),
            'MIN': (44.974, -93.258), 'NE': (42.091, -71.264), 'NO': (29.951, -90.081), 'NYG': (40.813, -74.074), 'NYJ': (40.813, -74.074),
            'PHI': (39.901, -75.168), 'PIT': (40.447, -80.016), 'SF': (37.403, -121.970), 'SEA': (47.595, -122.332), 'TB': (27.976, -82.503),
            'TEN': (36.166, -86.771), 'WAS': (38.908, -76.864)}


def weather_at(team, kickoff_iso):
    """Forecast at kickoff for the home team's stadium: {'t': temp F, 'w': wind mph, 'g': gusts mph, 'pp': rain/snow chance %}.
    Returns None when the stadium is unknown or the game is more than about two weeks out."""
    import json, datetime as dt
    if team not in STADIUMS: return None
    lat, lon = STADIUMS[team]
    k = dt.datetime.fromisoformat(kickoff_iso.replace('Z', '+00:00'))
    day = k.strftime('%Y-%m-%d')
    url = ('https://api.open-meteo.com/v1/forecast?latitude=%s&longitude=%s&hourly=temperature_2m,wind_speed_10m,wind_gusts_10m,precipitation_probability'
           '&temperature_unit=fahrenheit&wind_speed_unit=mph&timezone=UTC&start_date=%s&end_date=%s') % (lat, lon, day, day)
    h = json.load(_get(url))['hourly']
    i = min(range(len(h['time'])), key=lambda j: abs((dt.datetime.fromisoformat(h['time'][j] + '+00:00') - k).total_seconds()))
    g = lambda c: (None if h[c][i] is None else round(h[c][i]))
    return {'t': g('temperature_2m'), 'w': g('wind_speed_10m'), 'g': g('wind_gusts_10m'), 'pp': g('precipitation_probability')}
