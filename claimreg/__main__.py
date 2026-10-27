"""claimreg command line: `python3 -m claimreg <command>`."""
import argparse
import sys
from pathlib import Path

from . import registry
from .applies import CONTEXT_SIZES, applicable
from .quotes import check_quotes
from .validate import stale_claims, validate


def _rel(path, root):
    try:
        return Path(path).relative_to(root)
    except ValueError:
        return path


def cmd_validate(args):
    reg = registry.load(args.root)
    errors = validate(reg)
    for path, msg in errors:
        print(f"{_rel(path, reg.root)}: {msg}")
    stale = stale_claims(reg)
    for claim in stale:
        print(f"{_rel(claim.path, reg.root)}: stale since {claim.data['review_by']}")
    print(f"{len(reg.claims)} claims, {len(errors)} errors, {len(stale)} stale")
    return 1 if errors else 0


def cmd_check_quotes(args):
    reg = registry.load(args.root)
    bad = 0
    for claim, n, url, status in check_quotes(reg, ids=set(args.ids) or None):
        if status != "ok":
            bad += 1
        if status != "ok" or args.verbose:
            print(f"{status.upper() if status in ('ok', 'missing') else status}  "
                  f"{claim.id} evidence[{n}]  {url}")
    print(f"{bad} quotes not found")
    return 1 if bad else 0


def cmd_applies(args):
    reg = registry.load(args.root)
    try:
        rows = applicable(reg, args.model, args.version, args.context_size)
    except ValueError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    width = max((len(c.id) for c, _ in rows), default=0)
    for claim, conds in rows:
        direction = (claim.data.get("effect") or {}).get("direction")
        line = f"{claim.id:<{width}}  {direction:<9}  {' '.join(conds)}"
        print(line.rstrip())
    size = f", {args.context_size} context" if args.context_size else ""
    print(f"{len(rows)} claims apply to {args.model} {args.version}{size}")
    return 0


def main(argv=None):
    p = argparse.ArgumentParser(prog="claimreg", description="Claim registry tools.")
    p.add_argument("--root", default=".", help="registry checkout (default: current directory)")
    sub = p.add_subparsers(dest="command", required=True)
    sub.add_parser("validate", help="check every claim against docs/claim-format.md") \
        .set_defaults(func=cmd_validate)
    q = sub.add_parser("check-quotes", help="fetch each source and confirm its quote is on the page")
    q.add_argument("ids", nargs="*", help="only these claim ids (default: all)")
    q.add_argument("-v", "--verbose", action="store_true", help="also list quotes that were found")
    q.set_defaults(func=cmd_check_quotes)
    a = sub.add_parser("applies", help="list the active claims that apply to a model and version")
    a.add_argument("--model", required=True, help="family or line, e.g. claude-sonnet")
    a.add_argument("--version", required=True, help="a version listed for it, e.g. 5.5")
    a.add_argument("--context-size", choices=CONTEXT_SIZES,
                   help="drop claims for the other input size (default: keep all, show the condition)")
    a.set_defaults(func=cmd_applies)
    args = p.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
