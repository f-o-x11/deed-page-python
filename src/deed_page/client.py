"""deed.page API client using only the Python standard library."""
import base64
import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

VERSION = "0.1.0"
DEFAULT_BASE = "https://deed.page"
BODY_LIMIT = 4 * 1000 * 1000  # per-request cap documented at https://deed.page/llms.txt
SLUG_RE = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$")
TOKEN_RE = re.compile(r"deed_tok_[A-Za-z0-9_\-]+")
TEXT_EXT = {".html", ".htm", ".css", ".js", ".mjs", ".json", ".txt", ".md", ".svg", ".xml", ".csv",
            ".map", ".webmanifest", ".yml", ".yaml", ".toml"}
SKIP = {".git", "node_modules", ".DS_Store", ".deed-page", "__pycache__"}


class DeedPageError(Exception):
    def __init__(self, message, status=None, body=None):
        super().__init__(message)
        self.status = status
        self.body = body or {}
        self.code = self.body.get("error") or self.body.get("code") if isinstance(self.body, dict) else None


def config_dir():
    base = os.environ.get("XDG_CONFIG_HOME") or os.path.join(os.path.expanduser("~"), ".config")
    return Path(base) / "deed-page"


def token_path():
    return config_dir() / "token"


def load_token():
    """Token order: DEED_PAGE_TOKEN, DEEDPAGE_TOKEN, then ~/.config/deed-page/token."""
    env = (os.environ.get("DEED_PAGE_TOKEN") or os.environ.get("DEEDPAGE_TOKEN") or "").strip()
    if env:
        return env
    try:
        return token_path().read_text().strip() or None
    except OSError:
        return None


def save_token(token):
    """Save a newly minted token (dir 700, file 600). Never overwrites with an empty value."""
    if not token:
        return None
    d = config_dir()
    d.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(d, 0o700)
    p = token_path()
    fd = os.open(str(p), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as f:
        f.write(token)
    os.chmod(p, 0o600)
    return str(p)


def redact(value):
    """Replace any deed_tok_ value so a token is never printed."""
    return json.loads(TOKEN_RE.sub("<redacted>", json.dumps(value)))


def _encode(path):
    data = Path(path).read_bytes()
    if Path(path).suffix.lower() in TEXT_EXT:
        try:
            return data.decode("utf-8")
        except UnicodeDecodeError:
            pass
    return {"base64": base64.b64encode(data).decode("ascii")}


def collect_files(target):
    """Read a file or folder into a deed.page JSON file map."""
    target = Path(target)
    if target.is_file():
        name = "index.html" if target.suffix.lower() in (".html", ".htm") else target.name
        return {name: _encode(target)}
    if not target.is_dir():
        raise FileNotFoundError("Not a file or folder: %s" % target)
    files = {}
    for root, dirs, names in os.walk(target):
        dirs[:] = sorted(d for d in dirs if d not in SKIP and not os.path.islink(os.path.join(root, d)))
        for n in sorted(names):
            p = Path(root) / n
            if n in SKIP or p.is_symlink() or not p.is_file():
                continue
            files[p.relative_to(target).as_posix()] = _encode(p)
    if not files:
        raise ValueError("No files found in %s" % target)
    return files


class DeedPage:
    """Publish, update, list and delete deed.page sites."""

    def __init__(self, token=None, base_url=None, client=None, save_new_token=True, timeout=60):
        self.base = (base_url or os.environ.get("DEED_PAGE_API") or DEFAULT_BASE).rstrip("/")
        self.token = token if token is not None else load_token()
        self.client = client or "deed-page-pypi/%s" % VERSION
        self.save_new_token = save_new_token
        self.timeout = timeout
        self.new_token = None

    def _request(self, method, path, body=None, headers=None, auth=True):
        h = {"X-Client": self.client, "User-Agent": "deed-page-pypi/%s" % VERSION, "Accept": "application/json"}
        h.update(headers or {})
        if auth and self.token:
            h["Authorization"] = "Bearer %s" % self.token
        req = urllib.request.Request(self.base + path, data=body, headers=h, method=method)
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as res:
                status, text = res.status, res.read().decode("utf-8", "replace")
        except urllib.error.HTTPError as e:
            status, text = e.code, e.read().decode("utf-8", "replace")
        try:
            data = json.loads(text) if text else {}
        except ValueError:
            data = {"message": text}
        if status >= 400:
            msg = data.get("message_for_user") or data.get("message") or data.get("error") or "HTTP %s" % status
            raise DeedPageError(TOKEN_RE.sub("<redacted>", str(msg)), status, data)
        return data

    def _need_token(self):
        if not self.token:
            raise DeedPageError("No token found. Set DEED_PAGE_TOKEN or save it to %s" % token_path())

    def publish(self, source, slug, merge=False, spa=False, ttl=None, ref="pypi", heard_from=None):
        """Publish a path or a {path: content} map to https://{slug}.deed.page/. Re-publishing updates it."""
        if not slug or not SLUG_RE.match(slug):
            raise ValueError('Invalid slug "%s": 1-63 lowercase letters, digits, hyphens; no leading/trailing hyphen' % slug)
        files = collect_files(source) if isinstance(source, (str, os.PathLike)) else source
        payload = {"slug": slug, "files": files}
        if heard_from and not self.token:
            payload["heard_from"] = heard_from
        body = json.dumps(payload).encode("utf-8")
        if len(body) > BODY_LIMIT:
            raise DeedPageError("Upload is %.1f MB, over the 4 MB per-request cap. Use the manifest upload: "
                                "https://deed.page/docs" % (len(body) / 1e6))
        headers = {"Content-Type": "application/json"}
        if merge:
            headers["X-Merge"] = "1"
        if spa:
            headers["X-Spa"] = "1"
        if ttl:
            headers["X-Ttl"] = str(ttl)
        data = self._request("POST", "/v1/sites?ref=%s" % urllib.parse.quote(ref), body, headers)
        minted = data.get("token")
        if minted:
            self.token = minted
            self.new_token = None if self.save_new_token else minted
            data["token_saved_to"] = save_token(minted) if self.save_new_token else None
            data["token"] = "<saved>"
        return data

    def update(self, source, slug, **kw):
        """Update a site you own. Same as publish, but refuses to run without a token."""
        self._need_token()
        return self.publish(source, slug, **kw)

    def list(self):
        self._need_token()
        return self._request("GET", "/v1/sites")

    def get(self, slug):
        return self._request("GET", "/v1/sites/%s" % urllib.parse.quote(slug))

    def delete(self, slug):
        self._need_token()
        return self._request("DELETE", "/v1/sites/%s" % urllib.parse.quote(slug))

    def whoami(self):
        self._need_token()
        return self._request("GET", "/v1/whoami")
