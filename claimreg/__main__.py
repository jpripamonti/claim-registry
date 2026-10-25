"""claimreg command line: `python3 -m claimreg <command>`."""
import argparse
import sys
from pathlib import Path

from . import registry
from .quotes import check_quotes
from .validate import validate


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
    print(f"{len(reg.claims)} claims, {len(errors)} errors")
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
    args = p.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
