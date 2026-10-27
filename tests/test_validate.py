import copy
import datetime as dt
from pathlib import Path

import pytest
import yaml

from claimreg import registry
from claimreg.__main__ import main
from claimreg.validate import stale_claims, validate

ROOT = Path(__file__).resolve().parent.parent

BASE = {
    "id": "alpha",
    "version": "1.0.0",
    "title": "Alpha",
    "status": "active",
    "technique": {"summary": "Do the thing."},
    "conditions": {
        "model_family": ["claude"], "model_versions": ">=4.5", "task_family": ["unspecified"],
        "reasoning": "unspecified", "tool_use": "unspecified", "context_size": "unspecified",
    },
    "effect": {"direction": "helps", "outcome": "quality", "magnitude": None},
    "evidence": [{"tier": "asserted", "source": "https://example.com", "retrieved": "2026-10-25",
                  "quote": "It helps."}],
    "as_of": "2026-10-25",
    "review_by": "2027-04-25",
    "relations": {"contradicts": [], "refines": [], "superseded_by": None},
    "history": ["1.0.0 2026-10-25 created"],
}


def make_registry(tmp_path, *claims):
    (tmp_path / "vocab").mkdir()
    (tmp_path / "vocab/model-families.yaml").write_text(
        (ROOT / "vocab/model-families.yaml").read_text())
    (tmp_path / "vocab/task-families.yaml").write_text(
        (ROOT / "vocab/task-families.yaml").read_text())
    (tmp_path / "claims/t").mkdir(parents=True)
    for c in claims:
        text = yaml.safe_dump(c, sort_keys=False)
        # dates as real YAML dates, the way claim files write them
        for f in ("as_of", "review_by", "retrieved"):
            text = text.replace(f"{f}: '2026-10-25'", f"{f}: 2026-10-25") \
                       .replace(f"{f}: '2027-04-25'", f"{f}: 2027-04-25")
        (tmp_path / f"claims/t/{c['id']}.yaml").write_text(text)
    return registry.load(tmp_path)


def claim(**changes):
    c = copy.deepcopy(BASE)
    for dotted, value in changes.items():
        *path, last = dotted.split("__")
        target = c
        for key in path:
            target = target[key]
        target[last] = value
    return c


def messages(reg):
    return [m for _, m in validate(reg)]


def test_real_registry_is_valid():
    reg = registry.load(ROOT)
    assert len(reg.claims) >= 30
    assert validate(reg) == []


def test_base_claim_is_valid(tmp_path):
    assert messages(make_registry(tmp_path, claim())) == []


@pytest.mark.parametrize("changes, expected", [
    ({"conditions__model_family": ["claude-opsu"]}, "model family 'claude-opsu' not in"),
    ({"conditions__model_versions": ">=9.9"}, "not a valid range for 'claude'"),
    ({"conditions__model_family": ["claude-sonnet"], "conditions__model_versions": ["4.8"]},
     "version '4.8' not listed for 'claude-sonnet'"),
    ({"conditions__task_family": ["vibes"]}, "task family 'vibes' not in"),
    ({"conditions__reasoning": "maybe"}, "conditions.reasoning 'maybe'"),
    ({"conditions__model_family": ["claude", "gpt"]}, "several model families need a model_versions map"),
    ({"conditions__model_family": ["claude", "gpt"], "conditions__model_versions": {"claude": "any"}},
     "map keys must equal model_family"),
    ({"effect__direction": "great"}, "effect.direction 'great'"),
    ({"status": "deprecated"}, "status 'deprecated'"),
    ({"version": "1.0"}, "not MAJOR.MINOR.PATCH"),
    ({"evidence": []}, "no evidence items"),
    ({"relations__refines": ["ghost"]}, "refines unknown claim 'ghost'"),
    ({"relations__superseded_by": "ghost"}, "superseded_by unknown claim 'ghost'"),
    ({"disputes": [{"issue": "https://x", "evidence": 3, "status": "open"}]},
     "evidence must be an evidence index or 'claim'"),
    ({"disputes": [{"issue": "https://x", "evidence": 0, "status": "pending"}]}, "status 'pending'"),
])
def test_rule_violations_are_reported(tmp_path, changes, expected):
    msgs = messages(make_registry(tmp_path, claim(**changes)))
    assert any(expected in m for m in msgs), msgs


def test_map_form_versions_accepted(tmp_path):
    c = claim(**{"conditions__model_family": ["claude-opus", "gpt", "other"],
                 "conditions__model_versions": {"claude-opus": ["4.5"], "gpt": ">=5",
                                                "other": ["Some-Model-7B"]}})
    assert messages(make_registry(tmp_path, c)) == []


def test_asserted_evidence_needs_quote(tmp_path):
    c = claim()
    del c["evidence"][0]["quote"]
    assert "evidence[0]: asserted evidence needs 'quote'" in messages(make_registry(tmp_path, c))


def test_observed_evidence_needs_config(tmp_path):
    c = claim()
    c["evidence"][0].update(tier="observed", reported_by="A", model="m", outcome="o")
    assert "evidence[0]: observed evidence needs 'config'" in messages(make_registry(tmp_path, c))


def test_contradicts_must_link_back(tmp_path):
    a = claim(**{"relations__contradicts": ["beta"]})
    b = claim(id="beta")
    msgs = messages(make_registry(tmp_path, a, b))
    assert "contradicts 'beta', but 'beta' does not link back" in msgs


def test_id_must_match_file_name(tmp_path):
    reg = make_registry(tmp_path, claim())
    (tmp_path / "claims/t/alpha.yaml").rename(tmp_path / "claims/t/other.yaml")
    reg = registry.load(tmp_path)
    assert any("does not match file name" in m for m in messages(reg))


def test_invalid_yaml_is_reported(tmp_path):
    make_registry(tmp_path, claim())
    (tmp_path / "claims/t/broken.yaml").write_text("id: [unclosed\n")
    assert any(m.startswith("invalid YAML") for m in messages(registry.load(tmp_path)))


def test_stale_claims_use_the_injected_date(tmp_path):
    reg = make_registry(tmp_path, claim(), claim(id="beta", review_by=dt.date(2026, 11, 1)))
    assert [c.id for c in stale_claims(reg, dt.date(2026, 10, 27))] == []
    assert [c.id for c in stale_claims(reg, dt.date(2027, 1, 1))] == ["beta"]
    assert [c.id for c in stale_claims(reg, dt.date(2027, 4, 25))] == ["beta"]   # review_by day itself is fresh
    assert [c.id for c in stale_claims(reg, dt.date(2030, 1, 1))] == ["alpha", "beta"]
    assert validate(reg) == []                      # stale is a warning, not an error


def test_validate_command_warns_about_stale_without_failing(tmp_path, capsys):
    make_registry(tmp_path, claim(review_by=dt.date(2020, 1, 1)))
    assert main(["--root", str(tmp_path), "validate"]) == 0
    out = capsys.readouterr().out
    assert "claims/t/alpha.yaml: stale since 2020-01-01" in out
    assert "1 claims, 0 errors, 1 stale" in out
