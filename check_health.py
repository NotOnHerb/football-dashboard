"""Reads data.json after a build and prints how each section did (META.health, written by build.py).
Exits 1 when a core section failed (this week's games, injuries, depth charts, weekly stats, or NFL odds), so the
refresh run shows red instead of quietly shipping a page with that section missing. Other failures print as warnings.
'skipped' (a secret simply isn't set) never fails the run.  Usage: python check_health.py [path/to/data.json]"""
import json, sys

CORE = ['schedule', 'injuries', 'depth', 'weekly', 'odds']
path = sys.argv[1] if len(sys.argv) > 1 else 'data.json'
H = json.load(open(path, encoding='utf-8')).get('META', {}).get('health')
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
print('health ok')
