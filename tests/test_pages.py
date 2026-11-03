"""pages.py: gathering the site for the Pages artifact, and rebuilding it from the published data.json.

Offline: the "published" data.json is the golden replay's, served by a stand-in for urlopen.
"""
import io, json, os, re, shutil, sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, ROOT)
import api_export  # noqa: E402
import pages  # noqa: E402
import replay_util  # noqa: E402
from schema import shards  # noqa: E402


@pytest.fixture(scope='module')
def built(tmp_path_factory):
    """The golden replay's folder as the refresh leaves it: data.json, data/, index.html, model.json, plus api/v1."""
    work = replay_util.replay_dir(tmp_path_factory)
    if not os.path.exists(work / 'api' / 'v1' / 'index.json'):
        api_export.export(json.load(open(work / 'data.json', encoding='utf-8')), str(work / 'api' / 'v1'))
    return work


def serve_published(monkeypatch, files):
    """Answers urlopen for SITE_URL + name from FILES {name: bytes}; anything else is a 404. Returns the URLs asked."""
    asked = []
    def fake(req, timeout=None):
        url = req.full_url
        asked.append(url)
        name = url[len(pages.site_url()):]
        if name not in files: raise OSError('404 %s' % url)
        return io.BytesIO(files[name])
    monkeypatch.setattr(pages.urllib.request, 'urlopen', fake)
    return asked


def tree(root):
    """{relative path: bytes} for every file under root."""
    out = {}
    for d, _, fs in os.walk(root):
        for f in fs:
            p = os.path.join(d, f)
            out[os.path.relpath(p, root).replace(os.sep, '/')] = open(p, 'rb').read()
    return out


def test_gather_copies_the_site(built, tmp_path):
    out = tmp_path / 'site'
    copied = pages.gather(str(out), str(built))
    assert set(pages.REQUIRED) <= set(copied) and 'api' in copied
    assert tree(out / 'data') == tree(built / 'data') and (out / 'data.json').read_bytes() == (built / 'data.json').read_bytes()
    assert not (out / 'tests').exists() and not (out / 'build.py').exists()   # only the site's own paths


def test_gather_refuses_an_incomplete_build(tmp_path):
    (tmp_path / 'index.html').write_text('x', encoding='utf-8')
    with pytest.raises(FileNotFoundError, match='data.json'):
        pages.gather(str(tmp_path / 'site'), str(tmp_path))
    assert not (tmp_path / 'site').exists()


def test_live_rebuild_matches_the_refresh(built, tmp_path, monkeypatch):
    """From the published data.json alone, --live writes the same data.json, data/ and api/v1/ the refresh wrote, and
    stamps index.html with the date that data was built."""
    root = tmp_path / 'checkout'; root.mkdir()
    shutil.copy(os.path.join(ROOT, 'template.html'), root / 'template.html')
    asked = serve_published(monkeypatch, {'data.json': (built / 'data.json').read_bytes()})
    built_at = pages.rebuild_from_live(str(root))
    assert asked == [pages.SITE_URL + 'data.json']
    assert (root / 'data.json').read_bytes() == (built / 'data.json').read_bytes()
    assert tree(root / 'data') == tree(built / 'data')
    assert tree(root / 'api') == tree(built / 'api')
    page = (root / 'index.html').read_text(encoding='utf-8')
    assert built_at == json.load(open(built / 'data.json', encoding='utf-8'))['META']['built']
    assert built_at in page and '__VER__' not in page and re.search(r'js/main\.js\?v=\d{12}', page)


def test_live_rebuild_needs_the_published_data(tmp_path, monkeypatch):
    """No published data.json, or one from before the data/ split: nothing is written, so nothing deploys."""
    serve_published(monkeypatch, {})
    with pytest.raises(RuntimeError, match='could not fetch'):
        pages.rebuild_from_live(str(tmp_path))
    assert os.listdir(tmp_path) == []
    serve_published(monkeypatch, {'data.json': json.dumps({'META': {'built': 'x'}}).encode()})
    with pytest.raises(ValueError, match='SHARDS'):
        pages.rebuild_from_live(str(tmp_path))
    assert os.listdir(tmp_path) == []


def test_site_url_can_be_overridden(monkeypatch):
    monkeypatch.setenv('FD_SITE_URL', 'https://example.test/site/')
    asked = serve_published(monkeypatch, {'data.json': b'{"a": 1}'})
    assert pages.fetch_published('data.json') == {'a': 1} and asked == ['https://example.test/site/data.json']


def test_cli_rejects_bad_arguments():
    for argv in ([], ['a', 'b'], ['--lve', 'out']):
        with pytest.raises(SystemExit):
            pages.main(argv)
