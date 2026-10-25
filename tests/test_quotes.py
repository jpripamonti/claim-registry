from pathlib import Path

from claimreg import registry
from claimreg.quotes import check_quotes, quote_in_page

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
