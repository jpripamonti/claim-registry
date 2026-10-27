import datetime as dt

import pytest

from claimreg import registry
from claimreg.__main__ import main
from claimreg.applies import applicable

from test_validate import ROOT, claim, make_registry


def ids(reg, family, version, context_size=None):
    return [c.id for c, _ in applicable(reg, family, version, context_size)]


def test_parent_family_claim_covers_its_lines(tmp_path):
    reg = make_registry(tmp_path, claim())          # claude >=4.5
    assert ids(reg, "claude-sonnet", "5.5") == ["alpha"]
    assert ids(reg, "claude-opus", "4.8") == ["alpha"]
    assert ids(reg, "claude", "5.1") == ["alpha"]
    assert ids(reg, "gpt", "5") == []


def test_line_claim_covers_only_that_line(tmp_path):
    reg = make_registry(tmp_path, claim(**{"conditions__model_family": ["claude-opus"],
                                           "conditions__model_versions": ["5"]}))
    assert ids(reg, "claude-opus", "5") == ["alpha"]
    assert ids(reg, "claude-sonnet", "5") == []
    assert ids(reg, "claude", "5") == []


@pytest.mark.parametrize("value, version, expected", [
    (">=4.5", "4.5", True), (">=4.5", "4", False), ("<4", "3.7", True), ("<4", "4", False),
    (">4.6", "4.7", True), ("<=4.6", "4.7", False), ("4.6", "4.6", True),
    (["4.5", "4.6"], "4.6", True), (["4.5", "4.6"], "4.7", False),
    ("any", "1.3", True), ("unspecified", "5.5", True),
])
def test_version_ranges(tmp_path, value, version, expected):
    reg = make_registry(tmp_path, claim(**{"conditions__model_versions": value}))
    assert (ids(reg, "claude", version) == ["alpha"]) is expected


def test_map_form_uses_each_familys_value(tmp_path):
    reg = make_registry(tmp_path, claim(**{
        "conditions__model_family": ["claude", "claude-mythos"],
        "conditions__model_versions": {"claude": ">=4.6", "claude-mythos": ["preview"]}}))
    assert ids(reg, "claude-mythos", "preview") == ["alpha"]   # via the line's own value
    assert ids(reg, "claude-mythos", "5") == ["alpha"]         # via the parent's range
    assert ids(reg, "claude-sonnet", "4.5") == []


def test_context_size_filter(tmp_path):
    reg = make_registry(tmp_path, *[claim(id=s, **{"conditions__context_size": s})
                                    for s in ("short", "long", "any", "unspecified")])
    assert ids(reg, "claude", "5", "long") == ["any", "long", "unspecified"]
    assert ids(reg, "claude", "5", "short") == ["any", "short", "unspecified"]
    rows = dict((c.id, conds) for c, conds in applicable(reg, "claude", "5"))
    assert rows == {"any": [], "long": ["context_size=long"],
                    "short": ["context_size=short"], "unspecified": []}


def test_open_conditions_listed(tmp_path):
    reg = make_registry(tmp_path, claim(**{"conditions__task_family": ["agentic-coding"],
                                           "conditions__reasoning": "enabled",
                                           "conditions__tool_use": "required"}))
    [(_, conds)] = applicable(reg, "claude", "5", "long")
    assert conds == ["task_family=agentic-coding", "reasoning=enabled", "tool_use=required"]


def test_superseded_and_withdrawn_claims_excluded(tmp_path):
    reg = make_registry(tmp_path, claim(), claim(id="beta", status="superseded"),
                        claim(id="gamma", status="withdrawn"))
    assert ids(reg, "claude", "5") == ["alpha"]


@pytest.mark.parametrize("model, version, message", [
    ("claude-sonet", "5.5", "unknown model family 'claude-sonet'"),
    ("claude-sonnet", "4.8", "version '4.8' not listed for 'claude-sonnet'"),
])
def test_unknown_model_or_version_is_an_error(tmp_path, capsys, model, version, message):
    make_registry(tmp_path, claim())
    code = main(["--root", str(tmp_path), "applies", "--model", model, "--version", version])
    assert code != 0
    assert message in capsys.readouterr().err


def test_real_registry_newest_claude_models():
    reg = registry.load(ROOT)
    for line in ("claude-sonnet", "claude-opus"):
        got = ids(reg, line, "5.5", "long")
        assert "long-context-query-at-end" in got
        assert "prefill-unsupported-claude-4-6-plus" in got
        assert "self-check-instruction-over-verifies-opus-5" not in got
        assert "aggressive-tool-language-overtriggers" not in got
    assert "self-check-instruction-over-verifies-opus-5" in ids(reg, "claude-opus", "5")


def test_stale_claims_are_marked(tmp_path):
    reg = make_registry(tmp_path, claim(), claim(id="beta", review_by=dt.date(2026, 11, 1)))

    def marks(today):
        return {c.id: conds for c, conds in applicable(reg, "claude", "5.1", today=today)}

    assert marks(dt.date(2026, 10, 27)) == {"alpha": [], "beta": []}
    assert marks(dt.date(2027, 1, 1)) == {"alpha": [], "beta": ["stale"]}
    assert marks(dt.date(2030, 1, 1)) == {"alpha": ["stale"], "beta": ["stale"]}
