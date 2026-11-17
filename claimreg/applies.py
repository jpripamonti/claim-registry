"""Which claims apply to a given model, version, input size and task family."""
from .registry import is_stale
from .versions import expand, versions_for

FOLLOWED_STATUSES = {"active"}      # superseded and withdrawn claims are no longer followed
CONTEXT_SIZES = ("short", "long")
REASONING = ("enabled", "disabled")
TOOL_USE = ("required", "none")   # tools are in use / the prompt gives the model no tools
_OPEN = ("any", "unspecified")      # condition values that rule nothing out


def check_model(reg, family, version):
    """Raise ValueError unless `version` is listed for `family` in the vocabulary."""
    if family not in reg.families:
        raise ValueError(f"unknown model family {family!r}; known: {', '.join(reg.families)}")
    known = (reg.families[family] or {}).get("versions")
    if known is not None and version not in known:
        raise ValueError(f"version {version!r} not listed for {family!r}; "
                         f"known: {', '.join(known)}")


def check_task_families(reg, tasks):
    """Raise ValueError unless each of `tasks` is a concrete task family in the vocabulary."""
    bad = [t for t in tasks if t not in reg.task_families or t in _OPEN]
    if bad:
        known = sorted(t for t in reg.task_families if t not in _OPEN)
        raise ValueError(f"unknown task family {', '.join(map(repr, bad))}; "
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


def _task_matches(conditions, tasks):
    """True when the claim's task_family is open or includes one of `tasks`."""
    return bool(set(conditions.get("task_family") or []) & {*_OPEN, *tasks})


def open_conditions(conditions, family, reg, context_size=None, task_families=None,
                    reasoning=None, tool_use=None):
    """Conditions the user still has to check, as short 'name=value' strings.

    A condition the user has stated (context size, task family, reasoning, tool use) is not
    listed."""
    out = []
    if context_size is None and conditions.get("context_size") not in _OPEN:
        out.append(f"context_size={conditions.get('context_size')}")
    tasks = [t for t in conditions.get("task_family") or [] if t not in _OPEN]
    if tasks and not task_families:
        out.append(f"task_family={','.join(tasks)}")
    for f, given in (("reasoning", reasoning), ("tool_use", tool_use)):
        if given is None and conditions.get(f) not in _OPEN:
            out.append(f"{f}={conditions.get(f)}")
    covering = {family, (reg.families.get(family) or {}).get("parent")}
    if any(versions_for(f, conditions) == "unspecified"
           for f in conditions.get("model_family") or [] if f in covering):
        out.append("versions=unspecified")
    return out


def applicable(reg, family, version, context_size=None, task_families=None, *,
               reasoning=None, tool_use=None, today=None):
    """Return [(claim, open_conditions)] for followed claims matching the model, sorted by id.

    With `task_families`, only claims whose task_family is open or includes one of them are
    kept. A claim past its review_by date on `today` (default: current date) gets "stale" as
    its last open condition. With `reasoning` or `tool_use`, claims whose condition is a
    different concrete value are dropped, like `context_size`."""
    check_model(reg, family, version)
    check_task_families(reg, task_families or [])
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
        if any(given and cond.get(f) not in (*_OPEN, given)
               for f, given in (("reasoning", reasoning), ("tool_use", tool_use))):
            continue
        if task_families and not _task_matches(cond, task_families):
            continue
        conds = open_conditions(cond, family, reg, context_size, task_families, reasoning, tool_use)
        if is_stale(claim, today):
            conds.append("stale")
        result.append((claim, conds))
    return result
