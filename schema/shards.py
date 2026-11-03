"""How data.json is split into the files the page loads.

build.py writes data.json whole (for analyst/snapshot.py, the Desk sync, api_export.py and the MCP server) and also
split by top-level key into data/<shard>.json, plus data/index.json, which is SHARDS as JSON. The page loads
data/index.json and data/core.json at boot, and a section's other shards the first time it is opened, using the
dataKeys each section declares (js/registry.js). Every top-level key is in exactly one shard, so the shards together
are data.json.

tests/test_page.py imports write() too, so the pages it serves from an edited data.json are split the same way.
"""
import json, os

SHARDS = {
    # The boot (META, the player rows P, X, OLP, the field names SCHEMA) and every NFL view, the default section.
    'core': ['META', 'SCHEMA', 'P', 'PC', 'T', 'TC', 'N', 'X', 'OLP', 'DEP', 'ALW', 'G'],
    # Player cards: headshot, bio and news id per player.
    'players': ['PL'],
    # Fantasy: dynasty values and draft picks (DY) and last season's points (PRI, which start/sit and the player
    # card's "this week" line blend in). The player card reads both too.
    'dynasty': ['DY', 'PRI'],
    # Fantasy -> College.
    'college': ['CF'],
    # Betting, NFL and college. LOG (game logs) lives here because Betting grades saved prop bets with it; the only
    # other reader, the player card, loads this shard anyway for its props.
    'odds': ['ODD', 'CFB', 'LOG'],
}
DIR = 'data'


def split(data):
    """{shard: {key: value}} for data (data.json as a dict), keys in SHARDS order. Raises ValueError unless every
    top-level key of data is in exactly one shard and every shard key is in data."""
    listed = [k for ks in SHARDS.values() for k in ks]
    twice = sorted({k for k in listed if listed.count(k) > 1})
    unmapped, absent = sorted(set(data) - set(listed)), sorted(set(listed) - set(data))
    if twice or unmapped or absent:
        raise ValueError('data.json keys and schema/shards.py SHARDS disagree: in no shard %s, missing from data %s, '
                         'in two shards %s' % (unmapped, absent, twice))
    return {name: {k: data[k] for k in keys} for name, keys in SHARDS.items()}


def dumps(obj):
    """JSON the way build.py writes data.json."""
    return json.dumps(obj, separators=(',', ':'), ensure_ascii=False, allow_nan=False)


def write(data, root='.'):
    """Writes root/data/<shard>.json for every shard and root/data/index.json, and removes any other .json file in
    root/data (a shard that was renamed or dropped). Returns {file name: bytes}."""
    parts = split(data)
    out = os.path.join(root, DIR)
    os.makedirs(out, exist_ok=True)
    files = {'%s.json' % name: dumps(part) for name, part in parts.items()}
    files['index.json'] = dumps(SHARDS)
    for f in os.listdir(out):
        if f.endswith('.json') and f not in files: os.remove(os.path.join(out, f))
    sizes = {}
    for f, text in files.items():
        raw = text.encode('utf-8')
        with open(os.path.join(out, f), 'wb') as fh: fh.write(raw)
        sizes[f] = len(raw)
    return sizes
