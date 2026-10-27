"""Check every claim against the rules in docs/claim-format.md."""
import datetime as dt
import re

from .registry import is_stale
from .versions import expand

ID_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
SEMVER_RE = re.compile(r"^\d+\.\d+\.\d+$")

TOP_FIELDS = ["id", "version", "title", "status", "technique", "conditions", "effect",
              "evidence", "as_of", "review_by", "relations", "history"]
STATUSES = {"active", "superseded", "withdrawn"}
DIRECTIONS = {"helps", "hurts", "no_effect", "mixed"}
CONDITION_VALUES = {
    "reasoning": {"enabled", "disabled", "any", "unspecified"},
    "tool_use": {"required", "none", "any", "unspecified"},
    "context_size": {"short", "long", "any", "unspecified"},
}
EVIDENCE_FIELDS = {
    "asserted": ["source", "retrieved", "quote"],
    "observed": ["source", "retrieved", "reported_by", "config", "model", "outcome", "quote"],
    "measured": ["harness_run", "effect_size", "interval", "n"],
}
DISPUTE_STATUSES = {"open", "upheld", "rejected"}


def validate(reg):
    """Return a list of (path, message), empty when the registry is valid."""
    errors = list(reg.load_errors)
    for claim in reg.claims.values():
        errors += [(claim.path, m) for m in _check_claim(claim, reg)]
    return errors


def stale_claims(reg, today=None):
    """Return the claims past their review_by date, sorted by id (a warning, not an error)."""
    return [reg.claims[cid] for cid in sorted(reg.claims) if is_stale(reg.claims[cid], today)]


def _check_claim(claim, reg):
    d = claim.data
    for f in TOP_FIELDS:
        if f not in d:
            yield f"missing field {f!r}"
    cid = d.get("id")
    if cid is not None:
        if not isinstance(cid, str) or not ID_RE.match(cid):
            yield f"id {cid!r} is not kebab-case"
        elif cid != claim.path.stem:
            yield f"id {cid!r} does not match file name {claim.path.name!r}"
    if "version" in d and not SEMVER_RE.match(str(d["version"])):
        yield f"version {d['version']!r} is not MAJOR.MINOR.PATCH"
    if "status" in d and d["status"] not in STATUSES:
        yield f"status {d['status']!r} not one of {sorted(STATUSES)}"
    for f in ("as_of", "review_by"):
        if f in d and not isinstance(d[f], dt.date):
            yield f"{f} {d[f]!r} is not a date (YYYY-MM-DD)"
    if not (d.get("technique") or {}).get("summary"):
        yield "technique.summary is empty"
    yield from _check_conditions(d.get("conditions") or {}, reg)
    yield from _check_effect(d.get("effect") or {})
    evidence = d.get("evidence") or []
    if not evidence:
        yield "no evidence items"
    for n, ev in enumerate(evidence):
        yield from (f"evidence[{n}]: {m}" for m in _check_evidence(ev))
    yield from _check_relations(d.get("relations") or {}, cid, reg)
    yield from _check_disputes(d.get("disputes") or [], len(evidence))
    if not d.get("history"):
        yield "history is empty"


def _check_conditions(c, reg):
    for f in ("model_family", "model_versions", "task_family", *CONDITION_VALUES):
        if f not in c:
            yield f"conditions.{f} missing"
    fams = c.get("model_family") or []
    if not isinstance(fams, list) or not fams:
        yield "conditions.model_family must be a non-empty list"
        fams = []
    for fam in fams:
        if fam not in reg.families:
            yield f"model family {fam!r} not in vocab/model-families.yaml"
    mv = c.get("model_versions")
    if isinstance(mv, dict):
        if set(mv) != set(fams):
            yield "model_versions map keys must equal model_family"
        for fam, value in mv.items():
            yield from _check_versions(fam, value, reg)
    elif mv is not None:
        if len(fams) > 1 and mv not in ("any", "unspecified"):
            yield "several model families need a model_versions map"
        for fam in fams:
            yield from _check_versions(fam, mv, reg)
    tasks = c.get("task_family") or []
    if not isinstance(tasks, list) or not tasks:
        yield "conditions.task_family must be a non-empty list"
        tasks = []
    for t in tasks:
        if t not in reg.task_families:
            yield f"task family {t!r} not in vocab/task-families.yaml"
    for f, allowed in CONDITION_VALUES.items():
        if f in c and c[f] not in allowed:
            yield f"conditions.{f} {c[f]!r} not one of {sorted(allowed)}"


def _check_versions(fam, value, reg):
    known = (reg.families.get(fam) or {}).get("versions")
    if known is None:            # unknown family (reported elsewhere) or free-text family "other"
        return
    try:
        expand(value, known)
    except ValueError as e:
        for msg in str(e).split("; "):
            yield f"{msg} for {fam!r}"


def _check_effect(e):
    if e.get("direction") not in DIRECTIONS:
        yield f"effect.direction {e.get('direction')!r} not one of {sorted(DIRECTIONS)}"
    if not e.get("outcome"):
        yield "effect.outcome is empty"


def _check_evidence(ev):
    tier = ev.get("tier")
    if tier not in EVIDENCE_FIELDS:
        yield f"tier {tier!r} not one of {sorted(EVIDENCE_FIELDS)}"
        return
    for f in EVIDENCE_FIELDS[tier]:
        if ev.get(f) in (None, ""):
            yield f"{tier} evidence needs {f!r}"
    if "retrieved" in ev and not isinstance(ev["retrieved"], dt.date):
        yield f"retrieved {ev['retrieved']!r} is not a date"


def _check_relations(r, cid, reg):
    for other in r.get("contradicts") or []:
        target = reg.claims.get(other)
        if target is None:
            yield f"contradicts unknown claim {other!r}"
        elif cid not in ((target.data.get("relations") or {}).get("contradicts") or []):
            yield f"contradicts {other!r}, but {other!r} does not link back"
    for other in r.get("refines") or []:
        if other not in reg.claims:
            yield f"refines unknown claim {other!r}"
        elif other == cid:
            yield "claim refines itself"
    sup = r.get("superseded_by")
    if sup is not None and sup not in reg.claims:
        yield f"superseded_by unknown claim {sup!r}"


def _check_disputes(disputes, n_evidence):
    for n, dsp in enumerate(disputes):
        if not dsp.get("issue"):
            yield f"disputes[{n}]: missing issue link"
        if dsp.get("status") not in DISPUTE_STATUSES:
            yield f"disputes[{n}]: status {dsp.get('status')!r} not one of {sorted(DISPUTE_STATUSES)}"
        target = dsp.get("evidence")
        if target != "claim" and not (isinstance(target, int) and 0 <= target < n_evidence):
            yield f"disputes[{n}]: evidence must be an evidence index or 'claim'"
