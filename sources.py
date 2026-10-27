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


def _get(url):
    req = urllib.request.Request(url, headers={'User-Agent': 'football-dashboard'})
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
    'schedule': nflverse_schedule,
}


def load(name):
    """Load one dataset. Returns (dataframe, info)."""
    return PROVIDERS[name]()
