"""check_health.py is the last step of the daily refresh, so it is where a frozen API export has to show red."""
import json, os, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SCRIPT = os.path.join(ROOT, 'check_health.py')
HEALTHY = {'schedule': 'ok', 'injuries': 'ok', 'depth': 'ok', 'weekly': 'ok', 'odds': 'ok', 'college_prospects': 'skipped: no CFBD_KEY secret'}


def run(folder, *flags):
    r = subprocess.run([sys.executable, SCRIPT, *flags, str(folder / 'data.json')], capture_output=True, text=True, env=dict(os.environ, PYTHONUTF8='1'))
    return r.returncode, r.stdout + r.stderr


def make(folder, built='Nov 02, 2026 at 12:00 UTC', health=HEALTHY):
    folder.mkdir(parents=True, exist_ok=True)
    (folder / 'data.json').write_text(json.dumps({'META': {'health': health, 'built': built}}), encoding='utf-8')


def test_passes_without_an_api_folder(tmp_path):
    make(tmp_path)
    code, out = run(tmp_path)
    assert code == 0 and 'health ok' in out


def test_require_api_fails_when_the_api_was_never_written(tmp_path):
    make(tmp_path)
    assert run(tmp_path, '--require-api')[0] == 1 and 'missing' in run(tmp_path, '--require-api')[1]
    assert run(tmp_path)[0] == 0   # without the flag a missing api folder is fine (local runs)
    (tmp_path / 'api' / 'v1').mkdir(parents=True)
    (tmp_path / 'api' / 'v1' / 'index.json').write_text(json.dumps({'built': 'Nov 02, 2026 at 12:00 UTC'}), encoding='utf-8')
    code, out = run(tmp_path, '--require-api')
    assert code == 0 and 'health ok' in out


def test_the_refresh_requires_the_api_and_the_test_workflow_watches_the_new_files():
    wf = os.path.join(ROOT, '.github', 'workflows')
    assert 'python check_health.py --require-api' in open(os.path.join(wf, 'refresh.yml'), encoding='utf-8').read()
    paths = open(os.path.join(wf, 'test.yml'), encoding='utf-8').read()
    for p in ('api_export.py', 'check_health.py', "'mcp_server/**'", "'schema/**'", "'engine/**'"): assert p in paths


def test_passes_when_the_api_was_built_from_this_data(tmp_path):
    make(tmp_path)
    (tmp_path / 'api' / 'v1').mkdir(parents=True)
    (tmp_path / 'api' / 'v1' / 'index.json').write_text(json.dumps({'built': 'Nov 02, 2026 at 12:00 UTC'}), encoding='utf-8')
    code, out = run(tmp_path)
    assert code == 0 and 'api/v1 matches data.json' in out


def test_fails_when_the_api_is_left_over_from_an_older_build(tmp_path):
    make(tmp_path, built='Nov 03, 2026 at 10:00 UTC')
    (tmp_path / 'api' / 'v1').mkdir(parents=True)
    (tmp_path / 'api' / 'v1' / 'index.json').write_text(json.dumps({'built': 'Nov 02, 2026 at 12:00 UTC'}), encoding='utf-8')
    code, out = run(tmp_path)
    assert code == 1 and 'api/v1 is stale' in out and 'Nov 02, 2026 at 12:00 UTC' in out


def test_core_failures_still_fail(tmp_path):
    make(tmp_path, health=dict(HEALTHY, odds='failed: no key'))
    code, out = run(tmp_path)
    assert code == 1 and 'core sections failed: odds' in out


def test_core_sections_are_defined_once():
    sys.path.insert(0, ROOT)
    import api_export
    from schema.health import CORE_SECTIONS
    assert api_export.CORE_SECTIONS is CORE_SECTIONS
    assert 'CORE = [' not in open(SCRIPT, encoding='utf-8').read()
