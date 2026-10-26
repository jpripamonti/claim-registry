"""Model version values in claim conditions: `any`, `unspecified`, a range or a list."""
import re

RANGE_RE = re.compile(r"^(>=|<=|>|<)?(.+)$")
_OPS = {">=": lambda i, j: i >= j, "<=": lambda i, j: i <= j,
        ">": lambda i, j: i > j, "<": lambda i, j: i < j, None: lambda i, j: i == j}


def versions_for(family, conditions):
    """The model_versions value that applies to `family` (handles the map form)."""
    mv = conditions.get("model_versions")
    return mv.get(family) if isinstance(mv, dict) else mv


def expand(value, known):
    """Versions in the ordered list `known` that `value` covers.

    Raises ValueError for list items not in `known` (one message per item, joined by "; ")
    or for an invalid range.
    """
    if value in ("any", "unspecified"):
        return list(known)
    if isinstance(value, list):
        bad = [v for v in value if str(v) not in known]
        if bad:
            raise ValueError("; ".join(f"version {v!r} not listed" for v in bad))
        return [str(v) for v in value]
    m = RANGE_RE.match(str(value))
    if not m or m.group(2) not in known:
        raise ValueError(f"model_versions {value!r} is not a valid range")
    pivot = known.index(m.group(2))
    return [v for i, v in enumerate(known) if _OPS[m.group(1)](i, pivot)]
