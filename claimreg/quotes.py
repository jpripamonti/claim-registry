"""Check that each evidence quote appears verbatim in its source page."""
import html
import re
import urllib.request

USER_AGENT = "Mozilla/5.0 (claim-registry quote checker)"
_PUNCT = str.maketrans({"‘": "'", "’": "'", "“": '"', "”": '"',
                        "–": "-", "—": "-", " ": " "})


def normalize(text):
    """Make page text and quotes comparable: entities, curly quotes, markdown marks, whitespace."""
    text = html.unescape(text).translate(_PUNCT)
    text = re.sub(r'\\n|\\"', " ", text)       # escaped text inside embedded JSON
    text = re.sub(r"[*_`#>]", "", text)         # markdown emphasis and headings
    return re.sub(r"\s+", " ", text).strip().lower()


def page_variants(raw_html):
    """Normalized versions of a page to search in.

    Tags are replaced by a space in one version and removed in another: a space is right
    between block elements, but wrong for an inline link or code span in mid-sentence.
    """
    text = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", raw_html, flags=re.S | re.I)
    return [normalize(re.sub(r"<[^>]+>", " ", text)),
            normalize(re.sub(r"<[^>]+>", "", text)),
            normalize(raw_html)]


def quote_in_page(quote, raw_html):
    q = normalize(quote)
    return bool(q) and any(q in v for v in page_variants(raw_html))


def fetch(url, timeout=40):
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode(resp.headers.get_content_charset() or "utf-8", "replace")


def check_quotes(reg, ids=None, fetcher=fetch):
    """Yield (claim, evidence_index, url, status) with status 'ok', 'missing' or 'error: ...'."""
    cache = {}
    for cid, claim in reg.claims.items():
        if ids and cid not in ids:
            continue
        for n, ev in enumerate(claim.data.get("evidence") or []):
            url, quote = ev.get("source"), ev.get("quote")
            if not url or not quote:
                continue
            if url not in cache:
                try:
                    cache[url] = fetcher(url)
                except Exception as e:  # network errors are reported, not fatal
                    cache[url] = e
            page = cache[url]
            if isinstance(page, Exception):
                status = f"error: {page}"
            else:
                status = "ok" if quote_in_page(quote, page) else "missing"
            yield claim, n, url, status
