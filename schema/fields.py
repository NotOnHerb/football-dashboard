"""Names for the positions in data.json's row arrays.

Most blocks in data.json are lists of positional rows (``row[8]``). FIELDS names every position of every row
block, in row order, so code and agents can say ``gsis_id`` instead of 8. ``export`` puts the same names into
data.json as the ``SCHEMA`` key, which the page reads as ``D.SCHEMA``.

Block keys are paths into data.json: ``'DY.P'`` is ``data['DY']['P']``. A block is a list of rows, except
``'P'`` (rows grouped by position), ``'LOG'`` (rows grouped by player) and ``'DY.L'`` (rows keyed by Sleeper id).

Two blocks have a variable tail after the named fields (see TAILS).
Layouts were read from build.py; docs/knowledgebase/03-data-contract.md describes the same rows.
"""

FIELDS = {
    # Offensive player; vals[] is labelled by PC[pos] (see export: 'P.vals').
    'P': ['name', 'team', 'games', 'vals', 'std_per_game', 'injury', 'depth_label', 'form', 'gsis_id'],
    # Defender (IDP). form is [null, null, snap % season, snap % last 3].
    'X': ['name', 'team', 'pos', 'games', 'tackles', 'solo', 'tackles_per_game', 'tfl', 'sacks', 'qb_hits',
          'interceptions', 'passes_defended', 'forced_fumbles', 'fumble_recoveries', 'tds', 'idp_pts',
          'idp_pts_per_game', 'injury', 'depth_label', 'form', 'gsis_id'],
    # One game of one player's log (LOG[gsis_id] is a list of these).
    'LOG': ['week', 'opponent', 'ppr_pts', 'std_pts', 'pos_yards', 'tds', 'receptions', 'pass_yds', 'rush_yds',
            'rec_yds', 'pass_tds', 'rush_rec_tds'],
    # Offensive lineman; slot is LT/LG/C/RG/RT for starters, an en dash otherwise.
    'OLP': ['name', 'team', 'pos', 'games', 'slot', 'penalties', 'penalty_yds', 'injury'],
    # Dynasty player.
    'DY.P': ['name', 'pos', 'team', 'age', 'draft_year', 'draft_round', 'college', 'value_1qb', 'value_2qb',
             'games', 'ppr_per_game', 'last3_ppr', 'snap_pct_season', 'snap_pct_last3', 'injury', 'depth_label',
             'gsis_id'],
    # Future draft pick.
    'DY.K': ['pick', 'value_1qb', 'value_2qb'],
    # Sleeper lookup (DY.L[sleeper_id]); idp_or_k_per_game is IDP pts/g, or kicker pts/g for kickers.
    'DY.L': ['name', 'pos', 'team', 'age', 'value_1qb', 'value_2qb', 'ppr_per_game', 'std_per_game', 'games',
             'last3_ppr', 'idp_or_k_per_game', 'injury', 'depth_label', 'last3_std', 'gsis_id'],
    # College prospect. 0-29 stats and bio, 30-34 computed, 35-39 consensus big board match.
    'CF.P': ['name', 'pos', 'team', 'conference', 'class_year', 'stars', 'recruit_rank', 'hs_class', 'usage_pct',
             'avg_ppa', 'total_ppa', 'draft_eligible',
             'pass_att', 'pass_pct', 'pass_yds', 'pass_td', 'pass_int', 'pass_ypa',
             'rush_car', 'rush_yds', 'rush_td', 'rush_ypc',
             'rec_rec', 'rec_yds', 'rec_td', 'rec_ypr',
             'rec_yds_share', 'rush_yds_share', 'height', 'weight',
             'dynasty_score', 'letter_grade', 'ppr_total', 'std_total', 'team_games',
             'consensus_rank', 'boards', 'best_rank', 'worst_rank', 'name_key'],
    # Consensus big board row; one rank per board follows (order of CF.CB.S).
    'CF.CB.P': ['rank', 'name', 'pos', 'school', 'avg_rank', 'boards', 'best_rank', 'worst_rank'],
    # A board that feeds the consensus.
    'CF.CB.S': ['source', 'url', 'updated', 'length'],
    # Team row; one value per TC column follows (labels: export 'T.cols').
    'T': ['code'],
    # This week's remaining games.
    'G': ['away', 'home', 'label'],
    # Final score this season.
    'ODD.FIN': ['week', 'away', 'home', 'away_score', 'home_score'],
}

# Blocks whose rows run past their named fields, and what the extra values are.
TAILS = {
    'T': 'one value per TC column, labelled by SCHEMA.T.cols',
    'CF.CB.P': 'one rank per board in CF.CB.S, same order (null where a board does not list the player)',
}


def export(pc, tc):
    """FIELDS plus the labels of the two variable parts, as the dict stored under data.json's SCHEMA key.

    pc is data.json's PC ({pos: [[label, decimals], ...]}) and tc its TC ([[label, decimals, ...], ...]).
    """
    out = {block: list(names) for block, names in FIELDS.items()}
    out['P.vals'] = {pos: [c[0] for c in cols] for pos, cols in pc.items()}
    out['T.cols'] = [c[0] for c in tc]
    return out


def named(block, row):
    """One row as {field name: value}. Values past the named fields (see TAILS) are left out."""
    return dict(zip(FIELDS[block], row))


def rows_named(block, rows):
    """A list of rows as a list of {field name: value}."""
    return [named(block, r) for r in rows]
