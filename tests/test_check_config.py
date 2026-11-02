import datetime as dt

import yaml

from claimreg.__main__ import main
from claimreg.config_check import check_citation, parse_citations

from test_validate import claim, make_registry


def run(tmp_path, capsys, text, *extra):
    cfg = tmp_path / "cfg"
    cfg.mkdir(exist_ok=True)
    (cfg / "CLAUDE.md").write_text(text)
    code = main(["--root", str(tmp_path), "check-config", str(cfg / "CLAUDE.md"), *extra])
    return code, capsys.readouterr().out


def test_parse_citations_several_per_file_and_repeats():
    text = "a <!-- claim: alpha@1 -->\nb\nc <!--claim: beta@2--> <!-- claim: alpha@1 -->\n"
    assert parse_citations(text) == [(1, "alpha", 1), (3, "beta", 2), (3, "alpha", 1)]


def test_ok_is_silent_unless_verbose(tmp_path, capsys):
    make_registry(tmp_path, claim())
    code, out = run(tmp_path, capsys, "x <!-- claim: alpha@1 -->\n")
    assert code == 0 and "alpha@1" not in out
    code, out = run(tmp_path, capsys, "x <!-- claim: alpha@1 -->\n", "-v")
    assert code == 0 and "CLAUDE.md:1: alpha@1  ok" in out


def test_unknown_claim_is_a_problem(tmp_path, capsys):
    make_registry(tmp_path, claim())
    code, out = run(tmp_path, capsys, "\n<!-- claim: nope@1 -->\n")
    assert code == 1 and "CLAUDE.md:2: nope@1  unknown" in out


def test_major_mismatch_shows_history(tmp_path, capsys):
    make_registry(tmp_path, claim(version="3.0.0", history=[
        "3.0.0 2026-12-01 direction now no_effect", "2.1.0 2026-11-15 new evidence",
        "2.0.0 2026-11-10 conditions narrowed", "1.0.0 2026-10-25 created"]))
    code, out = run(tmp_path, capsys, "<!-- claim: alpha@2 -->\n")
    assert code == 1
    assert "alpha@2  major mismatch: pinned @2, now 3.0.0" in out
    assert "    3.0.0 2026-12-01 direction now no_effect" in out
    assert "2.1.0" not in out and "1.0.0 2026" not in out


def test_superseded_and_withdrawn(tmp_path, capsys):
    make_registry(tmp_path, claim(status="superseded", **{"relations__superseded_by": "beta"}),
                  claim(id="beta"), claim(id="gamma", status="withdrawn"))
    code, out = run(tmp_path, capsys, "<!-- claim: alpha@1 -->\n<!-- claim: gamma@1 -->\n")
    assert code == 1
    assert "alpha@1  superseded by beta" in out
    assert "gamma@1  withdrawn" in out


def test_stale_is_a_warning_only(tmp_path, capsys):
    make_registry(tmp_path, claim(review_by=dt.date(2020, 1, 1)))
    code, out = run(tmp_path, capsys, "<!-- claim: alpha@1 -->\n")
    assert code == 0 and "alpha@1  stale since 2020-01-01" in out


def test_stale_depends_on_today(tmp_path):
    reg = make_registry(tmp_path, claim())
    assert check_citation(reg, "alpha", 1, today=dt.date(2026, 11, 1))[0] == ["ok"]
    assert check_citation(reg, "alpha", 1, today=dt.date(2028, 1, 1))[0] == \
        ["stale since 2027-04-25"]


def test_contradicting_claim_is_named(tmp_path, capsys):
    make_registry(tmp_path, claim(**{"relations__contradicts": ["beta"]}),
                  claim(id="beta", **{"relations__contradicts": ["alpha"]}),
                  claim(id="gamma", status="withdrawn", **{"relations__contradicts": ["alpha"]}))
    code, out = run(tmp_path, capsys, "<!-- claim: alpha@1 -->\n")
    assert code == 0
    assert "alpha@1  contradicted by beta" in out and "gamma" not in out


def test_write_lock(tmp_path, capsys):
    make_registry(tmp_path, claim(version="1.2.0"), claim(id="beta"))
    code, out = run(tmp_path, capsys, "<!-- claim: alpha@1 -->\n<!-- claim: beta@1 -->\n"
                                      "<!-- claim: alpha@1 --> <!-- claim: nope@1 -->\n",
                    "--write-lock")
    assert code == 1                    # the unknown citation, not the lock
    text = (tmp_path / "cfg/claims.lock").read_text()
    assert text.startswith("# The registry has no date tag yet")
    assert yaml.safe_load(text) == {"registry": dt.date.today(),
                                    "claims": {"alpha": "1.2.0", "beta": "1.0.0"}}


def test_lock_path_override(tmp_path, capsys):
    make_registry(tmp_path, claim())
    run(tmp_path, capsys, "<!-- claim: alpha@1 -->\n", "--write-lock",
        "--lock", str(tmp_path / "other.lock"))
    assert (tmp_path / "other.lock").exists() and not (tmp_path / "cfg/claims.lock").exists()


def _write_lock(tmp_path, claims):
    (tmp_path / "cfg").mkdir(exist_ok=True)
    (tmp_path / "cfg/claims.lock").write_text(
        yaml.safe_dump({"registry": "2026-10-25", "claims": claims}))


def test_lock_minor_change_is_informational(tmp_path, capsys):
    make_registry(tmp_path, claim(version="1.1.0", history=[
        "1.1.0 2026-11-01 new evidence", "1.0.0 2026-10-25 created"]), claim(id="beta"))
    _write_lock(tmp_path, {"alpha": "1.0.0", "old": "1.0.0"})
    code, out = run(tmp_path, capsys, "<!-- claim: alpha@1 -->\n<!-- claim: beta@1 -->\n")
    assert code == 0
    assert "changed alpha 1.0.0 -> 1.1.0\n    1.1.0 2026-11-01 new evidence\n" in out
    assert "1.0.0 2026-10-25 created" not in out
    assert "not in lock beta" in out
    assert "no longer cited old" in out


def test_lock_major_change_is_a_problem(tmp_path, capsys):
    make_registry(tmp_path, claim(version="2.0.0", history=[
        "2.0.0 2026-11-01 direction now hurts", "1.0.0 2026-10-25 created"]))
    _write_lock(tmp_path, {"alpha": "1.0.0"})
    code, out = run(tmp_path, capsys, "<!-- claim: alpha@2 -->\n")
    assert code == 1
    assert "changed alpha 1.0.0 -> 2.0.0\n    2.0.0 2026-11-01 direction now hurts\n" in out


def test_unchanged_lock_prints_nothing_extra(tmp_path, capsys):
    make_registry(tmp_path, claim())
    _write_lock(tmp_path, {"alpha": "1.0.0"})
    code, out = run(tmp_path, capsys, "<!-- claim: alpha@1 -->\n")
    assert code == 0 and out == "1 citations, 0 problems, 0 stale\n"
