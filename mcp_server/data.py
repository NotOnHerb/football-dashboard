"""Where the MCP server gets its data: the repo's own files, or the published API.

Default is the repo checkout: api/v1/<name>.json when it exists (the daily refresh writes it), otherwise built on the
spot from data.json with api_export.build, so a fresh clone works without running anything first.
Setting FD_API_URL (for example https://notonherb.github.io/football-dashboard/api/v1) reads the published files
instead. Nothing here writes to the data.
"""
import json, os, sys, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path: sys.path.insert(0, ROOT)
import api_export  # noqa: E402


class Source:
    """Named API documents (players, picks, ...) from a repo folder or a base URL. Documents are cached per Source."""

    def __init__(self, root=None, base_url=None):
        self.root = root or ROOT
        self.base_url = base_url.rstrip('/') if base_url else None
        self._cache = {}
        self._built = None

    @classmethod
    def from_env(cls):
        """FD_API_URL set: read the published API. Otherwise the repo checkout."""
        return cls(base_url=os.environ.get('FD_API_URL') or None)

    @property
    def where(self):
        return self.base_url or self.root

    def get(self, name):
        """The document called NAME ('picks', 'players', ...), or None when this source has no such file."""
        if name not in self._cache: self._cache[name] = self._load(name)
        return self._cache[name]

    def _load(self, name):
        if self.base_url:
            try:
                with urllib.request.urlopen('%s/%s.json' % (self.base_url, name), timeout=30) as r: return json.load(r)
            except OSError: return None   # includes HTTP 404: optional files such as picks_by_book are simply absent
        path = os.path.join(self.root, 'api', 'v1', name + '.json')
        if os.path.exists(path):
            with open(path, encoding='utf-8') as f: return json.load(f)
        if self._built is None:
            data_path = os.path.join(self.root, 'data.json')
            if not os.path.exists(data_path): self._built = {}
            else:
                with open(data_path, encoding='utf-8') as f: self._built = api_export.build(json.load(f))
        return self._built.get(name)

    def model(self):
        """model.json from the repo checkout (quantiles, calibration, sample sizes), or None (e.g. reading the published API)."""
        if self.base_url: return None
        path = os.path.join(self.root, 'model.json')
        if not os.path.exists(path): return None
        with open(path, encoding='utf-8') as f: return json.load(f)
