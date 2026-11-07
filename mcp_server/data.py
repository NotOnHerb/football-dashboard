"""Where the MCP server gets its data: the repo's own files, or the published API.

Default is the repo checkout, after a local build (git keeps no data files): api/v1/<name>.json, or documents built
on the spot from data.json with api_export.build when there is no api/v1/ or data.json was built more recently than
it (so a local build.py run is picked up without running api_export first).
Setting FD_API_URL (for example https://notonherb.github.io/football-dashboard/api/v1) reads the published files
instead. Files are re-read when they change on disk (local) or after REMOTE_TTL seconds (remote), so a long-running
server does not go stale. Nothing here writes to the data.
"""
import datetime, json, os, sys, time, urllib.error, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path: sys.path.insert(0, ROOT)
import api_export  # noqa: E402

REMOTE_TTL = 300   # seconds a published file is reused before it is fetched again


def parse_built(s):
    """META.built text ('Nov 02, 2026 at 12:00 UTC') as a datetime, or None if it is not in that form."""
    try: return datetime.datetime.strptime(s.replace(' UTC', ''), '%b %d, %Y at %H:%M')
    except (AttributeError, ValueError): return None


def _stamp(path):
    """(mtime, size) of a file, or None when it does not exist: changes whenever the file is rewritten."""
    try: st = os.stat(path)
    except OSError: return None
    return (st.st_mtime_ns, st.st_size)


def _read(path):
    with open(path, encoding='utf-8') as f: return json.load(f)


class Source:
    """Named API documents (players, picks, ...) from a repo folder or a base URL."""

    def __init__(self, root=None, base_url=None, ttl=REMOTE_TTL, clock=time.monotonic):
        self.root = root or ROOT
        self.base_url = base_url.rstrip('/') if base_url else None
        self.ttl, self.clock = ttl, clock
        self._files = {}    # name -> (stamp or fetch time, document)
        self._built = None  # (data.json stamp, documents built from it)
        self._data_built = None   # (data.json stamp, its META.built as a datetime)

    @classmethod
    def from_env(cls):
        """FD_API_URL set: read the published API. Otherwise the repo checkout."""
        return cls(base_url=os.environ.get('FD_API_URL') or None)

    @property
    def where(self):
        return self.base_url or self.root

    def get(self, name):
        """The document called NAME ('picks', 'players', ...), or None when this source has no such file."""
        return self._remote(name) if self.base_url else self._local(name)

    def _remote(self, name):
        hit = self._files.get(name)
        if hit and self.clock() - hit[0] < self.ttl: return hit[1]
        try:
            with urllib.request.urlopen('%s/%s.json' % (self.base_url, name), timeout=30) as r: doc = json.load(r)
        except urllib.error.HTTPError as e:
            if e.code != 404: raise RuntimeError('could not read %s/%s.json: HTTP %s' % (self.base_url, name, e.code)) from e
            doc = None   # a real 404: optional files such as picks_by_book are simply absent
        except OSError as e:   # timeouts, DNS, refused: not cached, the next call tries again
            raise RuntimeError('could not reach %s/%s.json: %s' % (self.base_url, name, e)) from e
        self._files[name] = (self.clock(), doc)
        return doc

    def _data_is_newer(self):
        """True when data.json exists and (there is no api/v1/index.json, or data.json's META.built is later)."""
        data_path, index_path = os.path.join(self.root, 'data.json'), os.path.join(self.root, 'api', 'v1', 'index.json')
        if _stamp(data_path) is None: return False
        if _stamp(index_path) is None: return True
        st = _stamp(data_path)
        if self._data_built is None or self._data_built[0] != st:
            self._data_built = (st, parse_built((_read(data_path).get('META') or {}).get('built')))
        built, api_built = self._data_built[1], parse_built(self._local_file(index_path).get('built'))
        return bool(built and api_built and built > api_built)

    def _from_data(self):
        """All documents built from data.json (rebuilt when the file changes)."""
        path = os.path.join(self.root, 'data.json'); st = _stamp(path)
        if self._built is None or self._built[0] != st:
            self._built = (st, api_export.build(_read(path)) if st else {})
        return self._built[1]

    def _local_file(self, path):
        st = _stamp(path)
        if st is None: return None
        hit = self._files.get(path)
        if not hit or hit[0] != st: hit = self._files[path] = (st, _read(path))
        return hit[1]

    def _local(self, name):
        if self._data_is_newer(): return self._from_data().get(name)
        path = os.path.join(self.root, 'api', 'v1', name + '.json')
        if _stamp(path) is not None: return self._local_file(path)
        if _stamp(os.path.join(self.root, 'api', 'v1', 'index.json')) is not None: return None   # a file this API version has not written
        return self._from_data().get(name)

    def model(self):
        """model.json from the repo checkout (quantiles, calibration, sample sizes), or None (e.g. reading the published API)."""
        if self.base_url: return None
        return self._local_file(os.path.join(self.root, 'model.json'))
