"""Gathers the published site into one folder for the GitHub Pages artifact.

Git keeps only the code and the ledgers (odds/, cfb/, model.json). The generated files (index.html, data.json, data/,
api/v1/) are built in the workflow and published through a Pages artifact, never committed.

    python pages.py OUT          copy the site as the build left it here into OUT (the daily refresh)
    python pages.py --live OUT   first rebuild the generated files here from the published data.json, then copy (the
                                 deploy workflow, after a push that changes only the page's code)

--live downloads data.json from the live site (SITE_URL, or FD_SITE_URL when set) and writes data/, api/v1/ and
index.html from it with the same code the refresh uses (schema/shards.py, api_export.py, restamp.py). No build, no
Odds API credits, and the data is exactly what the last refresh published.
"""
import json, os, shutil, sys, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import api_export  # noqa: E402
import restamp  # noqa: E402
from schema import shards  # noqa: E402

SITE_URL = 'https://notonherb.github.io/football-dashboard/'
# What the site serves: the page and its code, its data (whole and split), the API files, and the ledgers.
REQUIRED = ['index.html', 'data.json', shards.DIR, 'js', 'assets']
OPTIONAL = ['api', 'model.json', 'odds', 'cfb']   # api/ is missing only when api_export failed (check_health then fails the run)


def site_url():
    return os.environ.get('FD_SITE_URL') or SITE_URL


def fetch_published(name, base=None, timeout=60):
    """The published copy of a site file (e.g. data.json), parsed. Raises RuntimeError when it can't be fetched."""
    url = (base or site_url()).rstrip('/') + '/' + name
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': 'football-dashboard'}), timeout=timeout) as r:
            return json.load(r)
    except Exception as ex:
        raise RuntimeError('could not fetch %s: %s' % (url, ex)) from ex


def rebuild_from_live(root='.'):
    """Writes ROOT/data.json from the live site, then data/, api/v1/ and index.html from it. Returns META.built."""
    data = fetch_published('data.json')
    shards.split(data)   # raises before anything is written if the published data.json predates the data/ split
    with open(os.path.join(root, 'data.json'), 'w', encoding='utf-8') as f: f.write(shards.dumps(data))
    shards.write(data, root)
    api_export.export(data, os.path.join(root, 'api', 'v1'))
    built = data['META']['built']
    restamp.stamp(built, os.path.join(root, 'template.html'), os.path.join(root, 'index.html'))
    return built


def gather(out, root='.'):
    """Copies the site's files from ROOT into OUT (emptied first). Returns the paths copied. Raises if a required
    file is missing, so a broken build never replaces the live site."""
    missing = [p for p in REQUIRED if not os.path.exists(os.path.join(root, p))]
    if missing: raise FileNotFoundError('the site needs %s; the build did not write them' % missing)
    shutil.rmtree(out, ignore_errors=True); os.makedirs(out)
    copied = []
    for p in REQUIRED + OPTIONAL:
        src = os.path.join(root, p)
        if not os.path.exists(src): continue
        (shutil.copytree(src, os.path.join(out, p), ignore=shutil.ignore_patterns('__pycache__')) if os.path.isdir(src)
         else shutil.copy(src, os.path.join(out, p)))
        copied.append(p)
    return copied


def main(argv):
    live = '--live' in argv
    args = [a for a in argv if a != '--live']
    if len(args) != 1 or args[0].startswith('-'): sys.exit('usage: python pages.py [--live] OUT')
    if live: print('rebuilt from the published data.json, built', rebuild_from_live())
    print('site:', ', '.join(gather(args[0])))


if __name__ == '__main__':
    main(sys.argv[1:])
