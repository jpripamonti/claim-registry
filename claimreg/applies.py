"""Which claims apply to a given model, version and input size."""
from .versions import expand, versions_for

FOLLOWED_STATUSES = {"active"}      # superseded and withdrawn claims are no longer followed
CONTEXT_SIZES = ("short", "long")
_OPEN = ("any", "unspecified")      # condition values that rule nothing out


def check_model(reg, family, version):
    """Raise ValueError unless `version` is listed for `family` in the vocabulary."""
    if family not in reg.families:
        raise ValueError(f"unknown model family {family!r}; known: {', '.join(reg.families)}")
    known = (reg.families[family] or {}).get("versions")
    if known is not None and version not in known:
        raise ValueError(f"version {version!r} not listed for {family!r}; "
                         f"known: {', '.join(known)}")


def _model_matches(conditions, family, version, reg):
    """True when one of the claim's families is `family` or its parent and covers `version`."""
    covering = {family, (reg.families.get(family) or {}).get("parent")}
    for fam in conditions.get("model_family") or []:
        if fam not in covering:
            continue
        value = versions_for(fam, conditions)
        known = (reg.families.get(fam) or {}).get("versions")
        if known is None:                       # free-text family "other"
            if value in _OPEN or version in (value if isinstance(value, list) else [value]):
                return True
            continue
        try:
            if version in expand(value, known):
                return True
        except ValueError:                      # invalid value; `validate` reports it
            continue
    return False


def open_conditions(conditions, family, reg, context_size=None):
    """Conditions the user still has to check, as short 'name=value' strings."""
    out = []
    if context_size is None and conditions.get("context_size") not in _OPEN:
        out.append(f"context_size={conditions.get('context_size')}")
    tasks = [t for t in conditions.get("task_family") or [] if t not in _OPEN]
    if tasks:
        out.append(f"task_family={','.join(tasks)}")
    for f in ("reasoning", "tool_use"):
        if conditions.get(f) not in _OPEN:
            out.append(f"{f}={conditions.get(f)}")
    covering = {family, (reg.families.get(family) or {}).get("parent")}
    if any(versions_for(f, conditions) == "unspecified"
           for f in conditions.get("model_family") or [] if f in covering):
        out.append("versions=unspecified")
    return out


def applicable(reg, family, version, context_size=None):
    """Return [(claim, open_conditions)] for followed claims matching the model, sorted by id."""
    check_model(reg, family, version)
    result = []
    for cid in sorted(reg.claims):
        claim = reg.claims[cid]
        d = claim.data
        if d.get("status") not in FOLLOWED_STATUSES:
            continue
        cond = d.get("conditions") or {}
        if not _model_matches(cond, family, version, reg):
            continue
        if context_size and cond.get("context_size") not in (*_OPEN, context_size):
            continue
        result.append((claim, open_conditions(cond, family, reg, context_size)))
    return result
