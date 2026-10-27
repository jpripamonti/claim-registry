import shutil
from pathlib import Path

import pytest

from claimreg import __main__ as cli, quotes, registry
from claimreg.quotes import check_quotes, quote_in_page
from claimreg.snapshots import page_lines, save_snapshot, snapshot_diff, snapshot_name, snapshot_path

ROOT = Path(__file__).resolve().parent.parent


def test_plain_match_ignores_case_and_whitespace():
    page = "<p>Include 3–5   examples\nfor best results.</p>"
    assert quote_in_page("include 3–5 examples for best results.", page)


def test_curly_quotes_and_entities_match_straight_ones():
    page = "<p>don&rsquo;t say “think step by step,” please</p>"
    assert quote_in_page('don\'t say "think step by step," please', page)


def test_inline_link_mid_sentence():
    page = 'Starting with <a href="/x">Claude Mythos Preview</a>, prefills fail.'
    assert quote_in_page("Starting with Claude Mythos Preview, prefills fail.", page)


def test_inline_code_before_punctuation():
    page = "keep the <code>temperature</code> at <code>1.0</code>."
    assert quote_in_page("keep the temperature at 1.0.", page)


def test_block_elements_keep_words_apart():
    page = "<p>First paragraph.</p><p>Second paragraph.</p>"
    assert quote_in_page("First paragraph. Second paragraph.", page)


def test_script_contents_ignored_but_text_found():
    page = "<script>var x = 'decoy';</script><p>Real text.</p>"
    assert quote_in_page("Real text.", page)


def test_absent_quote_and_empty_quote_fail():
    assert not quote_in_page("Not on the page.", "<p>Something else.</p>")
    assert not quote_in_page("", "<p>Anything.</p>")


def test_check_quotes_reports_ok_missing_and_errors():
    reg = registry.load(ROOT)
    target = "long-context-query-at-end"
    quotes = [ev["quote"] for ev in reg.claims[target].data["evidence"]]
    page = "<p>" + quotes[0] + "</p>"        # only the first quote is on the fake page

    results = list(check_quotes(reg, ids={target}, fetcher=lambda url: page))
    assert [r[3] for r in results] == ["ok", "missing"]

    def broken(url):
        raise OSError("offline")
    results = list(check_quotes(reg, ids={target}, fetcher=broken))
    assert all(r[3] == "error: offline" for r in results)


def test_each_url_fetched_once():
    reg = registry.load(ROOT)
    calls = []
    list(check_quotes(reg, fetcher=lambda url: calls.append(url) or ""))
    assert len(calls) == len(set(calls))


# Source snapshots

URL = "https://example.com/docs/guide/"
PAGE = ("<html><script>var x = 1;</script><h1>Guide</h1><p>Put the query last. "
        "It helps on long inputs! " + "word " * 40 + "end.</p><p>Use examples?</p></html>")


def test_snapshot_name_is_stable_and_readable():
    assert snapshot_name(URL) == "example.com_docs_guide.txt"
    assert snapshot_name("https://example.com/docs/guide") == snapshot_name(URL)
    assert snapshot_name("https://arxiv.org/html/2401.0001v2?x=1") == "arxiv.org_html_2401.0001v2_x_1.txt"


def test_page_lines_split_at_sentences_and_wrap():
    lines = page_lines(PAGE)
    assert lines[:2] == ["Guide Put the query last.", "It helps on long inputs!"]
    assert lines[-1] == "Use examples?"
    assert all(len(ln) <= 100 for ln in lines)
    assert "var x" not in " ".join(lines)


def test_resave_of_unchanged_page_is_identical(tmp_path):
    assert save_snapshot(tmp_path, URL, PAGE, today="2026-01-01")
    first = snapshot_path(tmp_path, URL).read_bytes()
    assert first.startswith(b"source: https://example.com/docs/guide/\nretrieved: 2026-01-01\n")
    assert not save_snapshot(tmp_path, URL, PAGE, today="2026-02-02")
    assert snapshot_path(tmp_path, URL).read_bytes() == first
    assert snapshot_diff(tmp_path, URL, PAGE) == []


def test_diff_against_snapshot(tmp_path):
    save_snapshot(tmp_path, URL, PAGE)
    diff = snapshot_diff(tmp_path, URL, PAGE.replace("query last", "query first"))
    assert "-Guide Put the query last." in diff
    assert "+Guide Put the query first." in diff
    assert snapshot_diff(tmp_path, "https://example.com/other", PAGE) is None


@pytest.fixture
def reg_copy(tmp_path, monkeypatch):
    """A copy of the registry and a fake fetcher serving one page without any quote on it."""
    for d in ("claims", "vocab"):
        shutil.copytree(ROOT / d, tmp_path / d)
    monkeypatch.setattr(quotes, "fetch", lambda url: PAGE)
    return tmp_path


def _run(root, *args):
    return cli.main(["--root", str(root), "check-quotes", "long-context-query-at-end", *args])


def test_missing_quote_without_snapshot_prints_note(reg_copy, capsys):
    assert _run(reg_copy) == 1
    out = capsys.readouterr().out
    assert "MISSING  long-context-query-at-end evidence[0]" in out
    assert "no snapshot of this page" in out
    assert not (reg_copy / "sources").exists()       # nothing written without the flag


def test_missing_quote_with_snapshot_prints_diff(reg_copy, capsys):
    reg = registry.load(reg_copy)
    url = reg.claims["long-context-query-at-end"].data["evidence"][0]["source"]
    quote = reg.claims["long-context-query-at-end"].data["evidence"][0]["quote"]
    save_snapshot(reg_copy, url, "<p>Intro.</p><p>" + quote + "</p>")
    _run(reg_copy)
    out = capsys.readouterr().out
    assert "--- sources/" in out and "+++ current page" in out
    assert "    -" + page_lines(quote)[0] in out


def test_save_sources_flag_writes_snapshots(reg_copy, capsys):
    _run(reg_copy, "--save-sources")
    files = list((reg_copy / "sources").iterdir())
    assert files and all(f.read_text().splitlines()[3:] == page_lines(PAGE) for f in files)
