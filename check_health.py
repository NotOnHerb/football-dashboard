"""Reads data.json after a build and prints how each section did (META.health, written by build.py).
Exits 1 when a core section failed (this week's games, injuries, depth charts, weekly stats, or NFL odds), so the
refresh run shows red instead of quietly shipping a page with that section missing. Other failures print as warnings.
'skipped' (a secret simply isn't set) never fails the run.
Also exits 1 when api/v1/index.json (next to data.json) exists but was built from an older data.json: the API export
step only warns when it fails, so this is where a frozen API shows red. With --require-api a missing api/v1/index.json
fails too (the daily refresh uses it, so an export that never worked cannot stay green).
Usage: python check_health.py [--require-api] [path/to/data.json]"""
import json, os, sys

from schema.health import CORE_SECTIONS as CORE
args = [a for a in sys.argv[1:] if not a.startswith('--')]
REQUIRE_API = '--require-api' in sys.argv[1:]
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
index_path = os.path.join(os.path.dirname(os.path.abspath(path)), 'api', 'v1', 'index.json')
if os.path.exists(index_path):
    api_built = json.load(open(index_path, encoding='utf-8')).get('built')
    if api_built != DATA['META'].get('built'):
        print('FAILED: api/v1 is stale: index.json built %r, data.json built %r (api_export.py did not run or failed)' % (api_built, DATA['META'].get('built')))
        sys.exit(1)
    print('api/v1 matches data.json')
elif REQUIRE_API:
    print('FAILED: %s is missing (api_export.py never succeeded)' % index_path); sys.exit(1)
print('health ok')
