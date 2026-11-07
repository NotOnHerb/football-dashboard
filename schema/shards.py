"""How data.json is split into the files the page loads.

build.py writes data.json whole (for analyst/snapshot.py, the Desk sync, api_export.py and the MCP server) and also
split by top-level key into data/<shard>.json, plus data/index.json. The page loads data/index.json and
data/core.json at boot, and a section's other shards the first time it is opened, using the dataKeys each section
declares (js/registry.js). Every top-level key is in exactly one shard, so the shards together are data.json.

Each file carries the build it came from, so the page never mixes two days' data (a tab left open across the daily
refresh, or the CDN serving some files new and some old):
    data/index.json     {"build": B, "shards": SHARDS}
    data/<shard>.json   {"build": B, "data": {key: value, ...}}   the keys SHARDS lists for it, in that order
B (build_id) is a hash of data.json's content. The page refuses a shard whose build differs from core.json's or
whose keys differ from index.json's list, and falls back to loading data.json whole when index.json or core.json
can't be loaded or disagree.

tests/test_page.py imports write() too, so the pages it serves from an edited data.json are split the same way.
"""
import hashlib, json, os

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


def build_id(data):
    """The build stamp every data/ file carries: the first 16 hex digits of the SHA-256 of data.json's content."""
    return hashlib.sha256(dumps(data).encode('utf-8')).hexdigest()[:16]


def files(data):
    """{file name in data/: JSON text} for data: one file per shard, and index.json."""
    parts, b = split(data), build_id(data)
    out = {'%s.json' % name: dumps({'build': b, 'data': part}) for name, part in parts.items()}
    out['index.json'] = dumps({'build': b, 'shards': SHARDS})
    return out


def write(data, root='.'):
    """Writes files(data) to root/data/ and removes any other .json file there (a shard that was renamed or dropped).
    Returns {file name: bytes}."""
    texts = files(data)
    out = os.path.join(root, DIR)
    os.makedirs(out, exist_ok=True)
    for f in os.listdir(out):
        if f.endswith('.json') and f not in texts: os.remove(os.path.join(out, f))
    sizes = {}
    for f, text in texts.items():
        raw = text.encode('utf-8')
        with open(os.path.join(out, f), 'wb') as fh: fh.write(raw)
        sizes[f] = len(raw)
    return sizes
