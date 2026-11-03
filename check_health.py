"""Reads data.json after a build and prints how each section did (META.health, written by build.py).
Exits 1 when a core section failed (this week's games, injuries, depth charts, weekly stats, or NFL odds), so the
refresh run shows red instead of quietly shipping a page with that section missing. Other failures print as warnings.
'skipped' (a secret simply isn't set) never fails the run.
Also exits 1 when api/v1/index.json (next to data.json) exists but was built from an older data.json: the API export
step only warns when it fails, so this is where a frozen API shows red. With --require-api a missing api/v1/index.json
fails too (the daily refresh uses it, so an export that never worked cannot stay green).
The same goes for the page's split files: when data/index.json (next to data.json) exists its build stamp must equal
schema.shards.build_id(data.json), the function build.py stamps them with; a mismatch would send every visitor to the
page's slower whole-data.json fallback without any sign of it. With --require-shards a missing data/index.json fails too.
An unknown --flag exits 2 (a typo of --require-api must not quietly turn that check off).
Usage: python check_health.py [--require-api] [--require-shards] [path/to/data.json]"""
import json, os, sys

from schema.health import CORE_SECTIONS as CORE
from schema.shards import build_id
FLAGS = ('--require-api', '--require-shards')
unknown = [a for a in sys.argv[1:] if a.startswith('--') and a not in FLAGS]
if unknown:
    print('unknown option%s: %s (known: %s)' % ('s' if len(unknown) > 1 else '', ' '.join(unknown), ' '.join(FLAGS))); sys.exit(2)
args = [a for a in sys.argv[1:] if not a.startswith('--')]
REQUIRE_API, REQUIRE_SHARDS = '--require-api' in sys.argv[1:], '--require-shards' in sys.argv[1:]
path = args[0] if args else 'data.json'
DATA = json.load(open(path, encoding='utf-8'))
H = DATA.get('META', {}).get('health')
if not H:
    print('no META.health in', path, '(built by an older build.py?)'); sys.exit(1)
bad = []
for k, v in sorted(H.items(), key=lambda kv: (kv[0] not in CORE, kv[0])):
    core = k in CORE
    print('%-18s %-5s %s' % (k, 'core' if core else '', v))
    if v.startswith('failed'): bad.append((k, core))
for k in CORE:
    if k not in H: print('%-18s core  missing (section never reported)' % k); bad.append((k, True))
if [k for k, c in bad if not c]: print('WARNING: optional sections failed:', ', '.join(k for k, c in bad if not c))
if [k for k, c in bad if c]:
    print('FAILED: core sections failed:', ', '.join(k for k, c in bad if c)); sys.exit(1)
root = os.path.dirname(os.path.abspath(path))
index_path = os.path.join(root, 'api', 'v1', 'index.json')
if os.path.exists(index_path):
    api_built = json.load(open(index_path, encoding='utf-8')).get('built')
    if api_built != DATA['META'].get('built'):
        print('FAILED: api/v1 is stale: index.json built %r, data.json built %r (api_export.py did not run or failed)' % (api_built, DATA['META'].get('built')))
        sys.exit(1)
    print('api/v1 matches data.json')
elif REQUIRE_API:
    print('FAILED: %s is missing (api_export.py never succeeded)' % index_path); sys.exit(1)
shards_path = os.path.join(root, 'data', 'index.json')
if os.path.exists(shards_path):
    try: shards_build = json.load(open(shards_path, encoding='utf-8')).get('build')
    except Exception as ex: shards_build = 'unreadable (%s)' % ex
    want = build_id(DATA)
    if shards_build != want:
        print('FAILED: data/ is out of step with data.json: index.json build %r, data.json build %r (the page would fall back to loading data.json whole)' % (shards_build, want))
        sys.exit(1)
    print('data/ matches data.json')
elif REQUIRE_SHARDS:
    print('FAILED: %s is missing (build.py never wrote the split files)' % shards_path); sys.exit(1)
print('health ok')
