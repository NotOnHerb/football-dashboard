"""Builds the golden replay's data.json once per pytest run, for the tests that read it (API export, MCP server).

The replay (tests/golden/runner.py replay) builds from recorded fixtures with the clock frozen, so it needs no network.
Its work folder has data.json and model.json, the way the repo root does.
"""
import json, os, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
RUNNER = os.path.join(HERE, 'golden', 'runner.py')
_cache = {}


def replay_dir(tmp_path_factory):
    """The folder holding the replay's data.json and model.json (built on first call)."""
    if 'dir' not in _cache:
        work = tmp_path_factory.mktemp('replay')
        env = dict(os.environ, PYTHONHASHSEED='0', PYTHONUTF8='1')
        r = subprocess.run([sys.executable, RUNNER, 'replay', str(work)], env=env, capture_output=True, text=True)
        assert r.returncode == 0, r.stdout[-3000:] + r.stderr[-3000:]
        _cache['dir'] = work
    return _cache['dir']


def replay_data(tmp_path_factory):
    with open(replay_dir(tmp_path_factory) / 'data.json', encoding='utf-8') as f: return json.load(f)
