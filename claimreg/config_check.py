"""Check the claims a config cites, and its claims.lock (docs/claim-format.md, "Citing claims")."""
import datetime as dt
import re
import subprocess

import yaml

from .registry import is_stale

CITE_RE = re.compile(r"<!--\s*claim:\s*([a-z0-9]+(?:-[a-z0-9]+)*)@(\d+)\s*-->")
TAG_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
UNTAGGED_NOTE = "# The registry has no date tag yet; registry is the date this lock was written."


def parse_citations(text):
    """Return [(line number, claim id, pinned major)] in file order."""
    return [(n, m.group(1), int(m.group(2)))
            for n, line in enumerate(text.splitlines(), 1) for m in CITE_RE.finditer(line)]


def _version(v):
    return tuple(int(x) for x in str(v).split("."))


def history_since(claim, newer_than):
    """History lines (newest first) whose version is above the tuple `newer_than`."""
    out = []
    for line in claim.data.get("history") or []:
        try:
            v = _version(str(line).split()[0])
        except (ValueError, IndexError):
            continue
        if v > newer_than:
            out.append(str(line))
    return out


def contradicted_by(reg, cid):
    """Ids of active claims that list `cid` in relations.contradicts."""
    return [other.id for other in reg.claims.values()
            if other.data.get("status") == "active"
            and cid in ((other.data.get("relations") or {}).get("contradicts") or [])]


def check_citation(reg, cid, major, today=None):
    """Return (findings, details, problem).

    findings: short strings for the citation's line ("ok" when nothing else applies);
    details: history lines to show under it; problem: True if it should fail the check."""
    claim = reg.claims.get(cid)
    if claim is None:
        return ["unknown"], [], True
    findings, details, problem = [], [], False
    d = claim.data
    current = str(d.get("version"))
    if _version(current)[0] != major:
        findings.append(f"major mismatch: pinned @{major}, now {current}")
        details = history_since(claim, (major, float("inf"), float("inf")))
        problem = True
    status = d.get("status")
    if status == "withdrawn":
        findings.append("withdrawn")
        problem = True
    elif status == "superseded":
        findings.append(f"superseded by {(d.get('relations') or {}).get('superseded_by')}")
        problem = True
    if is_stale(claim, today):
        findings.append(f"stale since {d.get('review_by')}")
    findings += [f"contradicted by {other}" for other in contradicted_by(reg, cid)]
    return findings or ["ok"], details, problem


def registry_date(root):
    """(date string, tagged): the newest YYYY-MM-DD git tag, else today's date."""
    try:
        out = subprocess.run(["git", "-C", str(root), "tag", "--list"],
                             capture_output=True, text=True, check=True).stdout
    except (OSError, subprocess.CalledProcessError):
        out = ""
    tags = sorted(t for t in out.split() if TAG_RE.match(t))
    if tags:
        return tags[-1], True
    return dt.date.today().isoformat(), False


def lock_text(date, versions, tagged=True):
    """The claims.lock content for {id: version}, ids sorted."""
    lines = [] if tagged else [UNTAGGED_NOTE]
    lines += [f"registry: {date}", "claims:" if versions else "claims: {}"]
    lines += [f"  {cid}: {versions[cid]}" for cid in sorted(versions)]
    return "\n".join(lines) + "\n"


def compare_lock(reg, lock, cited):
    """Compare a parsed lock with the cited claim ids.

    Yields (line, details, problem) for each difference."""
    locked = {k: str(v) for k, v in ((lock or {}).get("claims") or {}).items()}
    known = [cid for cid in dict.fromkeys(cited) if cid in reg.claims]
    for cid in known:
        claim = reg.claims[cid]
        current = str(claim.data.get("version"))
        if cid not in locked:
            yield f"not in lock {cid} (now {current})", [], False
        elif locked[cid] != current:
            old = _version(locked[cid])
            yield (f"changed {cid} {locked[cid]} -> {current}", history_since(claim, old),
                   _version(current)[0] != old[0])
    for cid in sorted(set(locked) - set(cited)):
        yield f"no longer cited {cid} (locked at {locked[cid]})", [], False
