"""Plain-text snapshots of source pages under sources/, and diffs against them."""
import difflib
import re
import textwrap
from datetime import date
from pathlib import Path
from urllib.parse import urlsplit

from .quotes import clean, strip_tags

SOURCES_DIR = "sources"
WIDTH = 100
MAX_DIFF_LINES = 60


def snapshot_name(url):
    """Stable file name for a URL: host and path, every other character replaced by '_'."""
    parts = urlsplit(url)
    name = parts.netloc + parts.path.rstrip("/")
    if parts.query:
        name += "_" + parts.query
    return re.sub(r"[^A-Za-z0-9.-]+", "_", name).strip("_") + ".txt"


def snapshot_path(root, url):
    return Path(root) / SOURCES_DIR / snapshot_name(url)


def page_lines(raw_html):
    """The page's plain text, one sentence per line, sentences longer than WIDTH wrapped."""
    text = clean(strip_tags(raw_html, " "))
    lines = []
    for sentence in re.split(r"(?<=[.!?])\s+", text):
        lines.extend(textwrap.wrap(sentence, WIDTH, break_long_words=False,
                                   break_on_hyphens=False) or [""])
    return [ln for ln in lines if ln]


def _header(url, retrieved):
    return [f"source: {url}", f"retrieved: {retrieved}", ""]


def read_snapshot(path):
    """Body lines of a snapshot file (header dropped), or None if there is no file."""
    path = Path(path)
    if not path.exists():
        return None
    lines = path.read_text(encoding="utf-8").splitlines()
    return lines[len(_header("", "")):]


def save_snapshot(root, url, raw_html, today=None):
    """Write the snapshot of a page. An unchanged page keeps its file and date.

    Returns True when the file was written.
    """
    path = snapshot_path(root, url)
    body = page_lines(raw_html)
    if read_snapshot(path) == body:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = _header(url, today or date.today().isoformat()) + body
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return True


def snapshot_diff(root, url, raw_html, limit=MAX_DIFF_LINES):
    """Unified diff from the snapshot to the current page, as lines; None if no snapshot."""
    path = snapshot_path(root, url)
    old = read_snapshot(path)
    if old is None:
        return None
    diff = list(difflib.unified_diff(old, page_lines(raw_html), f"{SOURCES_DIR}/{path.name}",
                                     "current page", n=3, lineterm=""))
    if len(diff) > limit:
        diff = diff[:limit] + [f"... {len(diff) - limit} more diff lines"]
    return diff
